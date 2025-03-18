import streamlit as st
import pandas as pd
import datetime
import streamlit.components.v1 as components
from db import get_sqlalchemy_engine

# Define shift durations
SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 14}

def load_machines():
    engine = get_sqlalchemy_engine()
    query = "SELECT name FROM machines"
    df = pd.read_sql(query, engine)
    return df["name"].tolist()

def load_batches(start_date, end_date):
    engine = get_sqlalchemy_engine()
    query = """
        SELECT product, batch_number, machine, time, schedule 
        FROM production_plan
        WHERE 
            (schedule = FALSE)  -- Always load unscheduled batches
            OR 
            (schedule = TRUE AND planned_start_datetime BETWEEN %s AND %s)  -- Filter scheduled batches by date
    """
    df = pd.read_sql(query, engine, params=[start_date, end_date])
    return df

def scheduler_page():
    st.title("Production Scheduler")

    # Select scheduling period
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date", datetime.date.today())
    end_date = col2.date_input("End Date", datetime.date.today() + datetime.timedelta(days=7))

    machines = load_machines()
    date_range = pd.date_range(start=start_date, end=end_date)
    
    # Button to load batches
    if st.button("Load Batches"):
        st.session_state.batches = load_batches(start_date, end_date)
    
    # Fetch unscheduled batches from session state
    if "batches" not in st.session_state:
        st.session_state.batches = pd.DataFrame()
    df_batches = st.session_state.batches.copy()
    
    # Display batch selection
    st.subheader("Select Batches to Schedule")
    if not df_batches.empty:
        df_batches["select"] = False
        selected_batches = st.data_editor(df_batches, key="batch_selection", use_container_width=True)
    else:
        st.warning("No unscheduled batches available.")
    
    # Shift configuration table
    st.subheader("Shift Configuration")
    shift_df = pd.DataFrame(index=machines, columns=[date.strftime("%Y-%m-%d") for date in date_range])
    for machine in machines:
        for date in date_range:
            shift_df.loc[machine, date.strftime("%Y-%m-%d")] = st.selectbox(
                f"{machine} - {date.strftime('%Y-%m-%d')}", SHIFT_DURATIONS.keys(), key=f"{machine}_{date}")
    
    # Display shift configuration
    st.dataframe(shift_df)
    
    # Interactive Drag-and-Drop Scheduler with interact.js
    st.subheader("Interactive Scheduler")
    
    batch_html = "".join([f'<div class="draggable" id="batch_{row.batch_number}" data-batch="{row.batch_number}">{row.product} - {row.batch_number}</div>' for _, row in df_batches.iterrows()])
    machine_html = "".join([f'<div class="dropzone" id="zone_{machine.replace(" ", "_")}">{machine}</div>' for machine in machines])
    
    scheduler_html = f"""
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/interact.js/1.10.11/interact.min.js"></script>
        <style>
            .draggable {{ width: 120px; height: 50px; background: #3498db; color: white; text-align: center; cursor: move; margin: 5px; }}
            .dropzone {{ width: 150px; height: 100px; border: 2px dashed #ccc; display: inline-block; margin: 5px; }}
        </style>
    </head>
    <body>
        <h3>Unscheduled Batches</h3>
        <div id="batches">{batch_html}</div>
        <h3>Machines</h3>
        <div id="machines">{machine_html}</div>

        <script>
            interact('.draggable').draggable({{
                listeners: {{
                    move(event) {{
                        let x = (parseFloat(event.target.getAttribute('data-x')) || 0) + event.dx;
                        let y = (parseFloat(event.target.getAttribute('data-y')) || 0) + event.dy;
                        if (!isNaN(x) && !isNaN(y)) {{
                            event.target.style.transform = "translate(" + x + "px, " + y + "px)";
                            event.target.setAttribute('data-x', x);
                            event.target.setAttribute('data-y', y);
                        }}
                    }}
                }}
            }});
            
            interact('.dropzone').dropzone({{
                ondrop(event) {{
                    event.target.style.backgroundColor = 'lightgreen';
                    let batch = event.relatedTarget.getAttribute('data-batch');
                    alert("Scheduled batch: " + batch + " on " + event.target.id);
                }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(scheduler_html, height=500)
    
    # Scheduler logic
    if st.button("Start Scheduling"):
        st.write("Processing schedule...")
        # Implement scheduling logic here considering shift constraints
    
    # Export scheduled data
    if st.button("Export Schedule"):
        st.write("Saving schedule to database...")
        # Implement export logic

scheduler_page()
