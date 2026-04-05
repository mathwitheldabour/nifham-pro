import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time, random

# --- 1. الثوابت والإعدادات (حل مشكلة NameError) ---
st.set_page_config(page_title="NIFHAM Pro", layout="wide")
PASSING_SCORE = 50  # تعريف المتغير عالمياً

# ضع رابط الـ Web App الصحيح هنا (تأكد أنه ينتهي بـ /exec)
GAS_URL = "https://script.google.com/macros/s/AKfycbzZvxhGjYN-nOm8Fgz1IZUAJJyjlwYu8sOtDXqU--P_Sohb7qT-mjSr5WLgICGMYLYYlA/exec"

# --- 2. محرك البيانات المؤمن ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    # تنظيف أسماء الأعمدة (حل مشكلة KeyError)
    df.columns = [str(c).strip() for c in df.columns]
    # تنظيف المحتوى
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

# --- 4. نظام تسجيل الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role_choice = st.selectbox("Login as", ["Student / طالب", "Teacher / معلم"])
    with st.form("login"):
        uid = st.text_input("ID").strip()
        upw = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Sign In"):
            target = "Students" if "Student" in role_choice else "Users"
            df_u = clean_data(load_sheet(target))
            match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': 'student' if "Student" in role_choice else 'teacher'})
                st.rerun()
            else: st.error("Invalid Credentials")

# --- 5. لوحة المعلم المحدثة ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("Navigation", ["📊 Matrix", "📈 Analytics", "📚 Library", "📝 Manager"])
    
    # تحميل البيانات فوراً
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))

    if menu == "📚 Library":
        st.header("Exams Library")
        for _, row in df_exm.iterrows():
            with st.expander(f"📖 {row['Title']}"):
                # المعاينة تفتح في نافذة جديدة تماماً لتجنب مشاكل جوجل درايف
                p_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                st.link_button("👁️ Open Preview / معاينة الاختبار", p_url)

    elif menu == "📈 Analytics":
        st.header("Analytics")
        if not df_grd.empty:
            st.metric("Avg Score", f"{df_grd['Score'].mean():.1f}%")
            # حل مشكلة الـ NameError في نسبة النجاح
            pass_rate = (df_grd['Score'] >= PASSING_SCORE).mean() * 100
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
            st.bar_chart(df_grd.set_index('Exam_ID')['Score'])

    elif menu == "📊 Matrix":
        st.header("Results Matrix")
        if 'Student_ID' in df_grd.columns and not df_stu.empty:
            merged = pd.merge(df_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if 'Exam_ID' in merged.columns:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix, use_container_width=True)
        else: st.info("No data yet.")

    if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()

# --- 6. لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    
    my_subs = df_gr[df_gr['Student_ID'] == str(u['ID'])] if 'Student_ID' in df_gr.columns else pd.DataFrame()
    taken_ids = my_subs['Exam_ID'].unique().tolist() if not my_subs.empty else []

    st.title(f"Welcome, {u['Name']} 👋")
    t1, t2 = st.tabs(["📋 Assignments", "✅ History"])

    with t1:
        pending = df_ex[~df_ex['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        for _, row in pending.iterrows():
            if str(u['Section']) in str(row['Section']):
                st.info(f"Exam: {row['Title']}")
                ex_url = f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam"
                st.link_button("Start Exam / ابدأ الاختبار", ex_url)

    with t2:
        if not my_subs.empty:
            st.dataframe(my_subs[['Exam_ID', 'Score']], use_container_width=True)
