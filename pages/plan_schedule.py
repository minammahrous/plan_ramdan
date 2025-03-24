import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Importing database connection function

# Shift durations in hours
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 15}
# Initialize session state variables
if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = {}
if "selected_batches_df" not in st.session_state:
    st.session_state.selected_batches_df = pd.DataFrame(columns=["product", "batch_number", "machine", "time"])
if "schedule_df" not in st.session_state:
    st.session_state.schedule_df = pd.DataFrame(columns=["Machine", "Date", "Shift", "Batch", "% of Batch", "Utilization"])

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

# Initialize session state variables
if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
    st.session_state.schedule_data = {}
    st.session_state.selected_batches_df = pd.DataFrame(columns=["product", "batch_number", "machine", "time"])
    st.session_state.schedule_df = pd.DataFrame(columns=["Machine", "Date", "Shift", "Batch", "% of Batch", "Utilization"])

def schedule_machine(machine_id):
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")

    # Load available batches and filter out selected ones
    batches = load_unscheduled_batches()
    available_batches_df = batches[batches["machine"] == selected_machine]
    available_batches_df = available_batches_df[~available_batches_df["batch_number"].isin(st.session_state.selected_batches_df["batch_number"])]

    if not available_batches_df.empty:
        st.write(f"### Schedule for {selected_machine}")
        temp_schedule = []

        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

                batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", available_batches_df["display_name"].tolist(), key=f"batch_{date}_{machine_id}")

                percent_selection = [st.number_input(f"% of {batch} ({date.strftime('%Y-%m-%d')})", 0, 100, step=10, value=100, key=f"percent_{batch}_{date}_{machine_id}") for batch in batch_selection]

                # Calculate utilization
                total_utilization = sum((available_batches_df.loc[available_batches_df["display_name"] == batch, "time"].values[0] * percent / 100) for batch, percent in zip(batch_selection, percent_selection))
                utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0

                # Store in temporary schedule list
                for batch, percent in zip(batch_selection, percent_selection):
                    temp_schedule.append([selected_machine, date.strftime("%Y-%m-%d"), shift, batch, percent, f"{utilization_percentage:.2f}%"])

                # Append to selected_batches_df to remove from future selections
                selected_rows = available_batches_df[available_batches_df["display_name"].isin(batch_selection)]
                st.session_state.selected_batches_df = pd.concat([st.session_state.selected_batches_df, selected_rows])

        # Append temp_schedule to main schedule DataFrame
        if temp_schedule:
            temp_schedule_df = pd.DataFrame(temp_schedule, columns=["Machine", "Date", "Shift", "Batch", "% of Batch", "Utilization"])
            st.session_state.schedule_df = pd.concat([st.session_state.schedule_df, temp_schedule_df])

# Initial Scheduling
for i in range(len(st.session_state.machines_scheduled) + 1):
    schedule_machine(i)

if st.button("Add Another Machine"):
    st.session_state.machines_scheduled.append(f"machine_{len(st.session_state.machines_scheduled) + 1}")

# Display Updated Schedule
if not st.session_state.schedule_df.empty:
    st.write("### Updated Schedule")
    st.dataframe(st.session_state.schedule_df)

if st.session_state.schedule_data:
    st.write("### Consolidated Schedule")
    all_data = []
    if st.session_state.schedule_data:
        st.write("### Consolidated Schedule")
        all_data = []
        for machine, df in st.session_state.schedule_data.items():
            if "Machine" not in df.columns:  # ✅ Check before inserting
                df.insert(0, "Machine", machine)
            all_data.append(df)
    
    consolidated_df = pd.concat(all_data)
    st.dataframe(consolidated_df)

    
    if st.button("Save Full Schedule"):
        conn = get_db_connection()
        cur = conn.cursor()
        for _, row in st.session_state.schedule_df.iterrows():
            cur.execute(
                """
                INSERT INTO plan_instance (machine, schedule_date, shift, batch_number, percentage, utilization) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (row["Machine"], row["Date"], row["Shift"], row["Batch"], row["% of Batch"], row["Utilization"]))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Full schedule saved successfully!")
