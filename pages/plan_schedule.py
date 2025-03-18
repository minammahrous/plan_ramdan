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

# Fetch unscheduled batches (where schedule = FALSE)
cur.execute("SELECT product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE")
unscheduled_batches = cur.fetchall()

# ✅ Process all batches and group by machine
for product, batch_number, machine, time_needed in unscheduled_batches:
    if machine not in st.session_state["storage_frames"]:
        st.session_state["storage_frames"][machine] = []  # Initialize machine list

    # ✅ Prevent duplicate entries
    existing_batches = [b["batch_number"] for b in st.session_state["storage_frames"][machine]]
    if batch_number not in existing_batches:
        st.session_state["storage_frames"][machine].append({
            "product": product,
            "batch_number": batch_number,
            "time_needed": time_needed
        })

st.write("### 🏭 Available Batches for Scheduling")

if "clicked_batches" not in st.session_state:
    st.session_state["clicked_batches"] = set()  # Store added batch numbers

for machine, batches in st.session_state["storage_frames"].items():
    st.subheader(f"⚙️ {machine}")

    for batch in batches:
        batch_key = f"{machine}_{batch['batch_number']}"  # Unique batch key

        if batch_key in st.session_state["clicked_batches"]:
            continue  # Skip already added batches

        if st.button(f"➕ Add {batch['batch_number']} ({batch['product']})", key=batch_key):
            st.session_state["scheduled_batches"].append({
                "machine": machine,
                "product": batch["product"],
                "batch_number": batch["batch_number"],
                "time_needed": batch["time_needed"],
                "start": None,
                "end": None
            })

            # ✅ Remove batch from available list and update state
            st.session_state["storage_frames"][machine] = [
                b for b in batches if b["batch_number"] != batch["batch_number"]
            ]
            st.session_state["clicked_batches"].add(batch_key)

            st.rerun()  # Force rerun to update UI

# **User selects scheduling period**
start_date = st.date_input("📅 Select Start Date")
end_date = st.date_input("📅 Select End Date")
date_range = pd.date_range(start=start_date, end=end_date)

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
scheduled_data = []
for batch in st.session_state["scheduled_batches"]:
    for date in date_range:
        available_time = shift_selection.get(batch["machine"], {}).get(str(date.date()), 0)
        if available_time >= batch["time_needed"]:
            batch["start"] = date
            batch["end"] = date  # Adjust if needed for multi-day batches
            scheduled_data.append(batch)
            break

# ✅ Remove None values from scheduled_data before plotting
scheduled_data = [b for b in scheduled_data if b["start"] is not None and b["end"] is not None]

# **Display Scheduled Batches**
if scheduled_data:
    st.write("### 📊 Scheduled Production Plan")
    df = pd.DataFrame(scheduled_data)

    # ✅ Ensure DataFrame has data before plotting
    if not df.empty:
        fig = px.timeline(df, x_start="start", x_end="end", y="machine", color="product", text="batch_number")
        fig.update_layout(title="📆 Production Schedule", xaxis_title="Date", yaxis_title="Machine")
        st.plotly_chart(fig)
    else:
        st.warning("⚠️ No scheduled batches to display.")

# **Save Schedule to Database**
if st.button("✅ Save Schedule"):
    try:
        for batch in st.session_state["scheduled_batches"]:
            cur.execute("UPDATE production_plan SET schedule = TRUE WHERE batch_number = %s", (batch["batch_number"],))
        conn.commit()
        st.success("✅ Schedule saved successfully!")

        # ✅ Reset scheduled batches after saving
        st.session_state["scheduled_batches"] = []
        st.rerun()

    except Exception as e:
        st.error(f"❌ Error saving schedule: {e}")
    finally:
        cur.close()
        conn.close()
