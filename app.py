import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 全平台存取與操作優化 ---
st.set_page_config(
    page_title="產險行動辦公室", 
    layout="wide", 
    initial_sidebar_state="expanded" 
)

# 目錄與檔案設定
ATTACH_DIR = "attachments"
DB_RENEW = "renew_db.csv"
DB_PROG = "prog_db.csv"

if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 資料結構與欄位精確定義 ---
# 續保明細 (17 欄位)
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
# 出單進度 (25 欄位)
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# --- 5. 穩定性要求：防錯機制 (解決 KeyError) ---
def load_data(file_path, cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path).fillna("")
            # 清洗標題空格，解決 KeyError
            df.columns = [str(c).strip() for c in df.columns] 
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: 
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, file_path):
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

# 初始化 Session 狀態
if "renew_db" not in st.session_state: st.session_state.renew_db = load_data(DB_RENEW, RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = load_data(DB_PROG, PROG_FIELDS)
if "auth" not in st.session_state: st.session_state.auth = False

# --- 4. 手機端操作優化：安全性 (密碼機制) ---
if not st.session_state.auth:
    st.title("🔐 產險管理系統")
    with st.form("login_form"):
        pwd = st.text_input("請輸入授權密碼", type="password")
        # 手機優化：加寬按鈕
        if st.form_submit_button("確認登入", use_container_width=True):
            if pwd == "085799":
                st.session_state.auth = True
                st.rerun()
            else: 
                st.error("密碼錯誤")
    st.stop()

# --- 1. 核心智慧提醒邏輯 (系統大腦) ---
def get_reminders():
    today = datetime.now().date()
    
    # A. 進度表追蹤：假日提前處理邏輯
    target_dates = [today]
    if today.weekday() == 4: # 若今天是週五，自動包含週六、週日
        target_dates.append(today + timedelta(days=1))
        target_dates.append(today + timedelta(days=2))

    p_df = st.session_state.prog_db.copy()
    p_df['到期日_dt'] = pd.to_datetime(p_df['到期日'], errors='coerce').dt.date
    p_urgent = p_df[p_df['到期日_dt'].isin(target_dates)]

    # B. 續保預警：2個月預警 + 自動勾稽停止
    r_df = st.session_state.renew_db.copy()
    r_df['到期日_dt'] = pd.to_datetime(r_df['到期日'], errors='coerce').dt.date
    two_months_limit = today + timedelta(days=60)
    
    # 建立勾稽比對清單 (進度表已有的案子)
    proc_ids = set(st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str))
    proc_plates = set(st.session_state.prog_db['牌照號碼'].astype(str))

    r_remind = r_df[
        (r_df['到期日_dt'] <= two_months_limit) & (r_df['到期日_dt'] >= today) &
        (~r_df['被保險人ID'].astype(str).isin(proc_ids)) &
        (~r_df['牌照號碼'].astype(str).isin(proc_plates))
    ]
    return p_urgent, r_remind

# --- 3. 自動化歸檔與附件管理 (智慧配對) ---
def display_files(plate, uid, prefix, index):
    m_keys = [str(plate).strip(), str(uid).strip()]
    m_keys = [k for k in m_keys if k and k != "nan" and k != ""]
    
    if os.path.exists(ATTACH_DIR):
        for fn in os.listdir(ATTACH_DIR):
            if any(k in fn for k in m_keys):
                fpath = os.path.join(ATTACH_DIR, fn)
                ext = fn.lower().split('.')[-1]
                # 多元格式支援：圖片預覽
                if ext in ['png', 'jpg', 'jpeg']:
                    st.image(fpath, caption=f"附件: {fn}", use_container_width=True)
                # 多元格式支援：PDF 下載鈕
                elif ext == 'pdf':
                    with open(fpath, "rb") as f:
                        st.download_button(
                            label=f"📥 查看 PDF: {fn}",
                            data=f,
                            file_name=fn,
                            key=f"dl_{prefix}_{index}_{fn}",
                            use_container_width=True
                        )

# --- 系統介面佈局 ---
st.title("📱 產險行動辦公室")

