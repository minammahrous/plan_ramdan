import streamlit as st
import pandas as pd
import plotly.express as px
from auth import authenticate_user
from db import get_branches, get_db_connection

# Ensure user is authenticated
check_authentication()

st.title("Production Plan")

# Ensure branches are loaded
if "branches" not in st.session_state:
    st.session_state["branches"] = get_branches()

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in st.session_state["branches"]:
    st.session_state["branch"] = st.session_state["branches"][0]

# Branch selection
selected_branch = st.selectbox(
    "Select Database Branch:",
    st.session_state["branches"],
    index=st.session_state["branches"].index(st.session_state["branch"])
)

if selected_branch != st.session_state["branch"]:
    st.session_state["branch"] = selected_branch
    st.session_state["batch_entries"] = []  # Reset all batches when switching branches
    st.session_state["selected_product"] = None
    st.rerun()

st.sidebar.success(f"Working on branch: {st.session_state['branch']}")

# Connect to the selected branch
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()
# Define shift types and their available hours
shift_types = {
        "LD": 11,
        "NS": 22,
        "ELD": 15,
        "ND": 9,
        "OFF": 0
}
    
# Ensure session state variables exist
if "scheduled_batches" not in st.session_state:
        st.session_state["scheduled_batches"] = []
if "storage_frames" not in st.session_state:
        st.session_state["storage_frames"] = {}
    
    # Fetch unscheduled batches (schedule = False)
cur.execute("SELECT product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE")
unscheduled_batches = cur.fetchall()
    
    # Organize batches by machine
for batch in unscheduled_batches:
        product, batch_number, machine, time_needed = batch
        if machine not in st.session_state["storage_frames"]:
            st.session_state["storage_frames"][machine] = []
        st.session_state["storage_frames"][machine].append({
            "product": product,
            "batch_number": batch_number,
            "time_needed": time_needed
        })
    
    # User selects scheduling period
start_date = st.date_input("Select Start Date")
end_date = st.date_input("Select End Date")
    
    # Table layout: Machines as rows, Days as columns
machines = list(st.session_state["storage_frames"].keys())
date_range = pd.date_range(start=start_date, end=end_date)
    
data = []  # Data for Gantt chart
    
    # Display storage frames & shift selection
st.write("### Machine Storage Frames")
    for machine in machines:
        st.write(f"#### {machine}")
        for batch in st.session_state["storage_frames"][machine]:
            if st.button(f"Add {batch['batch_number']} ({batch['product']})", key=f"add_{machine}_{batch['batch_number']}"):
                st.session_state["scheduled_batches"].append({
                    "machine": machine,
                    "product": batch["product"],
                    "batch_number": batch["batch_number"],
                    "time_needed": batch["time_needed"],
                    "start": None,
                    "end": None
                })
                st.session_state["storage_frames"][machine].remove(batch)
                st.rerun()
    
    # Shift Selection Table
st.write("### Shift Availability")
    shift_selection = {}
    for machine in machines:
        shift_selection[machine] = {}
        cols = st.columns(len(date_range))
        for idx, date in enumerate(date_range):
            shift = cols[idx].selectbox(f"{machine} - {date.date()}", list(shift_types.keys()), key=f"shift_{machine}_{date}")
            shift_selection[machine][str(date.date())] = shift_types[shift]
    
    # Assign batches to timeline
for batch in st.session_state["scheduled_batches"]:
        for date in date_range:
            available_time = shift_selection[batch["machine"]][str(date.date())]
            if available_time >= batch["time_needed"]:
                batch["start"] = date
                batch["end"] = date
                data.append(batch)
                break
    
    # Gantt Chart
if data:
        df = pd.DataFrame(data)
        fig = px.timeline(df, x_start="start", x_end="end", y="machine", color="product", text="batch_number")
        fig.update_layout(title="Scheduled Batches", xaxis_title="Date", yaxis_title="Machine")
        st.plotly_chart(fig)
    
    # Save scheduled batches
if st.button("✅ Save Schedule"):
        for batch in st.session_state["scheduled_batches"]:
            cur.execute("UPDATE production_plan SET schedule = TRUE WHERE batch_number = %s", (batch["batch_number"],))
        conn.commit()
        st.success("✅ Schedule saved successfully!")
        st.session_state["scheduled_batches"] = []
        st.rerun()
    
cur.close()
conn.close()
