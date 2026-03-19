import streamlit as st
import json
import uuid
from rjpq_component import rjpq_tactics_board

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
    """取得房間的顏色佔用表 {"Red": session_id or None, ...}"""
    return ALL_ROOMS[room_id]["color_claims"]

def try_claim_color(room_id, color, session_id):
    """嘗試佔用顏色，成功回傳 True，顏色已被他人佔用回傳 False"""
    claims = get_claims(room_id)
    # 先釋放該 session 目前持有的顏色
    for c in claims:
        if claims[c] == session_id:
            claims[c] = None
    # 嘗試佔用新顏色
    if claims[color] is None:
        claims[color] = session_id
        return True
    return False  # 顏色已被其他人佔用

def release_color(room_id, session_id):
    """釋放該 session 持有的顏色"""
    if room_id not in ALL_ROOMS:
        return
    claims = get_claims(room_id)
    for c in claims:
        if claims[c] == session_id:
            claims[c] = None

def get_my_color(room_id, session_id):
    """取得該 session 目前持有的顏色，沒有則回傳 None"""
    claims = get_claims(room_id)
    for c, sid in claims.items():
        if sid == session_id:
            return c
    return None

# --- 3. 初始化 Session State ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())  # 每個用戶唯一識別碼
if 'brush' not in st.session_state:
    st.session_state.brush = None  # 尚未選擇顏色
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
                    "color_claims": {c: None for c in COLOR_CONFIG}  # 顏色佔用表
                }
                st.session_state.room_id = new_id
                st.rerun()
    st.stop()

# --- 5. 防護：伺服器重啟後 ALL_ROOMS 清空 ---
if st.session_state.room_id not in ALL_ROOMS:
    release_color(st.session_state.room_id, st.session_state.session_id)
    del st.session_state.room_id
    st.session_state.brush = None
    st.warning("⚠️ 伺服器已重啟，房間資料已清除，請重新建立房間。")
    st.rerun()

room_id   = st.session_state.room_id
room_info = ALL_ROOMS[room_id]
session_id = st.session_state.session_id

# 確保顏色佔用表存在（相容舊資料）
if "color_claims" not in room_info:
    room_info["color_claims"] = {c: None for c in COLOR_CONFIG}

# 同步：若 session 已有持有顏色但 brush 尚未設定，補回來
if st.session_state.brush is None:
    owned = get_my_color(room_id, session_id)
    if owned:
        st.session_state.brush = owned

# --- 6. 介面渲染 ---
brush  = st.session_state.brush
claims = get_claims(room_id)

# 頂部欄
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

# 畫筆選擇（含顏色鎖定狀態顯示）
b_cols = st.columns(4)
for i, (name, info) in enumerate(COLOR_CONFIG.items()):
    owner     = claims[name]
    is_mine   = (owner == session_id)
    is_taken  = (owner is not None and not is_mine)

    if is_mine:
        label = f"🎯 {info['icon']} {name}"       # 我持有
    elif is_taken:
        label = f"🔒 {info['icon']} {name}"       # 被他人佔用
    else:
        label = f"{info['icon']} {name}"           # 可選

    if b_cols[i].button(label, key=f"b_{name}", use_container_width=True, disabled=is_taken):
        success = try_claim_color(room_id, name, session_id)
        if success:
            st.session_state.brush = name
        st.rerun()

st.divider()

# --- 7. 戰術板（含多人同步）---
@st.fragment(run_every=2)
def sync_board():
    if room_id not in ALL_ROOMS:
        return

    # 每 2 秒直接從記憶體拿最新資料，讓所有人看到彼此的點擊
    latest_data  = ALL_ROOMS[room_id]["data"]
    current_brush = st.session_state.brush or "Red"  # 未選顏色時預設 Red 但不能點（按鈕已 disabled）

    updated_data = rjpq_tactics_board(latest_data, current_brush, key=f"board_{st.session_state.board_version}")

    # 用戶點擊回傳資料 → 存入記憶體
    if updated_data is not None and isinstance(updated_data, dict):
        # 未選顏色的用戶不允許寫入
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
        release_color(room_id, session_id)  # 釋放顏色
        del st.session_state.room_id
        st.session_state.brush = None
        st.rerun()