import streamlit as st
from auth import authenticate_user
from db import get_branches

# Authenticate the user
user_info = authenticate_user()

if user_info:
    st.sidebar.header("Branch Selection")
    
    # Get available branches from the database
    branches = get_branches()
    
    # Allow only admin to select branches
    if user_info["role"] == "admin":
        selected_branch = st.sidebar.selectbox("Select a branch to work on:", branches)
        st.session_state["branch"] = selected_branch  # Store selected branch
        st.sidebar.success(f"Working on branch: {selected_branch}")

    # Main Navigation
    st.title("Production Planning App")

    # Initialize session state for page navigation
    if "page" not in st.session_state:
        st.session_state["page"] = "Production Plan"

    # Sidebar navigation
    page = st.sidebar.radio(
        "Go to:", 
        ["Production Plan", "Plan Scheduler", "Reports", "Logout"]
    )

    # Set session state instead of query params
    if page == "Production Plan":
        st.session_state["page"] = "Production Plan"
        st.rerun()
    
    elif page == "Plan Scheduler":
        st.session_state["page"] = "Plan Scheduler"
        st.rerun()
    
    elif page == "Reports":
        st.session_state["page"] = "Reports"
        st.rerun()
    
    elif page == "Logout":
        st.session_state.clear()  # Reset session
        st.rerun()
