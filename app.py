import streamlit as st
import pandas as pd
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math | منصة نفهم", layout="centered")

# --- تنسيق احترافي ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .arabic-text { direction: rtl; text-align: right; color: #555; font-size: 0.9em; }
    .user-tag { background-color: #e1f5fe; padding: 5px 15px; border-radius: 15px; color: #0288d1; font-weight: bold; }
    .exam-box { padding: 15px; border-radius: 10px; border: 1px solid #ddd; background: white; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- دالة قراءة البيانات المباشرة ---
def get_data_from_google(sheet_name):
    SHEET_ID = "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns] # تنظيف أسماء الأعمدة
        return df
    except Exception as e:
        return pd.DataFrame()

# --- إدارة الحالة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None})

# --- 1. شاشة الدخول الموحدة ---
if not st.session_state.auth:
    st.title("NIFHAM Math Platform")
    st.markdown('<p class="arabic-text">مرحباً بك في منصة نفهم للرياضيات</p>', unsafe_allow_html=True)
    
    # اختيار نوع المستخدم
    role_choice = st.radio("Login as / الدخول كـ:", ["Student / طالب", "Teacher / معلم"], horizontal=True)
    
    with st.form("login_form"):
        u_id = st.text_input("ID / رقم المستخدم").strip()
        u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
        submit = st.form_submit_button("Sign In / دخول")
        
        if submit:
            # تحديد الشيت المطلوب بناءً على الاختيار
            sheet_target = "Students" if "Student" in role_choice else "Users"
            df_users = get_data_from_google(sheet_target)
            
            if not df_users.empty:
                # تحويل البيانات لنصوص للمطابقة
                df_users['ID'] = df_users['ID'].astype(str).str.strip()
                df_users['Password'] = df_users['Password'].astype(str).str.strip()
                
                match = df_users[(df_users['ID'] == u_id) & (df_users['Password'] == u_pass)]
                
                if not match.empty:
                    st.session_state.auth = True
                    st.session_state.user = match.iloc[0].to_dict()
                    st.session_state.role = "Student" if "Student" in role_choice else "Teacher"
                    st.success(f"Welcome {st.session_state.user['Name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid ID or Password / خطأ في رقم المستخدم أو كلمة المرور")
            else:
                st.error(f"Sheet '{sheet_target}' not found! / تأكد من وجود الشيت بالاسم الصحيح")

# --- 2. لوحة التحكم ---
else:
    u = st.session_state.user
    role = st.session_state.role
    
    # الشريط الجانبي
    st.sidebar.markdown(f'<div class="user-tag">{role}</div>', unsafe_allow_html=True)
    st.sidebar.title(f"Hi, {u['Name']}")
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None})
        st.rerun()

    # --- واجهة المعلم (Teacher Dashboard) ---
    if role == "Teacher":
        st.title("Teacher Dashboard")
        st.markdown('<p class="arabic-text">لوحة تحكم المعلم</p>', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Exams Management / إدارة الامتحانات", "Student Grades / درجات الطلاب"])
        
        with tab1:
            st.write("Current Exams in Google Sheet:")
            df_exams = get_data_from_google("Exams")
            if not df_exams.empty:
                st.dataframe(df_exams[['Exam_ID', 'Title', 'Section', 'Status']])
            else:
                st.warning("No exams found in 'Exams' sheet.")
        
        with tab2:
            st.write("Viewing Grades (from 'Grades' sheet):")
            df_grades = get_data_from_google("Grades")
            if not df_grades.empty:
                st.dataframe(df_grades)
            else:
                st.info("No grades recorded yet.")

    # --- واجهة الطالب (Student Dashboard) ---
    else:
        if st.session_state.exam is None:
            st.title("My Exams")
            st.markdown(f'<p class="arabic-text">امتحانات {u["Section"]}</p>', unsafe_allow_html=True)
            
            df_exams = get_data_from_google("Exams")
            if not df_exams.empty:
                # تصفية حسب الشعبة
                my_exams = df_exams[
                    (df_exams['Status'] == 'Active') & 
                    ((df_exams['Section'].astype(str) == str(u['Section'])) | (df_exams['Section'] == 'All'))
                ]
                
                if my_exams.empty:
                    st.info("No active exams / لا توجد امتحانات مفعلة حالياً")
                else:
                    for _, row in my_exams.iterrows():
                        with st.container():
                            st.markdown(f"""<div class="exam-box">
                                <strong>{row['Title']}</strong><br>Lesson: {row['Lesson']} | Duration: {row['Duration']} min
                            </div>""", unsafe_allow_html=True)
                            if st.button("Start / ابدأ", key=f"ex_{row['Exam_ID']}"):
                                st.session_state.exam = row.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()
        else:
            # مشغل الامتحان (كما في الكود السابق)
            exam = st.session_state.exam
            st.title(exam['Title'])
            rem = (int(exam['Duration']) * 60) - int(time.time() - st.session_state.start_t)
            
            if rem <= 0:
                st.error("Time finished!")
                if st.button("Back"): st.session_state.exam = None; st.rerun()
            else:
                m, s = divmod(rem, 60)
                st.metric("Time Remaining", f"{m:02d}:{s:02d}")
                st.components.v1.html(exam['HTML_Code'], height=700, scrolling=True)
                if st.button("Submit"):
                    st.success("Submitted successfully!"); time.sleep(2)
                    st.session_state.exam = None; st.rerun()
