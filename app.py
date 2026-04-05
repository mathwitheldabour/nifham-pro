import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random

# الإعدادات الأساسية
st.set_page_config(page_title="NIFHAM Pro", layout="wide")
PASSING_SCORE = 50

# التنسيق البصري
st.markdown("""
    <style>
    .arabic-sub { direction: rtl; text-align: right; color: #6c757d; font-size: 0.9em; display: block; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# الاتصال بالبيانات
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0)

def clean_data(df):
    if df.empty: return df
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Section_Name']
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# إدارة الجلسة
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- منطق الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role = st.selectbox("Login as", ["Student", "Teacher"])
    with st.form("login"):
        u_id = st.text_input("User ID")
        u_pw = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            sheet = "Students" if role == "Student" else "Users"
            df_u = clean_data(load_sheet(sheet))
            match = df_u[(df_u['ID'] == u_id) & (df_u['Password'] == u_pw)]
            if not match.empty:
                u_data = match.iloc[0].to_dict()
                st.session_state.update({'auth': True, 'user': u_data, 'role': role.lower()})
                st.rerun()
            else: st.error("Wrong ID or Password")

# --- لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, Mr. Ibrahim")
    menu = st.sidebar.radio("Menu", ["Matrix", "Settings"])
    
    if menu == "Matrix":
        st.header("Results Matrix")
        df_grd = clean_data(load_sheet("Grades"))
        st.dataframe(df_grd, use_container_width=True)
    
    elif menu == "Settings":
        st.header("System Settings")
        # إضافة شعبة أو طالب هنا

# --- لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    my_taken = df_gr[df_gr['Student_ID'] == str(u['ID'])]['Exam_ID'].unique().tolist()

    st.title(f"Hello, {u['Name']} 👋")
    tab1, tab2 = st.tabs(["📋 Assignments", "✅ Results"])

    with tab1:
        st.subheader("Pending Exams")
        now = datetime.now()
        req = df_ex[(df_ex['Status'] == 'Active') & (df_ex['Section'].str.contains(str(u['Section']), na=False))]
        pending = req[~req['Exam_ID'].astype(str).isin(map(str, my_taken))]

        for _, row in pending.iterrows():
            with st.container():
                st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                
                # الرابط السحري (ضع رابط الـ GAS الخاص بك هنا)
                gas_url = "https://script.google.com/macros/s/XXXXX/exec"
                full_link = f"{gas_url}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}"
                
                st.markdown(f'<a href="{full_link}" target="_blank" style="text-decoration:none;"><button style="background:#28a745; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">Start Exam / ابدأ الاختبار</button></a>', unsafe_allow_html=True)

    with tab2:
        st.subheader("Your Scores")
        st.table(my_taken)

if st.sidebar.button("Logout"):
    st.session_state.update({'auth': False}); st.rerun()
