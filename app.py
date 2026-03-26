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

# --- 2. محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

def clean_data(df):
    for col in ['ID', 'Password', 'Section']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    return df

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
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_target))
                
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent')
                    st.session_state.update({'auth': True, 'user': user_data, 'role': f_role})
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 5. لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    df_exams = load_sheet("Exams")
    df_students = clean_data(load_sheet("Students"))
    df_grades = load_sheet("Grades")
    
    try:
        available_sections = load_sheet("Sections")['Section_Name'].unique().tolist()
    except:
        available_sections = df_students['Section'].unique().tolist() if not df_students.empty else []

    # --- مصفوفة النتائج المحدثة ---
    if menu == "Exams Matrix":
        st.header("📊 Results Matrix / مصفوفة النتائج")
        
        if not df_students.empty:
            # الفلتر يظهر دائماً طالما يوجد طلاب
            selected_sec = st.selectbox("Select Section / اختر الشعبة", ["All / الجميع"] + available_sections)
            
            # فلترة الطلاب حسب الشعبة
            if selected_sec != "All / الجميع":
                current_students = df_students[df_students['Section'] == selected_sec]
            else:
                current_students = df_students

            if not df_grades.empty:
                # دمج الدرجات مع الطلاب
                df_merged = pd.merge(current_students[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
                # بناء المصفوفة
                matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='lightgreen'), use_container_width=True)
            else:
                # إذا لم تكن هناك درجات بعد، نعرض قائمة الطلاب فقط
                st.info("No grades recorded yet. Displaying student list: / لم تسجل درجات بعد. قائمة الطلاب:")
                st.table(current_students[['ID', 'Name', 'Section']])
        else:
            st.warning("No students found in 'Students' sheet / لا يوجد طلاب مسجلون")

    # --- إدارة الشعب والطلاب ---
    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        t1, t2 = st.tabs(["Add Section / إضافة شعبة", "Add Student / إضافة طالب"])
        with t1:
            with st.form("sec"):
                n_s = st.text_input("Section Name")
                if st.form_submit_button("Save"):
                    conn.create(worksheet="Sections", data=pd.DataFrame([{"Section_Name": n_s}]))
                    st.success("Done!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("stu"):
                s_n = st.text_input("Student Name")
                s_i = st.text_input("Student ID")
                s_s = st.selectbox("Section", available_sections)
                s_p = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    conn.create(worksheet="Students", data=pd.DataFrame([{"ID": s_i, "Name": s_n, "Password": s_p, "Section": s_s}]))
                    st.success("Registered!"); time.sleep(1); st.rerun()

    # --- إضافة اختبار جديد ---
    elif menu == "Add Exam":
        st.header("📝 Add New Exam")
        with st.form("exam"):
            e_id = st.text_input("Exam ID")
            e_ti = st.text_input("Title")
            e_le = st.text_input("Lesson")
            e_se = st.multiselect("Sections", available_sections)
            e_du = st.number_input("Duration", value=60)
            e_ht = st.text_area("HTML Code")
            if st.form_submit_button("Save"):
                conn.create(worksheet="Exams", data=pd.DataFrame([{"Exam_ID": e_id, "Title": e_ti, "Lesson": e_le, "Section": ",".join(e_se), "Duration": e_du, "HTML_Code": e_ht, "Status": "Active"}]))
                st.success("Saved!")

# --- 6. لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    st.title(f"Welcome, {u['Name']}")
    # (كود الطالب كما هو في النسخ السابقة)
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({'auth': False}))
