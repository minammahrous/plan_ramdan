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

if "schedule_data" not in st.session_state:
    st.session_state.schedule_data = {}

if "downtime_data" not in st.session_state:
    st.session_state.downtime_data = {}  # Initialize as an empty dictionary

def schedule_machine(machine_id):
    machines = load_machines()
    selected_machine = st.selectbox(f"Select Machine {machine_id+1}", machines, key=f"machine_{machine_id}")
    
    batches = load_unscheduled_batches()
    machine_batches = batches[batches["machine"] == selected_machine]
    
    if not machine_batches.empty:
        st.write(f"### Schedule for {selected_machine}")
        schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization", "Downtime"], columns=date_range.strftime("%Y-%m-%d"))
        
        for date in date_range:
            with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
                shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}_{machine_id}")
                
                batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", machine_batches["display_name"].tolist(), key=f"batch_{date}_{machine_id}")
                
                percent_selection = [st.number_input(f"% of {batch} ({date.strftime('%Y-%m-%d')})", 0, 100, step=10, value=100, key=f"percent_{batch}_{date}_{machine_id}") for batch in batch_selection]
                
                total_utilization = sum((machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0] * percent / 100) for batch, percent in zip(batch_selection, percent_selection))
                utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0
                
                formatted_batches = "<br>".join([f"{batch} - <span style='color:green;'>{percent}%</span>" for batch, percent in zip(batch_selection, percent_selection)])
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
    
    # Ensure date_range is valid
    if not date_range.empty:
        date_columns = date_range.strftime("%Y-%m-%d").tolist()
    else:
        st.error("Invalid date range selected. Please adjust the Start and End dates.")
        date_columns = []

    # Create an empty DataFrame
    consolidated_df = pd.DataFrame(columns=["Machine"] + date_columns)

    for machine, df in st.session_state.schedule_data.items():
        row = {"Machine": machine}
        
        for date in date_columns:
            shift = df.loc["Shift", date] if date in df.columns else ""
            batch = df.loc["Batch", date] if date in df.columns else ""
            utilization = df.loc["Utilization", date] if date in df.columns else ""
            downtime = df.loc["Downtime", date] if "Downtime" in df.index and date in df.columns else ""

            row[date] = f"{shift}<br>{batch}<br>{utilization}<br>{downtime}"

        # Append row as DataFrame to consolidated_df
        consolidated_df = pd.concat([consolidated_df, pd.DataFrame([row])], ignore_index=True)
    
    # Display the table in Streamlit with HTML formatting
    st.markdown(consolidated_df.to_html(escape=False, index=False), unsafe_allow_html=True)


# Save Button
if st.button("Save Schedule"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for machine, df in st.session_state.schedule_data.items():
        for date in date_range.strftime("%Y-%m-%d"):
            shift = df.loc["Shift", date]
            batch_info = df.loc["Batch", date]
            utilization = df.loc["Utilization", date]
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

