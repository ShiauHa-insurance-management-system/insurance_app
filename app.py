import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. 系統路徑與基礎設定 ---
st.set_page_config(page_title="產險大師-智慧行動辦公室", layout="wide")
ATTACH_DIR = "attachments"
if not os.path.exists(ATTACH_DIR):
    os.makedirs(ATTACH_DIR)

# --- 2. 欄位定義 (完全對接您的要求) ---
RENEW_FIELDS = ["投保險種", "被保險人", "被保險人ID", "要保人", "要保人ID", "電話", "出單日", "起保日", "到期日", "保費", "牌照號碼", "業務來源", "行員 ID", "行員姓名", "通訊地址", "收費地址", "標的物地址"]
PROG_FIELDS = ["保險種類", "被保險人姓名", "給業代/客人繳費方式日", "起保日", "到期日", "保險費用", "是否繳費", "牌照號碼", "業務來源", "業務人員/產險證字號", "實際服務人員", "通路代號", "網銀匯款日期", "繳費方式", "交給核保日", "摺單日", "送單日", "新年度保單號碼", "被保險人通訊地址", "被保險人身份證字號/統一編號", "要保人姓名", "要保人身份證字號/統一編號", "公司負責人", "公司負責人身分證字號", "公司負責人出生年月日"]

# 初始化 Session State 資料庫
if "renew_db" not in st.session_state: st.session_state.renew_db = pd.DataFrame(columns=RENEW_FIELDS)
if "prog_db" not in st.session_state: st.session_state.prog_db = pd.DataFrame(columns=PROG_FIELDS)

# --- 3. 側邊欄：手動新增 (動態對應 17/25 欄位) ---
st.sidebar.header("➕ 行動手動錄入")
db_choice = st.sidebar.selectbox("存入目標資料庫", ["續保明細", "出單進度"])

with st.sidebar.form("manual_entry_form", clear_on_submit=True):
    new_entry = {}
    current_fields = RENEW_FIELDS if db_choice == "續保明細" else PROG_FIELDS
    
    st.write(f"請輸入 {db_choice} 資料：")
    for field in current_fields:
        if "日" in field and "期" in field or field.endswith("日"):
            new_entry[field] = str(st.date_input(field, key=f"sidebar_{field}"))
        else:
            new_entry[field] = st.text_input(field, key=f"sidebar_{field}")
    
    if st.form_submit_button("確認新增"):
        if db_choice == "續保明細":
            st.session_state.renew_db = pd.concat([st.session_state.renew_db, pd.DataFrame([new_entry])], ignore_index=True)
        else:
            st.session_state.prog_db = pd.concat([st.session_state.prog_db, pd.DataFrame([new_entry])], ignore_index=True)
        st.success(f"✅ 已成功存入 {db_choice}！")

# --- 4. 智慧提醒運算 (週末提前 + 2個月預警 + 自動勾稽) ---
def calculate_reminders():
    today = datetime.now().date()
    # A. 案進急件 (週末提前)
    df_p = st.session_state.prog_db.copy()
    urgent_p = pd.DataFrame()
    if not df_p.empty:
        df_p['到期日_dt'] = pd.to_datetime(df_p['到期日'], errors='coerce').dt.date
        target_dates = [today]
        if today.weekday() == 4: # 週五則包含六日
            target_dates += [today + timedelta(days=1), today + timedelta(days=2)]
        urgent_p = df_p[df_p['到期日_dt'].isin(target_dates)]

    # B. 續保預警 (60天 + 跨表勾稽)
    df_r = st.session_state.renew_db.copy()
    remind_r = pd.DataFrame()
    if not df_r.empty:
        df_r['到期日_dt'] = pd.to_datetime(df_r['到期日'], errors='coerce').dt.date
        remind_r = df_r[(df_r['到期日_dt'] >= today) & (df_r['到期日_dt'] <= today + timedelta(days=60))]
        # 自動勾稽：排除已出現在進度表中的客戶
        p_ids = st.session_state.prog_db['被保險人身份證字號/統一編號'].astype(str).unique()
        remind_r = remind_r[~remind_r['被保險人ID'].astype(str).isin(p_ids)]
    return urgent_p, remind_r

