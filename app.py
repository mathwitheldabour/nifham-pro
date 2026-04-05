import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time, random

# --- 1. الإعدادات الأساسية ودوال التنظيف (يجب أن تكون في البداية) ---
st.set_page_config(page_title="NIFHAM Pro", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0)

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    # تنظيف المسافات والنصوص
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    # تحويل الدرجة لرقم
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 2. التحقق من الدخول ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role_choice = st.selectbox("Login as", ["Student", "Teacher"])
    with st.form("login_gate"):
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            target_sheet = "Students" if role_choice == "Student" else "Users"
            users_df = clean_data(load_sheet(target_sheet))
            match = users_df[(users_df['ID'] == u_id) & (users_df['Password'] == u_pw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': role_choice.lower()})
                st.rerun()
            else: st.error("Wrong ID or Password!")

# --- 3. لوحة المعلم (Teacher Dashboard) - تم الإصلاح ---
elif st.session_state.role == 'teacher':
    st.sidebar.success(f"Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("Navigation", ["📊 Results Matrix", "📝 Exams Manager", "⚙️ Settings"])
    
    # تحميل البيانات (داخل النطاق الصحيح)
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    all_sec = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        sel = st.selectbox("Section", ["All"] + all_sec)
        f_stu = df_stu[df_stu['Section'] == sel] if sel != "All" else df_stu
        merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
        if not merged['Exam_ID'].dropna().empty:
            matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
            st.dataframe(matrix, use_container_width=True)

    elif menu == "📝 Exams Manager":
        st.header("Exams Manager")
        with st.form("exam_creation"):
            eid = st.text_input("Exam Code")
            etitle = st.text_input("Title")
            col1, col2 = st.columns(2)
            with col1: sd = st.date_input("Start Date"); stm = st.time_input("Start Time")
            with col2: ed = st.date_input("End Date"); etm = st.time_input("End Time")
            esections = st.multiselect("Sections", all_sec)
            allow_review = st.checkbox("Allow Students to review answers after submission", value=True)
            if st.form_submit_button("Publish"):
                new_ex = pd.DataFrame([{"Exam_ID": eid, "Title": etitle, "Section": ",".join(esections), "Status": "Active", "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}", "Allow_Review": str(allow_review)}])
                conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                st.success("Exam Published!"); st.rerun()

# --- 4. لوحة الطالب (Student Dashboard) - ميزة المراجعة ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    
    # معرفة الاختبارات التي تم حلها
    my_submissions = df_gr[df_gr['Student_ID'] == str(u['ID'])]
    taken_ids = my_submissions['Exam_ID'].unique().tolist()

    st.title(f"Student Portal | {u['Name']}")
    t1, t2 = st.tabs(["📋 Assigned Exams", "✅ Completed & Review"])

    with t1:
        now = datetime.now()
        # عرض الاختبارات النشطة التي لم يحلها بعد
        active_req = df_ex[(df_ex['Section'].str.contains(str(u['Section']), na=False))]
        pending = active_req[~active_req['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        
        for _, r in pending.iterrows():
            st.info(f"Exam: {r['Title']}")
            # رابط الـ GAS (استبدل بالرابط الخاص بك)
            gas_url = "https://nifham-pro.streamlit.app/"
            link = f"https://script.google.com/macros/s/AKfycbxvSS3YRa4_u7aH4_OiNJ9jCjiEMFDPo3MqYj1JC0KWQMISJQwdJoY3FwqMFyxzN5yXiQ/exec"
            st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><button style="background:#28a745; color:white; border:none; padding:10px; border-radius:5px; width:100%;">Start Exam</button></a>', unsafe_allow_html=True)

    with t2:
        st.subheader("Your Submission History")
        completed = active_req[active_req['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        
        for _, r in completed.iterrows():
            score = my_submissions[my_submissions['Exam_ID'] == r['Exam_ID']]['Score'].iloc[0]
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"**{r['Title']}** | Score: {score}%")
            
            # ميزة المراجعة
            if str(r.get('Allow_Review', 'True')) == 'True':
                gas_url = "رابط_الـ_Web_App_الخاص_بك_هنا"
                review_link = f"{gas_url}?sid={u['ID']}&eid={r['Exam_ID']}&name={u['Name']}&mode=review"
                col_b.markdown(f'<a href="{review_link}" target="_blank">Review Answers</a>', unsafe_allow_html=True)
            else:
                col_b.write("Review Disabled")

if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
