import streamlit as st
import pandas as pd
import uuid
from auth import check_authentication
from db import get_branches, get_db_connection
from gantt_component import gantt_chart  # Import custom component

# Ensure authentication
check_authentication()

st.title("📅 Interactive Production Plan Scheduler")

# Load available branches
if "branches" not in st.session_state:
    st.session_state["branches"] = get_branches()

if "branch" not in st.session_state:
    st.session_state["branch"] = st.session_state["branches"][0]

# Branch selection
selected_branch = st.selectbox("🔀 Select Database Branch:", st.session_state["branches"])
if selected_branch != st.session_state["branch"]:
    st.session_state["branch"] = selected_branch
    st.session_state["scheduled_batches"] = []
    st.rerun()

st.sidebar.success(f"✅ Working on branch: **{st.session_state['branch']}**")

# Database connection
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()

# Fetch unscheduled batches (where schedule = False)
cur.execute("SELECT product, batch_number, machine, time FROM production_plan WHERE schedule = FALSE")
unscheduled_batches = cur.fetchall()

df = pd.DataFrame(unscheduled_batches, columns=["product", "batch_number", "machine", "time_needed"])

if "scheduled_batches" not in st.session_state:
    st.session_state["scheduled_batches"] = []

if not st.session_state["scheduled_batches"]:
    for _, row in df.iterrows():
        st.session_state["scheduled_batches"].append({
            "id": str(uuid.uuid4()),  
            "name": f"{row['product']} - {row['batch_number']}",
            "machine": row["machine"],
            "start": pd.Timestamp.now(),
            "end": pd.Timestamp.now() + pd.Timedelta(hours=row["time_needed"]),
            "progress": 50
        })

# Convert to Gantt format
gantt_data = [
    {
        "id": task["id"],
        "name": task["name"],
        "start": task["start"].isoformat(),
        "end": task["end"].isoformat(),
        "machine": task["machine"]
    }
    for task in st.session_state["scheduled_batches"]
]

# Display Interactive Gantt
st.write("### 📊 Drag & Drop to Adjust Schedule")
updated_tasks = gantt_chart(gantt_data)

if updated_tasks:
    for updated_task in updated_tasks:
        for task in st.session_state["scheduled_batches"]:
            if task["id"] == updated_task["id"]:
                task["start"] = pd.to_datetime(updated_task["start"])
                task["end"] = pd.to_datetime(updated_task["end"])
                task["machine"] = updated_task["machine"]

    st.success("✅ Schedule updated! Click **Save** to store in the database.")

# Save changes
if st.button("💾 Save Schedule"):
    try:
        for task in st.session_state["scheduled_batches"]:
            cur.execute(
                """
                UPDATE production_plan
                SET schedule = TRUE, start_date = %s, end_date = %s, machine = %s
                WHERE batch_number = %s
                """,
                (task["start"], task["end"], task["machine"], task["name"].split(" - ")[1])
            )
        conn.commit()
        st.success("✅ Schedule saved successfully!")
        st.session_state["scheduled_batches"] = []
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving schedule: {e}")

cur.close()
conn.close()
