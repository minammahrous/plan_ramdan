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
    st.session_state["batch_entries"] = []  # Reset all batches when switching branches
    st.session_state["selected_product"] = None
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

# Create product dictionary
product_dict = {p[0]: {"batch_size": p[1], "units_per_box": p[2], "primary_units_per_box": p[3]} for p in products}

# Select Product
selected_product = st.selectbox("Select a Product:", list(product_dict.keys()))
st.session_state["selected_product"] = selected_product

# Fetch product details
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

# Batch Storage (Use a Temporary List)
if "batch_entries" not in st.session_state:
    st.session_state["batch_entries"] = []

# Number of Batches (Min set to 0)
num_batches = st.number_input("Enter number of batches:", min_value=0, step=1, key="num_batches")

# Generate Batch Numbers with Auto-Increment
batch_data = []
starting_batch_number = None

for i in range(num_batches):
    batch_key = f"batch_{i}"

    if i == 0:
        batch_number = st.text_input(f"Batch Number {i+1}:", key=batch_key)
        if batch_number.isnumeric():
            starting_batch_number = int(batch_number)
    else:
        if starting_batch_number is not None:
            batch_number = st.text_input(f"Batch Number {i+1}:", value=str(starting_batch_number + i), key=batch_key)
        else:
            batch_number = st.text_input(f"Batch Number {i+1}:", key=batch_key)

    if batch_number:
        # Calculate Time for Each Machine
        time_per_machine = {}
        for machine, data in machine_data.items():
            rate = data["rate"] or 1
            qty_uom = data["qty_uom"]

            if qty_uom == "batch":
                time_per_machine[machine] = round(1 / rate, 2) if rate else None
            elif qty_uom == "thousand units":
                time_per_machine[machine] = round((batch_size * units_per_box) / (1000 * rate), 2) if rate and units_per_box else None
            elif qty_uom == "thousand units 1ry":
                time_per_machine[machine] = round((batch_size * primary_units_per_box) / (1000 * rate), 2) if rate and primary_units_per_box else None
            else:
                time_per_machine[machine] = None

        batch_data.append({"Product": selected_product, "Batch Number": batch_number, **time_per_machine})

# Append batch data only when the user confirms
if st.button("➕ Add Batches"):
    st.session_state["batch_entries"].extend(batch_data)
    st.rerun()

# Display All Added Batches with Delete Option
if st.session_state["batch_entries"]:
    st.write("### All Added Batches")

    batch_df = pd.DataFrame(st.session_state["batch_entries"])

    updated_batches = st.session_state["batch_entries"].copy()  # Keep a copy to update after deletion

    for index, row in batch_df.iterrows():
        col1, col2, col3 = st.columns([3, 3, 1])  # Layout: Batch Number | Product | Delete Button
        
        with col1:
            st.write(f"**Batch Number:** {row['Batch Number']}")
        
        with col2:
            st.write(f"**Product:** {row['Product']}")

        with col3:
            if st.button("🗑", key=f"delete_{index}"):  # Unique key for each batch
                updated_batches.pop(index)  # Remove the batch
                st.session_state["batch_entries"] = updated_batches  # Save updated batch list
                st.rerun()  # Refresh UI after deletion

# Move Editable DataFrame to Bottom (Always Visible)
if st.session_state["batch_entries"]:
    st.write("### Review and Edit Batches Before Saving")
    batch_df = pd.DataFrame(st.session_state["batch_entries"])
    st.session_state["batch_df"] = st.data_editor(batch_df, use_container_width=True)

# Ensure "Approve & Save" Button is Always Visible
if st.session_state["batch_entries"] and st.button("✅ Approve & Save Plan"):
    for row in st.session_state["batch_entries"]:
        for machine in machine_data.keys():
            time_value = row.get(machine, None)

            cur.execute("""
                INSERT INTO production_plan 
                (product, batch_number, machine, planned_start_datetime, planned_end_datetime, time, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW(), %s, NOW())
            """, (row["Product"], row["Batch Number"], machine, time_value))

    conn.commit()
    st.success("✅ Production plan saved successfully!")
    st.session_state["batch_entries"] = []
    st.rerun()
