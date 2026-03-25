import streamlit as st
import pandas as pd
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math | منصة نفهم", layout="centered")

# --- تنسيق احترافي ---
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; background-color: #007bff; color: white; }
    .arabic-text { direction: rtl; text-align: right; color: #555; font-size: 0.9em; }
    .exam-box { padding: 15px; border-radius: 10px; border: 1px solid #ddd; background: white; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- دالة قراءة البيانات (الطريقة المباشرة والأضمن) ---
def get_data_from_google(sheet_name):
    # ده الـ ID بتاع ملفك اللي بعتهولي
    SHEET_ID = "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY"
    # رابط تحويل الشيت لـ CSV مباشر
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        # تنظيف الداتا من أي مسافات أو قيم فارغة
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Connection Error: {e} / مشكلة في الاتصال")
        return pd.DataFrame()

# --- إدارة حالة المستخدم ---
if 'auth' not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = None
    st.session_state.exam = None

# --- 1. شاشة الدخول ---
if not st.session_state.auth:
    st.title("Student Login")
    st.markdown('<p class="arabic-text">تسجيل دخول الطالب</p>', unsafe_allow_html=True)
    
    with st.form("login"):
        sid = st.text_input("ID / رقم الطالب").strip()
        spass = st.text_input("Password / كلمة المرور", type="password").strip()
        
        if st.form_submit_button("Sign In / دخول"):
            df_students = get_data_from_google("Students")
            if not df_students.empty:
                # التأكد من تحويل الأعمدة لنصوص للمقارنة الدقيقة
                df_students['ID'] = df_students['ID'].astype(str).str.strip()
                df_students['Password'] = df_students['Password'].astype(str).str.strip()
                
                user = df_students[(df_students['ID'] == sid) & (df_students['Password'] == spass)]
                
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.user = user.iloc[0].to_dict()
                    st.success("Welcome! / تم الدخول")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid Login / خطأ في البيانات")
            else:
                st.error("Check Sheet names! / تأكد من أسماء التبويبات في الشيت")

# --- 2. لوحة الامتحانات (بتظهر بعد الدخول) ---
elif st.session_state.auth and st.session_state.exam is None:
    u = st.session_state.user
    st.title(f"Hello, {u['Name']}")
    st.markdown(f'<p class="arabic-text">أهلاً بك يا {u["Name"]} (شعبة {u["Section"]})</p>', unsafe_allow_html=True)
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.auth = False
        st.rerun()

    st.subheader("Available Exams")
    df_exams = get_data_from_google("Exams")
    
    if not df_exams.empty:
        # تصفية الامتحانات حسب الشعبة والحالة
        my_exams = df_exams[
            (df_exams['Status'] == 'Active') & 
            ((df_exams['Section'].astype(str) == str(u['Section'])) | (df_exams['Section'] == 'All'))
        ]
        
        if my_exams.empty:
            st.info("No exams active / لا توجد امتحانات مفعلة")
        else:
            for _, row in my_exams.iterrows():
                with st.container():
                    st.markdown(f"""<div class="exam-box">
                        <strong>{row['Title']}</strong><br>Lesson: {row['Lesson']} | Duration: {row['Duration']} min
                    </div>""", unsafe_allow_html=True)
                    if st.button("Start / ابدأ", key=row['Exam_ID']):
                        st.session_state.exam = row.to_dict()
                        st.session_state.start_t = time.time()
                        st.rerun()

# --- 3. مشغل الامتحان ---
else:
    exam = st.session_state.exam
    st.title(exam['Title'])
    
    # حساب الوقت
    rem = (int(exam['Duration']) * 60) - int(time.time() - st.session_state.start_t)
    
    if rem <= 0:
        st.error("Time finished! / انتهى الوقت")
        if st.button("Back / عودة"):
            st.session_state.exam = None
            st.rerun()
    else:
        m, s = divmod(rem, 60)
        st.metric("Time Remaining / الوقت المتبقي", f"{m:02d}:{s:02d}")
        st.components.v1.html(exam['HTML_Code'], height=700, scrolling=True)
        
        if st.button("Submit / تسليم"):
            st.success("Submitted! / تم التسليم")
            time.sleep(2)
            st.session_state.exam = None
            st.rerun()
