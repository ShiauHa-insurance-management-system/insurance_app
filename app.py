import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 全平台操作優化 ---
st.set_page_config(
    page_title="產險行動辦公室", 
    layout="wide", 
    initial_sidebar_state="collapsed" # 手機版建議先收起，騰出空間
)

# 手機端 UI 優化
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3.5em; margin-bottom: 10px; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; height: 3.5em; }
    /* 刪除按鈕特別標色 */
    div[data-testid="stForm"] button[kind="secondary"] { color: white; background-color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位精確定義 ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 3. 穩定性資料處理 ---
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

# 初始化 Session
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 4. 授權登入 ---
if not st.session_state.auth:
    st.title("🔐 產險管理系統")
    with st.form("login_gate"):
        pwd = st.text_input("請輸入授權密碼", type="password")
        if st.form_submit_button("確認登入", use_container_width=True):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: st.error("密碼錯誤")
    st.stop()

# --- 5. 智慧提醒大腦 ---
def get_reminders():
    today = datetime.now().date()
    target_dates = [today]
    if today.weekday() == 4: target_dates.extend([today + timedelta(days=1), today + timedelta(days=2)])

    p_df = st.session_state.prog_db.copy()
    p_df['到期日_dt'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日_dt'].isin(target_dates)]

    r_df = st.session_state.renew_db.copy()
    r_df['到期日_dt'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    limit = today + timedelta(days=60)
    
    proc_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    proc_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日_dt'] <= limit) & (r_df['到期日_dt'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(proc_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(proc_plates))
    ]
    return p_urgent, r_remind

# --- 6. 附件顯示功能 ---
def display_attachments(plate, uid, prefix, idx):
    search_keys = [str(plate).strip(), str(uid).strip()]
    search_keys = [k for k in search_keys if k and k != "nan" and k != ""]
    found = False
    if os.path.exists(ATTACH_DIR):
        for fn in os.listdir(ATTACH_DIR):
            if any(key in fn for key in search_keys):
                found = True
                fpath = os.path.join(ATTACH_DIR, fn)
                ext = fn.lower().split('.')[-1]
                if ext in ['png', 'jpg', 'jpeg']:
                    st.image(fpath, caption=f"圖檔: {fn}", use_container_width=True)
                elif ext == 'pdf':
                    with open(fpath, "rb") as f:
                        st.download_button(label=f"📄 查看 PDF: {fn}", data=f, file_name=fn, key=f"dl_{prefix}_{idx}_{fn}")
    if not found: st.info("ℹ️ 暫無關聯附件")

# --- 7. 主頁面與側邊欄錄入 ---
st.title("📱 產險行動辦公室")

with st.sidebar:
    st.header("➕ 手動錄入")
    target = st.selectbox("存入目標", ["續保明細", "出單進度"])
    with st.form("manual_form", clear_on_submit=True):
        entry_data = {}
        fields = RENEW_FIELDS if target == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f: entry_data[f] = str(st.date_input(f))
            else: entry_data[f] = st.text_input(f)
        if st.form_submit_button("確認存檔", use_container_width=True):
            new_row = pd.DataFrame([entry_data])
            if target == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_row], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_row], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("存檔成功"); st.rerun()

# 顯示提醒
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.expander("🚨 今日核心作業提醒", expanded=True):
        if not p_urgent.empty:
            for _, r in p_urgent.iterrows(): st.error(f"⚠️ {r['被保險人姓名']} | {r['牌照號碼']} ({r['到期日']})")
        if not r_remind.empty:
            for _, r in r_remind.iterrows(): st.warning(f"🔔 {r['被保險人']} | {r['牌照號碼']} ({r['到期日']})")
    st.divider()

# --- 8. 資料列表與 修改/刪除 邏輯 ---
t_ren, t_pro, t_man = st.tabs(["🔍 續保清單", "📑 進度查詢", "⚙️ 管理分頁"])

def render_list(db_key, name_k, plate_k, id_k, fields, prefix, db_file):
    df = st.session_state[db_key]
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"s_{prefix}", placeholder="快速關鍵字搜尋...")
    rdf = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    for i, row in rdf.iterrows():
        with st.expander(f"👤 {row.get(name_k)} | 🚗 {row.get(plate_k)}"):
            # A. 顯示模式
            st.markdown("**📋 詳細資料**")
            for f in fields:
                if row.get(f): st.write(f"**{f}:** {row.get(f)}")
            
            st.divider()
            display_attachments(row.get(plate_k), row.get(id_k), prefix, i)
            st.divider()

            # B. 編輯與刪除按鈕 (並排)
            c1, c2 = st.columns(2)
            edit_mode = st.toggle("📝 啟動編輯/刪除模式", key=f"edit_toggle_{prefix}_{i}")
            
            if edit_mode:
                with st.form(f"form_{prefix}_{i}"):
                    st.subheader("🛠️ 修改資料內容")
                    updated_data = {}
                    for f in fields:
                        # 簡單判斷日期格式
                        if "日" in f:
                            try:
                                curr_date = pd.to_datetime(row.get(f)).date()
                            except:
                                curr_date = datetime.now().date()
                            updated_data[f] = str(st.date_input(f"修改 {f}", value=curr_date))
                        else:
                            updated_data[f] = st.text_input(f"修改 {f}", value=str(row.get(f)))
                    
                    st.divider()
                    st.subheader("🗑️ 危險區域")
                    confirm_del = st.checkbox("我確認要刪除此筆資料", key=f"del_check_{prefix}_{i}")
                    
                    col_save, col_del = st.columns(2)
                    if col_save.form_submit_button("💾 儲存修改", use_container_width=True):
                        st.session_state[db_key].loc[i] = updated_data
                        save_data(st.session_state[db_key], db_file)
                        st.success("修改成功！"); st.rerun()
                    
                    if col_del.form_submit_button("🔥 執行刪除", use_container_width=True):
                        if confirm_del:
                            st.session_state[db_key] = st.session_state[db_key].drop(i).reset_index(drop=True)
                            save_data(st.session_state[db_key], db_file)
                            st.warning("資料已刪除"); st.rerun()
                        else:
                            st.error("請先勾選確認刪除方塊")

with t_ren:
    render_list("renew_db", "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "ren", DB_RENEW)

with t_pro:
    render_list("prog_db", "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "prog", DB_PROG)

with t_man:
    if st.button("🔓 安全登出系統", type="primary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    ur = st.file_uploader("更新續保 Excel", type="xlsx")
    if ur:
        st.session_state.renew_db = pd.read_excel(ur).fillna("")
        save_data(st.session_state.renew_db, DB_RENEW); st.rerun()
    up = st.file_uploader("更新進度 Excel", type="xlsx")
    if up:
        st.session_state.prog_db = pd.read_excel(up).fillna("")
        save_data(st.session_state.prog_db, DB_PROG); st.rerun()
    st.divider()
    af = st.file_uploader("附件批次同步", accept_multiple_files=True)
    if af:
        for f in af:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.success("附件上傳成功"); st.rerun()