# --- 5. 主儀表板呈現 ---
st.title("🛡️ 產險大師行動辦公系統")
up_p, rm_r = calculate_reminders()

col1, col2 = st.columns(2)
with col1:
    st.error(f"🚨 今日/週末案進急件：{len(up_p)} 筆")
    if not up_p.empty: st.dataframe(up_p[['被保險人姓名', '牌照號碼', '到期日']], use_container_width=True)
with col2:
    st.warning(f"⏳ 續保預警 (60天內)：{len(rm_r)} 筆")
    if not rm_r.empty: st.dataframe(rm_r[['被保險人', '牌照號碼', '到期日']], use_container_width=True)

# --- 6. 分頁功能：查詢與檔案管理 ---
tab_renew, tab_prog, tab_files = st.tabs(["🔍 續保明細查詢", "📑 出單進度查詢", "📤 檔案與上傳專區"])

def show_data_list(df, name_col, id_col, plate_col, fields, key_prefix):
    # 【關鍵功能】關鍵字查詢框
    query = st.text_input(f"🔍 搜尋客戶姓名、車牌或證號", key=f"q_{key_prefix}")
    
    if query:
        # 全欄位關鍵字過濾
        display_df = df[df.astype(str).apply(lambda x: x.str.contains(query, case=False)).any(axis=1)]
    else:
        display_df = df

    if display_df.empty:
        st.info("目前無符合條件的資料。")
    else:
        for i, row in display_df.iterrows():
            with st.expander(f"👤 {row[name_col]} | 🚗 {row[plate_col]} | 📅 {row['到期日']}"):
                c_info, c_file = st.columns([2, 1])
                with c_info:
                    for f in fields: st.write(f"**{f}:** {row.get(f,'')}")
                with c_file:
                    st.write("📂 關聯附件")
                    # 智慧檔名匹配邏輯
                    m_keys = [str(row.get(plate_col,'')), str(row.get(id_col,''))]
                    for f_name in os.listdir(ATTACH_DIR):
                        if any(k in f_name for k in m_keys if k != "" and k != "nan"):
                            f_path = os.path.join(ATTACH_DIR, f_name)
                            if f_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(f_path)
                            st.download_button(f"📄 開啟 {f_name}", data=open(f_path,"rb"), file_name=f_name, key=f"dl_{key_prefix}_{i}_{f_name}")

with tab_renew:
    show_data_list(st.session_state.renew_db, "被保險人", "被保險人ID", "牌照號碼", RENEW_FIELDS, "ren")

with tab_prog:
    show_data_list(st.session_state.prog_db, "被保險人姓名", "被保險人身份證字號/統一編號", "牌照號碼", PROG_FIELDS, "pro")

# --- 7. 檔案管理與刪除 ---
with tab_files:
    st.subheader("📊 資料庫覆蓋更新")
    up_r = st.file_uploader("上傳最新【續保明細 Excel】", type=["xlsx"])
    if up_r: 
        st.session_state.renew_db = pd.read_excel(up_r)
        st.success("續保明細已更新")
        st.rerun()
    
    up_p = st.file_uploader("上傳最新【出單進度 Excel】", type=["xlsx"])
    if up_p: 
        st.session_state.prog_db = pd.read_excel(up_p)
        st.success("出單進度已更新")
        st.rerun()

    st.divider()
    st.subheader("🖼️ 附件管理 (歸檔與刪除)")
    up_att = st.file_uploader("批次上傳圖片/PDF (檔名請含車牌或ID)", accept_multiple_files=True)
    if up_att:
        for f in up_att:
            with open(os.path.join(ATTACH_DIR, f.name), "wb") as sf: sf.write(f.getbuffer())
        st.success("附件上傳成功")
        st.rerun()

    st.write("目前系統內檔案：")
    for f in os.listdir(ATTACH_DIR):
        if f == ".gitkeep": continue
        c_fname, c_del = st.columns([4, 1])
        c_fname.write(f)
        if c_del.button("❌ 刪除", key=f"del_file_{f}"):
            os.remove(os.path.join(ATTACH_DIR, f))
            st.rerun()