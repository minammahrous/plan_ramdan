from db import get_branches

# Print session state branch
st.write(f"Current DB Branch: `{st.session_state.get('branch', 'main')}`")

# Fetch branches
branches = get_branches()

# Show branches
st.write("Fetched branches:", branches)

# Dropdown
selected_branch = st.selectbox("Select Database Branch:", branches)
st.session_state["branch"] = selected_branch
st.write(f"Connected to branch: **{selected_branch}**")
