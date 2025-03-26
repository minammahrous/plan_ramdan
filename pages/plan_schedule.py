import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Importing database connection function

# Shift durations in hours
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 15}

# Load Machines
def load_machines():
    """Load machines from database"""
    conn = get_db_connection()
    query = "SELECT name FROM machines ORDER BY name"
    machines = pd.read_sql(query, conn)
    conn.close()
    return machines["name"].tolist()

# Load Unscheduled Batches
def load_unscheduled_batches():
    """Load unscheduled batches from database"""
    conn = get_db_connection()
    query = """
    SELECT id, product, batch_number, machine, time, CAST(progress AS FLOAT) AS progress
    FROM production_plan 
    WHERE schedule = FALSE
    """
    batches = pd.read_sql(query, conn)
    conn.close()
    
    batches["display_name"] = batches["product"] + " - " + batches["batch_number"]
    batches["remaining_percentage"] = 100 - batches["progress"]
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
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = {}
if "downtime_data" not in st.session_state:
    st.session_state.downtime_data = {}
if "unscheduled_batches" not in st.session_state:
    st.session_state.unscheduled_batches = load_unscheduled_batches()
if "batch_percentages" not in st.session_state:
    st.session_state.batch_percentages = {
        row["display_name"]: float(100 - row["progress"]) for _, row in st.session_state.unscheduled_batches.iterrows()
    }

# Function to schedule machines
def schedule_machine(machine_id):
    """Schedule machine"""
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")

    # Filter batches by machine
    batches = st.session_state.unscheduled_batches
    machine_batches = batches[batches["machine"] == selected_machine]

    if selected_machine not in st.session_state.schedule_data:
        st.session_state.schedule_data[selected_machine] = pd.DataFrame(index=["Shift", "Batch", "Utilization", "Downtime"], columns=date_range.strftime("%Y-%m-%d"))

    schedule_df = st.session_state.schedule_data[selected_machine]

    for date in date_range:
        with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
            shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

            # Get available batches
            available_batches = [
                batch for batch in machine_batches["display_name"].tolist()
                if st.session_state.batch_percentages.get(batch, 0) > 0
            ]
            print("Available batches:", available_batches)

            batch_selection = st.multiselect(
                f"Batch ({date.strftime('%Y-%m-%d')})", available_batches, key=f"batch_{date}_{machine_id}"
            )

            percent_selection = []
            for batch in batch_selection:
                max_percent = st.session_state.batch_percentages.get(batch, 0)
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
                    st.warning(f"Batch {
