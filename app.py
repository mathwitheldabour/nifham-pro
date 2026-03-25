import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# 1. Page Configuration / إعدادات الصفحة
st.set_page_config(page_title="NIFHAM Math Platform", layout="centered")

# Custom CSS for Professional Look / تنسيق المظهر
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .arabic-text { direction: rtl; text-align: right; color: #555; font-size: 0.9em; margin-top: -15px; }
    .exam-card { padding: 20px; border-radius: 10px; border: 1px solid #ddd; background-color: white; margin-bottom: 10px; }
    .timer-text { color: #d9534f; font-weight: bold; font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# 2. Connection Initialization / إعداد الاتصال
# سيقوم الكود بالبحث عن الرابط في الـ Secrets تلقائياً
conn = st.connection("gsheets", type=GSheetsConnection)

def get_sheet_data(name):
    try:
        # قراءة البيانات مع إلغاء الكاش لضمان التحديث المستمر
        return conn.read(worksheet=name, ttl=0)
    except Exception as e:
        st.error(f"Connection Error: Please ensure the sheet is shared as 'Anyone with link' / تأكد من مشاركة الشيت للجميع")
        return pd.DataFrame()

# 3. Session State Management / إدارة الجلسة
if 'login_status' not in st.session_state:
    st.session_state.login_status = False
    st.session_state.user = None
    st.session_state.current_exam = None

# --- UI LOGIC ---

# A. Login Screen / شاشة تسجيل الدخول
if not st.session_state.login_status:
    st.title("Student Login")
    st.markdown('<p class="arabic-text">تسجيل دخول الطالب</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        u_id = st.text_input("Student ID / رقم الطالب")
        u_pass = st.text_input("Password / كلمة المرور", type="password")
        submit = st.form_submit_button("Sign In / دخول")
        
        if submit:
            df_students = get_sheet_data("Students")
            if not df_students.empty:
                # البحث في شيت الطلاب بناءً على الصورة المرسلة (ID و Password)
                user_match = df_students[
                    (df_students['ID'].astype(str) == str(u_id)) & 
                    (df_students['Password'].astype(str) == str(u_pass))
                ]
                
                if not user_match.empty:
                    st.session_state.login_status = True
                    st.session_state.user = user_match.iloc[0].to_dict()
                    st.success("Login Successful! / تم الدخول بنجاح")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid ID or Password / بيانات الدخول غير صحيحة")

# B. Exam Selection & Dashboard / لوحة الامتحانات
elif st.session_state.login_status and st.session_state.current_exam is None:
    user = st.session_state.user
    st.title(f"Welcome, {user['Name']}")
    st.markdown(f'<p class="arabic-text">أهلاً بك يا {user["Name"]}</p>', unsafe_allow_html=True)
    
    st.sidebar.button("Logout / خروج", on_click=lambda: st.session_state.update({"login_status": False}))

    st.subheader("Available Exams / الامتحانات المتاحة")
    df_exams = get_sheet_data("Exams")
    
    if not df_exams.empty:
        # تصفية الامتحانات حسب الشعبة والحالة (Active)
        # الأعمدة: Exam_ID, Title, Lesson, Section, Duration, Status
        my_exams = df_exams[
            (df_exams['Status'] == 'Active') & 
            ((df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All'))
        ]
        
        if my_exams.empty:
            st.info("No active exams for your section / لا توجد امتحانات متاحة لشعبتك حالياً")
        else:
            for _, row in my_exams.iterrows():
                with st.container():
                    st.markdown(f"""
                        <div class="exam-card">
                            <h4>{row['Title']}</h4>
                            <p>Lesson: {row['Lesson']} | Duration: {row['Duration']} Mins</p>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Start Exam / ابدأ الامتحان", key=f"btn_{row['Exam_ID']}"):
                        st.session_state.current_exam = row.to_dict()
                        st.session_state.start_time = time.time()
                        st.rerun()

# C. Exam Player / مشغل الامتحان
else:
    exam = st.session_state.current_exam
    user = st.session_state.user
    
    st.title(exam['Title'])
    
    # Timer Logic / حساب الوقت
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = (int(exam['Duration']) * 60) - elapsed
    
    if remaining <= 0:
        st.error("Time is up! / انتهى وقت الامتحان")
        if st.button("Return to Dashboard"):
            st.session_state.current_exam = None
            st.rerun()
    else:
        mins, secs = divmod(remaining, 60)
        st.markdown(f'<p class="timer-text">Time Remaining / الوقت المتبقي: {mins:02d}:{secs:02d}</p>', unsafe_allow_html=True)
        
        # Display Exam Content (HTML) / عرض محتوى الامتحان
        st.components.v1.html(exam['HTML_Code'], height=600, scrolling=True)
        
        if st.button("Submit Exam / تسليم الإجابات"):
            # هنا يتم إضافة الكود الخاص بحفظ الدرجة في شيت Grades
            st.balloons()
            st.success("Submitted successfully! / تم التسليم بنجاح")
            time.sleep(2)
            st.session_state.current_exam = None
            st.rerun()
