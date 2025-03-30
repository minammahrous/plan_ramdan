def schedule_machine(machine_id):
    # ... (rest of the function)

    for date in date_range:
        with st.expander(f"{date.strftime('%Y-%m-%d')} - {selected_machine}"):
            # ... (rest of the date loop)

            percent_selection = {}
            for batch in batch_selection:
                # Recalculate available_percentage for each batch selection
                available_percentage = 100 - st.session_state.total_allocated[selected_machine][batch]

                current_selection = already_selected.get(batch, 0)

                # Debugging: Print values before number_input
                st.write(f"Batch: {batch}, Available Percentage: {available_percentage}, Current Selection: {current_selection}, total allocated {st.session_state.total_allocated[selected_machine][batch]}")

                try:
                    percent = st.number_input(f"% of {batch} (Available: {available_percentage}%) ({date.strftime('%Y-%m-%d')})",
                                                0, available_percentage, step=10, value=current_selection)
                except streamlit.errors.StreamlitValueAboveMaxError as e:
                    st.error(f"StreamlitValueAboveMaxError: {e}")
                    st.error(f"Batch: {batch}, Available Percentage: {available_percentage}, Current Selection: {current_selection}, total allocated {st.session_state.total_allocated[selected_machine][batch]}")
                    percent = current_selection # use the current selection to prevent app crashing.
                # ... (rest of the batch loop)
            # ... (rest of the date loop)
    # ... (rest of the function)
