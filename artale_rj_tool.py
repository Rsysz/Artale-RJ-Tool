import streamlit as st
import json
import uuid
from rjpq_component import rjpq_tactics_board
from brush_component import brush_selector

# --- 基礎配置 ---
st.set_page_config(page_title="RJPQ 戰術分配系統", layout="wide")

COLOR_CONFIG = {
    "Red":    {"hex": "#FF4B4B", "icon": "🔴"},
    "Blue":   {"hex": "#1C83E1", "icon": "🔵"},
    "Green":  {"hex": "#28B62C", "icon": "🟢"},
    "Yellow": {"hex": "#FFD700", "icon": "🟡"}
}

# --- 1. 全域共享記憶體 ---
@st.cache_resource
def get_all_rooms() -> dict:
    return {}

ALL_ROOMS = get_all_rooms()

def get_reset_data():
    return {f"{i}F": [{"main": None, "excludes": []} for _ in range(4)] for i in range(1, 11)}

# --- 2. 顏色鎖定工具函式 ---
def get_claims(room_id):
    return ALL_ROOMS[room_id]["color_claims"]

def try_claim_color(room_id, color, session_id):
    claims = get_claims(room_id)
    for c in claims:
        if claims[c] == session_id:
            claims[c] = None
    if claims[color] is None:
        claims[color] = session_id
        return True
    return False

def release_color(room_id, session_id):
    if room_id not in ALL_ROOMS:
        return
    claims = get_claims(room_id)
    for c in claims:
        if claims[c] == session_id:
            claims[c] = None

def get_my_color(room_id, session_id):
    claims = get_claims(room_id)
    for c, sid in claims.items():
        if sid == session_id:
            return c
    return None

# --- 3. 初始化 Session State ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'brush' not in st.session_state:
    st.session_state.brush = None
if 'last_json_save' not in st.session_state:
    st.session_state.last_json_save = ""
if 'board_version' not in st.session_state:
    st.session_state.board_version = 0

# --- 4. 登入邏輯 ---
if 'room_id' not in st.session_state:
    st.title("🛡️ RJPQ 戰術系統")
    tab_login, tab_create = st.tabs(["🚪 進入房間", "➕ 創立新房間"])
    with tab_login:
        in_id  = st.text_input("輸入房號", key="login_id")
        in_pwd = st.text_input("輸入密碼", type="password", key="login_pwd")
        if st.button("確認進入", use_container_width=True):
            if in_id in ALL_ROOMS and ALL_ROOMS[in_id]["password"] == in_pwd:
                st.session_state.room_id = in_id
                st.rerun()
            else:
                st.error("房號不存在或密碼錯誤")
    with tab_create:
        new_id  = st.text_input("設定新房號", key="create_id")
        new_pwd = st.text_input("設定密碼",   key="create_pwd")
        if st.button("立即創立並進入", use_container_width=True):
            if not new_id or not new_pwd:
                st.warning("請填寫房號與密碼")
            elif new_id in ALL_ROOMS:
                st.error("此房號已存在")
            else:
                ALL_ROOMS[new_id] = {
                    "password":     new_pwd,
                    "data":         get_reset_data(),
                    "color_claims": {c: None for c in COLOR_CONFIG}
                }
                st.session_state.room_id = new_id
                st.rerun()
    st.stop()

# --- 5. 防護：伺服器重啟後 ALL_ROOMS 清空 ---
if st.session_state.room_id not in ALL_ROOMS:
    del st.session_state.room_id
    st.session_state.brush = None
    st.warning("⚠️ 伺服器已重啟，房間資料已清除，請重新建立房間。")
    st.rerun()

room_id    = st.session_state.room_id
room_info  = ALL_ROOMS[room_id]
session_id = st.session_state.session_id

if "color_claims" not in room_info:
    room_info["color_claims"] = {c: None for c in COLOR_CONFIG}

# 同步：若此 session 已持有顏色但 brush 尚未設定（例如剛重連），補回來
if st.session_state.brush is None:
    owned = get_my_color(room_id, session_id)
    if owned:
        st.session_state.brush = owned

brush  = st.session_state.brush
claims = get_claims(room_id)

# --- 6. 頂部欄 ---
top_col1, top_col2 = st.columns([4, 1])
with top_col1:
    brush_display = COLOR_CONFIG[brush]["icon"] if brush else "⬜ 未選擇"
    st.write(f"### 🏰 房間: `{room_id}` | 🔑 密碼: `{room_info['password']}` | 🎨 畫筆: {brush_display}")
with top_col2:
    with st.popover("🧹 清除全房資料", use_container_width=True):
        st.warning("確定要清除所有樓層的顏色嗎？")
        if st.button("確定清除", type="primary", use_container_width=True):
            fresh_data = get_reset_data()
            room_info["data"] = fresh_data
            st.session_state.last_json_save = json.dumps(fresh_data)
            st.session_state.board_version += 1
            st.rerun()

# --- 7. 筆刷選擇組件 ---
selected_brush = brush_selector(
    claims=claims,
    session_id=session_id,
    key="brush_selector"
)

# 用戶點擊了某個筆刷
if selected_brush is not None and isinstance(selected_brush, str):
    owner = claims.get(selected_brush)
    # 只處理「點自己已持有的（toggle off 不做任何事）」或「點空閒的」
    if owner != session_id:
        if try_claim_color(room_id, selected_brush, session_id):
            st.session_state.brush = selected_brush
            st.rerun()

st.divider()

# --- 8. 戰術板（含多人同步）---
@st.fragment(run_every=0.5)
def sync_board():
    if room_id not in ALL_ROOMS:
        return

    latest_data   = ALL_ROOMS[room_id]["data"]
    current_brush = st.session_state.brush or "Red"

    updated_data = rjpq_tactics_board(
        latest_data, current_brush,
        key=f"board_{st.session_state.board_version}"
    )

    if updated_data is not None and isinstance(updated_data, dict):
        if st.session_state.brush is None:
            return
        data_str = json.dumps(updated_data)
        if data_str != st.session_state.last_json_save:
            ALL_ROOMS[room_id]["data"] = updated_data
            st.session_state.last_json_save = data_str

sync_board()

# --- Sidebar ---
with st.sidebar:
    if st.button("🚪 登出 / 切換房間", use_container_width=True):
        release_color(room_id, session_id)
        del st.session_state.room_id
        st.session_state.brush = None
        st.rerun()