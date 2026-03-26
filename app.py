import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random

# --- 1. Page Configuration / إعدادات الصفحة ---
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

# --- 2. Data Engine / محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0)

def clean_login_data(df):
    """تنظيف بيانات الدخول"""
    for col in ['ID', 'Password']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    return df

# --- 3. Session State / إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Login Screen / شاشة الدخول ---
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
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_users = clean_login_data(load_sheet(sheet_target))
                
                user_match = df_users[(df_users['ID'] == str(u_id)) & (df_users['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    final_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent')
                    st.session_state.update({'auth': True, 'user': user_data, 'role': final_role})
                    st.success(f"Welcome / مرحباً بك: {user_data['Name']}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 5. Teacher Dashboard / لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    df_exams = load_sheet("Exams")
    df_students = load_sheet("Students")
    df_grades = load_sheet("Grades")

    if menu == "Add Exam":
        st.header("📝 Create New Exam / إضافة اختبار جديد")
        with st.form("new_exam"):
            col1, col2 = st.columns(2)
            with col1:
                e_id = st.text_input("Exam ID")
                e_title = st.text_input("Exam Title")
                e_lesson = st.text_input("Lesson / الدرس")
            with col2:
                e_dur = st.number_input("Duration / المدة", min_value=1, value=60)
                e_status = st.selectbox("Status", ["Active", "Hidden"])
                all_sec = st.checkbox("Assign to all sections")
                target_sec = st.multiselect("Sections", df_students['Section'].unique()) if not all_sec else ["All"]
            
            e_html = st.text_area("HTML Code")
            show_ans = st.selectbox("Show Answers?", ["No", "Yes"])

            if st.form_submit_button("Save Exam"):
                new_row = pd.DataFrame([{
                    "Exam_ID": e_id, "Title": e_title, "Lesson": e_lesson,
                    "Section": ",".join(map(str, target_sec)), "Duration": e_dur,
                    "HTML_Code": e_html, "Status": e_status, "Show_Answers": show_ans
                }])
                conn.create(worksheet="Exams", data=new_row)
                st.success("Exam saved successfully!")

elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        
        # إنشاء تبويبين: الأول للشعب والثاني للطلاب
        tab1, tab2 = st.tabs(["Add Section / إضافة شعبة", "Add Student / إضافة طالب"])
        
        # 1. إضافة شعبة جديدة
        with tab1:
            st.subheader("Add New Section / إضافة شعبة جديدة")
            with st.form("section_form"):
                new_sec_name = st.text_input("New Section Name / اسم الشعبة (مثلاً: 12A)")
                if st.form_submit_button("Save Section / حفظ الشعبة"):
                    if new_sec_name:
                        try:
                            # حفظ الشعبة في شيت "Sections"
                            new_sec_df = pd.DataFrame([{"Section_Name": str(new_sec_name).strip()}])
                            conn.create(worksheet="Sections", data=new_sec_df)
                            st.success(f"Section '{new_sec_name}' added successfully!")
                            time.sleep(1)
                            st.rerun() # لإعادة تحميل القوائم بالشعبة الجديدة
                        except Exception as e:
                            st.error(f"Error: Make sure a sheet named 'Sections' exists. / تأكد من وجود شيت باسم Sections")
                    else:
                        st.warning("Please enter a name / يرجى إدخال اسم")

        # 2. إضافة طالب جديد
        with tab2:
            st.subheader("Register Student / تسجيل طالب")
            # جلب الشعب من شيت "Sections" بدلاً من شيت الطلاب
            try:
                df_all_sections = load_sheet("Sections")
                list_of_sections = df_all_sections['Section_Name'].unique().tolist()
            except:
                list_of_sections = []

            if not list_of_sections:
                st.warning("Please add a Section first in the previous tab! / يرجى إضافة شعبة أولاً من التبويب السابق")
            else:
                with st.form("add_student_form"):
                    s_name = st.text_input("Full Name / الاسم الكامل")
                    s_id = st.text_input("ID / الرقم التعريفي")
                    s_sec = st.selectbox("Select Section / اختر الشعبة", list_of_sections)
                    s_pass = st.text_input("Password / كلمة المرور", value=str(random.randint(1000, 9999)))
                    
                    if st.form_submit_button("Save Student / حفظ الطالب"):
                        if s_name and s_id:
                            try:
                                new_s_df = pd.DataFrame([{
                                    "ID": str(s_id).strip(),
                                    "Name": str(s_name).strip(),
                                    "Password": str(s_pass).strip(),
                                    "Section": str(s_sec).strip()
                                }])
                                conn.create(worksheet="Students", data=new_s_df)
                                st.success(f"Student {s_name} registered successfully!")
                            except Exception as e:
                                st.error(f"Write Error: Check service account permissions. / خطأ في الكتابة: تأكد من صلاحيات المحرر")
                        else:
                            st.error("Please fill all fields / يرجى ملء جميع الحقول")
    elif menu == "Exams Matrix":
        st.header("📊 Results Matrix")
        if not df_grades.empty:
            matrix = df_grades.pivot_table(index='Student_Name', columns='Exam_ID', values='Score', aggfunc='max')
            st.dataframe(matrix, use_container_width=True)

# --- 6. Student Dashboard / لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    if st.session_state.exam is None:
        st.title(f"Welcome, {u['Name']}")
        tab1, tab2 = st.tabs(["📋 To-do / الاختبارات", "✅ Completed / المنجزة"])
        
        df_exams = load_sheet("Exams")
        df_grades = load_sheet("Grades")
        
        with tab1:
            # --- إصلاح الخطأ الجوهري هنا ---
            # تحويل عمود الشعبة لنصوص قبل البحث
            df_exams['Section'] = df_exams['Section'].astype(str)
            student_section = str(u.get('Section', ''))
            
            todo = df_exams[
                (df_exams['Status'] == 'Active') & 
                (df_exams['Section'].str.contains(student_section, na=False) | (df_exams['Section'] == "All"))
            ]
            
            if todo.empty:
                st.info("No active exams for your section / لا توجد امتحانات حالياً")
            else:
                for _, ex in todo.iterrows():
                    with st.container():
                        st.markdown(f'<div class="exam-card"><h4>{ex["Title"]}</h4><p>{ex["Lesson"]} | {ex["Duration"]} min</p></div>', unsafe_allow_html=True)
                        if st.button("Start / ابدأ", key=ex['Exam_ID']):
                            st.session_state.update({'exam': ex.to_dict(), 'start_t': time.time()})
                            st.rerun()

        with tab2:
            if not df_grades.empty:
                my_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
                st.dataframe(my_grades, use_container_width=True)
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
            if st.button("Submit / تسليم"):
                new_g = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Student_ID": u['ID'], "Student_Name": u['Name'], "Exam_ID": ex['Exam_ID'], "Score": 10}])
                conn.create(worksheet="Grades", data=new_g)
                st.success("Submitted!"); time.sleep(2); st.session_state.exam = None; st.rerun()

# --- 7. Parent Dashboard / لوحة ولي الأمر ---
elif st.session_state.role == 'parent':
    st.title("👪 Parent Portal")
    u = st.session_state.user
    st.info(f"Report for Student ID: {u['ID']}")
    df_grades = load_sheet("Grades")
    if not df_grades.empty:
        my_child_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
        if not my_child_grades.empty:
            fig = px.bar(my_child_grades, x='Exam_ID', y='Score', title="Grades History")
            st.plotly_chart(fig)
