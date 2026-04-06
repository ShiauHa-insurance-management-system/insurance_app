import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64

# --- 1. 基礎設定 ---
st.set_page_config(
    page_title="產險行動辦公室-自動提醒版", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 安全資料讀取 ---
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

# 初始化 Session State
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 4. 登入系統 ---
if not st.session_state.auth:
    st.title("🔐 產險管理系統 - 登入")
    with st.form("login_form"):
        pwd = st.text_input("請輸入授權密碼", type="password")
        if st.form_submit_button("確認登入"):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: st.error("密碼錯誤")
    st.stop()

# --- 5. 核心提醒邏輯 (修正筆誤) ---
def get_reminders():
    today = datetime.now().date()
    
    # A. 案子進度表提醒 (假日提前處理)
    target_dates = [today]
    if today.weekday() == 4: # 週五則包含週末
        target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日'].isin(target_dates)]

    # B. 續保清單提醒 (提前2個月 + 自動勾稽終止)
    r_df = st.session_state.renew_db.copy()
    r_df['到期日'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date # 已修正到期日筆誤
    two_months_later = today + timedelta(days=60)
    
    processed_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    processed_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日'] <= two_months_later) & 
        (r_df['到期日'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(processed_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(processed_plates))
    ]
    return p_urgent, r_remind

# --- 6. 側邊欄：手動錄入 ---
with st.sidebar:
    st.header("➕ 手動錄入")
    target = st.selectbox("目標", ["續保明細", "出單進度"])
    with st.form("sidebar_form", clear_on_submit=True):
        entry = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f: entry[f] = str(st.date_input(f))
            else: entry[f] = st.text_input(f)
        if st.form_submit_button("確認新增"):
            new_row = pd.DataFrame([entry])
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_row], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_row], ignore_index=True)
                save_data