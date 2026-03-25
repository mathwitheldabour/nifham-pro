import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. إعدادات المنصة والتنسيق الجمالي ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide", initial_sidebar_state="expanded")

# تصميم مخصص للألوان (Midnight Blue & Emerald)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #0f172a; color: white; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 10px; width: 100%; font-weight: bold; }
    .stButton>button:hover { background-color: #10b981; color: white; border: none; }
    .ar-text { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .card { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px; }
    .status-wanted { color: #f59e0b; font-weight: bold; border: 1px solid #f59e0b; padding: 2px 8px; border-radius: 5px; }
    .status-done { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 8px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك جلب البيانات من Google Sheets ---
# تأكد من وضع SHEET_ID في Secrets الموقع
if "SHEET_ID" not in st.secrets:
    st.error("الرجاء ضبط SHEET_ID في إعدادات Secrets.")
    st.stop()

SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    # قراءة البيانات كنصوص لتجنب مشاكل الأرقام
    return pd.read_csv(url, dtype=str).fillna("")

# --- 3. إدارة جلسة المستخدم ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. بوابة تسجيل الدخول (الدخول الموحد) ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Welcome to the Advanced Learning Portal</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            st.info("Login | تسجيل الدخول")
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            submit = st.form_submit_button("Enter | دخول")
            
            if submit:
                # محاولة البحث في شيت المعلمين
                try:
                    df_u = load_data("Users")
                    admin = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                    if not admin.empty:
                        st.session_state.role = str(admin.iloc[0]['Roll']).lower().strip()
                        st.session_state.user = admin.iloc[0]
                        st.rerun()
                except: pass

                # محاولة البحث في شيت الطلاب
                try:
                    df_s = load_data("Students")
                    user = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                    if not user.empty:
                        # إذا لم يوجد عمود Roll نعتبره طالب
                        st.session_state.role = str(user.iloc[0].get('Roll', 'student')).lower().strip()
                        st.session_state.user = user.iloc[0]
                        st.rerun()
                except: pass
                
                st.error("بيانات الدخول غير صحيحة | Invalid Login")

# --- 5. لوحة تحكم المعلم (Teacher Command Center) ---
elif st.session_state.role == 'teacher':
    st.sidebar.markdown(f"### 👨‍🏫 Mr. Ibrahim")
    menu = st.sidebar.radio("القائمة", ["Dashboard", "Exam Preview", "Add Exam", "Students Matrix"])
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    if menu == "Dashboard":
        st.title("📈 Performance Analytics")
        try:
            df_grades = load_data("Grades")
            df_grades['Score'] = pd.to_numeric(df_grades['Score'], errors='coerce')
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Submissions", len(df_grades))
            col2.metric("Avg Score", f"{df_grades['Score'].mean():.1f}%")
            col3.metric("Highest", f"{df_grades['Score'].max()}%")
            
            fig = px.histogram(df_grades, x="Score", nbins=10, title="Grade Distribution", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig, use_container_width=True)
        except: st.info("لا توجد درجات مسجلة بعد.")

    elif menu == "Exam Preview":
        st.title("🖥️ شرح الاختبارات")
        df_exams = load_data("Exams")
        sel_ex = st.selectbox("اختر الاختبار للشرح", df_exams['Title'].unique())
        ex_code = df_exams[df_exams['Title'] == sel_ex].iloc[0]['HTML_Code']
        components.html(ex_code, height=900, scrolling=True)

    elif menu == "Add Exam":
        st.title("➕ إضافة اختبار/واجب جديد")
        with st.form("new_exam"):
            e_id = st.text_input("Exam ID (EX-00)")
            e_title = st.text_input("Title")
            e_lesson = st.text_input("Lesson Name (اسم الدرس)")
            e_section = st.selectbox("Section", ["12A", "12B", "12C", "All"])
            e_end = st.date_input("End Date")
            e_dur = st.number_input("Duration (Min)", value=45)
            e_html = st.text_area("HTML Quiz Code", height=200)
            if st.form_submit_button("نشر الاختبار"):
                st.success("تم تجهيز البيانات! انسخها لملف الإكسيل.")
                st.code(f"{e_id} | {e_title} | {e_lesson} | {e_end}")

    elif menu == "Students Matrix":
        st.title("👥 إدارة الطلاب ومصفوفة النتائج")
        df_s = load_data("Students")
        st.dataframe(df_s, use_container_width=True)

# --- 6. لوحة تحكم الطالب (Student Path) ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.sidebar.markdown(f"### 🎓 {user['Name']}")
    st.sidebar.write(f"Section: {user['Section']}")
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    st.title("My Learning Path | مساري التعليمي")
    
    # تحميل البيانات
    df_exams = load_data("Exams")
    df_grades = load_data("Grades")
    
    # تصفية الاختبارات لشعبة الطالب
    my_exams = df_exams[(df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All')]
    
    # تجميع الاختبارات حسب الدرس
    lessons = my_exams['Lesson'].unique()
    
    for lesson in lessons:
        with st.expander(f"📚 الدرس: {lesson}"):
            l_exams = my_exams[my_exams['Lesson'] == lesson]
            for _, ex in l_exams.iterrows():
                # التحقق من الحل السابق
                attempt = df_grades[(df_grades['SID'] == str(user['ID'])) & (df_grades['EID'] == ex['Exam_ID'])]
                
                c1, c2, c3 = st.columns([3, 1, 2])
                c1.write(f"**{ex['Title']}**")
                
                if not attempt.empty:
                    c2.markdown("<span class='status-done'>DONE</span>", unsafe_allow_html=True)
                    score = attempt.iloc[0]['Score']
                    c3.write(f"Result: {score}%")
                    # مراجعة الإجابات بصلاحية المعلم
                    if str(ex['Show_Answers']).upper() == "TRUE":
                        if st.button("Review", key=f"rev_{ex['Exam_ID']}"):
                            components.html(ex['HTML_Code'], height=800, scrolling=True)
                else:
                    c2.markdown("<span class='status-wanted'>WANTED</span>", unsafe_allow_html=True)
                    if st.button("Start", key=f"start_{ex['Exam_ID']}"):
                        components.html(ex['HTML_Code'], height=800, scrolling=True)

# --- 7. لوحة تحكم ولي الأمر (Parent Dashboard) ---
elif st.session_state.role == 'parent':
    user = st.session_state.user
    st.title(f"🏠 متابعة ولي الأمر: {user['Name']}")
    df_grades = load_data("Grades")
    my_child = df_grades[df_grades['SID'] == str(user['ID'])]
    
    if not my_child.empty:
        my_child['Score'] = pd.to_numeric(my_child['Score'])
        fig = px.line(my_child, x='Date', y='Score', title="منحنى تطور مستوى الطالب", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        st.table(my_child[['EID', 'Score', 'Date']])
    else:
        st.info("لا توجد نتائج مسجلة للطالب بعد.")
