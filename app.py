import streamlit as st
import pandas as pd
import os
import holidays
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --- 1. 系統基礎設定與國定假日 ---
st.set_page_config(page_title="保險管理系統", layout="wide")
tw_holidays = holidays.TW()  # 台灣國定假日設定

# 密碼設定
LOGIN_PASSWORD = "1234"

# 初始化 Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 資料庫路徑 (雲端暫存環境)
DB_P = 'progress_data.csv'
DB_R = 'renewal_data.csv'
ATTACH_DIR = "attachments"
if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# 欄位定義
COLUMNS_P = [
    "保險種類", "被保險人姓名", "被保險人身份證字號", "牌照號碼", "到期日", 
    "起保日", "要保書進件日", "保險費用", "是否繳費", "業務來源", 
    "實際服務人員", "客戶保險內容(圖片路徑)"
]

COLUMNS_R = [
    "投保型態", "被保險人", "被保險人ID", "牌照號碼", "到期日", 
    "起保日", "電話", "保費", "客戶保險內容(圖片路徑)"
]

# --- 2. 核心邏輯函式 ---

def load_data(file, cols):
    if os.path.exists(file):
        df = pd.read_csv(file).fillna("")
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[cols]
    return pd.DataFrame(columns=cols)

def save_data(df, file):
    df.to_csv(file, index=False, encoding='utf-8-sig')

def is_workday(date):
    """判斷是否為工作天 (非週末且非國定假日)"""
    return date.weekday() < 5 and date not in tw_holidays

def get_previous_workday(date):
    """取得前一個工作天"""
    curr = date - timedelta(days=1)
    while not is_workday(curr):
        curr -= timedelta(days=1)
    return curr

# --- 3. 登入介面 ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] { background-color: #1E3A5F; color: white; }
        .stButton>button { width: 100%; border-radius: 20px; height: 3em; }
        </style>
    """, unsafe_allow_html=True)
    st.title("🔒 保險管理系統")
    st.subheader("行動端身分驗證")
    pwd = st.text_input("請輸入管理員密碼：", type="password")
    if st.button("登入系統"):
        if pwd == LOGIN_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密碼錯誤！")
    st.stop()

# --- 4. 登入後：側邊欄 (手動新增功能) ---
with st.sidebar:
    st.title("🛠️ 控制台")
    st.write(f"📅 今天：{datetime.now().strftime('%Y-%m-%d')} ({'假日' if not is_workday(datetime.now().date()) else '工作天'})")
    
    if st.button("🚀 安全登出"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.divider()
    st.header("➕ 手動新增資料")
    add_mode = st.radio("選擇類別：", ["案子進度", "續保清單"])
    
    with st.form("side_add_form", clear_on_submit=True):
        fields = COLUMNS_P[:-1] if add_mode == "案子進度" else COLUMNS_R[:-1]
        new_data = {f: st.text_input(f) for f in fields}
        if st.form_submit_button("💾 立即儲存"):
            target_db = DB_P if add_mode == "案子進度" else DB_R
            df_curr = load_data(target_db, COLUMNS_P if add_mode == "案子進度" else COLUMNS_R)
            new_data["客戶保險內容(圖片路徑)"] = "無檔案"
            df_updated = pd.concat([df_curr, pd.DataFrame([new_data])], ignore_index=True)
            save_data(df_updated, target_db)
            st.success("已新增至資料庫！")
            st.rerun()

# --- 5. 主頁面：智慧提醒區塊 ---
st.markdown("## 🔔 今日作業重要提醒")
today = datetime.now().date()
df_p = load_data(DB_P, COLUMNS_P)
df_r = load_data(DB_R, COLUMNS_R)

reminders_p = []
reminders_r = []

# A. 案子進度提醒邏輯
for _, row in df_p.iterrows():
    try:
        due_date = pd.to_datetime(row['到期日']).date()
        if due_date == today:
            reminders_p.append(f"🚩 {row['被保險人姓名']} - 今日到期")
        elif not is_workday(due_date) and today == get_previous_workday(due_date):
            reminders_p.append(f"🚩 {row['被保險人姓名']} - 假日提前提醒 (原到期日 {due_date})")
    except: continue

# B. 續保清單提醒邏輯 (提前 2 個月 + 自動勾稽)
for _, row in df_r.iterrows():
    try:
        due_date = pd.to_datetime(row['到期日']).date()
        start_remind = due_date - relativedelta(months=2)
        
        # 檢查是否已在案子進度表中 (依 ID 或 車牌 勾稽)
        in_progress = (df_p['被保險人身份證字號'] == row['被保險人ID']).any() or \
                      (df_p['牌照號碼'] == row['牌照號碼']).any()
        
        if not in_progress and today >= start_remind:
            reminders_r.append(f"🔄 {row['被保險人']} - 續保提醒 (到期日: {due_date})")
    except: continue

if reminders_p or reminders_r:
    with st.expander("展開檢視提醒清單", expanded=True):
        for msg in reminders_p: st.error(msg)
        for msg in reminders_r: st.info(msg)
else:
    st.success("✅ 今日暫無特定提醒事項。")

st.divider()

# --- 6. 分頁內容：資料管理區 ---
tab1, tab2 = st.tabs(["📈 案子進度 (淺藍)", "🔄 續保清單 (白色)"])

# --- Tab 1: 案子進度 ---
with tab1:
    st.markdown("<style>[data-testid='stAppViewContainer'] {background-color: #F0F8FF;}</style>", unsafe_allow_html=True)
    st.header("📊 案子進度管理")
    
    # 智慧附件上