import streamlit as st
from db import get_branches , get_sqlalchemy_engine
import pandas as pd

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
# Get SQLAlchemy engine for the selected branch
engine = get_sqlalchemy_engine()  # No arguments needed, it reads from session state

# Fetch products from the `product` table
query = "SELECT * FROM product"
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


