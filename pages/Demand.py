import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_sqlalchemy_engine  # Import your database connection function
from db import get_branches  # Ensure this function is correctly imported

# ✅ Debug: Check if the function is being called
if "branch" not in st.session_state:
    st.session_state["branch"] = "main"

# ✅ Fetch branches
branches = get_branches()
st.write("DEBUG - Fetched Branches in Demand Page:", branches)  # Check if it's fetching correctly

# ✅ Display branch selection
selected_branch = st.selectbox("Select Database Branch:", branches, key="demand_branch")
st.session_state["branch"] = selected_branch

st.write(f"Demand Page connected to branch: **{selected_branch}**")
# Fetch products from the database
def fetch_products():
    engine = get_sqlalchemy_engine()
    query = "SELECT name, batch_size FROM products"
    return pd.read_sql(query, engine)

# Save demand entry to the database
def save_demand(entries):
    engine = get_sqlalchemy_engine()
    query = """
    INSERT INTO demand (products, batch_number, week, year, batch_size, created_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    with engine.connect() as conn:
        conn.execute(query, entries)

# Streamlit UI
st.title("Demand Planning")

# Fetch product list
products_df = fetch_products()

# Product selection
product_name = st.selectbox("Select Product", products_df["name"])

# Get batch size
batch_size = products_df.loc[products_df["name"] == product_name, "batch_size"].values[0]
st.write(f"Batch Size: {batch_size}")

# Number of batches input
num_batches = st.number_input("Number of Batches", min_value=1, step=1, value=1)

# Collect batch numbers and weeks
batch_entries = []
for i in range(num_batches):
    batch_number = st.text_input(f"Enter Batch Number {i+1}")
    week = st.selectbox(f"Select Week for Batch {i+1}", list(range(1, 53)))
    batch_entries.append((product_name, batch_number, week, datetime.now().year, batch_size))

# Submit button
if st.button("Add to Demand"):
    if all(entry[1] for entry in batch_entries):  # Ensure batch numbers are entered
        save_demand(batch_entries)
        st.success("Demand added successfully!")
    else:
        st.error("Please enter all batch numbers.")

