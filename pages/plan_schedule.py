import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import get_db_connection  # Database connection function

# Define shift durations in hours
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 15}

# Initialize session state for storing unscheduled batches
if "unscheduled_batches" not in st.session_state:
    def load_unscheduled_batches():
        conn = get_db_connection()
        query = """
        SELECT id, product, batch_number, machine, time, progress 
        FROM production_plan 
        WHERE schedule = FALSE
        """
        batches = pd.read_sql(query, conn)
        conn.close()
        
        # Calculate remaining progress
        batches["remaining_progress"] = 100 - batches["progress"]
        
        # Remove fully scheduled batches before storing in session state
        batches = batches[batches["remaining_progress"] > 0]
        
        return batches

    # Load data into session state
    st.session_state.unscheduled_batches = load_unscheduled_batches()
    st.session_state.batch_progress = {}  # Track progress of each batch

# UI - Title
st.title("Machine Scheduling")

# Select Date Range
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", datetime.today())
with col2:
    end_date = st.date_input("End Date", datetime.today() + timedelta(days=7))

date_range = pd.date_range(start=start_date, end=end_date)

# Initialize session state for machine scheduling
if "machines_scheduled" not in st.session_state:
    st.session_state.machines_scheduled = []
    st.session_state.schedule_data = {}

# Function to get machine list
def load_machines():
    conn = get_db_connection()
    query = "SELECT DISTINCT machine FROM production_plan"
    machines = pd.read_sql(query, conn)["machine"].tolist()
    conn.close()
    return machines

# Function to schedule a machine
def schedule_machine(machine_id):
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")

    # Use the stored DataFrame in session state
    machine_batches = st.session_state.unscheduled_batches
    machine_batches = machine_batches[machine_batches["machine"] == selected_machine]

    if not machine_batches.empty:
        st.write(f"### Schedule for {selected_machine}")
        schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization"], columns=date_range.strftime("%Y-%m-%d"))

        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")

                # Display available batches with remaining progress
                machine_batches["display_name"] = machine_batches.apply(
                    lambda row: f"{row['product']} - {row['batch_number']} (Remaining: {int(row['remaining_progress'])}%)", axis=1
                )
                
                batch_selection = st.multiselect(
                    f"Batch ({date.strftime('%Y-%m-%d')})",
                    machine_batches["display_name"].tolist(),
                    key=f"batch_{date}_{machine_id}"
                )

                percent_selection = []
                for batch in batch_selection:
                    batch_data = machine_batches[machine_batches["display_name"] == batch].iloc[0]
                    batch_id = batch_data["id"]
                    remaining_progress = int(batch_data["remaining_progress"])  # Track remaining work

                    # Ensure the total doesn't exceed 100%
                    max_allowed = min(remaining_progress, 100 - st.session_state.batch_progress.get(batch_id, 0))

                    percent_done = st.number_input(
                        f"% of {batch} ({date.strftime('%Y-%m-%d')})", 
                        min_value=0, 
                        max_value=max_allowed,  
                        step=10, 
                        value=min(max_allowed, remaining_progress),  
                        key=f"percent_{batch}_{date}_{machine_id}"
                    )

                    # Update session state tracking
                    if batch_id not in st.session_state.batch_progress:
                        st.session_state.batch_progress[batch_id] = 0
                    st.session_state.batch_progress[batch_id] += percent_done

                    # If fully scheduled, remove from DataFrame
                    if st.session_state.batch_progress[batch_id] >= 100:
                        machine_batches = machine_batches[machine_batches["id"] != batch_id]

                    # Update session state DataFrame instead of DB
                    if percent_done >= remaining_progress:
                        st.session_state.unscheduled_batches = st.session_state.unscheduled_batches[st.session_state.unscheduled_batches["id"] != batch_id]
                    else:
                        st.session_state.unscheduled_batches.loc[
                            st.session_state.unscheduled_batches["id"] == batch_id, "remaining_progress"
                        ] -= percent_done

                # Calculate utilization percentage
                total_utilization = sum(
                    (
                        machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0] * percent / 100
                        if not machine_batches.loc[machine_batches["display_name"] == batch, "time"].empty else 0
                    )
                    for batch, percent in zip(batch_selection, percent_selection)
                )

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
            row[date] = f"{df.loc['Shift', date]}<br>{df.loc['Batch', date]}<br>{df.loc['Utilization', date]}"
        consolidated_df = pd.concat([consolidated_df, pd.DataFrame([row])], ignore_index=True)
    
    st.markdown(consolidated_df.to_html(escape=False, index=False), unsafe_allow_html=True)

# Save Button
if st.button("Save Schedule"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for _, row in st.session_state.unscheduled_batches.iterrows():
        query = "UPDATE production_plan SET progress = %s WHERE id = %s"
        cursor.execute(query, (100 - row["remaining_progress"], row["id"]))

        if row["remaining_progress"] == 0:
            query = "UPDATE production_plan SET schedule = TRUE WHERE id = %s"
            cursor.execute(query, (row["id"],))

    conn.commit()
    conn.close()
    st.success("Schedule saved successfully!")
