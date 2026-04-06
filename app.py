import streamlit as st
import pandas as pd
import os

# 1. 基礎設定
st.set_page_config(page_title="產險行動辦公室", layout="wide")

# 欄位定義 (確保跟您的 Excel 標題完全一致)
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]

# 登入邏輯
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 系統安全登入")
    pwd = st.text_input("請輸入密碼", type="password")
    if st.button("確認登入"):
        if pwd == "085799":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# 2. 安全讀取函數 (解決 KeyError)
def safe_load():
    if os.path.exists("renew_db.csv"):
        try:
            df = pd.read_csv("renew_db.csv").fillna("")
            # 核心修復：如果 Excel 沒這欄位，就自動補一個空的，才不會報錯
            for col in RENEW_FIELDS:
                if col not in df.columns: df[col] = ""
            return df
        except: return pd.DataFrame(columns=RENEW_FIELDS)
    return pd.DataFrame(columns=RENEW_FIELDS)

st.title("📱 產險行動辦公室")
tab1, tab2 = st.tabs(["🔍 續保搜尋", "⚙️ 管理頁面"])

df = safe_load()

with tab1:
    q = st.text_input("搜尋姓名或車牌", key="search_input")
    # 修正搜尋報錯邏輯
    if q:
        rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
    else:
        rdf = df
    
    for i, row in rdf.iterrows():
        # 使用 .get() 確保抓不到資料時不會當機
        with st.expander(f"👤 {row.get('被保險人', '未知')} | 🚗 {row.get('牌照號碼', '無')}"):
            for f in RENEW_FIELDS: st.write(f"**{f}:** {row.get(f, '')}")

with tab2:
    if st.button("🔓 安全登出"):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    u_f = st.file_uploader("上傳最新 Excel 更新資料庫", type="xlsx")
    if u_f:
        pd.read_excel(u_f).fillna("").to_csv("renew_db.csv", index=False)
        st.success("資料庫上傳成功！"); st.rerun()