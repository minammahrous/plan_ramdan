import streamlit as st
from db import get_branches, get_sqlalchemy_engine
import pandas as pd
from sqlalchemy import text  # ✅ Import text from SQLAlchemy
from auth import check_authentication, check_access

# Authenticate user and get user details
user = check_authentication()

# Debugging: Ensure user details are fetched correctly
st.write(f"Debug: User details -> {user}")

# Ensure user is valid
if not user or not isinstance(user, dict) or "branch" not in user:
    st.error("Authentication failed: User details not available or invalid.")
    st.stop()

check_access(["planner"])

st.set_page_config(page_title="Production Planning", layout="wide")
st.title("Production Planning Dashboard")

# Fetch available branches
branches = get_branches()

# Get user's assigned branch
user_branch = user.get("branch", "main")

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in branches:
    st.session_state["branch"] = user_branch if user_branch in branches else (branches[0] if branches else "main")

# Dropdown to select a database branch
selected_branch = st.selectbox("Select Database Branch:", branches, 
                               index=branches.index(st.session_state["branch"]) if st.session_state["branch"] in branches else 0)

# If branch changes, update session state and force refresh
if st.session_state["branch"] != selected_branch:
    st.session_state["branch"] = selected_branch
    st.rerun()

# Display selected branch
st.write(f"Using Database Branch: `{st.session_state['branch']}`")

# Get SQLAlchemy engine for the selected branch
engine = get_sqlalchemy_engine()

# ✅ Explicitly set the schema before running queries
with engine.connect() as connection:
    connection.execute(text(f"SET search_path TO {st.session_state['branch']}"))  # ✅ Use text() to execute SQL

# ✅ Fetch products from the correct schema
query = "SELECT * FROM products"
try:
    df_products = pd.read_sql(query, con=engine)
    st.write(f"✅ Successfully fetched product data from branch: {st.session_state['branch']}")
except Exception as e:
    st.error(f"❌ Error fetching products: {e}")
    st.stop()

# Ensure products data is available
if df_products.empty:
    st.error("No products found in the selected branch.")
    st.stop()

# Product selection
selected_product = st.selectbox("Select Product:", df_products["name"])

# Get the batch size for the selected product
batch_size = df_products.loc[df_products["name"] == selected_product, "batch_size"].values[0]
st.write(f"Batch Size: {batch_size}")

# Input for number of batches
num_batches = st.number_input("Number of Batches:", min_value=1, step=1)

# Dynamic inputs for batch numbers
batch_numbers = [st.text_input(f"Batch Number {i+1}:") for i in range(num_batches)]

# Assigning batches to a week
week_numbers = [st.number_input(f"Week for Batch {i+1}:", min_value=1, max_value=52, step=1) for i in range(num_batches)]

# Ensure all batch numbers are filled before saving
def validate_batch_numbers(batch_numbers):
    return all(batch_number.strip() for batch_number in batch_numbers)

# Save the demand data
if st.button("Save Demand Data"):
    if validate_batch_numbers(batch_numbers):
        demand_data = pd.DataFrame({
            "product": [selected_product] * num_batches,
            "batch_number": batch_numbers,
            "week": week_numbers,
            "quantity": [batch_size] * num_batches
        })

        try:
            demand_data.to_sql("demand", engine, if_exists="append", index=False)
            st.success("Demand data saved successfully!")
        except Exception as e:
            st.error(f"❌ Error saving demand data: {e}")
    else:
        st.error("❌ Please fill in all batch numbers before saving.")
