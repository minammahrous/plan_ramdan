import streamlit as st
import pandas as pd
import json
import streamlit.components.v1 as components
from datetime import datetime, timedelta

# **🔹 Function to Generate Gantt Chart HTML**
def gantt_chart(tasks_json):
    """Render an interactive Gantt chart with drag-and-drop using Frappe Gantt."""
    html_code = f"""
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/frappe-gantt/0.5.0/frappe-gantt.min.js"></script>
        <style>
            .gantt-target {{
                width: 100%;
                height: 500px;
            }}
        </style>
    </head>
    <body>
        <div class="gantt-target"></div>
        <script>
            let tasks = {tasks_json};

            let gantt = new Gantt(".gantt-target", tasks, {{
                on_date_change: (task, start, end) => {{
                    console.log("Updated Task:", task.id, start, end);
                    fetch("/update_task", {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/json"
                        }},
                        body: JSON.stringify({{"id": task.id, "start": start, "end": end}})
                    }});
                }},
                custom_popup_html: (task) => {{
                    return `<b>{'{'}task.name{'}'}</b><br>Start: {'{'}task.start{'}'}<br>End: {'{'}task.end{'}'}`;
                }}
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=550)

# **🔹 Simulated Production Plan Data**
df = pd.DataFrame([
    {"id": "1", "name": "Batch A - Machine 1", "start": datetime(2025, 3, 18), "time_needed": 5},
    {"id": "2", "name": "Batch B - Machine 2", "start": datetime(2025, 3, 20), "time_needed": 3},
    {"id": "3", "name": "Batch C - Machine 3", "start": datetime(2025, 3, 23), "time_needed": 4},
])

# **🔹 Calculate End Times Based on Duration (Time in Hours)**
df["end"] = df["start"] + df["time_needed"].apply(lambda x: timedelta(hours=x))

# **🔹 Convert DataFrame to JSON for Frappe Gantt**
tasks = df[["id", "name", "start", "end"]].copy()
tasks["start"] = tasks["start"].dt.strftime("%Y-%m-%d %H:%M")
tasks["end"] = tasks["end"].dt.strftime("%Y-%m-%d %H:%M")
tasks_json = json.dumps(tasks.to_dict(orient="records"))

# **🔹 Streamlit UI**
st.title("📅 Plan Schedule - Interactive Gantt Chart")

# **📊 Show Data Table**
st.write("### 📜 Production Plan Data (Before Editing)")
st.dataframe(df)

# **🖱️ Display Drag-and-Drop Gantt Chart**
st.write("### 🏗️ Production Schedule")
gantt_chart(tasks_json)
