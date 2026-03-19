import streamlit.components.v1 as components
import os

_component_func = components.declare_component(
    "rjpq_tactics_board",
    path=os.path.dirname(__file__)
)

def rjpq_tactics_board(room_data, brush, key=None):
    return _component_func(room_data=room_data, brush=brush, key=key)
