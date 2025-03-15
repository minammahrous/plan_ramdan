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
    st.session_state["df_batches"] = pd.DataFrame(columns=["Product", "Batch Number"])  # Reset DataFrame when branch changes
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

# Reset product selection if coming from "Add Another Product"
if "product_selected" not in st.session_state:
    st.session_state["product_selected"] = False

if not st.session_state["product_selected"]:
    selected_product = st.selectbox("Select a Product:", list(product_dict.keys()), key="selected_product")
    st.session_state["product_selected"] = True
    st.session_state["selected_product"] = selected_product  # Store in session state
else:
    selected_product = st.session_state.get("selected_product", None)

if selected_product is None:
    st.warning("⚠️ Please select a product.")
    st.stop()

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

    # Input: Number of Batches (Min set to 0)
    num_batches = st.number_input("Enter number of batches:", min_value=0, step=1, key="num_batches")

    # Initialize DataFrame for Planning if not exists
    if "df_batches" not in st.session_state or st.session_state["df_batches"].empty:
        st.session_state["df_batches"] = pd.DataFrame(columns=["Product", "Batch Number"] + list(machine_data.keys()))

    batch_data = []
    starting_batch_number = None

    # Generate Batch Numbers with Auto-Increment
    for i in range(num_batches):
        batch_key = f"batch_{i}"

        if i == 0:
            batch_number = st.text_input(f"Batch Number {i+1}:", key=batch_key)
            if batch_number.isnumeric():  # Check if numeric
                starting_batch_number = int(batch_number)
        else:
            if starting_batch_number is not None:
                batch_number = st.text_input(f"Batch Number {i+1}:", value=str(starting_batch_number + i), key=batch_key)
            else:
                batch_number = st.text_input(f"Batch Number {i+1}:", key=batch_key)

        if batch_number and batch_number not in st.session_state["df_batches"]["Batch Number"].values:
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
                    time_per_machine[machine] = None

            batch_data.append({"Product": selected_product, "Batch Number": batch_number, **time_per_machine})

    if batch_data:
        new_batches_df = pd.DataFrame(batch_data)
        st.session_state["df_batches"] = pd.concat([st.session_state["df_batches"], new_batches_df], ignore_index=True)

# Button to Add Another Product
if st.button("➕ Add Another Product"):
    st.session_state["product_selected"] = False
    st.session_state["num_batches"] = 0
    for key in list(st.session_state.keys()):
        if key.startswith("batch_"):
            del st.session_state[key]
    st.rerun()

# Display the DataFrame as an editable table
st.write("### Production Plan")
if not st.session_state["df_batches"].empty:
    st.session_state["df_batches"] = st.data_editor(
        st.session_state["df_batches"],
        use_container_width=True
    )

# Approve & Save Button
if st.button("✅ Approve & Save Plan") and not st.session_state["df_batches"].empty:
    for _, row in st.session_state["df_batches"].iterrows():
        for machine in machine_data.keys():
            time_value = row.get(machine, None)

            cur.execute("""
                INSERT INTO production_plan 
                (product, batch_number, machine, planned_start_datetime, planned_end_datetime, time, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW(), %s, NOW())
            """, (row["Product"], row["Batch Number"], machine, time_value))

    conn.commit()
    st.success("✅ Production plan saved successfully!")
    st.session_state["df_batches"] = pd.DataFrame(columns=["Product", "Batch Number"])
    st.rerun()

# Restart Form Button (Preserves Authentication & Branch)
if st.button("🔄 Restart Form"):
    branch = st.session_state["branch"]
    authenticated_user = st.session_state.get("authenticated_user")

    keys_to_clear = [key for key in st.session_state.keys() if key.startswith("batch_") or key in ["df_batches", "num_batches", "selected_product", "product_selected"]]
    for key in keys_to_clear:
        del st.session_state[key]

    st.session_state["branch"] = branch  
    if authenticated_user:
        st.session_state["authenticated_user"] = authenticated_user  

    st.rerun()

cur.close()
conn.close()
