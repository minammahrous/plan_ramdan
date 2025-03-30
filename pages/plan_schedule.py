import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Import database connection function
import streamlit.errors # explicit import of streamlit errors.

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

# Define defaults to prevent NameError
selected_machine = st.session_state.get("selected_machine", None)
date = st.session_state.get("selected_date", None)

# Ensure selected_batches and downtimes exist in session state
if "selected_batches" not in st.session_state:
    st.session_state.selected_batches = {}

if "downtimes" not in st.session_state:
    st.session_state.downtimes = {}

# Track already selected batches
def schedule_machine(machine_id):
    machines = load_machines()

    selected_machine = st.selectbox(f"Select Machine {machine_id + 1}", machines, key=f"machine_{machine_id}")

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
                # Recalculate available_percentage for each batch selection
                available_percentage = 100 - st.session_state.total_allocated[selected_machine][batch]

                current_selection = already_selected.get(batch, 0)
                current_selection = min(current_selection, available_percentage) # ensure current selection is within available percentage

                # Debugging: Print values before number_input
                st.write(f"Batch: {batch}, Available Percentage: {available_percentage}, Current Selection: {current_selection}, total allocated {st.session_state.total_allocated[selected_machine][batch]}")

                percent = st.number_input(f"% of {batch} (Available: {available_percentage}%) ({date.strftime('%Y-%m-%d')})",
                                                0, available_percentage, step=10, value=current_selection, key = f"num_input_{batch}_{date}_{machine_id}")

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

            # Update total_allocated and progress_remaining for removed batches
            for batch in already_selected:
                if batch not in batch_selection:
                    st.session_state.total_allocated[selected_machine][batch] = max(0, st.session_state.total_allocated[selected_machine][batch] - already_selected[batch])
                    st.session_state.progress_remaining[selected_machine][batch] += already_selected[batch]

            st.session_state.selected_batches[(selected_machine, date)].update(st.session_state.selected_batches[(selected_machine, date)])  # Store selected batches and their percentages

            # Total utilization calculation
            total_utilization = sum((machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0] * percent / 100)
                                        for batch, percent in st.session_state.selected_batches[(selected_machine, date)].items())
            utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0

            formatted_batches = "<br>".join([f"{batch} - <span style='color:green;'>{st.session_state.selected_batches[(selected_machine, date)].get(batch, 0)}%</span>" for batch in st.session_state.selected_batches[(selected_machine, date)]])
            schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = f"<b style='color:red;'>{shift}</b>"
            schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = formatted_batches
            schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = f"Util= {utilization_percentage:.2f}%"

            # Downtime Selection
            if st.button(f"+DT ({date.strftime('%Y-%m-%d')}) - {selected_machine}", key=f"dt_button_{date}_{machine_id}"):
                if (selected_machine, date) not in st.session_state.downtime_data:
                    st.session_state.downtime_data[(selected_machine, date)] = {"type": None, "hours": 0}

            if (selected_machine, date) in st.session_state.downtime_data:
                dt_type = st.selectbox("Select Downtime Type", ["Cleaning", "Preventive Maintenance", "Calibration"], key=f"dt_type_{date}_{machine_id}")
                dt_hours = st.number_input("Downtime Hours", min_value=0.0, step=0.5, key=f"dt_hours_{date}_{machine_id}")
                if dt_hours >24:
                    dt_hours=24;
                    st.warning("Max downtime is 24 Hours")
                st.session_state.downtime_data[(selected_machine, date)] = {"type": dt_type, "hours": dt_hours}
                schedule_df.loc["Downtime", date.strftime("%Y-%m-%d")] = f"<span style='color:purple;'>{dt_type} ({dt_hours} hrs)</span>"

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
        row = {"Machine": machine}  # Initialize row for the machine
        for date in date_range.strftime("%Y-%m-%d"):
            batch_data = df.loc["Batch", date] if "Batch" in df.index else ""
            downtime_data = df.loc["Downtime", date] if "Downtime" in df.index else ""
            shift_data = df.loc["Shift", date] if "Shift" in df.index else ""
            util_data = df.loc["Utilization", date] if "Utilization" in df.index else ""

            row[date] = f"{shift_data}<br>{batch_data}<br>{util_data}<br>{downtime_data}"  # Add date data to the row
        consolidated_df = pd.concat([consolidated_df, pd.DataFrame([row])], ignore_index=True)

    st.markdown(consolidated_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# Save Button
if st.button("Save Schedule"):
    conn = get_db_connection()
    cursor = conn.cursor()

    for machine, df in st.session_state.schedule_data.items():
        for date in date_range.strftime("%Y-%m-%d"):
            shift = df.loc["Shift", date]
            batch_info = df.loc["Batch", date] if 'Batch' in df.index else ''
            utilization = df.loc["Utilization", date] if 'Utilization' in df.index else ''
            downtime = df.loc["Downtime", date] if "Downtime" in df.index else ""

            query = """
                INSERT INTO plan_instance (machine, date, shift, batch_info, utilization, downtime)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (machine, date) DO UPDATE
                SET shift = EXCLUDED.shift, batch_info = EXCLUDED.batch_info, utilization = EXCLUDED.utilization, downtime = EXCLUDED.downtime
                """
            cursor.execute(query, (machine, date, shift, batch_info, utilization, downtime))

    conn.commit()
    conn.close()
    st.success("Schedule saved successfully!")
