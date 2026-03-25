import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

# --- 1. SETTINGS & STYLING | الإعدادات والتنسيق ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# Custom CSS for Prestige Look
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 12px; height: 3em; width: 100%; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #10b981; border: none; }
    .ar-text { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; color: #475569; }
    .en-main { font-weight: 800; color: #0f172a; font-size: 1.5rem; }
    .card { background-color: white; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION | الاتصال بالقاعدة ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0) # ttl=0 لضمان تحديث البيانات لحظياً

# --- 3. AUTHENTICATION | نظام الدخول ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='ar-text' style='text-align: center;'>منصة نفهم للرياضيات المتقدمة - مستر إبراهيم الدبور</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            uid = st.text_input("User ID | كود المستخدم")
            upass = st.text_input("Password | كلمة المرور", type="password")
            submit = st.form_submit_button("Login | دخول")
            
            if submit:
                # Check Students
                df_s = load_sheet("Students")
                user = df_s[(df_s['ID'].astype(str) == uid) & (df_s['Password'].astype(str) == upass)]
                
                if not user.empty:
                    st.session_state.role = 'student'
                    st.session_state.user = user.iloc[0]
                    st.rerun()
                
                # Check Teachers/Admin in Users sheet
                df_u = load_sheet("Users")
                admin = df_u[(df_u['ID'].astype(str) == uid) & (df_u['Password'].astype(str) == upass)]
                if not admin.empty:
                    st.session_state.role = admin.iloc[0]['Role']
                    st.session_state.user = admin.iloc[0]
                    st.rerun()
                
                st.error("Invalid Credentials | بيانات غير صحيحة")

# --- 4. TEACHER DASHBOARD | لوحة تحكم المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Control Panel")
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navigation", ["Analytics Dashboard", "Manage Exams", "Lessons & Content"])
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    if menu == "Analytics Dashboard":
        st.title("Performance Analytics | تحليلات الأداء")
        
        # Load Grades for Charts
        df_grades = load_sheet("Grades")
        
        col1, col2 = st.columns(2)
        with col1:
            # Chart 1: Average score per exam
            avg_scores = df_grades.groupby('EID')['Score'].mean().reset_index()
            fig = px.bar(avg_scores, x='EID', y='Score', title="Average Score Per Exam", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Chart 2: Success rate
            fig2 = px.pie(df_grades, names='Score', title="Score Distribution", hole=0.4, color_discrete_sequence=px.colors.sequential.Tealgrn)
            st.plotly_chart(fig2, use_container_width=True)

    elif menu == "Manage Exams":
        st.title("Manage Exams | إدارة الاختبارات")
        df_exams = load_sheet("Exams")
        st.write("Control answer visibility and exam status:")
        st.data_editor(df_exams) # يسمح لك بالتعديل المباشر وحفظ التغييرات لاحقاً
        st.info("Tip: Set 'Show_Answers' to TRUE when you want students to see their results.")

# --- 5. STUDENT DASHBOARD | لوحة الطالب ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user['Name']}")
    st.sidebar.info(f"Section: {user['Section']}")
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Learning Path | دروسي", "Assessments | التقييمات", "Progress Report | تقريري"])

    with tab1:
        st.markdown("### My Lessons | الدروس المنهجية")
        df_lessons = load_sheet("Lessons")
        for idx, row in df_lessons.iterrows():
            with st.expander(f"Lesson: {row['Title']}"):
                st.write(row['Content'])
                if pd.notna(row['Video_Link']):
                    st.video(row['Video_Link'])

    with tab2:
        st.markdown("### Active Assessments | الاختبارات المتاحة")
        df_exams = load_sheet("Exams")
        active_exams = df_exams[df_exams['Status'] == 'Active']
        
        for idx, row in active_exams.iterrows():
            st.markdown(f"""<div class='card'><b>{row['Title']}</b><br><small>Related to Lesson ID: {row['Lesson_ID']}</small></div>""", unsafe_allow_html=True)
            if st.button(f"Enter Exam: {row['Title']}", key=row['Exam_ID']):
                st.session_state.current_exam = row['Exam_ID']
                st.info("Exam UI would load here...")

    with tab3:
        st.markdown("### My Progress & Archive | أرشيف الأداء")
        df_grades = load_sheet("Grades")
        my_grades = df_grades[df_grades['SID'].astype(str) == str(user['ID'])]
        
        df_exams = load_sheet("Exams")
        
        for idx, row in my_grades.iterrows():
            exam_info = df_exams[df_exams['Exam_ID'] == row['EID']].iloc[0]
            with st.expander(f"{exam_info['Title']} - Score: {row['Score']}%"):
                if exam_info['Show_Answers'] == "TRUE":
                    st.success("Review is Available | مراجعة الإجابات متاحة")
                    st.json(row['Analytics']) # هنا نعرض تفاصيل الإجابات
                else:
                    st.warning("Answers are hidden by teacher | الإجابات مخفية من قِبل المعلم")
