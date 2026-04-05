import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time
import random

# --- 1. الإعدادات وتنسيق الواجهة ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

GAS_URL = "https://script.google.com/macros/s/AKfycbzZvxhGjYN-nOm8Fgz1IZUAJJyjlwYu8sOtDXqU--P_Sohb7qT-mjSr5WLgICGMYLYYlA/exec"

st.markdown("""
    <style>
    .arabic-sub { direction: rtl; text-align: right; color: #6c757d; font-size: 0.85em; display: block; margin-bottom: 10px; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (المعدل لحل الـ KeyError) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    
    # السر هنا: تنظيف أسماء الأعمدة نفسها من أي مسافات زائدة
    df.columns = [str(c).strip() for c in df.columns]
    
    # تنظيف محتوى الأعمدة
    cols_to_fix = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password']
    for col in df.columns:
        if col in cols_to_fix:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- 4. نظام الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role_choice = st.selectbox("Login as", ["Student / طالب", "Teacher / معلم"])
    with st.form("login_gate"):
        u_id = st.text_input("User ID").strip()
        u_pw = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Sign In"):
            target = "Students" if "Student" in role_choice else "Users"
            df_u = clean_data(load_sheet(target))
            match = df_u[(df_u['ID'] == u_id) & (df_u['Password'] == u_pw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': 'student' if "Student" in role_choice else 'teacher'})
                st.rerun()
            else: st.error("Wrong ID or Password")

# --- 5. لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("Navigation", ["📊 Results Matrix", "📚 Exams Library", "📝 Exams Manager"])
    
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))

    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        st.dataframe(df_grd, use_container_width=True)

    elif menu == "📚 Exams Library":
        st.header("Exams Library")
        for _, row in df_exm.iterrows():
            with st.expander(f"📖 {row['Title']}"):
                p_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                st.markdown(f'<a href="{p_url}" target="_blank">Preview Exam</a>', unsafe_allow_html=True)

    elif menu == "📝 Exams Manager":
        st.header("Exams Manager")
        with st.form("new_ex"):
            eid = st.text_input("Exam ID")
            etitle = st.text_input("Title")
            esec = st.text_input("Section (e.g., 12A)")
            if st.form_submit_button("Publish"):
                new_row = pd.DataFrame([{"Exam_ID": eid, "Title": etitle, "Section": esec, "Status": "Active"}])
                conn.update(worksheet="Exams", data=pd.concat([df_exm, new_row], ignore_index=True))
                st.success("Published!"); st.rerun()

# --- 6. لوحة الطالب (تم إصلاح خطأ الـ Student_ID هنا) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    
    # فحص أمان: هل عمود Student_ID موجود فعلاً؟
    if not df_gr_stu.empty and 'Student_ID' in df_gr_stu.columns:
        my_subs = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]
    else:
        my_subs = pd.DataFrame(columns=['Exam_ID', 'Score']) # شيت فاضي لو مفيش درجات

    taken_ids = my_subs['Exam_ID'].unique().tolist() if not my_subs.empty else []

    st.title(f"Welcome, {u['Name']} 👋")
    tab1, tab2 = st.tabs(["📋 Assignments", "✅ History"])

    with tab1:
        st.subheader("Pending Exams")
        # فلترة ذكية للاختبارات الخاصة بشعبة الطالب
        pending = df_ex_stu[~df_ex_stu['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        
        for _, row in pending.iterrows():
            if str(u['Section']) in str(row['Section']):
                with st.container():
                    st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                    exam_url = f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam"
                    st.markdown(f'<a href="{exam_url}" target="_blank"><button style="width:100%; background:#28a745; color:white; border:none; padding:10px; border-radius:8px; cursor:pointer;">Start Exam</button></a>', unsafe_allow_html=True)

    with tab2:
        st.subheader("Your Submission History")
        if not my_subs.empty:
            for _, sub in my_subs.iterrows():
                st.write(f"✅ Exam: **{sub['Exam_ID']}** | Score: **{sub['Score']}%**")
                review_url = f"{GAS_URL}?sid={u['ID']}&eid={sub['Exam_ID']}&name={u['Name']}&mode=review"
                st.markdown(f'<a href="{review_url}" target="_blank">Review Answers</a>', unsafe_allow_html=True)
        else:
            st.info("No completed exams yet.")

if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
