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
    query = "SELECT id, product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE"
    batches = pd.read_sql(query, conn)
    conn.close()
    batches["display_name"] = batches["product"] + " - " + batches["batch_number"]
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

if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
    st.session_state.schedule_data = {}

def schedule_machine(machine_id):
    # Select Machine
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")
    
    # Load Available Batches
    batches = load_unscheduled_batches()
    machine_batches = batches[batches["machine"] == selected_machine]
    
    if not machine_batches.empty:
        st.write(f"### Schedule for {selected_machine}")
        schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization"], columns=date_range.strftime("%Y-%m-%d"))
        
        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")
                
                available_batches = machine_batches["display_name"].tolist()
                batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", available_batches, key=f"batch_{date}_{machine_id}")
                
                percent_selection = []
                for batch in batch_selection:
                    percent = st.number_input(f"% of {batch} ({date.strftime('%Y-%m-%d')})", 0, 100, step=10, value=100, key=f"percent_{batch}_{date}_{machine_id}")
                    percent_selection.append(percent)
                
                total_utilization = sum((machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0] * percent / 100) for batch, percent in zip(batch_selection, percent_selection))
                utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0
                
                schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = shift
                schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = ", ".join(batch_selection)
                schedule_df.loc["% of Batch", date.strftime("%Y-%m-%d")] = ", ".join(map(str, percent_selection))
                schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = f"{utilization_percentage:.2f}%"
        
        st.session_state.schedule_data[selected_machine] = schedule_df
        
        st.write("### Planned Schedule")
        st.dataframe(schedule_df)
        
# Initial Scheduling
for i in range(len(st.session_state.machines_scheduled) + 1):
    schedule_machine(i)

if st.button("Add Another Machine"):
    st.session_state.machines_scheduled.append(f"machine_{len(st.session_state.machines_scheduled) + 1}")

# Display All Scheduled Machines in a Single Table
if st.session_state.schedule_data:
    st.write("### Consolidated Schedule")
    all_data = []
    for machine, df in st.session_state.schedule_data.items():
        df.insert(0, "Machine", machine)
        all_data.append(df)
    consolidated_df = pd.concat(all_data)
    st.dataframe(consolidated_df)
    
    if st.button("Save Full Schedule"):
        conn = get_db_connection()
        cur = conn.cursor()
        for machine, df in st.session_state.schedule_data.items():
            for date in date_range:
                cur.execute(
                    """
                    INSERT INTO plan_instance (machine, schedule_date, shift, batch_number, percentage, utilization) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (machine, date, df.loc["Shift", date.strftime("%Y-%m-%d")],
                     df.loc["Batch", date.strftime("%Y-%m-%d")],
                     df.loc["% of Batch", date.strftime("%Y-%m-%d")],
                     df.loc["Utilization", date.strftime("%Y-%m-%d")]))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Full schedule saved successfully!")
