import streamlit as st
import pandas as pd

# Initialize session state for the DataFrame
if "df_batches" not in st.session_state:
    st.session_state["df_batches"] = pd.DataFrame([
        {"Product": "Product A", "Batch Number": "B001", "Standard Rate": 5, "Plan Time": 7, "Delete": False},
        {"Product": "Product B", "Batch Number": "B002", "Standard Rate": 6, "Plan Time": 8, "Delete": False}
    ])

# Function to delete selected rows
def delete_selected_rows():
    df = st.session_state["df_batches"]
    df = df[df["Delete"] == False].reset_index(drop=True)  # Keep only unchecked rows
    st.session_state["df_batches"] = df  # Update session state
    st.rerun()  # Rerun to refresh UI

# Display the DataFrame with checkboxes for deletion
st.write("### Production Plan")
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

# Delete button to remove checked rows
if st.button("❌ Delete Selected Rows"):
    st.session_state["df_batches"]["Delete"] = edited_df["Delete"]  # Sync checkbox selections
    delete_selected_rows()

# Approve & Save Button
if st.button("✅ Approve & Save Plan") and not st.session_state["df_batches"].empty:
    st.success("Plan Approved & Saved!")  # Replace with database save logic
