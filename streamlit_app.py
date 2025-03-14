import streamlit as st

st.set_page_config(page_title="Production Planning", layout="wide")

st.title("Production Planning Dashboard")

st.write("Navigate to the **Demand Page** using the sidebar.")

# Adding a link to the demand page
st.page_link("pages/demand.py", label="Go to Demand Page", icon="📅")

