import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64

# --- 1. 基礎設定與行動端優化 ---
st.set_page_config(
    page_title="產險行動辦公室-完整版", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位定義 (請確保與您的 Excel 標題一致) ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 安全資料讀取與儲存 (修正 KeyError) ---
def load_data(file_path, cols):
    if os.path.exists(file_path):
        try:
            # 讀取並清除前後空格，防止欄位名稱對不上的問題
            df = pd.read_csv(file_path).fillna("")
            df.columns = [c.strip() for c in df.columns]
            # 自動補齊缺失欄位，防止 KeyError
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

# --- 5. 側邊欄：手動錄入 ---
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
            new_df = pd.DataFrame([entry])
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_df], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_df], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("已存檔"); st.rerun()

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
                    st.write(f"📄 PDF: {fn}")
                    with open(fpath, "rb") as f:
                        st.download_button(label=f"📥 下載/查看", data=f, file_name=fn, mime="application/pdf", key=f"dl_{prefix}_{index}_{fn}")
    if not found_any:
        st.caption("無關聯附件")

# --- 7. 主介面 ---
st.title("📱 產險行動辦公室")
t_ren, t_pro, t_man = st.tabs(["🔍 續保查詢", "📑 進度查詢", "⚙️ 系統管理"])

def show_data_list(df, name_k, plate_k, id_k, fields, prefix):
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"search_{prefix}")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    for i, row in rdf.iterrows():
        # 使用 .get() 確保不會報錯
        label = f"👤 {row.get(name_k, '無姓名')} | 🚗 {row.get(plate_k, '無車牌')}"
        with st.expander(label):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**📋 詳細資料**")
                for f in fields: st.write(f"**{f}:** {row.get(f, '')}")
            with c2:
                st.markdown("**📂 自動歸檔附件**")
                display_files(row.get(plate_k), row.get(id_k), prefix, i)

with t_ren: show_data_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")
with t_pro: show_data_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p")

with t_man:
    if st.button("🔓 安全登出系統", type="primary"):
        st.session_state.auth = False
        st.rerun()
    
    st.divider()
    st.subheader("📊 數據管理 (Excel)")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        u_r = st.file_uploader("上傳續保 Excel", type="xlsx")
        if u_r:
            st.session_state.renew_db = pd.read_excel(u_r).fillna("")
            save_data(st.session_state.renew_db, DB_RENEW); st.success("續保資料已更新"); st.rerun()
    with col_u2:
        u_p = st.file_uploader("上傳進度 Excel", type="xlsx")
        if u_p:
            st.session_state.prog_db = pd.read_excel(u_p).fillna("")
            save_data(st.session_state.prog_db, DB_PROG); st.success("進度資料已更新"); st.rerun()

    st.divider()
    st.subheader("📁 附件上傳 (PDF/圖片)")
    up_files = st.file_uploader("上傳檔案 (檔名包含車牌或ID)", accept_multiple_files=True)
    if up_files:
        for f in up_files:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.success(f"已上傳 {len(up_files)} 個檔案"); st.rerun()
    
    # 伺服器檔案列表與刪除功能
    st.write("目前伺服器檔案列表：")
    for f in os.listdir(ATTACH_DIR):
        if f == ".gitkeep": continue
        c_n, c_d = st.columns([4, 1])
        c_n.write(f)
        if c_d.button("❌", key=f"del_{f}"):
            os.remove(os.path.join(ATTACH_DIR, f)); st.rerun()