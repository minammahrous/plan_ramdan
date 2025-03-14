import streamlit as st
from auth import authenticate_user, check_authentication, check_access, ROLE_ACCESS
from db import get_sqlalchemy_engine, get_branches

# Streamlit page config
st.set_page_config(page_title="Production Scheduling App", layout="wide")

def main():
    user = authenticate_user()  # Handles login
    if not user:
        st.stop()
    
    # Display branch selection dropdown
    branches = get_branches()
    selected_branch = st.sidebar.selectbox("Select Branch", branches, index=branches.index(user["branch"]))
    st.session_state["branch"] = selected_branch  # Update session state with selected branch
    
    # Navigation menu based on role
    st.sidebar.title("Navigation")
    if user["role"] == "planner":
        page = "demand"
    else:
        st.error("Access denied.")
        st.stop()
    
    # Load pages dynamically
    if page == "demand":
        show_demand_page()
    else:
        st.error("Page not found or access denied.")

def show_demand_page():
    check_authentication()
    check_access(["planner"])  # Restrict access to planners only
    st.title("Demand Planning")
    st.write("Manage and assign production demand.")

if __name__ == "__main__":
    main()
