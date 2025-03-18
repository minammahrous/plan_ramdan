import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
from auth import check_authentication
from db import get_branches, get_db_connection

# Ensure user is authenticated
check_authentication()

st.title("📅 Production Plan Scheduler")

# Load available branches
if "branches" not in st.session_state:
    st.session_state["branches"] = get_branches()

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in st.session_state["branches"]:
    st.session_state["branch"] = st.session_state["branches"][0]

# Branch selection dropdown
selected_branch = st.selectbox(
    "🔀 Select Database Branch:",
    st.session_state["branches"],
    index=st.session_state["branches"].index(st.session_state["branch"])
)

# Handle branch switch
if selected_branch != st.session_state["branch"]:
    st.session_state["branch"] = selected_branch
    st.session_state["scheduled_batches"] = []
    st.session_state["storage_frames"] = {}
    st.rerun()

st.sidebar.success(f"✅ Working on branch: **{st.session_state['branch']}**")

# Database connection
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()

# Shift types and available hours
shift_types = {
    "LD": 11,
    "NS": 22,
    "ELD": 15,
    "ND": 9,
    "OFF": 0
}

# Initialize session state variables
if "scheduled_batches" not in st.session_state:
    st.session_state["scheduled_batches"] = []
if "storage_frames" not in st.session_state:
    st.session_state["storage_frames"] = {}

# ✅ Reset storage_frames to avoid duplicates
st.session_state["storage_frames"] = {}

# Fetch unscheduled batches (where schedule = False)
cur.execute("SELECT product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE")
unscheduled_batches = cur.fetchall()

# ✅ Ensure each machine only has unique batches
for product, batch_number, machine, time_needed in unscheduled_batches:
    if machine not in st.session_state["storage_frames"]:
        st.session_state["storage_frames"][machine] = []

    # ✅ Prevent duplicate entries
    if not any(b["batch_number"] == batch_number for b in st.session_state["storage_frames"][machine]):
        st.session_state["storage_frames"][machine].append({
            "product": product,
            "batch_number": batch_number,
            "time_needed": time_needed
        })


# User selects scheduling period
start_date = st.date_input("📅 Select Start Date")
end_date = st.date_input("📅 Select End Date")

# Generate date range for scheduling
date_range = pd.date_range(start=start_date, end=end_date)

# **Display available batches & allow scheduling**
st.write("### 🏭 Available Batches for Scheduling")
for machine, batches in st.session_state["storage_frames"].items():
    st.subheader(f"⚙️ {machine}")
    for batch in batches:
        batch_number_str = str(batch["batch_number"]).replace(" ", "_")
        unique_key = f"add_{machine}_{batch_number_str}_{uuid.uuid4().hex}"  # Ensure unique key

        if st.button(f"➕ Add {batch['batch_number']} ({batch['product']})", key=unique_key):
    # Ensure batch is not already scheduled
            if not any(b["batch_number"] == batch["batch_number"] for b in st.session_state["scheduled_batches"]):
        # Add batch to scheduled list
                st.session_state["scheduled_batches"].append({
                    "machine": machine,
                    "product": batch["product"],
                    "batch_number": batch["batch_number"],
                    "time_needed": batch["time_needed"],
                    "start": None,
                    "end": None
                })

        # ✅ Ensure batch is removed from available storage
        st.session_state["storage_frames"][machine] = [
            b for b in st.session_state["storage_frames"][machine] if b["batch_number"] != batch["batch_number"]
        ]
        
        # ✅ Ensure rerun updates the UI properly
        st.rerun()

# **Shift Selection Table**
st.write("### 🕒 Shift Availability")
shift_selection = {}
for machine in st.session_state["storage_frames"].keys():
    shift_selection[machine] = {}
    cols = st.columns(len(date_range))
    for idx, date in enumerate(date_range):
        shift = cols[idx].selectbox(
            f"{machine} - {date.date()}",
            list(shift_types.keys()),
            key=f"shift_{machine}_{date}"
        )
        shift_selection[machine][str(date.date())] = shift_types[shift]

# **Assign batches to timeline**
data = []
scheduled_batches_set = set()  # Track already scheduled batches

for batch in st.session_state["scheduled_batches"]:
    batch_scheduled = False  # Track if the batch is already placed
    for date in date_range:
        available_time = shift_selection[batch["machine"]][str(date.date())]
        if available_time >= batch["time_needed"] and batch["batch_number"] not in scheduled_batches_set:
            batch["start"] = date
            batch["end"] = date
            data.append(batch)
            scheduled_batches_set.add(batch["batch_number"])  # Mark batch as scheduled
            batch_scheduled = True
            break  # Stop trying to schedule this batch further

    if not batch_scheduled:
        st.warning(f"⚠️ Batch {batch['batch_number']} ({batch['product']}) couldn't be scheduled!")

# **Display Debug Information**
st.write("### 🔍 Debugging Info")
st.write("#### Scheduled Data for Plotly")
st.dataframe(pd.DataFrame(data))  # Display raw data used for the Gantt chart

# **Display Scheduled Batches**
if data:
    st.write("### 📊 Scheduled Production Plan")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Ensure 'start' and 'end' are in datetime format
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])

    # Debugging messages
    st.write("#### DataFrame being passed to px.timeline:")
    st.dataframe(df)

    # Plot the timeline
    fig = px.timeline(df, x_start="start", x_end="end", y="machine", color="product", text="batch_number")
    fig.update_layout(title="📆 Production Schedule", xaxis_title="Date", yaxis_title="Machine")
    st.plotly_chart(fig)

else:
    st.warning("⚠️ No batches were scheduled. Try adjusting shifts or adding more batches.")

# **Save Schedule to Database**
if st.button("✅ Save Schedule"):
    try:
        for batch in st.session_state["scheduled_batches"]:
            cur.execute("UPDATE production_plan SET schedule = TRUE WHERE batch_number = %s", (batch["batch_number"],))
        conn.commit()
        st.success("✅ Schedule saved successfully!")
        st.session_state["scheduled_batches"] = []
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving schedule: {e}")
    finally:
        cur.close()
        conn.close()
