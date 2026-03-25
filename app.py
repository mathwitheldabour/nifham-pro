import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# تصميم الواجهة (Midnight Blue & Emerald)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 12px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #10b981; border: none; transform: scale(1.02); }
    .ar-text { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; color: #1e293b; }
    .card { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, dtype=str)

# --- 3. SESSION MANAGEMENT ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. LOGIN PORTAL ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login"):
            st.markdown("<p class='ar-text'>تسجيل الدخول - مستر إبراهيم الدبور</p>", unsafe_allow_html=True)
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            if st.form_submit_button("Login | دخول"):
                try:
                    # فحص المعلمين أولاً
                    df_u = load_data("Users")
                    admin = df_u[(df_u['ID'].astype(str) == uid) & (df_u['Password'].astype(str) == upass)]
                    if not admin.empty:
                        st.session_state.role = 'teacher'
                        st.session_state.user = admin.iloc[0]
                        st.rerun()
                    
                    # فحص الطلاب وأولياء الأمور
                    df_s = load_data("Students")
                    user = df_s[(df_s['ID'].astype(str) == uid) & (df_s['Password'].astype(str) == upass)]
                    if not user.empty:
                        st.session_state.role = user.iloc[0].get('Roll', 'student').lower().strip()
                        st.session_state.user = user.iloc[0]
                        st.rerun()
                    
                    st.error("Invalid Login | بيانات غير صحيحة")
                except: st.error("Database Connection Error")

# --- 5. TEACHER DASHBOARD (The Command Center) ---
elif st.session_state.role == 'teacher':
    st.sidebar.markdown(f"### Welcome Mr. Ibrahim")
    menu = st.sidebar.radio("Navigation", ["Analytics Dashboard", "Add Exam/Assignment", "Manage Students"])
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    if menu == "Add Exam/Assignment":
        st.title("➕ Create New Assessment | إضافة اختبار أو واجب")
        with st.form("exam_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                e_id = st.text_input("Exam ID (e.g., EX101)")
                e_title = st.text_input("Title | عنوان الاختبار")
                e_lesson = st.text_input("Lesson | الدرس")
            with col_b:
                e_section = st.selectbox("Section | الشعبة", ["12A", "12B", "12C", "All"])
                e_date = st.date_input("Start Date | تاريخ البدء")
                e_duration = st.number_input("Duration (Minutes) | زمن الاختبار", min_value=5, max_value=180)
            
            e_html = st.text_area("HTML Code | كود أسئلة الاختبار", height=300, help="Paste your HTML quiz code here")
            
            if st.form_submit_button("Publish Assessment | نشر التقييم"):
                # هنا يتم إرسال البيانات للجوجل شيت (نحتاج لربط مكتبة gspread للتحديث المباشر)
                st.success(f"Exam '{e_title}' has been staged! Please update your 'Exams' sheet with this data.")
                st.code(f"{e_id}, {e_title}, {e_lesson}, {e_section}, {e_date}, {e_duration}")

    elif menu == "Analytics Dashboard":
        st.title("📊 Student Performance | أداء الطلاب")
        df_grades = load_data("Grades")
        # رسم بياني لتوزيع الدرجات
        fig = px.bar(df_grades, x='SID', y='Score', color='Score', title="Individual Scores Overview")
        st.plotly_chart(fig, use_container_width=True)

# --- 6. STUDENT DASHBOARD ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.title(f"🎓 Portal: {user['Name']}")
    tab1, tab2 = st.tabs(["Active Exams | الاختبارات", "My Results | نتايجي"])
    
    with tab1:
        df_exams = load_data("Exams")
        # فلترة حسب شعبة الطالب
        my_exams = df_exams[(df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All')]
        
        for idx, ex in my_exams.iterrows():
            with st.expander(f"📝 {ex['Title']} (Lesson: {ex['Lesson']})"):
                st.write(f"⏱ Time: {ex['Duration']} Minutes")
                if st.button(f"Start | ابدأ", key=ex['Exam_ID']):
                    # عرض كود الـ HTML المخزن في الشيت
                    components.html(ex['HTML_Code'], height=800, scrolling=True)

    with tab2:
        st.markdown("### Previous Scores")
        df_grades = load_data("Grades")
        my_results = df_grades[df_grades['SID'] == user['ID']]
        st.dataframe(my_results)

# --- 7. PARENT DASHBOARD ---
elif st.session_state.role == 'parent':
    st.title("🏠 Parent Dashboard | متابعة ولي الأمر")
    st.write(f"Tracking Progress for: {st.session_state.user['Name']}")
    # عرض رسم بياني لتطور ابنه
    df_grades = load_data("Grades")
    my_child_grades = df_grades[df_grades['SID'] == st.session_state.user['ID']]
    fig_prog = px.line(my_child_grades, x='Date', y='Score', title="Learning Progress Curve")
    st.plotly_chart(fig_prog)
