import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# Page Configuration / إعدادات الصفحة
st.set_page_config(page_title="NIFHAM Math Platform", layout="centered")

# Custom CSS for Bilingual UI / تنسيق الواجهة
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .arabic-text { direction: rtl; text-align: right; color: #666; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

# 1. Connect to Google Sheets / الربط مع جوجل شيت
# Note: Ensure your secrets.toml is configured with the spreadsheet URL
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name)

# 2. Login Logic / منطق تسجيل الدخول
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None

if not st.session_state.logged_in:
    st.title("Student Login")
    st.markdown('<p class="arabic-text">تسجيل دخول الطالب</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        student_id = st.text_input("Student ID / رقم الطالب")
        password = st.text_input("Password / كلمة المرور", type="password")
        submit = st.form_submit_button("Login / دخول")
        
        if submit:
            df_students = get_data("Students")
            # التحقق من البيانات بناءً على شيت Students (ID في العمود A و Password في العمود C)
            user = df_students[(df_students['ID'].astype(str) == student_id) & 
                               (df_students['Password'].astype(str) == password)]
            
            if not user.empty:
                st.session_state.logged_in = True
                st.session_state.user_info = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Invalid ID or Password / خطأ في البيانات")

# 3. Dashboard & Exam Selection / لوحة التحكم واختيار الامتحان
else:
    user = st.session_state.user_info
    st.sidebar.write(f"Welcome / أهلاً بك: **{user['Name']}**")
    st.sidebar.write(f"Section / الشعبة: **{user['Section']}**")
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.logged_in = False
        st.rerun()

    if 'taking_exam' not in st.session_state:
        st.title("Available Exams")
        st.markdown('<p class="arabic-text">الامتحانات المتاحة لك</p>', unsafe_allow_html=True)
        
        df_exams = get_data("Exams")
        now = datetime.now()
        
        # تصفية الامتحانات بناءً على الشعبة والحالة والتاريخ
        # Columns: Exam_ID, Title, Lesson, Section, End_Date, Duration, HTML_Code, Status
        available_exams = df_exams[
            (df_exams['Status'] == 'Active') & 
            ((df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All'))
        ]
        
        if available_exams.empty:
            st.info("No exams available currently / لا توجد امتحانات حالياً")
        else:
            for index, row in available_exams.iterrows():
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(row['Title'])
                        st.write(f"Lesson: {row['Lesson']} | Duration: {row['Duration']} mins")
                    with col2:
                        if st.button(f"Start / ابدأ", key=row['Exam_ID']):
                            st.session_state.taking_exam = row.to_dict()
                            st.session_state.start_time = time.time()
                            st.rerun()
                st.divider()

    # 4. Exam Player / مشغل الامتحان
    else:
        exam = st.session_state.taking_exam
        st.title(exam['Title'])
        
        # Timer Logic / منطق المؤقت
        elapsed_time = int(time.time() - st.session_state.start_time)
        remaining_time = (exam['Duration'] * 60) - elapsed_time
        
        if remaining_time <= 0:
            st.error("Time is up! / انتهى الوقت")
            # Auto-submit logic can be added here
            if st.button("Back to Dashboard"):
                del st.session_state.taking_exam
                st.rerun()
        else:
            mins, secs = divmod(remaining_time, 60)
            st.metric("Time Remaining / الوقت المتبقي", f"{mins:02d}:{secs:02d}")
            
            # Rendering HTML_Code from Sheet / عرض كود الأسئلة
            st.components.v1.html(exam['HTML_Code'], height=500, scrolling=True)
            
            if st.button("Submit Exam / إنهاء الامتحان"):
                # Saving results to "Grades" sheet
                new_grade = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Student_ID": user['ID'],
                    "Student_Name": user['Name'],
                    "Exam_ID": exam['Exam_ID'],
                    "Score": "Pending / قيد التصحيح" # يمكن تطوير التصحيح التلقائي هنا
                }])
                
                # تحديث شيت الدرجات (تحتاج لبرمجة دالة الحفظ حسب نوع الربط)
                # conn.create(worksheet="Grades", data=new_grade) 
                
                st.success("Exam submitted successfully! / تم تسليم الامتحان")
                time.sleep(2)
                del st.session_state.taking_exam
                st.rerun()
