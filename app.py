import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 全平台介面適配 ---
st.set_page_config(
    page_title="產險行動辦公室", 
    layout="wide", 
    initial_sidebar_state="expanded" 
)

ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 資料自動清洗與存檔 ---
def load_data(file_path, cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path).fillna("")
            df.columns = [c.strip() for c in df.columns] 
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

# 初始化狀態
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 4. 登入防護 ---
if not st.session_state.auth:
    st.title("🔐 產險管理系統")
    with st.form("login_gate"):
        pwd = st.text_input("請輸入授權密碼", type="password")
        if st.form_submit_button("確認登入", use_container_width=True):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: st.error("密碼錯誤")
    st.stop()

# --- 5. 核心智慧提醒邏輯 ---
def get_reminders():
    today = datetime.now().date()
    # A. 進度表：到期提醒 (含假日提前邏輯)
    target_dates = [today]
    if today.weekday() == 4: # 若今天是週五，提前預警週六、週日
        target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日_dt'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日_dt'].isin(target_dates)]

    # B. 續保表：2個月預警 + 自動勾稽停止邏輯
    r_df = st.session_state.renew_db.copy()
    r_df['到期日_dt'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    two_months_limit = today + timedelta(days=60)
    
    # 建立已勾稽集合 (進度表中已存在的 ID 或 車牌)
    proc_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    proc_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日_dt'] <= two_months_limit) & (r_df['到期日_dt'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(proc_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(proc_plates))
    ]
    return p_urgent, r_remind

# --- 6. 附件管理與顯示 ---
def display_files(plate, uid, prefix, index):
    m_keys = [str(plate).strip(), str(uid).strip()]
    m_keys = [k for k in m_keys if k and k != "nan" and k != ""]
    if os.path.exists(ATTACH_DIR):
        for fn in os.listdir(ATTACH_DIR):
            if any(k in fn for k in m_keys):
                fpath = os.path.join(ATTACH_DIR, fn)
                ext = fn.lower().split('.')[-1]
                if ext in ['png', 'jpg', 'jpeg']: 
                    st.image(fpath, use_container_width=True)
                elif ext == 'pdf':
                    with open(fpath, "rb") as f:
                        st.download_button(f"📥 查看/下載 {fn}", f, file_name=fn, key=f"dl_{prefix}_{index}_{fn}", use_container_width=True)

# --- 7. 主畫面介面 ---
st.title("📱 產險行動辦公室")

# 左側側邊欄：手動錄入區 (隨時隨地新增資料)
with st.sidebar:
    st.header("➕ 手動錄入案件")
    target = st.selectbox("存入目標", ["續保明細", "出單進度"])
    with st.form("sidebar_entry_form", clear_on_submit=True):
        entry_data = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f: entry_data[f] = str(st.date_input(f))
            else: entry_data[f] = st.text_input(f)
        
        if st.form_submit_button("