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

# Initialize session state variables
if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = {}
if "selected_batches_df" not in st.session_state:
    st.session_state.selected_batches_df = pd.DataFrame(columns=["product", "batch_number", "machine", "time"])
if "schedule_df" not in st.session_state:
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
        temp_schedule = pd.DataFrame(index=machines, columns=date_range.strftime("%Y-%m-%d"))

        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

                batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", available_batches_df["display_name"].tolist(), key=f"batch_{date}_{machine_id}")

                percent_selection = [st.number_input(f"% of {batch} ({date.strftime('%Y-%m-%d')})", 0, 100, step=10, value=100, key=f"percent_{batch}_{date}_{machine_id}") for batch in batch_selection]

                temp_schedule.loc[selected_machine, date.strftime("%Y-%m-%d")] = " | ".join(batch_selection)

        st.session_state.schedule_data[selected_machine] = temp_schedule
        st.write("### Planned Schedule")
        st.dataframe(temp_schedule)

# Initial Scheduling
for i in range(len(st.session_state.machines_scheduled) + 1):
    schedule_machine(i)

if st.button("Add Another Machine"):
    st.session_state.machines_scheduled.append(f"machine_{len(st.session_state.machines_scheduled) + 1}")

# Display All Scheduled Machines in a Matrix Format
if st.session_state.schedule_data:
    st.write("### Consolidated Schedule")
    consolidated_df = pd.concat(st.session_state.schedule_data.values(), axis=1)
    st.dataframe(consolidated_df)
# Display All Scheduled Machines in a Single Table
if st.session_state.schedule_data:
    st.write("### Consolidated Schedule")
    consolidated_df = pd.DataFrame(columns=["Machine"] + date_range.strftime("%Y-%m-%d").tolist())
    
    for machine, df in st.session_state.schedule_data.items():
        row = {"Machine": machine}
        for date in date_range.strftime("%Y-%m-%d"):
            row[date] = (
                f"{df.loc['Shift', date] if 'Shift' in df.index else ''}<br>"
                f"{df.loc['Batch', date] if 'Batch' in df.index else ''}<br>"
                f"{df.loc['Utilization', date] if 'Utilization' in df.index else ''}<br>"
                f"{df.loc['Downtime', date] if 'Downtime' in df.index else ''}"
            )
        consolidated_df = pd.concat([consolidated_df, pd.DataFrame([row])], ignore_index=True)
    
    st.markdown(consolidated_df.to_html(escape=False, index=False), unsafe_allow_html=True)

if st.button("Save Full Schedule"):
    conn = get_db_connection()
    cur = conn.cursor()
    
    for machine, df in st.session_state.schedule_data.items():
        for date in date_range:
            # Check if the date exists in the DataFrame
            if date.strftime("%Y-%m-%d") in df.columns:
                shift = df.at[machine, date.strftime("%Y-%m-%d")] if machine in df.index else None
                cur.execute(
                    """
                    INSERT INTO plan_instance (machine, schedule_date, shift, batch_number, percentage, utilization) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (machine, date, shift, None, None, None)
                )
    conn.commit()
    cur.close()
    conn.close()
    
    st.success("Full schedule saved successfully!")  # Ensure proper indentation

