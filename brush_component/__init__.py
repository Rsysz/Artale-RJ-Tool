import streamlit.components.v1 as components
import os

_component_func = components.declare_component(
    "brush_selector",
    path=os.path.dirname(__file__)
)

def brush_selector(claims, session_id, key=None):
    """
    claims      : dict {"Red": session_id or None, ...}
    session_id  : 當前用戶的 session id
    回傳值       : 用戶點擊的顏色名稱字串，或 None（未點擊）
    """
    return _component_func(claims=claims, session_id=session_id, key=key)
