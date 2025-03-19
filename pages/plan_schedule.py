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

# Select Machine
machines = load_machines()
selected_machine = st.selectbox("Select Machine", machines)

# Load Available Batches
batches = load_unscheduled_batches()
machine_batches = batches[batches["machine"] == selected_machine]
remaining_batches = machine_batches.copy()

if not machine_batches.empty:
    st.write("### Schedule for", selected_machine)
    schedule_df = pd.DataFrame(index=["Shift", "Batch", "% of Batch", "Utilization"], columns=date_range.strftime("%Y-%m-%d"))
    
    for date in date_range:
        with st.expander(f"{date.strftime('%Y-%m-%d')}"):
            shift = st.selectbox(f"Shift ({date.strftime('%Y-%m-%d')})", list(SHIFT_DURATIONS.keys()), key=f"shift_{date}")
            available_batches = remaining_batches["display_name"].tolist()
            batch_selection = st.multiselect(f"Batch ({date.strftime('%Y-%m-%d')})", available_batches, key=f"batch_{date}")
            
            percent_selection = [st.number_input(f"% of {batch} ({date.strftime('%Y-%m-%d')})", 0, 100, step=10, value=100, key=f"percent_{batch}_{date}") for batch in batch_selection]
            
            total_utilization = 0
            utilization_list = []
            for batch, percent in zip(batch_selection, percent_selection):
                batch_time = machine_batches.loc[machine_batches["display_name"] == batch, "time"].values[0]
                utilization_hours = (percent / 100) * batch_time
                total_utilization += utilization_hours
                utilization_list.append(f"{utilization_hours:.2f} hours")
            
            utilization_percentage = (total_utilization / SHIFT_DURATIONS[shift]) * 100 if SHIFT_DURATIONS[shift] > 0 else 0
            
            schedule_df.loc["Shift", date.strftime("%Y-%m-%d")] = shift
            schedule_df.loc["Batch", date.strftime("%Y-%m-%d")] = ", ".join(batch_selection)
            schedule_df.loc["% of Batch", date.strftime("%Y-%m-%d")] = ", ".join(map(str, percent_selection))
            schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")] = f"{utilization_percentage:.2f}%"
            
            # Remove selected batches from future selections
            remaining_batches = remaining_batches[~remaining_batches["display_name"].isin(batch_selection)]
    
    st.write("### Planned Schedule")
    st.dataframe(schedule_df)
    
    if st.button("Save Schedule"):
        conn = get_db_connection()
        cur = conn.cursor()
        for date in date_range:
            cur.execute(
                """
                INSERT INTO plan_instance (machine, schedule_date, shift, batch_number, percentage, utilization) 
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (selected_machine, date, schedule_df.loc["Shift", date.strftime("%Y-%m-%d")],
                 schedule_df.loc["Batch", date.strftime("%Y-%m-%d")],
                 schedule_df.loc["% of Batch", date.strftime("%Y-%m-%d")],
                 schedule_df.loc["Utilization", date.strftime("%Y-%m-%d")]))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Schedule saved successfully!")
else:
    st.warning("No unscheduled batches for this machine.")
