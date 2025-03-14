import streamlit as st
from db import get_branches

if "branch" not in st.session_state:
    st.session_state["branch"] = "main"

# ✅ Debugging: Print fetched branches
branches = get_branches()
st.write("DEBUG - Fetched Branches:", branches)

# ✅ Ensure the dropdown works
selected_branch = st.selectbox("Select Database Branch:", branches)
st.session_state["branch"] = selected_branch

st.write(f"Connected to branch: **{selected_branch}**")
