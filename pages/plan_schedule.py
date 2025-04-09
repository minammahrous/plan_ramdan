import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Import database connection function
import streamlit.errors  # Explicit import of streamlit errors

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
    query = "SELECT id, product, batch_number, machine, time, progress FROM production_plan WHERE schedule = FALSE"
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
    st.session_state.downtime_data = {}
    st.session_state.progress_remaining = {}
    st.session_state.total_allocated = {}
    st.session_state.selected_batches = {}

# Track already selected batches
def schedule_machine(machine_id):
    machines = load_machines()

    # Include a blank option at the start of the list
    selected_machine = st.selectbox(f"Select Machine {machine_id + 1}", [""] + machines, index=0, key=f"machine_{machine_id}")

    if not selected_machine:
        st.warning("Please select a machine.")
        return  # Exit if no machine is selected

    # Load unscheduled batches for selected machine
    batches = load_unscheduled_batches()

    if batches.empty:
        st.warning("No unscheduled batches available in the database.")
        return

    machine_batches = batches[batches["machine"] == selected_machine]

    # Initialize session state for the selected machine
    if selected_machine not in st.session_state.progress_remaining:
        st.session_state.progress_remaining[selected_machine] = {batch: progress for batch, progress in zip(machine_batches["display_name"], machine_batches["progress"])}
        st.session_state.total_allocated[selected_machine] = {batch: 0 for batch in machine_batches["display_name"]}

    st.write(f"### Schedule for {selected_machine}")
    schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization", "Downtime"], columns=date_range.strftime("%Y-%m-%d"))

    for date in date_range:
        with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
            shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

            # Initialize selected_batches for the date if not already present
            if (selected_machine, date) not in st.session_state.selected_batches:
                st.session_state.selected_batches[(selected_machine, date)] = {}

            selected_batches_for_date = st.session_state.selected_batches[(selected_machine, date)]
            already_selected = {batch: percent for batch, percent in selected_batches_for_date.items()}
            machine_batches_filtered = machine_batches[~machine_batches["display_name"].isin(already_selected)]

            # Compute allowed batches
            allowed_batches = {}
            for batch in st.session_state.progress_remaining[selected_machine]:
                if st.session_state.total_allocated[selected_machine][batch] < 100:
                    allowed_batches[batch] = 100 - st.session_state.total_allocated[selected_machine][batch]

            if not allowed_batches:
                st.warning("No batches are available for selection based on progress remaining.")
                continue

            # Set default selections for the multiselect
            default_batches = list(selected_batches_for_date.keys())
            valid_defaults = [batch for batch in default_batches if batch in allowed_batches]  # Ensure valid defaults

            batch_selection = st.multiselect(
                f"Batch ({date.strftime('%Y-%m-%d')})",
                list(allowed_batches.keys()),
                default=valid_defaults,  # Set previously selected batches if valid
                key=f"batch_{date}_{machine_id}"
            )

            percent_selection = {}
            for batch in batch_selection:
                available_percentage = 100 - st.session_state.total_allocated[selected_machine][batch]

                current_selection = already_selected.get(batch, 0)
                current_selection = min(current_selection, available_percentage)  # Ensure current selection is within available percentage

                st.write(f"Batch: {batch}, Available Percentage: {available_percentage}, Current Selection: {current_selection}, Total Allocated: {st.session_state.total_allocated[selected_machine][batch]}")

                percent = st.number_input(f"% of {batch} (Available: {available_percentage}%) ({date.strftime('%Y-%m-%d')})",
                                            0, available_percentage, step=10, value=current_selection, key=f"num_input_{batch}_{date}_{machine_id}")

                add_button = st.button(f"Add {batch}", key=f"add_{batch}_{date}_{machine_id}")
                update_button = st.button(f"Update {batch}", key=f"update_{batch}_{date}_{machine_id}", disabled=batch not in st.session_state.selected_batches[(selected_machine, date)])
                delete_button = st.button(f"Delete {batch}", key=f"delete_{batch}_{date}_{machine_id}", disabled=batch not in st.session_state.selected_batches[(selected_machine, date)])

                if add_button:
                    st.session_state.selected_batches[(selected_machine, date)][batch] = percent
                    st.session_state.total_allocated[selected_machine][batch] += percent
                    st.session_state.progress_remaining[selected_machine][batch] -= percent

                if update_button:
                    old_percent = st.session_state.selected_batches[(selected_machine, date)][batch]
                    st.session_state.total_allocated[selected_machine][batch] += (percent - old_percent)
                    st.session_state.progress_remaining[selected_machine][batch] -= (percent - old_percent)
                    st.session_state.selected_batches[(selected_machine, date)][batch] = percent

                if delete_button:
                    old_percent = st.session_state.selected_batches[(selected_machine, date)][batch]
                    del st.session_state.selected_batches[(selected_machine, date)][batch]
                    st.session_state.total_allocated[selected_machine][batch] -= old_percent
                    st.session_state.progress_remaining[selected_machine][batch] += old_percent

                # Check if all batches are removed for this date
                if not st.session_state.selected_batches[(selected_machine, date)]:
                    # Clear the schedule_df for this date
                    schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = ""
                    schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = ""
                    schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = ""
                    schedule_df.loc["Downtime", date.strftime
