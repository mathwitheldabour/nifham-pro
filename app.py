import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time
import random

# --- 1. الإعدادات الأساسية (Configuration) ---
st.set_page_config(page_title="NIFHAM Pro | Mr. Ibrahim Eldabour", layout="wide")

# الرابط الخاص بك (الجسر)
GAS_URL = "https://script.google.com/macros/s/AKfycbzZvxhGjYN-nOm8Fgz1IZUAJJyjlwYu8sOtDXqU--P_Sohb7qT-mjSr5WLgICGMYLYYlA/exec"

# التنسيق البصري (CSS)
st.markdown("""
    <style>
    .arabic-sub { direction: rtl; text-align: right; color: #6c757d; font-size: 0.9em; display: block; margin-bottom: 10px; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stMetric { background: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (Data Engine) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    # تنظيف أسماء الأعمدة (حل مشكلة KeyError)
    df.columns = [str(c).strip() for c in df.columns]
    # تنظيف محتوى الأعمدة الأساسية
    cols_to_fix = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password', 'Section_Name']
    for col in df.columns:
        if col in cols_to_fix:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# إدارة الجلسة
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- 3. نظام تسجيل الدخول (Login) ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>مدرسة خالد بن الوليد | الأستاذ إبراهيم الدبور</span>", unsafe_allow_html=True)
    
    role_choice = st.selectbox("Login as", ["Student / طالب", "Teacher / معلم"])
    with st.form("login_gate"):
        u_id = st.text_input("User ID").strip()
        u_pw = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Sign In / دخول"):
            target = "Students" if "Student" in role_choice else "Users"
            df_users = clean_data(load_sheet(target))
            if not df_users.empty:
                match = df_users[(df_users['ID'] == u_id) & (df_users['Password'] == u_pw)]
                if not match.empty:
                    st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': 'student' if "Student" in role_choice else 'teacher'})
                    st.rerun()
                else: st.error("Wrong ID or Password!")

# --- 4. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("القائمة الرئيسية", ["📊 مصفوفة الدرجات", "👤 نتائج الطلاب الفردية", "📚 مكتبة المعاينة", "📝 مدير الاختبارات", "⚙️ الإعدادات"])
    
    # تحميل البيانات للمعلم
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    active_sections = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    # أ- مصفوفة الدرجات (Results Matrix)
    if menu == "📊 مصفوفة الدرجات":
        st.header("Results Matrix / مصفوفة الدرجات")
        if not active_sections: st.warning("Add sections first.")
        else:
            sel_sec = st.selectbox("اختر الشعبة", active_sections)
            f_stu = df_stu[df_stu['Section'] == sel_sec]
            if 'Student_ID' in df_grd.columns:
                merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
                if 'Exam_ID' in merged.columns:
                    matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                    st.dataframe(matrix, use_container_width=True)
            else: st.info("لا توجد بيانات درجات بعد.")

    # ب- نتائج الطلاب الفردية (Individual Reports)
    elif menu == "👤 نتائج الطلاب الفردية":
        st.header("Individual Student Report")
        col1, col2 = st.columns(2)
        with col1: s_sec = st.selectbox("اختر الشعبة", active_sections, key="sec_rep")
        with col2:
            students_in_sec = df_stu[df_stu['Section'] == s_sec]['Name'].tolist()
            s_name = st.selectbox("اختر الطالب", students_in_sec)
        
        if s_name:
            student_id = df_stu[df_stu['Name'] == s_name]['ID'].values[0]
            personal_grd = df_grd[df_grd['Student_ID'] == str(student_id)]
            if not personal_grd.empty:
                st.subheader(f"تقرير الطالب: {s_name}")
                st.table(personal_grd[['Date', 'Exam_ID', 'Score']])
            else: st.info("الطالب لم يقدم أي اختبارات بعد.")

    # ج- مكتبة المعاينة (Exams Library)
    elif menu == "📚 مكتبة المعاينة":
        st.header("Exams Library / معاينة الاختبارات")
        for _, row in df_exm.iterrows():
            with st.expander(f"📖 {row['Title']} (Code: {row['Exam_ID']})"):
                st.write(f"الشعب المستهدفة: {row['Section']}")
                preview_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                st.link_button("👁️ Preview Exam / معاينة", preview_url)

    # د- مدير الاختبارات (Exams Manager)
    elif menu == "📝 مدير الاختبارات":
        st.header("Exams Manager / إضافة اختبار")
        with st.form("exam_form"):
            e_id = st.text_input("Exam Code (ID)")
            e_title = st.text_input("Exam Title")
            e_sec = st.multiselect("Assign to Sections", active_sections)
            e_html = st.text_area("HTML Code (من العمود H)")
            if st.form_submit_button("Publish / نشر"):
                new_ex = pd.DataFrame([{"Exam_ID": e_id, "Title": e_title, "Section": ",".join(e_sec), "HTML_Code": e_html, "Status": "Active"}])
                conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                st.success("Exam Published!"); st.rerun()

# --- 5. لوحة الطالب (Student Dashboard) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    
    # فحص الدرجات السابقة للطالب
    my_subs = df_gr[df_gr['Student_ID'] == str(u['ID'])] if 'Student_ID' in df_gr.columns else pd.DataFrame()
    taken_ids = my_subs['Exam_ID'].unique().tolist() if not my_subs.empty else []

    st.title(f"Welcome, {u['Name']} 👋")
    st.markdown(f"<span class='arabic-sub'>شعبة: {u['Section']}</span>", unsafe_allow_html=True)
    
    t_pending, t_history = st.tabs(["📋 الاختبارات المقررة", "✅ المراجعة والنتائج"])

    with t_pending:
        # عرض الاختبارات التي تنتمي لشعبة الطالب ولم يحلها بعد
        pending = df_ex[~df_ex['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        for _, row in pending.iterrows():
            if str(u['Section']) in str(row['Section']):
                with st.container():
                    st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                    exam_url = f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam"
                    st.link_button("ابدأ الاختبار / Start", exam_url)

    with t_history:
        st.subheader("سجل اختباراتك")
        if not my_subs.empty:
            for _, sub in my_subs.iterrows():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"✅ اختبار: **{sub['Exam_ID']}** | الدرجة: **{sub['Score']}%**")
                    # مراجعة فقط بدون إمكانية التسليم
                    rev_url = f"{GAS_URL}?sid={u['ID']}&eid={sub['Exam_ID']}&name={u['Name']}&mode=review"
                    c2.link_button("مراجعة", rev_url)
        else: st.info("لا توجد اختبارات مكتملة.")

if st.sidebar.button("Logout / خروج"):
    st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
