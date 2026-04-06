import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 全平台基礎設定 ---
st.set_page_config(
    page_title="產險行動辦公室", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 目錄設定
ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位精確定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 資料處理防錯 ---
def load_data(file_path, cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path).fillna("")
            df.columns = [str(c).strip() for c in df.columns] 
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: 
            return pd.DataFrame(columns=cols)
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
            else: 
                st.error("密碼錯誤")
    st.stop()

# --- 5. 核心智慧提醒邏輯 ---
def get_reminders():
    today = datetime.now().date()
    # 進度表：今日/週末提前提醒
    target_dates = [today]
    if today.weekday() == 4:
        target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日_dt'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日_dt'].isin(target_dates)]

    # 續保表：2個月預警 + 自動勾稽排除
    r_df = st.session_state.renew_db.copy()
    r_df['到期日_dt'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    two_months = today + timedelta(days=60)
    
    proc_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    proc_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日_dt'] <= two_months) & (r_df['到期日_dt'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(proc_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(proc_plates))
    ]
    return p_urgent, r_remind

# --- 6. 智慧附件顯示 ---
def display_attachments(plate, uid, prefix, index):
    m_keys = [str(plate).strip(), str(uid).strip()]
    m_keys = [k for k in m_keys if k and k != "nan" and k != ""]
    if os.path.exists(ATTACH_DIR):
        for fn in os.listdir(ATTACH_DIR):
            if any(k in fn for k in m_keys):
                fpath = os.path.join(ATTACH_DIR, fn)
                ext = fn.lower().split('.')[-1]
                if ext in ['png', 'jpg', 'jpeg']:
                    st.image(fpath, caption=fn, use_container_width=True)
                elif ext == 'pdf':
                    with open(fpath, "rb") as f:
                        st.download_button(f"📥 下載 {fn}", f, file_name=fn, key=f"dl_{prefix}_{index}_{fn}", use_container_width=True)

# --- 7. 主介面介面 ---
st.title("📱 產險行動辦公室")

# 左側手動錄入 (解決 Missing Submit Button)
with st.sidebar:
    st.header("➕ 手動錄入")
    target = st.selectbox("存入目標", ["續保明細", "出單進度"])
    with st.form("sidebar_input_form", clear_on_submit=True):
        entry_dict = {}
        target_fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in target_fields:
            if "日" in f:
                entry_dict[f] = str(st.date_input(f))
            else:
                entry_dict[f] = st.text_input(f)
        
        # 確保 form 內一定有這個按鈕
        if st.form_submit_button("確認存檔", use_container_width=True):
            new_row = pd.DataFrame([entry_dict])
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_row], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_row], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("資料已成功存入")
            st.rerun()

# 提醒區塊
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.expander("🚨 今日核心作業提醒", expanded=True):
        if not p_urgent.empty:
            st.markdown("**📍 進度到期 (今日/週末)**")
            for _, r in p_urgent.iterrows():
                st.error(f"⚠️ {r['被保險人姓名']} | {r['牌照號碼']} ({r['到期日']})")
        if not r_remind.empty:
            st.markdown("**⏳ 續保預警 (2個月內)**")
            for _, r in r_remind.iterrows():
                st.warning(f"🔔 {r['被保險人']} | {r['牌照號碼']} ({r['到期日']})")
    st.divider()

# 分頁顯示
t_ren, t_pro, t_man = st.tabs(["🔍 續保清單", "📑 進度查詢", "⚙️ 管理"])

def show_data_list(df, name_k, plate_k, id_k, fields, prefix):
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"s_input_{prefix}")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    for i, row in rdf.iterrows():
        with st.expander(f"👤 {row.get(name_k)} | 🚗 {row.get(plate_k)}"):
            c1, c2 = st.columns([1, 1])
            with c1:
                for f in fields:
                    if row.get(f): st.write(f"**{f}:** {row.get(f)}")
            with c2:
                display_attachments(row.get(plate_k), row.get(id_k), prefix, i)

with t_ren:
    show_data_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")

with t_pro:
    show_data_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p")

with t_man:
    if st.button("🔓 安全登出系統", type="primary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    u_r = st.file_uploader("更新續保 Excel", type="xlsx")
    if u_r:
        st.session_state.renew_db = pd.read_excel(u_r).fillna("")
        save_data(st.session_state.renew_db, DB_RENEW)
        st.rerun()
    u_p = st.file_uploader("更新進度 Excel", type="xlsx")
    if u_p:
        st.session_state.prog_db = pd.read_excel(u_p).fillna("")
        save_data(st.session_state.prog_db, DB_PROG)
        st.rerun()
    st.divider()
    files = st.file_uploader("附件批次上傳", accept_multiple_files=True)
    if files:
        for f in files:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf:
                sf.write(f.getbuffer())
        st.success("上傳完成"); st.rerun()