import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime

# --- Page Config / إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math | منصة نفهم", layout="centered")

# --- Styling / التنسيق الجمالي ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .arabic-text { direction: rtl; text-align: right; color: #6c757d; font-size: 0.85em; margin-top: -10px; }
    .exam-card { padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; background-color: white; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .timer { font-size: 1.5rem; font-weight: bold; color: #dc3545; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- Connection / الربط مع جوجل شيت ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    # ttl=0 تضمن تحديث البيانات فوراً عند تغيير الشيت
    return conn.read(worksheet=sheet_name, ttl=0)

# --- State Management / إدارة حالة المستخدم ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_data = None
    st.session_state.active_exam = None

# --- UI LOGIC ---

# 1. Login Screen / شاشة الدخول
if not st.session_state.authenticated:
    st.title("Student Login")
    st.markdown('<p class="arabic-text">تسجيل دخول الطالب</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        sid = st.text_input("Student ID / رقم الطالب")
        spass = st.text_input("Password / كلمة المرور", type="password")
        if st.form_submit_button("Login / دخول"):
            df_students = load_data("Students")
            # التحقق من البيانات (تحويل الـ ID لنص لضمان المطابقة)
            user = df_students[(df_students['ID'].astype(str) == str(sid)) & 
                               (df_students['Password'].astype(str) == str(spass))]
            
            if not user.empty:
                st.session_state.authenticated = True
                st.session_state.user_data = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Invalid ID or Password / خطأ في الرقم أو كلمة المرور")

# 2. Exam Selection / اختيار الامتحان
elif st.session_state.authenticated and st.session_state.active_exam is None:
    u = st.session_state.user_data
    st.title(f"Welcome, {u['Name']}")
    st.markdown(f'<p class="arabic-text">أهلاً بك يا {u["Name"]} - شعبة {u["Section"]}</p>', unsafe_allow_html=True)
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.authenticated = False
        st.rerun()

    st.subheader("Your Exams / امتحاناتك المتاحة")
    df_exams = load_data("Exams")
    
    # تصفية الامتحانات النشطة والخاصة بشعبة الطالب (أو للجميع All)
    my_exams = df_exams[
        (df_exams['Status'] == 'Active') & 
        ((df_exams['Section'] == u['Section']) | (df_exams['Section'] == 'All'))
    ]
    
    if my_exams.empty:
        st.info("No active exams for you at the moment / لا توجد امتحانات متاحة لك حالياً")
    else:
        for _, row in my_exams.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="exam-card">
                    <h4>{row['Title']}</h4>
                    <p style="margin:0;">Lesson: {row['Lesson']} | Duration: {row['Duration']} Mins</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Start / ابدأ", key=f"ex_{row['Exam_ID']}"):
                    st.session_state.active_exam = row.to_dict()
                    st.session_state.start_time = time.time()
                    st.rerun()

# 3. Exam Player / مشغل الامتحان
else:
    exam = st.session_state.active_exam
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(exam['Title'])
    with col2:
        # حساب التايمر
        elapsed = int(time.time() - st.session_state.start_time)
        remaining = (int(exam['Duration']) * 60) - elapsed
        if remaining <= 0:
            st.error("Time is up! / انتهى الوقت")
            if st.button("Back / عودة"):
                st.session_state.active_exam = None
                st.rerun()
        else:
            m, s = divmod(remaining, 60)
            st.markdown(f'<div class="timer">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)

    st.divider()
    
    # عرض محتوى الـ HTML من الشيت
    st.components.v1.html(exam['HTML_Code'], height=800, scrolling=True)
    
    if st.button("Finish & Submit / إنهاء وتسليم"):
        st.balloons()
        st.success("Your answers have been submitted! / تم تسليم إجاباتك بنجاح")
        time.sleep(3)
        st.session_state.active_exam = None
        st.rerun()
