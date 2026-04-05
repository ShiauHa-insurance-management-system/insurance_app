import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 基礎設定與持久化路徑 ---
st.set_page_config(page_title="產險行動辦公室", layout="wide", initial_sidebar_state="collapsed")
ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

# 確保資料夾存在
if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位精確定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 資料讀取與儲存函數 ---
def load_data(file_path, cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path).fillna("")
            # 確保欄位完全符合，避免 KeyError
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

# 初始化資料
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)

# --- 4. 密碼驗證系統 ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 產險管理系統 - 行動登入")
    pwd = st.text_input("請輸入授權密碼", type="password")
    if st.button("確認登入"):
        if pwd == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    st.stop()

# --- 5. 側邊欄：手動新增與登出 ---
with st.sidebar:
    if st.button("🔓 安全登出"):
        st.session_state.auth = False
        st.rerun()
    
    st.header("➕ 行動手動錄入")
    target = st.selectbox("存入目標", ["續保明細", "出單進度"])
    
    with st.form("sidebar_form", clear_on_submit=True):
        entry = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f:
                entry[f] = str(st.date_input(f))
            else:
                entry[f] = st.text_input(f)
        
        if st.form_submit_button("確認新增"):
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, pd.DataFrame([entry])], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, pd.DataFrame([entry])], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("資料已永久儲存！")
            st.rerun()

# --- 6. 儀表板 (手機優化) ---
st.title("📱 產險行動辦公室")
today = datetime.now().date()

# 急件提醒邏輯
urgent_list = pd.DataFrame()
if not st.session_state.prog_db.empty:
    temp_p = st.session_state.prog_db.copy()
    temp_p['dt'] = pd.to_datetime(temp_p['到期日'], errors='coerce').dt.date
    targets = [today]
    if today.weekday() == 4: targets += [today + timedelta(1), today + timedelta(2)]
    urgent_list = temp_p[temp_p['dt'].isin(targets)]

st.metric("今日/週末急件", len(urgent_list))
if not urgent_list.empty:
    st.dataframe(urgent_list[['被保險人姓名', '牌照號碼', '到期日']], hide_index=True)

# --- 7. 分頁查詢功能 ---
t_ren, t_pro, t_man = st.tabs(["🔍 續保", "📑 進度", "⚙️ 管理"])

def show_ui(df, name_key, plate_key, id_key, fields, prefix):
    query = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"q_{prefix}")
    # 執行過濾
    if query:
        rdf = df[df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)]
    else:
        rdf = df

    for i, row in rdf.iterrows():
        label = f"{row.get(name_key, '無姓名')} | {row.get(plate_key, '無車牌')}"
        with st.expander(label):
            c1, c2 = st.columns([2, 1])
            with c1:
                for f in fields: st.write(f"**{f}:** {row.get(f, '')}")
            with c2:
                st.write("📂 關聯附件")
                m_keys = [str(row.get(plate_key, '')), str(row.get(id_key, ''))]
                if os.path.exists(ATTACH_DIR):
                    for fn in os.listdir(ATTACH_DIR):
                        if any(k in fn for k in m_keys if k and k != "nan"):
                            fpath = os.path.join(ATTACH_DIR, fn)
                            if fn.lower().endswith(('.png', '.jpg', '.jpeg')): st.image(fpath)
                            st.download_button(f"📄 開啟 {fn}", data=open(fpath,"rb"), file_name=fn, key=f"dl_{prefix}_{i}_{fn}")

with t_ren:
    show_ui(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "r")

with t_pro:
    show_ui(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "p")

with t_man:
    st.subheader("📊 數據覆蓋上傳 (Excel)")
    u_r = st.file_uploader("上傳續保 Excel", type="xlsx")
    if u_r:
        st.session_state.renew_db = pd.read_excel(u_r).fillna("")
        save_data(st.session_state.renew_db, DB_RENEW)
        st.success("續保資料已同步至伺服器"); st.rerun()
    
    u_p = st.file_uploader("上傳進度 Excel", type="xlsx")
    if u_p:
        st.session_state.prog_db = pd.read_excel(u_p).fillna("")
        save_data(st.session_state.prog_db, DB_PROG)
        st.success("進度資料已同步至伺服器"); st.rerun()

    st.divider()
    st.subheader("🖼️ 附件管理")
    up_files = st.file_uploader("批次上傳照片", accept_multiple_files=True)
    if up_files:
        for f in up_files:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.success("附件已存檔"); st.rerun()
    
    for f in os.listdir(ATTACH_DIR):
        if f == ".gitkeep": continue
        c_n, c_d = st.columns([4, 1])
        c_n.write(f)
        if c_d.button("❌", key=f"del_{f}"):
            os.remove(os.path.join(ATTACH_DIR, f)); st.rerun()