# --- 左側手動錄入區 (常駐功能，畫面穩定) ---
with st.sidebar:
    st.header("➕ 手動錄入")
    target_table = st.selectbox("存入目標", ["續保明細", "出單進度"])
    # 解決 Missing Submit Button 問題
    with st.form("manual_entry_form", clear_on_submit=True):
        entry_data = {}
        fields = RENEW_FIELDS if target_table == "續保明細" else PROG_FIELDS
        for f in fields:
            if "日" in f:
                entry_data[f] = str(st.date_input(f))
            else:
                entry_data[f] = st.text_input(f)
        
        if st.form_submit_button("確認存檔", use_container_width=True):
            new_row = pd.DataFrame([entry_data])
            if target_table == "續保明細":
                st.session_state.renew_db = pd.concat([st.session_state.renew_db, new_row], ignore_index=True)
                save_data(st.session_state.renew_db, DB_RENEW)
            else:
                st.session_state.prog_db = pd.concat([st.session_state.prog_db, new_row], ignore_index=True)
                save_data(st.session_state.prog_db, DB_PROG)
            st.success("資料已成功手動錄入")
            st.rerun()

# --- 1. 核心智慧提醒 (主頁面最上方) ---
p_urgent, r_remind = get_reminders()
if not p_urgent.empty or not r_remind.empty:
    with st.expander("🚨 今日核心作業提醒", expanded=True):
        if not p_urgent.empty:
            st.markdown("**📍 案子進度到期提醒 (含假日提前)**")
            for _, r in p_urgent.iterrows():
                st.error(f"⚠️ {r['被保險人姓名']} | {r['牌照號碼']} (到期日: {r['到期日']})")
        
        if not r_remind.empty:
            st.markdown("**⏳ 續保預警 (2個月內且未入件)**")
            for _, r in r_remind.iterrows():
                st.warning(f"🔔 {r['被保險人']} | {r['牌照號碼']} (到期日: {r['到期日']})")
    st.divider()

# --- 4. 快速搜尋與分頁 (單手操作優化) ---
t_ren, t_pro, t_man = st.tabs(["🔍 續保清單", "📑 進度查詢", "⚙️ 管理分頁"])

def render_data_list(df, name_key, plate_key, id_key, fields, prefix):
    # 手機優化：加寬搜尋框
    q = st.text_input(f"🔎 搜尋姓名/車牌/ID", key=f"q_{prefix}", placeholder="快速過濾任務...")
    display_df = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)] if q else df
    
    for i, row in display_df.iterrows():
        # 手機優化：摺疊面板顯示詳細資料
        with st.expander(f"👤 {row.get(name_key)} | 🚗 {row.get(plate_key)}"):
            st.markdown("**📋 詳細明細**")
            for f in fields:
                if row.get(f):
                    st.write(f"**{f}:** {row.get(f)}")
            st.divider()
            st.markdown("**📂 智慧配對附件**")
            display_files(row.get(plate_key), row.get(id_key), prefix, i)

with t_ren:
    render_data_list(st.session_state.renew_db, "被保險人", "牌照號碼", "被保險人ID", RENEW_FIELDS, "ren")

with t_pro:
    render_data_list(st.session_state.prog_db, "被保險人姓名", "牌照號碼", "被保險人身份證字號/統一編號", PROG_FIELDS, "prog")

with t_man:
    # 顯眼的「安全登出」按鈕
    if st.button("🔓 安全登出系統", type="primary", use_container_width=True):
        st.session_state.auth = False
        st.rerun()
    st.divider()
    
    # 雙軌輸入：Excel 整批上傳
    st.subheader("📊 資料批次更新")
    ur = st.file_uploader("上傳續保清單 (Excel)", type="xlsx")
    if ur:
        st.session_state.renew_db = pd.read_excel(ur).fillna("")
        save_data(st.session_state.renew_db, DB_RENEW)
        st.rerun()
    
    up = st.file_uploader("上傳出單進度 (Excel)", type="xlsx")
    if up:
        st.session_state.prog_db = pd.read_excel(up).fillna("")
        save_data(st.session_state.prog_db, DB_PROG)
        st.rerun()
    
    st.divider()
    st.subheader("📁 附件批次同步")
    files = st.file_uploader("上傳附件 (檔名含車牌或ID)", accept_multiple_files=True)
    if files:
        for f in files:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf:
                sf.write(f.getbuffer())
        st.success(f"成功存入 {len(files)} 個附件檔案"); st.rerun()