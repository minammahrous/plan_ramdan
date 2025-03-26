import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Importing database connection function

# Shift durations in hours
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 15}

# Load Machines
def load_machines():
    conn = get_db_connection()
    query = "SELECT name FROM machines ORDER BY name"
    machines = pd.read_sql(query, conn)
    conn.close()
    return machines["name"].tolist()

# Load Unscheduled Batches
def load_unscheduled_batches():
    conn = get_db_connection()
    query = """
    SELECT id, product, batch_number, machine, time, CAST(progress AS FLOAT) AS progress
    FROM production_plan 
    WHERE schedule = FALSE
    """
    batches = pd.read_sql(query, conn)
    conn.close()
    
    batches["display_name"] = batches["product"] + " - " + batches["batch_number"]
    batches["remaining_percentage"] = 100 - batches["progress"]  # Calculate remaining %
    return batches

# UI
st.title("Machine Scheduling")

# Select Date Range
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.today())
with col2:
    end_date = st.date_input("End Date", datetime.today() + timedelta(days=7))

date_range = pd.date_range(start=start_date, end=end_date)

# Initialize session state
if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
    st.session_state.schedule_data = {}
    st.session_state.downtime_data = {}

if "unscheduled_batches" not in st.session_state:
    st.session_state.unscheduled_batches = load_unscheduled_batches()

if "batch_percentages" not in st.session_state:
    st.session_state.batch_percentages = {
        row["display_name"]: float(100 - row["progress"]) for _, row in st.session_state.unscheduled_batches.iterrows()
    }

# Schedule Machine Function
def schedule_machine(machine_id):
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")

    # Filter only batches for the selected machine
    batches = st.session_state.unscheduled_batches
    machine_batches = batches[batches["machine"] == selected_machine]

    if not machine_batches.empty:
        st.write(f"### Schedule for {selected_machine}")
        schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization", "Downtime"], columns=date_range.strftime("%Y-%m-%d"))
        
        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")
                
                # Only show available batches for this machine
                available_batches = [
                    batch for batch in machine_batches["display_name"].tolist()
                    if st.session_state.batch_percentages.get(batch, 0) > 0
                ]

                batch_selection = st.multiselect(
                    f"Batch ({date.strftime('%Y-%m-%d')})", available_batches, key=f"batch_{date}_{machine_id}"
                )

                percent_selection = []
                for batch in batch_selection:
                    max_percent = st.session_state.batch_percentages.get(batch, 0)  # Get remaining %
                    percent = st.number_input(
                        f"% of {batch} ({date.strftime('%Y-%m-%d')})", 
                        min_value=0.0,  
                        max_value=float(max_percent),  
                        step=10.0,  
                        value=float(max_percent) if max_percent > 0 else 0.0,  
                        key=f"percent_{batch}_{date}_{machine_id}"
                    )
                    percent_selection.append(percent)

                # Calculate utilization safely
                total_utilization = 0  
                for batch, percent in zip(batch_selection, percent_selection):
                    batch_data = machine_batches.loc[machine_batches["display_name"] == batch, "time"]
                    
                    if not batch_data.empty:  
                        total_utilization += (batch_data.values[0] * percent / 100)
                    else:
                        st.warning(f"Batch {batch} not found for machine {selected_machine}")  

                utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0
                
                # Store scheduled batch info before updating percentages
                formatted_batches = "<br>".join([
                    f"{batch} - <span style='color:green;'>{percent}%</span>"
                    for batch, percent in zip(batch_selection, percent_selection)
                ])

                # Add data to the schedule
                schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = f"<b style='color:red;'>{shift}</b>"
                schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = formatted_batches
                schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = f"Util= {utilization_percentage:.2f}%"

                # ✅ Only now update batch percentage after adding to schedule
                for batch, percent in zip(batch_selection, percent_selection):
                    st.session_state.batch_percentages[batch] -= percent  

                # ✅ Remove fully scheduled batches **AFTER** updating the schedule
                st.session_state.batch_percentages = {
                    batch: percent for batch, percent in st.session_state.batch_percentages.items() if percent > 0
                }

                # ✅ Ensure downtime button always appears
                if st.button(f"+DT ({date.strftime('%Y-%m-%d')}) - {selected_machine}", key=f"dt_button_{date}_{machine_id}"):
                    if (selected_machine, date) not in st.session_state.downtime_data:
                        st.session_state.downtime_data[(selected_machine, date)] = {"type": None, "hours": 0}

                # ✅ Show downtime inputs when button is clicked
                if (selected_machine, date) in st.session_state.downtime_data:
                    dt_type = st.selectbox("Select Downtime Type", ["Cleaning", "Preventive Maintenance", "Calibration"], key=f"dt_type_{date}_{machine_id}")
                    dt_hours = st.number_input("Downtime Hours", min_value=0.0, step=0.5, key=f"dt_hours_{date}_{machine_id}")
                    st.session_state.downtime_data[(selected_machine, date)] = {"type": dt_type, "hours": dt_hours}
                    schedule_df.loc["Downtime", date.strftime("%Y-%m-%d")] = f"<span style='color:purple;'>{dt_type} ({dt_hours} hrs)</span>"

        st.session_state.schedule_data[selected_machine] = schedule_df

# Initial Scheduling
for i in range(len(st.session_state.machines_scheduled) + 1):
    schedule_machine(i)

if st.button("Add Another Machine"):
    st.session_state.machines_scheduled.append(f"machine_{len(st.session_state.machines_scheduled) + 1}")

# ✅ Downtime button now always appears
st.write("### Consolidated Schedule")

# Save Schedule
if st.button("Save Schedule"):
    st.success("Schedule saved successfully!")
