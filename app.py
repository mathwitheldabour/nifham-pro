import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. SETTINGS ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 12px; font-weight: bold; }
    .stButton>button:hover { background-color: #10b981; border: none; }
    .ar-text { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .card { background: white; padding: 20px; border-radius: 15px; border-left: 5px solid #10b981; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, dtype=str)

# --- 3. SESSION MANAGEMENT ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. LOGIN PORTAL ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("Bilingual Login | تسجيل الدخول")
        uid = st.text_input("User ID | الكود").strip()
        upass = st.text_input("Password | كلمة المرور", type="password").strip()
        
        if st.button("Login | دخول"):
            try:
                # محاولة دخول المعلم (من شيت Users)
                df_u = load_data("Users")
                admin = df_u[(df_u['ID'].astype(str) == uid) & (df_u['Password'].astype(str) == upass)]
                if not admin.empty:
                    st.session_state.role = 'teacher'
                    st.session_state.user = admin.iloc[0]
                    st.rerun()
                
                # محاولة دخول الطالب/ولي الأمر (من شيت Students)
                df_s = load_data("Students")
                user = df_s[(df_s['ID'].astype(str) == uid) & (df_s['Password'].astype(str) == upass)]
                if not user.empty:
                    st.session_state.role = user.iloc[0].get('Roll', 'student').lower().strip()
                    st.session_state.user = user.iloc[0]
                    st.rerun()
                
                st.error("بيانات الدخول غير صحيحة")
            except: st.error("خطأ في الاتصال بقاعدة البيانات")

# --- 5. TEACHER DASHBOARD ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Control Panel")
    menu = st.sidebar.radio("Navigation", ["Analytics Dashboard", "Add Exam/Assignment", "Manage Students"])
    
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()

    if menu == "Analytics Dashboard":
        st.title("📊 Performance Analytics | تحليلات الأداء")
        try:
            df_grades = load_data("Grades")
            df_grades['Score'] = pd.to_numeric(df_grades['Score'], errors='coerce')
            
            # إحصائيات عامة
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Total Attempts", len(df_grades))
            m_col2.metric("Average Score", f"{df_grades['Score'].mean():.1f}%")
            m_col3.metric("Highest Score", f"{df_grades['Score'].max()}%")
            
            # رسم بياني لتوزيع الدرجات
            fig = px.histogram(df_grades, x="Score", nbins=10, title="Grade Distribution", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig, use_container_width=True)
            
            # عرض جدول الدرجات الأخير
            st.markdown("### Recent Results")
            st.dataframe(df_grades.tail(10), use_container_width=True)
        except:
            st.warning("لا توجد بيانات درجات مسجلة حالياً.")

    elif menu == "Add Exam/Assignment":
        st.title("➕ Create New Assessment")
        with st.form("exam_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                e_id = st.text_input("Exam ID (e.g., EX101)")
                e_title = st.text_input("Title | العنوان")
                e_start = st.date_input("Start Date")
            with col_b:
                e_section = st.selectbox("Section | الشعبة", ["12A", "12B", "12C", "All"])
                e_end = st.date_input("End Date | تاريخ انتهاء الاختبار")
                e_duration = st.number_input("Duration (Min)", min_value=5, value=45)
            
            e_html = st.text_area("HTML Code | كود الاختبار", height=250)
            
            if st.form_submit_button("Publish | نشر"):
                st.success("Exam details captured! Update your 'Exams' sheet with these values.")
                st.code(f"{e_id}, {e_title}, {e_section}, {e_end}, {e_duration}")

    elif menu == "Manage Students":
        st.title("👥 Student Management | إدارة الطلاب")
        try:
            df_students = load_data("Students")
            st.markdown("### View and Edit Student Data")
            # استخدام data_editor للسماح للمعلم برؤية وتعديل البيانات
            st.data_editor(df_students, use_container_width=True, num_rows="dynamic")
            st.info("تأكد من تحديث ملف الإكسيل يدوياً بناءً على التغييرات أعلاه.")
        except:
            st.error("فشل تحميل بيانات الطلاب.")

# --- 6. STUDENT DASHBOARD ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.title(f"🎓 Portal: {user['Name']}")
    tab1, tab2 = st.tabs(["Active Exams", "My History"])
    
    with tab1:
        df_exams = load_data("Exams")
        # فلترة حسب الشعبة
        my_exams = df_exams[(df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All')]
        
        # الحصول على الوقت الحالي
        current_date = datetime.now().date()
        
        for idx, ex in my_exams.iterrows():
            # تحويل تاريخ الانتهاء للمقارنة
            end_date = pd.to_datetime(ex['End_Date']).date()
            
            if current_date <= end_date:
                with st.expander(f"📝 {ex['Title']}"):
                    st.write(f"Expires on: {ex['End_Date']}")
                    if st.button(f"Start | ابدأ", key=ex['Exam_ID']):
                        components.html(ex['HTML_Code'], height=800, scrolling=True)
            else:
                st.markdown(f"~~{ex['Title']} (Expired)~~")

    with tab2:
        try:
            df_grades = load_data("Grades")
            my_results = df_grades[df_grades['SID'] == str(user['ID'])]
            st.table(my_results[['EID', 'Score', 'Date']])
        except:
            st.write("No grades yet.")
