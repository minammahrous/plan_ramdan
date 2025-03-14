import streamlit as st
import pandas as pd
import psycopg2
from db import get_db_connection
from auth import check_authentication

# Ensure user is authenticated
check_authentication()

st.title("Production Plan")

# Database Connection
conn = get_db_connection()
if not conn:
    st.error("❌ Database connection failed.")
    st.stop()

cur = conn.cursor()

# Fetch Products (from `products` table)
cur.execute("SELECT name, batch_size, units_per_box, primary_units_per_box FROM products")
products = cur.fetchall()

if not products:
    st.error("❌ No products found.")
    st.stop()

product_dict = {
    p[0]: {
        "batch_size": p[1],
        "units_per_box": p[2],
        "primary_units_per_box": p[3]
    }
    for p in products
}

# Select Product
selected_product = st.selectbox("Select a Product:", list(product_dict.keys()))

if selected_product:
    batch_size = product_dict[selected_product]["batch_size"]
    units_per_box = product_dict[selected_product]["units_per_box"]
    primary_units_per_box = product_dict[selected_product]["primary_units_per_box"]

    st.write(f"**Batch Size:** {batch_size} boxes")

    # Fetch Machines & Rates (from `rates` and `machines` tables)
    cur.execute("""
        SELECT r.machine, r.rate, m.qty_uom 
        FROM rates r 
        JOIN machines m ON r.machine = m.name
        WHERE r.product = %s
    """, (selected_product,))
    
    machine_rates = cur.fetchall()

    if not machine_rates:
        st.error("❌ No machines found with rates for this product.")
        st.stop()

    # Store Machine Data
    machine_data = {m[0]: {"rate": m[1], "qty_uom": m[2]} for m in machine_rates}

    # Input: Number of Batches
    num_batches = st.number_input("Enter number of batches:", min_value=1, step=1, key="num_batches")

    # Initialize DataFrame for Planning
    batch_data = []

    # Generate Batch Numbers
    for i in range(num_batches):
        batch_number = st.text_input(f"Batch Number {i+1}:", key=f"batch_{i}")
        if batch_number:
            # Calculate Time for Each Machine
            time_per_machine = {}
            for machine, data in machine_data.items():
                rate = data["rate"]
                qty_uom = data["qty_uom"]

                if qty_uom == "batch":
                    time_per_machine[machine] = round(1 / rate, 2)  # Hours per batch
                elif qty_uom == "thousand units":
                    time_per_machine[machine] = round((batch_size * units_per_box) / (1000 * rate), 2)
                elif qty_uom == "thousand primary units":
                    time_per_machine[machine] = round((batch_size * primary_units_per_box) / (1000 * rate), 2)
                else:
                    time_per_machine[machine] = None  # Undefined unit

            # Append batch data
            batch_data.append({"Product": selected_product, "Batch Number": batch_number, **time_per_machine})

    # Convert to DataFrame
    df = pd.DataFrame(batch_data)

    # Display DataFrame
    if not df.empty:
        st.dataframe(df)

        # Allow User to Remove Batches
        batch_to_remove = st.multiselect("Select batch numbers to remove:", df["Batch Number"].tolist())
        if st.button("Remove Selected Batches"):
            df = df[~df["Batch Number"].isin(batch_to_remove)]
            st.experimental_rerun()

        # Approve & Save to Database
        if st.button("Approve & Save Plan"):
            for _, row in df.iterrows():
                for machine in machine_data.keys():
                    cur.execute("""
                        INSERT INTO production_plan 
                        (product, batch_number, machine, planned_start_datetime, planned_end_datetime, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW(), NOW())
                    """, (row["Product"], row["Batch Number"], machine))
            
            conn.commit()
            st.success("✅ Production plan saved successfully!")

# Close DB connection
cur.close()
conn.close()
