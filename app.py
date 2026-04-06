import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64

# --- 1. 基礎設定與行動端優化 ---
st.set_page_config(
    page_title="產險行動辦公室", 
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

# --- 3. 資料讀取函數 ---
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
    st.title("🔐 系統登入")
    with st.form("login_form"):
        pwd = st.text_input("授權密碼", type="password")
        if st.form_submit_button("確認登入", use_container_width=True):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: st.error("密碼錯誤")
    st.stop()

# --- 5. 核心功能：自動提醒邏輯 (新增) ---
def get_reminders():
    today = datetime.now().date()
    
    # A. 案子進度表：假日提前提醒
    target_dates = [today]
    if today.weekday() == 4: # 週五處理週末件
        target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日_dt'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日_dt'].isin(target_dates)]

    # B. 續保預警：前 2 個月 + 自動勾稽停止
    r_df = st.session_state.renew_db.copy()
    r_df['到期日_dt'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    two_months_later = today + timedelta(days=60)
    
    # 勾稽進度表標識
    processed_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    processed_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日_dt'] <= two_months_later) & (r_df['到期日_dt'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(processed_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(processed_plates))
    ]
    return p_urgent, r_remind

# --- 6. 檔案顯示組件 ---
def display_files(plate, uid, prefix, index):
    m_keys = [str(plate).strip(), str(uid).strip()]
    m_keys = [k for k in m_keys if k and k != "nan" and k != ""]
    found_any = False
    if os.path.exists(ATTACH_DIR):
        for fn in os.listdir(ATTACH_DIR):
            if any(k in fn for k in m_keys):
                found_any = True
                fpath = os.path.join(ATTACH_DIR, fn)
                ext = fn.lower().split('.')[-1]
                if ext in ['png', 'jpg', 'jpeg']:
                    st.image(fpath, caption=fn)
                elif ext == 'pdf':
                    with open(fpath, "rb") as f:
                        st.download_button(label=f"📥 下載 {fn}", data=f, file_name=fn, mime="application/pdf", key=f"dl_{prefix}_{index}_{fn}")
    if not found_any:
        st.caption("無關聯附件")

# --- 7. 主介面 ---
st.title("📱 產險行動辦公室")

# 置頂顯示提醒
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.expander("🚨 到期作業提醒", expanded=True):
        if not p_urgent.empty:
            st.markdown("**📅 案子進度到期 (今日/週末)**")
            for _, row in p_urgent.iterrows():
                st.write(f"⚠️ {row['被保險人姓名']} | {row['牌照號碼']} ({row['到期日']})")
        if not r_remind.empty:
            st.markdown("**⏳ 續保作業預警 (近2個月)**")
            for _, row in r_remind.iterrows():
                st.write(f"🔔 {row['被保險人']} | {row['牌照號碼']} ({row['到期日']})")
    st.divider()

t_ren, t_pro, t_man = st.tabs(["🔍 續保", "📑 進度", "⚙️ 設定"])

def show_data_list(df, name_k, plate_k, id_k, fields, prefix):
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"search_{prefix}", placeholder="請輸入關鍵字...")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    for i, row in rdf.iterrows():
        label = f"{row.get(name_k)} | {row.get(plate_k)}"
        with st.expander(label):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**📋 詳細資料**")
                for f in fields: 
                    val = row.get(f)
                    if val: st.write(f"**{f}:** {val}")
            with c2:
                st.markdown("**📂 自動歸檔附件**")
                display_files(row.get(plate_k), row.get(id_k), prefix, i)

with t_ren: show_data_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")
with t_pro: show_data_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p