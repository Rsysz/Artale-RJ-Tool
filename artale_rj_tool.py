import streamlit as st
import json
import streamlit.components.v1 as components

# --- 基礎配置 ---
st.set_page_config(page_title="RJPQ 戰術分配系統", layout="wide")

COLOR_CONFIG = {
    "Red":    {"hex": "#FF4B4B", "icon": "🔴"},
    "Blue":   {"hex": "#1C83E1", "icon": "🔵"},
    "Green":  {"hex": "#28B62C", "icon": "🟢"},
    "Yellow": {"hex": "#FFD700", "icon": "🟡"}
}

# --- 1. 全域共享記憶體 ---
# cache_resource 只在伺服器啟動時執行一次，所有用戶共享同一份 dict
# rerun 不會重置，伺服器重啟後才清空
@st.cache_resource
def get_all_rooms() -> dict:
    return {}

ALL_ROOMS = get_all_rooms()

def get_reset_data():
    return {f"{i}F": [{"main": None, "excludes": []} for _ in range(4)] for i in range(1, 11)}

# --- 2. 初始化 Session State ---
if 'brush' not in st.session_state:         st.session_state.brush = "Red"
if 'last_json_save' not in st.session_state: st.session_state.last_json_save = ""
if 'board_version' not in st.session_state:  st.session_state.board_version = 0

# --- 3. 登入邏輯 ---
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
                ALL_ROOMS[new_id] = {"password": new_pwd, "data": get_reset_data()}
                st.session_state.room_id = new_id
                st.rerun()
    st.stop()

