import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random

# --- 1. إعدادات الصفحة والتنسيق ---
st.set_page_config(page_title="NIFHAM Pro | منصة نفهم التعليمية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .arabic-text { direction: rtl; text-align: right; color: #555; }
    .exam-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border-right: 5px solid #007bff; direction: rtl; }
    .timer-box { font-size: 2rem; font-weight: bold; color: #d9534f; text-align: center; background: #fff; padding: 10px; border-radius: 10px; border: 2px solid #d9534f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (الاتصال بجوجل شيت) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0)

# --- 3. إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. شاشة الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown('<h3 class="arabic-text">تسجيل الدخول للمنصة</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                if "Student" in role_choice:
                    df = load_sheet("Students")
                    user = df[(df['ID'].astype(str) == u_id) & (df['Password'].astype(str) == u_pass)]
                    role = "student"
                else:
                    df = load_sheet("Users")
                    user = df[(df['ID'].astype(str) == u_id) & (df['Password'].astype(str) == u_pass)]
                    role = user.iloc[0]['Roll'] if not user.empty else None
                
                if not user.empty:
                    st.session_state.update({'auth': True, 'user': user.iloc[0].to_dict(), 'role': role})
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 5. واجهة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.auth = False
        st.rerun()

    df_exams = load_sheet("Exams")
    df_students = load_sheet("Students")
    df_grades = load_sheet("Grades")

    if menu == "Add Exam":
        st.header("📝 Create New Exam / إضافة اختبار جديد")
        with st.form("new_exam"):
            col1, col2 = st.columns(2)
            with col1:
                e_id = st.text_input("Exam ID / رمز الاختبار")
                e_title = st.text_input("Exam Title / العنوان")
                e_lesson = st.text_input("Lesson / الدرس")
            with col2:
                e_dur = st.number_input("Duration / المدة", min_value=1, value=60)
                e_status = st.selectbox("Status", ["Active", "Hidden"])
                all_sec = st.checkbox("Assign to all sections / لكل الشعب")
                target_sec = st.multiselect("Select Sections", df_students['Section'].unique()) if not all_sec else ["All"]
            
            e_html = st.text_area("HTML Code / كود الأسئلة")
            show_ans = st.selectbox("Allow Answer Review? / السماح بمراجعة الإجابات", ["No", "Yes"])

            if st.form_submit_button("Save to Cloud / حفظ في السحابة"):
                new_exam = pd.DataFrame([{
                    "Exam_ID": e_id, "Title": e_title, "Lesson": e_lesson,
                    "Section": ",".join(target_sec), "Duration": e_dur,
                    "HTML_Code": e_html, "Status": e_status, "Show_Answers": show_ans
                }])
                conn.create(worksheet="Exams", data=new_exam)
                st.success("Exam saved successfully! / تم الحفظ بنجاح")

    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        t1, t2 = st.tabs(["Add Section / شعبة", "Add Student / طالب"])
        with t2:
            with st.form("add_s"):
                s_name = st.text_input("Name / الاسم")
                s_id = st.text_input("ID / الرقم")
                s_sec = st.selectbox("Section", df_students['Section'].unique())
                s_pass = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register Student"):
                    new_s = pd.DataFrame([{"ID": s_id, "Name": s_name, "Password": s_pass, "Section": s_sec}])
                    conn.create(worksheet="Students", data=new_s)
                    st.success("Student added!")

    elif menu == "Exams Matrix":
        st.header("📊 Results Matrix")
        sec = st.selectbox("Section Filter", df_students['Section'].unique())
        if not df_grades.empty:
            matrix = df_grades.pivot_table(index='Student_Name', columns='Exam_ID', values='Score', aggfunc='max')
            st.dataframe(matrix.style.highlight_max(axis=0), use_container_width=True)

# --- 6. واجهة الطالب (Student Dashboard) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    if st.session_state.exam is None:
        st.title(f"Welcome, {u['Name']}")
        tab1, tab2 = st.tabs(["📋 To-do / الاختبارات المطلوبة", "✅ Completed / المنجزة"])
        
        df_exams = load_sheet("Exams")
        df_grades = load_sheet("Grades")
        
        with tab1:
            lesson_filter = st.selectbox("Filter by Lesson", ["All"] + list(df_exams['Lesson'].unique()))
            todo = df_exams[(df_exams['Status'] == 'Active') & 
                            (df_exams['Section'].str.contains(u['Section']) | (df_exams['Section'] == "All"))]
            if lesson_filter != "All": todo = todo[todo['Lesson'] == lesson_filter]
            
            for _, ex in todo.iterrows():
                with st.container():
                    st.markdown(f'<div class="exam-card"><h4>{ex["Title"]}</h4><p>{ex["Lesson"]} | {ex["Duration"]} min</p></div>', unsafe_allow_html=True)
                    if st.button("Start / ابدأ", key=ex['Exam_ID']):
                        st.session_state.update({'exam': ex.to_dict(), 'start_t': time.time()})
                        st.rerun()

        with tab2:
            my_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
            st.table(my_grades[['Date', 'Exam_ID', 'Score']])

    else:
        # مشغل الامتحان
        ex = st.session_state.exam
        rem = (int(ex['Duration']) * 60) - int(time.time() - st.session_state.start_t)
        if rem <= 0:
            st.error("Time Up!")
            if st.button("Exit"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(rem, 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            st.components.v1.html(ex['HTML_Code'], height=800, scrolling=True)
            
            # زر تسليم وهمي هنا (يجب أن يتم ربطه بـ JS لجمع الدرجة الفعلية)
            if st.button("Submit Exam / تسليم"):
                new_g = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Student_ID": u['ID'], "Student_Name": u['Name'],
                    "Exam_ID": ex['Exam_ID'], "Score": 10 # مثال
                }])
                conn.create(worksheet="Grades", data=new_g)
                st.success("Submitted!")
                time.sleep(2)
                st.session_state.exam = None
                st.rerun()

# --- 7. واجهة ولي الأمر (Parent Dashboard) ---
elif st.session_state.role == 'parent':
    st.title("👪 Parent Portal")
    u = st.session_state.user
    st.info(f"Student Progress Report: {u['Name']}")
    df_grades = load_sheet("Grades")
    my_child_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
    if not my_child_grades.empty:
        fig = px.bar(my_child_grades, x='Exam_ID', y='Score', color='Score', title="Grades Evolution")
        st.plotly_chart(fig)
        st.dataframe(my_child_grades)
