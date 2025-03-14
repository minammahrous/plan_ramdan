import streamlit as st
import psycopg2
import pandas as pd
import json
from decimal import Decimal
from psycopg2.extras import DictCursor

# Database connection function
def get_connection(branch):
    return psycopg2.connect(
        dbname="neondb",
        user=st.secrets["user"],
        password=st.secrets["password"],
        host=st.secrets["host"],
        options=f"-c search_path={branch}"
    )

# Fetch available branches
def get_branches():
    conn = get_connection("public")  # Assuming branches table is in public schema
    query = "SELECT branch_name FROM branches;"
    df = pd.read_sql(query, conn)
    conn.close()
    return df["branch_name"].tolist()

# Fetch available products
def get_products(branch):
    conn = get_connection(branch)
    query = "SELECT name, batch_size FROM product;"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Fetch production rates for a product
def get_rates(branch, product):
    conn = get_connection(branch)
    query = """
    SELECT machine, rate 
    FROM rates 
    WHERE product = %s;
    """
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, (product,))
        rates = cur.fetchall()
    conn.close()
    return {row["machine"]: Decimal(row["rate"]) for row in rates}

# Streamlit UI
st.title("Production Plan")

# Select database branch
branches = get_branches()
branch = st.selectbox("Select Database Branch:", branches)

# Select product
products_df = get_products(branch)
product_options = products_df["name"].tolist()
selected_product = st.selectbox("Select a Product:", product_options)

# Display batch size
batch_size = products_df[products_df["name"] == selected_product]["batch_size"].values[0]
st.write(f"**Batch Size:** {batch_size} boxes")

# Input number of batches
num_batches = st.number_input("Enter number of batches:", min_value=1, step=1)

# Collect batch numbers
batch_data = []
for i in range(num_batches):
    batch_number = st.text_input(f"Batch Number {i+1}:")
    batch_data.append({"Batch Number": batch_number, "Include": True})

# Convert to DataFrame
batch_df = pd.DataFrame(batch_data)

# Allow user to remove unwanted batches
if not batch_df.empty:
    batch_df["Include"] = st.data_editor(
        batch_df,
        column_config={"Include": st.column_config.CheckboxColumn()},
        disabled=["Batch Number"],  # Prevent editing batch numbers directly
    )

# Fetch production rates
if st.button("Generate Production Plan"):
    rates = get_rates(branch, selected_product)

    # Filter only selected batches
    selected_batches = batch_df[batch_df["Include"] == True]["Batch Number"].tolist()

    production_plan = []
    for batch in selected_batches:
        batch_plan = {
            "Product": selected_product,
            "Batch Number": batch,
        }
        batch_plan.update(rates)
        production_plan.append(batch_plan)

    # Display updated production plan
    st.json(production_plan)
