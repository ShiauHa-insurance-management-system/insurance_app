import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 基礎設定與行動端優化 ---
st.set_page_config(page_title="產險行動辦公室-自動提醒版", layout="wide", initial_sidebar_state="collapsed")

ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR): os.makedirs(ATTACH_DIR)

# --- 2. 欄位定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 安全讀取函數 (修正 KeyError) ---
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

# 初始化資料
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 4. 登入檢查 ---
if not st.session_state.auth:
    st.title("🔐 系統登入")
    pwd = st.text_input("授權密碼", type="password")
    if st.button("確認"):
        if pwd == "085799": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 5. 核心功能：自動提醒邏輯 (新增) ---
def get_reminders():
    today = datetime.now().date()
    
    # 假日提前處理邏輯 (週五處理週六、週日件)
    target_dates = [today]
    if today.weekday() == 4: # 今天是週五
        target_dates.append(today + timedelta(days=1)) # 明天週六
        target_dates.append(today + timedelta(days=2)) # 後天週日

    # A. 案子進度表提醒 (到期日 = 今天 或 週末提前)
    p_df = st.session_state.prog_db.copy()
    p_df['到期日'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日'].isin(target_dates)]

    # B. 續保清單提醒 (前 2 個月開始，並勾稽進度表自動終止)
    r_df = st.session_state.renew_db.copy()
    r_df['到期日'] = pd.to_datetime(r_df['到_期日'], errors='coerce').dt.date
    two_months_later = today + timedelta(days=60)
    
    # 勾稽邏輯：找出已在進度表中的「被保險人ID」或「車牌」
    processed_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    processed_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    # 篩選：日期符合 且 (ID與車牌皆不在進度表中)
    r_remind = r_df[
        (r_df['到期日'] <= two_months_later) & 
        (r_df['到期日'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(processed_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(processed_plates))
    ]
    
    return p_urgent, r_remind

# --- 6. 主介面顯示 ---
st.title("📱 產險行動辦公室")

# 顯示提醒區塊
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.container():
        st.warning("🚨 系統自動提醒")
        if not p_urgent.empty:
            st.subheader(f"📅 今日/週末急件 ({len(p_urgent)} 案)")
            for _, row in p_urgent.iterrows():
                st.write(f"⚠️ **到期:** {row['到期日']} | **客戶:** {row['被保險人姓名']} | **車牌:** {row['牌照號碼']}")
        
        if not r_remind.empty:
            st.subheader(f"⏳ 續保作業預警 (前2個月) - 已自動排除處理中物件")
            for _, row in r_remind.iterrows():
                st.write(f"🔔 **到期:** {row['到期日']} | **客戶:** {row['被保險人']} | **車牌:** {row['牌照號碼']}")
    st.divider()

# 分頁與其他功能 (保留您原本的顯示與上傳邏輯...)
t_ren, t_pro, t_man = st.tabs(["🔍 續保查詢", "📑 進度查詢", "⚙️ 系統管理"])

# ... (其餘 show_data_list, display_files, 側邊欄與管理功能皆維持不變)