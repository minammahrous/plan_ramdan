import streamlit as st
import psycopg2
from db import get_db_connection, get_branches
from auth import check_authentication

# Ensure user is authenticated
check_authentication()

st.title("Production Plan")

# Fetch available branches from the database
branches = get_branches()

# Ensure session state has a valid branch
if "branch" not in st.session_state or st.session_state["branch"] not in branches:
    st.session_state["branch"] = branches[0]  # Default to the first available branch

# Create branch selection dropdown
selected_branch = st.selectbox("Select Database Branch:", branches, index=branches.index(st.session_state["branch"]))
st.session_state["branch"] = selected_branch  # Update session state

st.sidebar.success(f"Working on branch: {selected_branch}")

# Connect to the selected branch
conn = get_db_connection()

if conn:
    st.success(f"✅ Connected to {selected_branch} branch")
    cur = conn.cursor()

    # Fetch products from the database
    cur.execute("SELECT name, batch_size FROM products")
    products = cur.fetchall()

    if products:
        # Convert products to a dictionary for easy lookup
        product_dict = {name: batch_size for name, batch_size in products}

        # Product selection dropdown
        selected_product = st.selectbox("Select a Product:", list(product_dict.keys()))

        if selected_product:
            batch_size = product_dict[selected_product]
            st.write(f"**Batch Size:** {batch_size}")

            # Input for the number of batches
            num_batches = st.number_input("Enter number of batches needed:", min_value=1, step=1)

            # Dynamically generate batch number inputs
            batch_numbers = []
            for i in range(num_batches):
                batch_number = st.text_input(f"Batch Number {i+1}:", key=f"batch_{i}")
                batch_numbers.append(batch_number)

            # Submit button
            if st.button("Save Production Plan"):
                # Validate input
                if all(batch_numbers):
                    for batch_number in batch_numbers:
                        cur.execute("""
                            INSERT INTO production_plan 
                            (product, batch_number, planned_start_datetime, planned_end_datetime, updated_at)
                            VALUES (%s, %s, NOW(), NOW(), NOW())
                        """, (selected_product, batch_number))
                    
                    conn.commit()
                    st.success(f"✅ Production plan saved to {selected_branch} branch successfully!")
                else:
                    st.error("❌ Please enter all batch numbers before saving.")

    else:
        st.error("❌ No products found in the database.")

    cur.close()
    conn.close()

else:
    st.error(f"❌ Database connection failed for branch: {selected_branch}")
