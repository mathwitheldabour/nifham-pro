import streamlit as st
import pandas as pd
import time
from datetime import datetime
import plotly.express as px

# --- 1. SETTINGS & CSS ---
st.set_page_config(page_title="NIFHAM Pro | منصة نفهم الاحترافية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #007bff; color: white; }
    .arabic-right { direction: rtl; text-align: right; }
    .exam-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border-right: 5px solid #007bff; }
    .status-tag { padding: 2px 10px; border-radius: 10px; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY"

def get_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'page': 'Home'})

# --- 4. LOGIN LOGIC (Teacher, Student, Parent) ---
def login_screen():
    st.title("🚀 NIFHAM Math Platform")
    st.markdown('<h3 class="arabic-right">تسجيل الدخول للمنصة</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        role = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                # Logic for Teacher/Parent
                if "Student" not in role:
                    df = get_data("Users")
                    user = df[(df['ID'].astype(str) == u_id) & (df['Password'].astype(str) == u_pass)]
                    if not user.empty:
                        st.session_state.update({'auth': True, 'user': user.iloc[0].to_dict(), 'role': user.iloc[0]['Roll']})
                        st.rerun()
                # Logic for Student
                else:
                    df = get_data("Students")
                    user = df[(df['ID'].astype(str) == u_id) & (df['Password'].astype(str) == u_pass)]
                    if not user.empty:
                        st.session_state.update({'auth': True, 'user': user.iloc[0].to_dict(), 'role': 'student'})
                        st.rerun()
                st.error("Invalid Credentials / بيانات خاطئة")

# --- 5. TEACHER DASHBOARD ---
def teacher_dashboard():
    st.sidebar.title("Teacher Tools")
    # التأكد من مطابقة الخيارات هنا مع الشروط بالأسفل
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    
    df_exams = get_data("Exams")
    df_students = get_data("Students")
    
    # --- 1. صفحة إضافة اختبار (كانت ناقصة وظهرت الآن) ---
    if menu == "Add Exam":
        st.header("📝 Create New Exam / إضافة اختبار جديد")
        with st.form("new_exam_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_id = st.text_input("Exam ID / رمز الاختبار (مثلاً: E105)")
                e_title = st.text_input("Exam Title / عنوان الاختبار")
                e_lesson = st.text_input("Lesson Name / اسم الدرس")
            with col2:
                e_section = st.selectbox("Target Section / الشعبة المستهدفة", df_students['Section'].unique())
                e_duration = st.number_input("Duration / المدة (بالدقائق)", min_value=1, value=60)
                e_status = st.selectbox("Status / الحالة", ["Active", "Hidden"])
            
            e_html = st.text_area("HTML Code / كود الأسئلة (Paste from Google Forms or Custom)")
            
            submitted = st.form_submit_button("Save Exam / حفظ الاختبار")
            if submitted:
                st.info("Exam UI created. To save to Google Sheets, writing permission is needed.")

    # --- 2. إدارة الشعب والطلاب ---
    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        
        tab1, tab2 = st.tabs(["Add Section / إضافة شعبة", "Add Student / إضافة طالب"])
        
        with tab1:
            new_sec = st.text_input("New Section Name / اسم الشعبة الجديدة")
            if st.button("Create Section"):
                # ملاحظة: لكي تظهر في القوائم، يجب حفظها في شيت خاص بالشعب
                st.success(f"Section '{new_sec}' created locally. Need Gspread to save to Sheet.")

        with tab2:
            st.subheader("Register New Student / تسجيل طالب جديد")
            with st.form("add_student_form"):
                s_name = st.text_input("Student Full Name / اسم الطالب")
                s_id = st.text_input("Student ID / الرقم التعريفي")
                # هنا الشعبة تظهر ديناميكياً
                s_sec = st.selectbox("Select Section / اختر الشعبة", df_students['Section'].unique())
                
                # --- حل مشكلة كلمة السر ---
                import random
                generated_pass = str(random.randint(100000, 999999)) # توليد 6 أرقام عشوائية
                s_pass = st.text_input("Password / كلمة المرور", value=generated_pass, help="You can change this or use the generated one")
                
                if st.form_submit_button("Register / تسجيل الطالب"):
                    st.write(f"Student {s_name} ready with Password: {s_pass}")

    # بقية الأقسام (Matrix & Analysis) كما هي...
# --- 6. STUDENT DASHBOARD ---
def student_dashboard():
    u = st.session_state.user
    st.title(f"Welcome, {u['Name']}")
    
    df_exams = get_data("Exams")
    df_grades = get_data("Grades")
    
    # Tabs for To-do and Completed
    tab1, tab2 = st.tabs(["📋 Required / المطلوبة", "✅ Completed / المنجزة"])
    
    with tab1:
        # Filter exams by Section and Lesson
        lessons = df_exams['Lesson'].unique()
        selected_lesson = st.selectbox("Filter by Lesson / تصفية بالدرس", lessons)
        
        todo = df_exams[(df_exams['Section'] == u['Section']) & (df_exams['Lesson'] == selected_lesson) & (df_exams['Status'] == 'Active')]
        
        for _, ex in todo.iterrows():
            with st.container():
                st.markdown(f"""<div class="exam-card">
                    <h4>{ex['Title']}</h4>
                    <p>Lesson: {ex['Lesson']} | Duration: {ex['Duration']} Mins</p>
                </div>""", unsafe_allow_html=True)
                if st.button(f"Start Exam / ابدأ", key=ex['Exam_ID']):
                    # Exam logic here
                    pass

    with tab2:
        done = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
        for _, d in done.iterrows():
            with st.expander(f"Exam: {d['Exam_ID']} - Score: {d['Score']}"):
                st.write(f"Completed on: {d['Date']}")
                # Permission logic
                exam_info = df_exams[df_exams['Exam_ID'] == d['Exam_ID']].iloc[0]
                if exam_info['Show_Answers'] == "Yes":
                    st.info("Teacher has allowed answer review / مسموح بمراجعة الإجابات")
                    st.button("Review My Answers / مراجعة إجاباتي", key=f"rev_{d['Exam_ID']}")
                else:
                    st.warning("Review is locked by teacher / المراجعة مغلقة من قبل المعلم")

# --- 7. PARENT DASHBOARD ---
def parent_dashboard():
    st.title("👪 Parent Portal / بوابة ولي الأمر")
    u = st.session_state.user
    # ولي الأمر يرى تقرير الطالب المرتبط بالـ ID الخاص به
    st.info(f"Monitoring progress for student linked to ID: {u['ID']}")
    df_grades = get_data("Grades")
    # عرض الدرجات والتحليل البياني

# --- MAIN APP ROUTING ---
if not st.session_state.auth:
    login_screen()
else:
    if st.sidebar.button("Logout / خروج"):
        st.session_state.auth = False
        st.rerun()
    
    if st.session_state.role == 'teacher':
        teacher_dashboard()
    elif st.session_state.role == 'student':
        student_dashboard()
    elif st.session_state.role == 'parent':
        parent_dashboard()
