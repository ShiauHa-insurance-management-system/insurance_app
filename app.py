import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統設定 (強化手機適配) ---
st.set_page_config(page_title="產險行動辦公室", layout="wide", initial_sidebar_state="collapsed")
ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR): os.makedirs(ATTACH_DIR)

# 欄位定義
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 2. 資料持久化與安全檢查 (防止 KeyError) ---
def load_data(path, cols):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path).fillna("")
            # 補齊缺失欄位避免報錯
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")

# 初始化
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 3. 登入邏輯 (強制停留) ---
if not st.session_state.auth:
    st.title("🔐 系統安全登入")
    pwd = st.text_input("請輸入密碼", type="password")
    if st.button("登入"):
        if pwd == "1234":
            st.session_state.auth = True
            st.rerun()
        else: st.error("密碼錯誤")
    st.stop()

# --- 4. 側邊欄：僅保留手動新增 ---
with st.sidebar:
    st.header("➕ 手動錄入")
    target = st.selectbox("存入目標", ["續保明細", "出單進度"])
    with st.form("entry_form", clear_on_submit=True):
        entry = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f: entry[f] = str(st.date_input(f))
            else: entry[f] = st.text_input(f)
        if st.form_submit_button("確認新增"):
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, pd.DataFrame([entry])], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, pd.DataFrame([entry])], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("已儲存"); st.rerun()

# --- 5. 主介面：將登出移入管理分頁 (防止手機誤觸) ---
st.title("📱 產險行動辦公室")
t_ren, t_pro, t_man = st.tabs(["🔍 續保", "📑 進度", "⚙️ 管理"])

def show_list(df, name_key, plate_key, id_key, fields, prefix):
    # 增加搜尋框穩定性
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"search_{prefix}", placeholder="輸入關鍵字...")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    if rdf.empty:
        st.info("查無資料")
        return

    for i, row in rdf.iterrows():
        # 使用 .get 確保不因欄位缺失而報錯
        label = f"👤 {row.get(name_key, '無姓名')} | 🚗 {row.get(plate_key, '無車牌')}"
        with st.expander(label):
            c1, c2 = st.columns([2, 1])
            with c1:
                for f in fields: st.write(f"**{f}:** {row.get(f, '')}")
            with c2:
                st.write("📂 附件")
                m_keys = [str(row.get(plate_key, '')), str(row.get(id_key, ''))]
                for fn in os.listdir(ATTACH_DIR):
                    if any(k in fn for k in m_keys if k and k != "nan" and k != ""):
                        f_path = os.path.join(ATTACH_DIR, fn)
                        if fn.lower().endswith(('.png', '.jpg', '.jpeg')): st.image(f_path)
                        st.download_button(f"📄 開啟", data=open(f_path,"rb"), file_name=fn, key=f"dl_{prefix}_{i}_{fn}")

with t_ren: show_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")
with t_pro: show_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p")

with t_man:
    # 登出按鈕移到這裡，避免手機滑動側邊欄時誤點
    if st.button("🔓 安全登出系統"):
        st.session_state.auth = False
        st.rerun()
    
    st.divider()
    st.subheader("Excel 覆蓋上傳")
    u_r = st.file_uploader("更新續保明細", type="xlsx")
    if u_r: 
        st.session_state.renew_db = pd.read_excel(u_r).fillna(""); save_data(st.session_state.renew_db, DB_RENEW); st.rerun()
    u_p = st.file_uploader("更新出單進度", type="xlsx")
    if u_p: 
        st.session_state.prog_db = pd.read_excel(u_p).fillna(""); save_data(st.session_state.prog_db, DB_PROG); st.rerun()