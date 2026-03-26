import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & CSS ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { font-family: 'Cairo', sans-serif; font-size: 0.85em; color: #6c757d; display: block; direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #007bff; }
    .timer-box { font-size: 1.8rem; font-weight: bold; color: #d9534f; text-align: center; background: #f8d7da; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Children_IDs']
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session State ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Main App Logic ---

# المحطة الأولى: شاشة الدخول (إذا لم يتم تسجيل الدخول)
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - الدخول</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID").strip()
            u_pass = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Sign In"):
                target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(target))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    u_data = user_match.iloc[0].to_dict()
                    # تحديد الدور برمجياً
                    role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': role})
                    st.rerun()
                else:
                    st.error("Invalid Credentials / بيانات الدخول غير صحيحة")

# المحطة الثانية: لوحة المعلم
elif st.session_state.role == 'teacher':
    st.title(f"Welcome, Mr. {st.session_state.user.get('Name', 'Teacher')}")
    # (هنا تضع كود المعلم الذي كتبناه سابقاً لإضافة الاختبارات والنتائج)
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

# المحطة الثالثة: لوحة الطالب
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is not None:
        # مشغل الامتحان
        ex = st.session_state.exam
        st.subheader(f"Exam: {ex['Title']}")
        elapsed = time.time() - st.session_state.start_t
        rem_sec = (int(float(ex.get('Duration', 60))) * 60) - elapsed
        
        if rem_sec <= 0:
            st.error("Time Expired!")
            if st.button("Close"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem_sec), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            # حقن البيانات
            html_raw = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID'])).replace("STUDENT_NAME_HERE", str(u['Name']))
            st.components.v1.html(html_raw, height=800, scrolling=True)
            if st.button("Cancel & Exit"): st.session_state.exam = None; st.rerun()
    else:
        # واجهة الطالب الرئيسية
        st.title(f"Welcome, {u['Name']} 👋")
        if st.sidebar.button("Logout"):
            st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

        t1, t2, t3 = st.tabs(["📋 Assigned", "✅ Grades", "📊 Performance"])
        with t1:
            st.subheader("Pending Exams")
            if not df_ex_stu.empty:
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                taken = my_grades['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken))]
                for _, row in required.iterrows():
                    st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                    if st.button(f"Start Exam", key=row['Exam_ID']):
                        st.session_state.exam = row.to_dict()
                        st.session_state.start_t = time.time(); st.rerun()
        with t2:
            st.subheader("Grade History")
            st.table(my_grades[['Exam_ID', 'Score']])
            st.divider()
            if st.button("Generate Smart Practice"):
                if not my_grades.empty:
                    last_id = my_grades.iloc[-1]['Exam_ID']
                    tmpl = df_ex_stu[df_ex_stu['Exam_ID'] == last_id].iloc[0]['HTML_Code']
                    # استبدال VAR_A و VAR_B بأرقام عشوائية
                    rendered = str(tmpl).replace("VAR_A", str(random.randint(2,9))).replace("VAR_B", str(random.randint(2,5)))
                    st.session_state.practice_view = rendered; st.rerun()
            if 'practice_view' in st.session_state:
                st.components.v1.html(st.session_state.practice_view, height=600, scrolling=True)
                if st.button("Close Practice"): del st.session_state.practice_view; st.rerun()

# المحطة الرابعة: لوحة ولي الأمر
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
    # (كود ولي الأمر المعتمد على Children_IDs)
    st.info("Parent monitoring dashboard is active.")

# المحطة الأخيرة: Catch-all
else:
    st.warning("Please login to continue.")
    st.session_state.update({'auth': False, 'user': None, 'role': None})
