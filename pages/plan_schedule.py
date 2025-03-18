import streamlit as st
import pandas as pd
from db import get_sqlalchemy_engine
import streamlit.components.v1 as components

SHIFT_DURATIONS = {"LD": 11, "NS": 22, "ND": 9, "ELD": 14}

def load_machines():
    engine = get_sqlalchemy_engine()
    query = "SELECT name FROM machines"
    df = pd.read_sql(query, engine)
    return df["machine"].tolist()

def scheduler_page():
    st.title("Production Scheduler")

    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date")
    end_date = col2.date_input("End Date")

    machines = load_machines()
    date_range = pd.date_range(start=start_date, end=end_date)

    engine = get_sqlalchemy_engine()
    query = "SELECT product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE"
    df_batches = pd.read_sql(query, engine)

    # Batch Selection Table
    st.subheader("Select Batches to Schedule")
    df_batches["select"] = False
    selected_batches = st.data_editor(df_batches, key="batch_selection", use_container_width=True)

    # Shift Configuration
    st.subheader("Shift Configuration")
    shift_df = pd.DataFrame(index=machines, columns=[date.strftime("%Y-%m-%d") for date in date_range])
    for machine in machines:
        for date in date_range:
            shift_df.loc[machine, date.strftime("%Y-%m-%d")] = st.selectbox(
                f"{machine} - {date.strftime('%Y-%m-%d')}", SHIFT_DURATIONS.keys(), key=f"{machine}_{date}")

    st.dataframe(shift_df)

    # JavaScript Scheduler
    st.subheader("Drag & Drop Scheduling")
    schedule_html = f"""
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/interact.js/1.10.11/interact.min.js"></script>
        <style>
            .calendar-container {{ display: grid; grid-template-columns: repeat({len(date_range) + 1}, 1fr); gap: 5px; }}
            .calendar-header, .calendar-cell {{ border: 1px solid #ddd; padding: 10px; text-align: center; min-height: 50px; }}
            .calendar-header {{ font-weight: bold; background: #f8f8f8; }}
            .batch {{ background: lightblue; padding: 5px; margin: 2px; cursor: grab; }}
        </style>
    </head>
    <body>
        <div class="calendar-container">
            <div class="calendar-header">Machines/Days</div>
            {"".join([f'<div class="calendar-header">{date.strftime("%Y-%m-%d")}</div>' for date in date_range])}
            {"".join([
                f'<div class="calendar-cell">{machine}</div>' + 
                "".join([f'<div class="calendar-cell" id="{machine}_{date.strftime("%Y-%m-%d")}" ondrop="drop(event)" ondragover="allowDrop(event)"></div>' for date in date_range])
                for machine in machines
            ])}
        </div>

        <script>
            function allowDrop(ev) {{
                ev.preventDefault();
            }}

            function drag(ev) {{
                ev.dataTransfer.setData("text", ev.target.id);
            }}

            function drop(ev) {{
                ev.preventDefault();
                var data = ev.dataTransfer.getData("text");
                ev.target.appendChild(document.getElementById(data));
            }}
        </script>

        <div>
            <h3>Unscheduled Batches</h3>
            {"".join([f'<div id="batch_{row["batch_number"]}" class="batch" draggable="true" ondragstart="drag(event)">{row["product"]} (Batch {row["batch_number"]})</div>' for _, row in df_batches.iterrows()])}
        </div>
    </body>
    </html>
    """
    components.html(schedule_html, height=600)

    # Export scheduled data
    if st.button("Export Schedule"):
        st.write("Saving schedule to database...")
        # Implement logic to capture updated batch placements

scheduler_page()
