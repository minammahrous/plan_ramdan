import streamlit as st
import pandas as pd
from db import get_sqlalchemy_engine, get_branches

# Ensure session state has a branch set
if "branch" not in st.session_state:
    st.session_state["branch"] = "main"  # Default to 'main'

# Fetch available branches from the `branches` table
branches = get_branches()

# Ensure current branch is valid
if st.session_state["branch"] not in branches:
    st.session_state["branch"] = "main"

# Dropdown to select a database branch
selected_branch = st.selectbox(
    "Select Database Branch:", branches, 
    index=branches.index(st.session_state["branch"]) if st.session_state["branch"] in branches else 0
)

# Store selected branch in session state
st.session_state["branch"] = selected_branch

# Debugging output
st.write(f"Using Database Branch: `{selected_branch}`")

# Get database engine for the selected branch
engine = get_sqlalchemy_engine()

# Fetch products from the `products` table
query = "SELECT * FROM products"
df_products = pd.read_sql(query, engine)

# Product selection
selected_product = st.selectbox("Select Product:", df_products["name"])

# Get the batch size for the selected product
batch_size = df_products[df_products["name"] == selected_product]["batch_size"].values[0]
st.write(f"Batch Size: {batch_size}")

# Input for number of batches
num_batches = st.number_input("Number of Batches:", min_value=1, step=1)

# Dynamic inputs for batch numbers
batch_numbers = []
for i in range(num_batches):
    batch_number = st.text_input(f"Batch Number {i+1}:")
    batch_numbers.append(batch_number)

# Assigning batches to a week
week_numbers = []
for i in range(num_batches):
    week_number = st.number_input(f"Week for Batch {batch_numbers[i]}:", min_value=1, max_value=52, step=1)
    week_numbers.append(week_number)

# Save the demand data
if st.button("Save Demand Data"):
    demand_data = pd.DataFrame({
        "product": [selected_product] * num_batches,
        "batch_number": batch_numbers,
        "week": week_numbers,
        "quantity": [batch_size] * num_batches
    })
    
    demand_data.to_sql("demand", engine, if_exists="append", index=False)
    st.success("Demand data saved successfully!")