# --- 4. 戰術板組件定義 ---
def rjpq_tactics_board(room_data, brush):
    color_conf_json = json.dumps(COLOR_CONFIG)
    room_data_json  = json.dumps(room_data)
    version         = st.session_state.get("board_version", 0)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <!-- version: {version} -->
        <style>
            body {{
                font-family: 'Open Sans', sans-serif;
                background-color: transparent;
                margin: 0; padding: 0;
            }}
            #board-container {{ display: flex; flex-direction: column; gap: 6px; }}
            .floor-row {{ display: grid; grid-template-columns: 50px repeat(4, 1fr); gap: 8px; align-items: center; }}
            .floor-name {{ color: #888; text-align: right; font-weight: bold; line-height: 38px; }}
            .p-cell {{ display: flex; flex-direction: column; }}
            .p-btn {{
                display: block; height: 38px; line-height: 38px; text-align: center;
                border-radius: 4px; font-weight: bold; cursor: pointer;
                border: 1px solid #444; font-size: 18px; transition: 0.1s;
                user-select: none;
            }}
            .ex-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; margin-top: 3px; padding: 0 4px; }}
            .ex-dot {{ height: 6px; border-radius: 2px; cursor: pointer; user-select: none; }}
        </style>
    </head>
    <body>
        <div id="board-container"></div>
        <script src="https://unpkg.com/@streamlit/component-lib/dist/streamlit-component-lib.js"></script>
        <script>
            const COLOR_CONFIG    = {color_conf_json};
            const currentRoomData = {room_data_json};
            const currentBrush    = "{brush}";
            const container       = document.getElementById('board-container');

            function handleClick(floor, slotIdx, action, color = null) {{
                const targetSlot = currentRoomData[floor][slotIdx];
                if (action === "main") {{
                    targetSlot["main"] = (targetSlot["main"] === currentBrush) ? null : currentBrush;
                }} else if (action === "exclude") {{
                    const index = targetSlot["excludes"].indexOf(color);
                    if (index > -1) targetSlot["excludes"].splice(index, 1);
                    else            targetSlot["excludes"].push(color);
                }}
                renderBoard();
                Streamlit.setComponentValue(currentRoomData);
            }}

            function renderBoard() {{
                container.innerHTML = "";
                for (let fIdx = 10; fIdx >= 1; fIdx--) {{
                    const fKey      = fIdx + "F";
                    const floorData = currentRoomData[fKey];
                    const floorRow  = document.createElement('div');
                    floorRow.className = 'floor-row';

                    const floorName = document.createElement('div');
                    floorName.className = 'floor-name';
                    floorName.innerText = fKey;
                    floorRow.appendChild(floorName);

                    [4, 3, 2, 1].forEach(pNum => {{
                        const pIdx = 4 - pNum;
                        const slot = floorData[pIdx];
                        const pCell = document.createElement('div');
                        pCell.className = 'p-cell';

                        const pBtn = document.createElement('div');
                        pBtn.className = 'p-btn';
                        pBtn.innerText = pNum;
                        pBtn.style.background = slot["main"] ? COLOR_CONFIG[slot["main"]]["hex"] : "#262730";
                        pBtn.style.color       = slot["main"] ? "black" : "#eee";
                        pBtn.onclick = () => handleClick(fKey, pIdx, "main");
                        pCell.appendChild(pBtn);

                        const exGrid = document.createElement('div');
                        exGrid.className = 'ex-grid';
                        Object.keys(COLOR_CONFIG).forEach(cName => {{
                            const exDot = document.createElement('div');
                            exDot.className = 'ex-dot';
                            exDot.style.background = COLOR_CONFIG[cName]["hex"];
                            exDot.style.opacity    = slot["excludes"].includes(cName) ? "1.0" : "0.08";
                            exDot.onclick = () => handleClick(fKey, pIdx, "exclude", cName);
                            exGrid.appendChild(exDot);
                        }});
                        pCell.appendChild(exGrid);
                        floorRow.appendChild(pCell);
                    }});
                    container.appendChild(floorRow);
                }}
            }}
            renderBoard();
        </script>
    </body>
    </html>
    """
    return components.html(html_content, height=700)

# --- 5. 工具介面渲染 ---
# 伺服器重啟後 ALL_ROOMS 會清空，但 session_state 還留著舊的 room_id
# 此時強制登出，讓用戶重新建立房間
if st.session_state.room_id not in ALL_ROOMS:
    del st.session_state.room_id
    st.warning("⚠️ 伺服器已重啟，房間資料已清除，請重新建立房間。")
    st.rerun()

room_info = ALL_ROOMS[st.session_state.room_id]

# 頂部欄
top_col1, top_col2 = st.columns([4, 1])
with top_col1:
    st.write(f"### 🏰 房間: `{st.session_state.room_id}` | 🔑 密碼: `{room_info['password']}` | 🎨 畫筆: {COLOR_CONFIG[st.session_state.brush]['icon']}")
with top_col2:
    with st.popover("🧹 清除全房資料", use_container_width=True):
        st.warning("確定要清除所有樓層的顏色嗎？")
        if st.button("確定清除", type="primary", use_container_width=True):
            fresh_data = get_reset_data()
            ALL_ROOMS[st.session_state.room_id]["data"] = fresh_data  # 直接寫入記憶體
            st.session_state.last_json_save = json.dumps(fresh_data)
            st.session_state.board_version += 1
            st.rerun()

# 畫筆選擇
b_cols = st.columns(4)
for i, (name, info) in enumerate(COLOR_CONFIG.items()):
    label = f"{'🎯' if st.session_state.brush == name else ''} {info['icon']} {name}"
    if b_cols[i].button(label, key=f"b_{name}", use_container_width=True):
        st.session_state.brush = name
        st.rerun()

st.divider()

# --- 6. 戰術板（含多人同步）---
@st.fragment(run_every=2)
def sync_board():
    # 直接從記憶體讀，不做任何 I/O
    if st.session_state.room_id not in ALL_ROOMS:
        return

    latest_data  = ALL_ROOMS[st.session_state.room_id]["data"]
    updated_data = rjpq_tactics_board(latest_data, st.session_state.brush)

    if updated_data is not None and isinstance(updated_data, dict):
        data_str = json.dumps(updated_data)
        if data_str != st.session_state.last_json_save:
            ALL_ROOMS[st.session_state.room_id]["data"] = updated_data  # 直接寫入記憶體
            st.session_state.last_json_save = data_str

sync_board()

# --- Sidebar ---
with st.sidebar:
    if st.button("🚪 登出 / 切換房間", use_container_width=True):
        del st.session_state.room_id
        st.rerun()