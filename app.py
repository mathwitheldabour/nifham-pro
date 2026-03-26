import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & CSS Styling ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

PASSING_SCORE = 50

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { 
        font-family: 'Cairo', sans-serif; font-size: 0.85em; 
        color: #6c757d; display: block; direction: rtl; text-align: right;
    }
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: bold; 
        height: 3em; background-color: #007bff; color: white; 
    }
    .exam-card { 
        background: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; 
        border-left: 5px solid #007bff; text-align: left;
    }
    .timer-box { 
        font-size: 1.8rem; font-weight: bold; color: #d9534f; 
        text-align: center; background: #f8d7da; padding: 10px; 
        border-radius: 8px; border: 1px solid #f5c6cb; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Engine (Connect & Clean) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except Exception as e:
        st.error(f"Error loading sheet '{name}': {e}")
        return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    cols_to_fix = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Section_Name']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session Management ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Login System ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>مرحباً بك في منصة نفهم التعليمية</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(target))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    u_data = user_match.iloc[0].to_dict()
                    role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': role})
                    st.rerun()
                else:
                    st.error("Invalid Login / بيانات الدخول غير صحيحة")

# --- 5. Teacher Dashboard ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Hi, {st.session_state.user.get('Name', 'Teacher')}")
    menu = st.sidebar.radio("Main Menu", ["Results Matrix", "Analytics", "Add New Exam", "Management"])
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    df_exams = load_sheet("Exams")
    
    # Generate Sections List
    sections_set = set()
    if not df_students.empty: sections_set.update(df_students['Section'].unique())
    try:
        df_sec_tab = clean_data(load_sheet("Sections"))
        if not df_sec_tab.empty: sections_set.update(df_sec_tab['Section_Name'].unique())
    except: pass
    final_sections = sorted([s for s in sections_set if str(s) != 'nan' and str(s).strip() != ""])

    # --- Matrix ---
    if menu == "Results Matrix":
        st.header("📊 Results Matrix")
        st.markdown("<span class='arabic-sub'>مصفوفة النتائج العامة</span>", unsafe_allow_html=True)
        if not df_students.empty and not df_grades.empty:
            sel_sec = st.selectbox("Filter Section", ["All"] + final_sections)
            f_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            merged = pd.merge(f_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
            else: st.info("No grades yet.")

    # --- Analytics ---
    elif menu == "Analytics":
        st.header("📈 Analytics Dashboard")
        st.markdown("<span class='arabic-sub'>لوحة تحليلات الأداء</span>", unsafe_allow_html=True)
        if not df_grades.empty and not df_students.empty:
            df_full = pd.merge(df_grades, df_students, left_on='Student_ID', right_on='ID', how='inner')
            c1, c2, c3 = st.columns(3)
            c1.metric("Students", len(df_students))
            c2.metric("Avg Score", f"{df_grades['Score'].mean():.1f}%")
            c3.metric("Exams Done", len(df_grades['Exam_ID'].unique()))
            
            # Chart
            sec_avg = df_full.groupby('Section')['Score'].mean().reset_index()
            fig = px.bar(sec_avg, x='Section', y='Score', title="Performance by Section", color='Score')
            st.plotly_chart(fig, use_container_width=True)
        else: st.warning("Not enough data.")

    # --- Add New Exam (FIXED) ---
    elif menu == "Add New Exam":
        st.header("📝 Create New Exam")
        st.markdown("<span class='arabic-sub'>إضافة اختبار جديد</span>", unsafe_allow_html=True)
        with st.form("new_exam_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                e_id = st.text_input("Exam Code (ID)")
                e_ti = st.text_input("Exam Title")
                s_dt = st.date_input("Start Date", datetime.now())
            with col_b:
                e_du = st.number_input("Duration (Min)", value=60)
                e_se = st.multiselect("Assign to Sections", final_sections)
                n_dt = st.date_input("End Date", datetime.now())
            e_ht = st.text_area("HTML Code")
            if st.form_submit_button("Publish Exam"):
                if e_id and e_ti and e_se:
                    old_ex = load_sheet("Exams")
                    new_row = pd.DataFrame([{"Exam_ID": e_id, "Title": e_ti, "Section": ",".join(e_se), "Duration": e_du, "HTML_Code": e_ht, "Status": "Active"}])
                    conn.update(worksheet="Exams", data=pd.concat([old_ex, new_row], ignore_index=True))
                    st.success("Exam Published!"); time.sleep(1); st.rerun()

    # --- Management (FIXED) ---
    elif menu == "Management":
        st.header("⚙️ System Management")
        st.markdown("<span class='arabic-sub'>إدارة الطلاب والشعب</span>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Sections", "Students"])
        with t1:
            with st.form("add_sec"):
                n_s = st.text_input("New Section Name")
                if st.form_submit_button("Add"):
                    old = load_sheet("Sections")
                    conn.update(worksheet="Sections", data=pd.concat([old, pd.DataFrame([{"Section_Name": n_s}])], ignore_index=True))
                    st.success("Added!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("add_stu"):
                sn = st.text_input("Student Name"); si = st.text_input("ID")
                ss = st.selectbox("Section", final_sections)
                sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    old = load_sheet("Students")
                    conn.update(worksheet="Students", data=pd.concat([old, pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])], ignore_index=True))
                    st.success("Registered!"); time.sleep(1); st.rerun()

# --- 6. Student Dashboard ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    # التحقق: هل الطالب في وضع "داخل الامتحان" أم في "اللوحة الرئيسية"؟
    if st.session_state.exam is not None:
        # --- 7. Exam Runner (داخل الامتحان) ---
        ex = st.session_state.exam
        st.subheader(f"Active Exam: {ex['Title']}")
        
        rem = (int(float(ex['Duration'])) * 60) - (time.time() - st.session_state.start_t)
        
        if rem <= 0:
            st.error("Time is Up! / انتهى الوقت")
            if st.button("Back to Dashboard"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            html_code = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID']))
            st.components.v1.html(html_code, height=800, scrolling=True)
            if st.button("Exit Exam"): st.session_state.exam = None; st.rerun()
            
    else:
        # --- اللوحة الرئيسية للطالب ---
        st.title(f"Welcome, {u['Name']} 👋")
        if st.sidebar.button("Logout"):
            st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

        tab1, tab2, tab3 = st.tabs(["📋 Exams", "✅ Grades", "📊 My Performance"])
        
        with tab1:
            st.subheader("Available Exams")
            if not df_ex_stu.empty:
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                taken_ids = my_grades['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]
                
                if required.empty: st.success("No exams pending!")
                for _, ex in required.iterrows():
                    st.markdown(f'<div class="exam-card"><b>{ex["Title"]}</b></div>', unsafe_allow_html=True)
                    if st.button(f"Start Exam", key=ex['Exam_ID']):
                        st.session_state.exam = ex.to_dict()
                        st.session_state.start_t = time.time()
                        st.rerun()

        with tab2:
            st.subheader("Grade History")
            st.table(my_grades[['Exam_ID', 'Score']])

        with tab3:
            st.subheader("Performance Chart")
            if not my_grades.empty:
                fig = px.line(my_grades, x='Exam_ID', y='Score', title="My Progress", markers=True)
                st.plotly_chart(fig, use_container_width=True)

# --- 8. Parent Dashboard (Section Added to fix the error) ---
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    st.markdown("<span class='arabic-sub'>بوابة ولي الأمر - متابعة مستوى الأبناء</span>", unsafe_allow_html=True)
    
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
    
    # تحميل بيانات الطالب المرتبط بولي الأمر (بافتراض أن ID ولي الأمر هو نفس ID الطالب للمتابعة)
    parent_data = st.session_state.user
    child_id = parent_data.get('ID') # أو أي حقل آخر يربطهم
    
    df_all_grades = clean_data(load_sheet("Grades"))
    child_grades = df_all_grades[df_all_grades['Student_ID'] == str(child_id)]
    
    if not child_grades.empty:
        st.subheader(f"Grades for Student ID: {child_id}")
        st.dataframe(child_grades[['Exam_ID', 'Score']], use_container_width=True)
        
        fig_parent = px.bar(child_grades, x='Exam_ID', y='Score', title="Child's Performance Index")
        st.plotly_chart(fig_parent, use_container_width=True)
    else:
        st.info("No grade records found for your child yet.")

# --- 9. Final Catch ---
else:
    st.warning("Please login to access this page.")
    if st.button("Back to Login"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
