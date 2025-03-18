import streamlit as st
import pandas as pd
import uuid
from auth import check_authentication
from db import get_branches, get_db_connection
import sys
import os

# Add pages/gantt_component to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "gantt_component")))

from gantt_component import gantt_chart  # Import Gantt component



# 🔒 Ensure user is authenticated
check_authentication()

st.title("📅 Production Plan Scheduler (Drag & Drop)")

# 🔀 Load available branches
if "branches" not in st.session_state:
    st.session_state["branches"] = get_branches()

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in st.session_state["branches"]:
    st.session_state["branch"] = st.session_state["branches"][0]

# 🔀 Branch selection dropdown
selected_branch = st.selectbox(
    "🔀 Select Database Branch:",
    st.session_state["branches"],
    index=st.session_state["branches"].index(st.session_state["branch"])
)

if selected_branch != st.session_state["branch"]:
    st.session_state["branch"] = selected_branch
    st.session_state["scheduled_batches"] = []
    st.rerun()

st.sidebar.success(f"✅ Working on branch: **{st.session_state['branch']}**")

# 🔗 Database connection
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()

# 📌 Fetch unscheduled batches
cur.execute(
    """
    SELECT product, batch_number, machine, time 
    FROM production_plan 
    WHERE schedule = FALSE
    """
)
unscheduled_batches = cur.fetchall()

# 📌 Convert to DataFrame
df = pd.DataFrame(unscheduled_batches, columns=["product", "batch_number", "machine", "time"])

# Ensure start and end s are set
if "scheduled_batches" not in st.session_state:
    st.session_state["scheduled_batches"] = []

if not st.session_state["scheduled_batches"]:
    for _, row in df.iterrows():
        start = pd.Timestamp.now()
        end = start + pd.Timedelta(hours=float(row["time"]))
        st.session_state["scheduled_batches"].append({
            "id": str(uuid.uuid4()),  # Unique ID
            "name": f"{row['product']} - {row['batch_number']}",
            "machine": row["machine"],
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "progress": 50
        })

# 📊 Display Gantt Chart using custom JS component
updated_tasks = gantt_chart(st.session_state["scheduled_batches"])

# Update session state with modified schedule
if updated_tasks:
    st.session_state["scheduled_batches"] = updated_tasks
    st.success("✅ Schedule updated! Click **Save** to store in the database.")

# 💾 Save changes to database
if st.button("💾 Save Schedule"):
    try:
        for task in st.session_state["scheduled_batches"]:
            cur.execute(
                """
                UPDATE production_plan
                SET schedule = TRUE, start_date = %s, end_date = %s
                WHERE batch_number = %s
                """,
                (task["start"], task["end"], task["name"].split(" - ")[1])  # Extract batch number
            )
        conn.commit()
        st.success("✅ Schedule saved successfully!")
        st.session_state["scheduled_batches"] = []
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving schedule: {e}")

cur.close()
conn.close()
