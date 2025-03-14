import streamlit as st
from auth import check_authentication
from db import get_db_connection

# Ensure user is authenticated
check_authentication()

st.title("Production Plan")

# Get database connection
conn = get_db_connection()

if conn:
    st.write("✅ Connected to database.")
else:
    st.error("❌ Database connection failed.")

