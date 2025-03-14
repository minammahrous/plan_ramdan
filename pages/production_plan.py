import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from streamlit_extras.dataframe_explorer import dataframe_explorer

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        dbname="neondb",
        user="your_user",
        password="your_password",
        host="ep-quiet-wave-a8pgbkwd-pooler.eastus2.azure.neon.tech",
        port="5432"
    )

# Fetch production rates from the database
def fetch_rates():
    conn = get_db_connection()
    query = "SELECT product, machine, rate AS standard_rate FROM rates;"
    df_rates = pd.read_sql(query, conn)
    conn.close()
    return df_rates

# Fetch scheduled production batches
def fetch_scheduled_batches():
    conn = get_db_connection()
    query = """
        SELECT product, batch_number, machine, standard_rate, time AS plan_time 
        FROM production_plan;
    """
    df_batches = pd.read_sql(query, conn)
    conn.close()
    df_batches["Delete"] = False  # Add checkbox column for deletion
    return df_batches

# Initialize session state for batches
if "df_batches" not in st.session_state:
    st.session_state["df_batches"] = fetch_scheduled_batches()

# Function to calculate production time
def calculate_time(batch_size, standard_rate):
    return batch_size / standard_rate if standard_rate > 0 else None

# Function to delete selected rows
def delete_selected_rows():
    df = st.session_state["df_batches"]
    df = df[df["Delete"] == False].reset_index(drop=True)  # Keep only unchecked rows
    st.session_state["df_batches"] = df  # Update session state
    st.rerun()  # Rerun to refresh UI

# Page Title
st.title("📅 Production Plan Scheduling")

# Display Data Editor
st.write("### Production Plan Overview")
edited_df = st.data_editor(
    st.session_state["df_batches"],
    column_config={
        "Delete": st.column_config.CheckboxColumn("Delete?"),
        "Standard Rate": st.column_config.NumberColumn("Standard Rate", format="%.2f"),
        "Plan Time": st.column_config.NumberColumn("Plan Time", format="%.2f")
    },
    hide_index=True,
    use_container_width=True
)

# Delete button
if st.button("❌ Delete Selected Rows"):
    st.session_state["df_batches"]["Delete"] = edited_df["Delete"]  # Sync checkbox selections
    delete_selected_rows()

# Approve & Save Button
if st.button("✅ Approve & Save Plan") and not st.session_state["df_batches"].empty:
    conn = get_db_connection()
    cur = conn.cursor()

    # Insert or update records in the production_plan table
    for _, row in st.session_state["df_batches"].iterrows():
        cur.execute("""
            INSERT INTO production_plan (product, batch_number, machine, standard_rate, time, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (batch_number) 
            DO UPDATE SET machine = EXCLUDED.machine, standard_rate = EXCLUDED.standard_rate, time = EXCLUDED.time, updated_at = NOW();
        """, (row["Product"], row["Batch Number"], row["Machine"], row["Standard Rate"], row["Plan Time"]))

    conn.commit()
    conn.close()
    st.success("✅ Plan Approved & Saved!")
