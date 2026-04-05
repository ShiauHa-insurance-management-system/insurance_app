import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統路徑與持久化設定 ---
st.set_page_config(page_title="產險行動辦公室", layout="wide", initial_sidebar_state="collapsed")
ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

for path in [ATTACH_DIR]:
    if not os.path.exists(path): os.makedirs(path)

# --- 2. 欄位定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 資料讀取/儲存邏輯 (解決資料消失問題) ---
def load_data(file_path, columns):
    if os.path.exists(file_path):
        return pd.read_csv(file_path).fillna("")
    return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

# 初始化資料庫
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)

# --- 4. 密碼登入與安全登出 ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 產險管理系統 - 登入")
    pwd = st.text_input("請輸入密碼", type="password")
    if st.button("登入"):
        if pwd == "1234": # 您的密碼
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    st.stop()

# 登出按鈕放在側邊欄最下方
if st.sidebar.button("🔓 安全登出"):
    st.session_state.auth = False
    st.rerun()

# --- 5. 側邊欄：手動新增 (完整欄位) ---
st.sidebar.header("➕ 行動手動錄入")
db_choice = st.sidebar.selectbox("存入目標", ["續保明細", "出單進度"])

with st.sidebar.form("manual_form", clear_on_submit=True):
    new_entry = {}
    current_fields = RENEW_FIELDS if db_choice == "續保明細" else PROG_FIELDS
    for field in current_fields:
        if "日" in field:
            new_entry[field] = str(st.date_input(field))
        else:
            new_entry[field] = st.text_input(field)
    
    if st.form_submit_button("確認新增"):
        if db_choice == "續保明細":
            st.session_state.renew_db = pd.concat([st.session_state.renew_db, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(st.session_state.renew_db, DB_RENEW)
        else:
            st.session_state.prog_db = pd.concat([st.session_state.prog_db, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(st.session_state.prog_db, DB_PROG)
        st.success("✅ 資料已儲存至伺服器")

# --- 6. 儀表板與提醒 (手機優化) ---
st.title("📱 產險行動辦公室")
today = datetime.now().date()

# 智慧提醒邏輯
urgent_p = pd.DataFrame()
if not st.session_state.prog_db.empty:
    df = st.session_state.prog_db.copy()
    df['dt'] = pd.to_datetime(df['到期日'], errors='coerce').dt.date
    target = [today]
    if today.weekday() == 4: target += [today+timedelta(1), today+timedelta(2)]
    urgent_p = df[df['dt'].isin(target)]

with st.container():
    c1, c2 = st.columns(2)
    c1.metric("今日/週末急件", len(urgent_p))
    if not urgent_p.empty: st.write(urgent_p[['被保險人姓名', '牌照號碼']])

# --- 7. 查詢與檔案管理 ---
t_ren, t_pro, t_file = st.tabs(["🔍 續保", "📑 進度", "📤 管理"])

def show_list(df, name_col, id_col, plate_col, fields, key_p):
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"q_{key_p}")
    res = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    for i, row in res.iterrows():
        with st.expander(f"{row[name_col]} | {row[plate_col]}"):
            for f in fields: st.write(f"**{f}:** {row.get(f,'')}")
            # 附件顯示
            m_keys = [str(row.get(plate_col,'')), str(row.get(id_col,''))]
            for f_name in os.listdir(ATTACH_DIR):
                if any(k in f_name for k in m_keys if k != "" and k != "nan"):
                    st.image(os.path.join(ATTACH_DIR, f_name))

with t_ren: show_list(st.session_state.renew_db, "被保險人", "被保險人ID", "牌照號碼", RENEW_FIELDS, "r")
with t_pro: show_list(st.session_state.prog_db, "被保險人姓名", "被保險人身份證字號/統一編號", "牌照號碼", PROG_FIELDS, "p")

with t_file:
    st.subheader("Excel 覆蓋上傳")
    u_r = st.file_uploader("更新續保明細", type="xlsx")
    if u_r: 
        st.session_state.renew_db = pd.read_excel(u_r); save_data(st.session_state.renew_db, DB_RENEW); st.rerun()
    u_p = st.file_uploader("更新出單進度", type="xlsx")
    if u_p: 
        st.session_state.prog_db = pd.read_excel(u_p); save_data(st.session_state.prog_db, DB_PROG); st.rerun()
    
    st.subheader("附件管理")
    ups = st.file_uploader("上傳照片", accept_multiple_files=True)
    if ups:
        for f in ups:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.rerun()