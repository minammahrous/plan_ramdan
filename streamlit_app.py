import streamlit as st
from auth import authenticate_user, check_authentication
from db import get_branches

# Authenticate the user
user_info = authenticate_user()

if user_info:
    st.sidebar.header("Branch Selection")
    
    # Get available branches from the database
    branches = get_branches()
    
    # Only allow admin to select branches
    if user_info["role"] == "admin":
        selected_branch = st.sidebar.selectbox("Select a branch to work on:", branches)
        st.session_state["branch"] = selected_branch  # Store selected branch
        st.sidebar.success(f"Working on branch: {selected_branch}")

    # Main Navigation
    st.title("Production Planning App")

    page = st.sidebar.radio(
        "Go to:", 
        ["Production Plan", "Reports", "Logout"]
    )

    if page == "Production Plan":
        st.experimental_set_query_params(page="production_plan")
        st.rerun()
    
    elif page == "Reports":
        st.experimental_set_query_params(page="reports")
        st.rerun()
    
    elif page == "Logout":
        st.session_state.clear()  # Reset session
        st.experimental_set_query_params()
        st.rerun()
