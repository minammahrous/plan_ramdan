import streamlit as st
from db import get_branches  # Import function from db.py

# Fetch available branches
branches = get_branches()

# Create a dropdown for branch selection
selected_branch = st.selectbox("Select Database Branch:", branches)

# Store the selected branch in session state
st.session_state["branch"] = selected_branch

st.write(f"Connected to branch: **{selected_branch}**")
