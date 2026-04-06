import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64

# --- 1. 基礎設定與行動端優化 ---
st.set_page_config(
    page_title="產險行動辦公室", 
    layout="wide", # 手機版會自動轉為單欄顯示
    initial_sidebar_state="collapsed" # 預設隱藏側邊欄，增加手機操作空間
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
    st.title("🔐 系統登入")
    with st.form("login_form"):
        pwd = st.text_input("請輸入授權密碼", type="password")
        if st.form_submit_button("確認登入"):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: st.error("密碼錯誤")
    st.stop()

# --- 5. 核心提醒邏輯 (手機首頁最上方) ---
def get_reminders():
    today = datetime.now().date()
    
    # A. 案子進度表：假日提前提醒
    target_dates = [today]
    if today.weekday() == 4: # 週五則包含週末
        target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日'].isin(target_dates)]

    # B. 續保預警：前 2 個月 + 自動勾稽停止
    r_df = st.session_state.renew_db.copy()
    r_df['到期日'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    two_months_later = today + timedelta(days=60)
    
    # 勾稽進度表，若已在處理中則不提醒
    processed_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    processed_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日'] <= two_months_later) & (r_df['到期日'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(processed_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(processed_plates))
    ]
    return p_urgent, r_remind

# --- 6. 檔案顯示組件 (手機下載優化) ---
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
                        st.download_button(label=f"📥 下載/查看 PDF: {fn}", data=f, file_name=fn, mime="application/pdf", key=f"dl_{prefix}_{index}_{fn}")
    if not found_any:
        st.caption("目前無附件")

# --- 7. 主介面 ---
st.title("📱 產險行動辦公室")

# 自動提醒區塊 (置頂)
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.expander("🚨 系統自動提醒 (重要)", expanded=True):
        if not p_urgent.empty:
            st.markdown("**📅 案子今日/週末到期**")
            st.dataframe(p_urgent[['被保險人姓名', '牌照號碼', '到期日']], hide_index=True)
        if not r_remind.empty:
            st.markdown("**⏳ 續保預警 (近2個月)**")
            st.dataframe(r_remind[['被保險人', '牌照號碼', '到期日']], hide_index=True)
    st.divider()

t_ren, t_pro, t_man = st.tabs(["🔍 續保", "📑 進度", "⚙️ 設定"])

def show_data_list(df, name_k, plate_k, id_k, fields, prefix):
    # 手機端搜尋框置頂
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"search_{prefix}", placeholder="輸入關鍵字...")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    # 使用清單式卡片顯示，適合手機滑動
    for i, row in rdf.iterrows():
        label = f"{row.get(name_k)} | {row.get(plate_k)}"
        with st.expander(label):
            # 在手機上將資料與附件上下排列
            st.markdown("**📋 詳細資料**")
            for f in fields: 
                val = row.get(f)
                if val: st.write(f"**{f}:** {val}")
            
            st.divider()
            st.markdown("**📂 相關附件**")
            display_files(row.get(plate_k), row.get(id_k), prefix, i)

with t_ren: show_data_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")
with t_pro: show_data_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p")

# 系統管理分頁
with t_man:
    if st.button("🔓 登出系統", type="primary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
    
    st.subheader("📊 資料同步")
    u_r = st.file_uploader("上傳續保 Excel", type="xlsx")
    if u_r:
        st.session_state.renew_db = pd.read_excel(u_r).fillna("")
        save_data(st.session_state.renew_db, DB_RENEW); st.success("更新成功"); st.rerun()
    
    u_p = st.file_uploader("上傳進度 Excel", type="xlsx")
    if u_p:
        st.session_state.prog_db = pd.read_excel(u_p).fillna("")
        save_data(st.session_state.prog_db, DB_PROG); st.success("更新成功"); st.rerun()

    st.subheader("📁 附件上傳")
    up_files = st.file_uploader("批次上傳 (含車牌或ID)", accept_multiple_files=True)
    if up_files:
        for f in up_files:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.success("上傳完成"); st.rerun()

# --- 8. 側邊欄：手動錄入 (適合手機側滑開啟) ---
with st.sidebar:
    st.header("➕ 快速錄入")
    target = st.selectbox("選擇表格", ["續保明細", "出單進度"])
    with st.form("sidebar_form", clear_on_submit=True):
        entry = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f: entry[f] = str(st.date_input(f))
            else: entry[f] = st.text_input(f)
        if st.form_submit_button("確認新增", use_container_width=True):
            new_df = pd.DataFrame([entry])
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_df], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_df], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("已存檔"); st.rerun()