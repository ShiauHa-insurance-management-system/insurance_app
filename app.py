import streamlit as st
import pandas as pd
import os

# --- 1. 手機版優化設定 ---
st.set_page_config(page_title="產險行動辦公室", layout="wide", initial_sidebar_state="collapsed")

# 欄位定義 (請確保與您的 Excel 標題一致)
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# 修正 KeyError 的讀取邏輯
def safe_read(path, target_cols):
    if os.path.exists(path):
        df = pd.read_csv(path).fillna("")
        for col in target_cols:
            if col not in df.columns: df[col] = "" # 補齊缺失欄位防止報錯
        return df[target_cols]
    return pd.DataFrame(columns=target_cols)

# --- 2. 登入系統 ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 系統安全登入")
    pwd = st.text_input("請輸入密碼", type="password")
    if st.button("確認"):
        if pwd == "085799":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 3. 主介面 ---
st.title("📱 產險行動辦公室")
t_ren, t_pro, t_man = st.tabs(["🔍 續保", "📑 進度", "⚙️ 管理"])

# 讀取資料
ren_df = safe_read("renew_db.csv", RENEW_FIELDS)
pro_df = safe_read("prog_db.csv", PROG_FIELDS)

with t_ren:
    q = st.text_input("搜尋姓名/車牌", key="q_r")
    rdf = ren_df[ren_df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else ren_df
    for i, row in rdf.iterrows():
        with st.expander(f"👤 {row.get('被保險人', '未知')} | 🚗 {row.get('牌照號碼', '無')}"):
            for f in RENEW_FIELDS: st.write(f"**{f}:** {row.get(f, '')}")

with t_man:
    if st.button("安全登出"):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    u_f = st.file_uploader("上傳最新 Excel 建立資料庫", type="xlsx")
    if u_f:
        pd.read_excel(u_f).fillna("").to_csv("renew_db.csv", index=False)
        st.success("資料已建立，請重新整理"); st.rerun()