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
    """تنظيف البيانات لضمان مطابقة النصوص والأرقام"""
    for col in ['ID', 'Password', 'Section', 'Student_ID']:
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

# --- 5. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات الأساسية للمعلم
    df_exams = load_sheet("Exams")
    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    
    # قائمة الشعب الشاملة (رادار الشعب)
    comprehensive_sections = set()
    if not df_students.empty: comprehensive_sections.update(df_students['Section'].unique().tolist())
    try: 
        df_sec_tab = load_sheet("Sections")
        if not df_sec_tab.empty: comprehensive_sections.update(df_sec_tab['Section_Name'].astype(str).unique().tolist())
    except: pass
    final_sections = sorted([s for s in comprehensive_sections if str(s).lower() != 'nan' and str(s).strip() != ""])

    # --- القسم الأول: مصفوفة النتائج ---
    if menu == "Exams Matrix":
        st.header("📊 Results Matrix / مصفوفة النتائج")
        if not df_students.empty:
            sel_sec = st.selectbox("Select Section / الشعبة", ["All"] + final_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            
            if not df_grades.empty:
                df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
                if not df_merged['Exam_ID'].dropna().empty:
                    matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                    st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
                else: st.info("No exams taken yet.")
            else: st.warning("No grades found.")
        else: st.error("No students registered.")

    # --- القسم الثاني: تحليل مستوى الطالب (المطور والجديد) ---
    elif menu == "Student Analysis":
        st.header("👤 Individual Analysis / تحليل مستوى الطالب")
        if not df_students.empty:
            c1, c2 = st.columns(2)
            with c1: sel_s = st.selectbox("1. Choose Section", final_sections)
            with c2:
                stu_list = df_students[df_students['Section'] == sel_s]
                sel_name = st.selectbox("2. Choose Student", stu_list['Name'].unique())
            
            curr_stu = stu_list[stu_list['Name'] == sel_name].iloc[0]
            if not df_grades.empty:
                stu_results = df_grades[df_grades['Student_ID'] == str(curr_stu['ID'])]
                if not stu_results.empty:
                    st.subheader(f"📊 Report for: {sel_name}")
                    st.table(stu_results[['Date', 'Exam_ID', 'Score']])
                    
                    # تحليل مهارات افتراضي (قابلة للطباعة)
                    st.write("### 🧠 Skills Analysis")
                    avg = stu_results['Score'].astype(float).mean()
                    skills = pd.DataFrame({
                        "Skill": ["Algebra", "Calculus", "Problem Solving"],
                        "Level": ["Excellent" if avg > 90 else "Good", "Strong" if avg > 80 else "Average", "Improving"]
                    })
                    st.table(skills)
                    st.info("💡 Print: Press Ctrl + P")
                else: st.warning("No grades for this student.")

    # --- القسم الثالث: الإدارة ---
    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        t1, t2 = st.tabs(["Add Section", "Add Student"])
        with t1:
            with st.form("add_sec"):
                n_sec = st.text_input("New Section Name")
                if st.form_submit_button("Save Section"):
                    try:
                        old_sec = load_sheet("Sections")
                        updated_sec = pd.concat([old_sec, pd.DataFrame([{"Section_Name": n_sec}])], ignore_index=True)
                        conn.update(worksheet="Sections", data=updated_sec)
                        st.success("Done!"); time.sleep(1); st.rerun()
                    except:
                        conn.create(worksheet="Sections", data=pd.DataFrame([{"Section_Name": n_sec}]))
                        st.success("Tab Created & Saved!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("add_stu"):
                s_n = st.text_input("Name"); s_i = st.text_input("ID")
                s_s = st.selectbox("Section", final_sections)
                s_p = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    old_stu = load_sheet("Students")
                    updated_stu = pd.concat([old_stu, pd.DataFrame([{"ID": s_i, "Name": s_n, "Password": s_p, "Section": s_s}])], ignore_index=True)
                    conn.update(worksheet="Students", data=updated_stu)
                    st.success("Registered!"); time.sleep(1); st.rerun()

    # --- القسم الرابع: إضافة اختبار ---
    elif menu == "Add Exam":
        st.header("📝 Create New Exam")
        with st.form("exam_form"):
            e_id = st.text_input("Exam ID"); e_ti = st.text_input("Title")
            e_le = st.text_input("Lesson"); e_se = st.multiselect("Target Sections", final_sections)
            e_du = st.number_input("Duration", value=60); e_ht = st.text_area("HTML Code")
            if st.form_submit_button("Save Exam"):
                old_ex = load_sheet("Exams")
                new_ex = pd.concat([old_ex, pd.DataFrame([{
                    "Exam_ID": e_id, "Title": e_ti, "Lesson": e_le, "Section": ",".join(e_se), 
                    "Duration": e_du, "HTML_Code": e_ht, "Status": "Active"
                }])], ignore_index=True)
                conn.update(worksheet="Exams", data=new_ex)
                st.success("Exam Saved!"); time.sleep(1); st.rerun()

# --- 6. لوحة الطالب (Student Dashboard) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    st.title(f"Hi, {u['Name']}")
    if st.sidebar.button("Logout"): st.session_state.auth = False; st.rerun()
    
    df_ex = load_sheet("Exams")
    df_gr = clean_data(load_sheet("Grades"))
    
    t1, t2 = st.tabs(["📋 To-do", "✅ Completed"])
    with t1:
        # عرض الاختبارات حسب الشعبة
        todo = df_ex[(df_ex['Status'] == 'Active') & (df_ex['Section'].str.contains(str(u['Section'])))]
        for _, ex in todo.iterrows():
            with st.container():
                st.markdown(f'<div class="exam-card"><h4>{ex["Title"]}</h4></div>', unsafe_allow_html=True)
                if st.button("Start / ابدأ", key=ex['Exam_ID']):
                    st.session_state.update({'exam': ex.to_dict(), 'start_t': time.time()})
                    st.rerun()
    with t2:
        st.table(df_gr[df_gr['Student_ID'] == str(u['ID'])])
