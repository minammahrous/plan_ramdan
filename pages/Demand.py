import streamlit as st
from db import get_branches

st.set_page_config(page_title="Production Planning", layout="wide")

st.title("Production Planning Dashboard")

# Ensure session state has a branch set
if "branch" not in st.session_state:
    st.session_state["branch"] = "main"  # Default branch

# Fetch available branches
branches = get_branches()

# Ensure the current branch is in the list; if not, reset to default
if st.session_state["branch"] not in branches:
    st.session_state["branch"] = "main"

# Dropdown to select a database branch
selected_branch = st.selectbox(
    "Select Database Branch:", branches, 
    index=branches.index(st.session_state["branch"]) if st.session_state["branch"] in branches else 0
)

# Update session state with selected branch
st.session_state["branch"] = selected_branch

# Debugging: Show selected branch
st.write(f"Using Database Branch: `{selected_branch}`")



