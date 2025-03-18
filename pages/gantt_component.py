import streamlit.components.v1 as components
import json

# Create a custom Streamlit component
def gantt_chart(tasks, height=500, width="100%"):
    component = components.declare_component(
        "custom_gantt",
        path="gantt_component",
    )
    return component(tasks=json.dumps(tasks), height=height, width=width)
