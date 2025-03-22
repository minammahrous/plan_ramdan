import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Importing database connection function

# Shift durations in hours
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 15}

# Initialize session state for progress tracking
if "batch_progress" not in st.session_state:
    st.session_state.batch_progress = {}

# Load Machines
def load_machines():
    conn = get_db_connection()
    query = "SELECT name FROM machines ORDER BY name"
    machines = pd.read_sql(query, conn)
    conn.close()
    return machines["name"].tolist()

# Load Unscheduled Batches with Progress
def load_unscheduled_batches():
    conn = get_db_connection()
    query = """
    SELECT id, product, batch_number, machine, time, progress 
    FROM production_plan 
    WHERE schedule = FALSE
    """
    batches = pd.read_sql(query, conn)
    conn.close()

    # Apply progress updates from session state
    for idx, row in batches.iterrows():
        batch_id = row["id"]
        if batch_id in st.session_state.batch_progress:
            row["progress"] = st.session_state.batch_progress[batch_id]

    # Calculate remaining progress
    batches["remaining_progress"] = 100 - batches["progress"]
    
    # Update display name to include remaining progress
    batches["display_name"] = batches["product"] + " - " + batches["batch_number"] + f" (Remaining: {batches['remaining_progress']}%)"
    
    # Only return batches that still have progress remaining
    return batches[batches["remaining_progress"] > 0]

# UI
st.title("Machine Scheduling")

# Select Date Range
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.today())
with col2:
    end_date = st.date_input("End Date", datetime.today() + timedelta(days=7))

date_range = pd.date_range(start=start_date, end=end_date)

if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
    st.session_state.schedule_data = {}
    st.session_state.downtime_data = {}

def schedule_machine(machine_id):
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")
    
    batches = load_unscheduled_batches()
    machine_batches = batches[batches["machine"] == selected_machine]

    # Remove fully scheduled batches before displaying
    machine_batches = machine_batches[machine_batches["remaining_progress"] > 0]
    
    if not machine_batches.empty:
        st.write(f"### Schedule for {selected_machine}")
        schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization", "Downtime"], columns=date_range.strftime("%Y-%m-%d"))
        
        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

                # Get list of batches with updated remaining progress
                available_batches = machine_batches["display_name"].tolist()
                batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", available_batches, key=f"batch_{date}_{machine_id}")
                
                percent_selection = []
                for batch in batch_selection:
                    batch_data = machine_batches[machine_batches["display_name"] == batch].iloc[0]
                    batch_id = batch_data["id"]
                    remaining_progress = int(batch_data["remaining_progress"])

                    # Set default % Done to remaining progress but ensure it's not negative
                    percent_done = st.number_input(
                        f"% of {batch} ({date.strftime('%Y-%m-%d')})", 
                        min_value=0, 
                        max_value=remaining_progress, 
                        step=10, 
                        value=min(remaining_progress, 100),  # Default to remaining progress, max 100%
                        key=f"percent_{batch}_{date}_{machine_id}"
                    )
                    percent_selection.append(percent_done)

                    # Ensure progress updates correctly in session state
                    if batch_id not in st.session_state.batch_progress:
                        st.session_state.batch_progress[batch_id] = 100 - remaining_progress  # Store actual progress
                    st.session_state.batch_progress[batch_id] += percent_done

                    # If batch is fully scheduled, remove it from available list
                    if st.session_state.batch_progress[batch_id] >= 100:
                        machine_batches = machine_batches[machine_batches["id"] != batch_id]
                
                total_utilization = sum((machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0] * percent / 100) for batch, percent in zip(batch_selection, percent_selection))
                utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0
                
                formatted_batches = "<br>".join([f"{batch} - <span style='color:green;'>{percent}%</span>" for batch, percent in zip(batch_selection, percent_selection)])
                schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = f"<b style='color:red;'>{shift}</b>"
                schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = formatted_batches
                schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = f"Util= {utilization_percentage:.2f}%"
                
        st.session_state.schedule_data[selected_machine] = schedule_df

# Initial Scheduling
for i in range(len(st.session_state.machines_scheduled) + 1):
    schedule_machine(i)

if st.button("Add Another Machine"):
    st.session_state.machines_scheduled.append(f"machine_{len(st.session_state.machines_scheduled) + 1}")

# Display All Scheduled Machines in a Single Table
if st.session_state.schedule_data:
    st.write("### Consolidated Schedule")
    consolidated_df = pd.DataFrame(columns=["Machine"] + date_range.strftime("%Y-%m-%d").tolist())
    
    for machine, df in st.session_state.schedule_data.items():
        row = {"Machine": machine}
        for date in date_range.strftime("%Y-%m-%d"):
            row[date] = f"{df.loc['Shift', date]}<br>{df.loc['Batch', date]}<br>{df.loc['Utilization', date]}<br>{df.loc['Downtime', date] if 'Downtime' in df.index else ''}"
        consolidated_df = pd.concat([consolidated_df, pd.DataFrame([row])], ignore_index=True)
    
    st.markdown(consolidated_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# Save Button
if st.button("Save Schedule"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for batch_id, new_progress in st.session_state.batch_progress.items():
        if new_progress >= 100:
            query = "UPDATE production_plan SET schedule = TRUE WHERE id = %s"
            cursor.execute(query, (batch_id,))
        else:
            query = "UPDATE production_plan SET progress = %s WHERE id = %s"
            cursor.execute(query, (new_progress, batch_id))
    
    conn.commit()
    conn.close()
    st.success("Schedule saved successfully!")
