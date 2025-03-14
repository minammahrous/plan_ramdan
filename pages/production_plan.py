import streamlit as st
import pandas as pd
import psycopg2
from db import get_db_connection, get_branches
from auth import check_authentication

# Ensure user is authenticated
check_authentication()

st.title("Production Plan")

# Ensure branches are loaded
if "branches" not in st.session_state:
    st.session_state["branches"] = get_branches()

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in st.session_state["branches"]:
    st.session_state["branch"] = st.session_state["branches"][0]

# Branch selection
selected_branch = st.selectbox(
    "Select Database Branch:",
    st.session_state["branches"],
    index=st.session_state["branches"].index(st.session_state["branch"])
)

if selected_branch != st.session_state["branch"]:
    st.session_state["branch"] = selected_branch
    st.rerun()

st.sidebar.success(f"Working on branch: {st.session_state['branch']}")

# Connect to the selected branch
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()

# Fetch Products
cur.execute("SELECT name, batch_size, units_per_box, primary_units_per_box FROM products")
products = cur.fetchall()

if not products:
    st.error("❌ No products found.")
    st.stop()

product_dict = {p[0]: {"batch_size": p[1], "units_per_box": p[2], "primary_units_per_box": p[3]} for p in products}

# Select Product
selected_product = st.selectbox("Select a Product:", list(product_dict.keys()))

if selected_product:
    batch_size = product_dict[selected_product]["batch_size"]
    units_per_box = product_dict[selected_product]["units_per_box"]
    primary_units_per_box = product_dict[selected_product]["primary_units_per_box"]

    st.write(f"**Batch Size:** {batch_size} boxes")

    # Fetch Machines & Rates
    cur.execute("""
        SELECT r.machine, r.standard_rate, m.qty_uom 
        FROM rates r 
        JOIN machines m ON r.machine = m.name
        WHERE r.product = %s
    """, (selected_product,))
    
    machine_rates = cur.fetchall()
    if not machine_rates:
        st.error("❌ No machines found with rates for this product.")
        st.stop()

    # Store machine data
    machine_data = {m[0]: {"rate": m[1], "qty_uom": m[2]} for m in machine_rates}

    # Input: Number of Batches
    num_batches = st.number_input("Enter number of batches:", min_value=1, step=1, key="num_batches")


# Initialize DataFrame in session_state if not already stored
if "df_batches" not in st.session_state:
    st.session_state["df_batches"] = pd.DataFrame(columns=["Product", "Batch Number"] + list(machine_data.keys()))

df_batches = st.session_state["df_batches"]

# Batch Data Input
batch_data = []

if selected_product and num_batches:
    for i in range(num_batches):
        batch_number = st.text_input(f"Batch Number {i+1}:", key=f"batch_{i}")
        if batch_number:
            # Calculate Time for Each Machine
            time_per_machine = {}
            for machine, data in machine_data.items():
                rate = data["rate"] or 1  # Prevent division by zero
                qty_uom = data["qty_uom"]

                if qty_uom == "batch":
                    time_per_machine[machine] = round(1 / rate, 2) if rate else None
                elif qty_uom == "thousand units":
                    time_per_machine[machine] = round((batch_size * units_per_box) / (1000 * rate), 2) if rate and units_per_box else None
                elif qty_uom == "thousand units 1ry":
                    time_per_machine[machine] = round((batch_size * primary_units_per_box) / (1000 * rate), 2) if rate and primary_units_per_box else None
                else:
                    time_per_machine[machine] = None  # Undefined unit

            # Append batch data
            batch_data.append({"Product": selected_product, "Batch Number": batch_number, **time_per_machine})

# Prevent duplication: Only add new batches
if batch_data:
    new_df = pd.DataFrame(batch_data)
    st.session_state["df_batches"] = pd.concat([st.session_state["df_batches"], new_df], ignore_index=True)

# Function to delete a row
def delete_row(index):
    if 0 <= index < len(st.session_state["df_batches"]):
        st.session_state["df_batches"] = st.session_state["df_batches"].drop(index).reset_index(drop=True)
        st.rerun()  # Rerun the script to refresh the UI properly

# Display the DataFrame as a table with delete buttons
st.write("### Production Plan")
df_display = st.session_state["df_batches"].copy()

if not df_display.empty:
    for i, row in df_display.iterrows():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(row.to_dict())
        with col2:
            if st.button(f"Delete {i}", key=f"delete_{i}"):
                delete_row(i)
