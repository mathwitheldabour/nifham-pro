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

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & CSS ---
st.set_page_config(page_title="NIFHAM Pro | Math", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { font-family: 'Cairo', sans-serif; font-size: 0.85em; color: #6c757d; display: block; direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #007bff; }
    .timer-box { font-size: 1.8rem; font-weight: bold; color: #d9534f; text-align: center; background: #f8d7da; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    for col in ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session State ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Logic ---
if not st.session_state.auth:
    # --- LOGIN SCREEN ---
    st.title("🚀 NIFHAM Math Platform")
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID").strip()
            u_pass = st.text_input("Password", type="password").strip()
            if st.form_submit_button("Sign In"):
                target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(target))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                if not user_match.empty:
                    u_data = user_match.iloc[0].to_dict()
                    role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': role})
                    st.rerun()
                else: st.error("Invalid Login")

elif st.session_state.role == 'student':
    # --- STUDENT DASHBOARD ---
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is not None:
        # EXAM RUNNER
        ex = st.session_state.exam
        st.subheader(f"Exam: {ex['Title']}")
        elapsed = time.time() - st.session_state.start_t
        rem_sec = (int(float(ex.get('Duration', 60))) * 60) - elapsed
        
        if rem_sec <= 0:
            st.error("Time Expired!")
            if st.button("Close"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem_sec), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            # الحقن الديناميكي للبيانات مع تصحيح الـ Backslashes
            html_raw = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID'])).replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            st.components.v1.html(html_raw, height=800, scrolling=True)
            if st.button("Cancel & Exit"): st.session_state.exam = None; st.rerun()
    else:
        # MAIN TABS
        st.title(f"Welcome, {u['Name']} 👋")
        if st.sidebar.button("Logout"):
            st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

        t1, t2, t3 = st.tabs(["📋 Assigned", "✅ Grades", "📊 Performance"])
        with t1:
            st.subheader("Pending Exams")
            required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
            taken = my_grades['Exam_ID'].unique().tolist()
            required = required[~required['Exam_ID'].astype(str).isin(map(str, taken))]
            for _, row in required.iterrows():
                st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                if st.button(f"Start Exam", key=row['Exam_ID']):
                    st.session_state.exam = row.to_dict()
                    st.session_state.start_t = time.time(); st.rerun()
        with t2:
            st.subheader("Grade History")
            st.table(my_grades[['Exam_ID', 'Score']])
            st.divider()
            if st.button("Generate Smart Practice"):
                if not my_grades.empty:
                    last_id = my_grades.iloc[-1]['Exam_ID']
                    tmpl = df_ex_stu[df_ex_stu['Exam_ID'] == last_id].iloc[0]['HTML_Code']
                    # توليد أرقام وتغيير VAR_A, VAR_B
                    rendered = str(tmpl).replace("VAR_A", str(random.randint(2,9))).replace("VAR_B", str(random.randint(2,5)))
                    st.session_state.practice_view = rendered; st.rerun()
            if 'practice_view' in st.session_state:
                st.components.v1.html(st.session_state.practice_view, height=500, scrolling=True)
                if st.button("Close Practice"): del st.session_state.practice_view; st.rerun()
        with t3:
            if not my_grades.empty:
                st.plotly_chart(px.line(my_grades, x='Exam_ID', y='Score', markers=True))

else:
    # CATCH-ALL FOR TEACHER/PARENT
    st.info("Module under construction or accessed by Teacher/Parent role.")
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
                
# --- 7. Final Protection (The "Catch-All") ---
# هذا الجزء يضمن عدم ظهور أي شيء إذا لم يتم تسجيل الدخول
elif not st.session_state.auth:
    pass # سيقوم النظام بعرض شاشة الدخول فقط كما هو مبرمج في البداية

# --- 8. Parent Dashboard (Enhanced) ---
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    st.markdown("<span class='arabic-sub'>بوابة ولي الأمر - متابعة مستوى الأبناء</span>", unsafe_allow_html=True)
    
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
    
    # 1. جلب بيانات ولي الأمر الحالية
    u = st.session_state.user
    
    # 2. الحصول على أرقام الأبناء من العمود الجديد (Children_IDs)
    # نقوم بتحويل النص "101, 102" إلى قائمة ['101', '102']
    raw_children = str(u.get('Children_IDs', ''))
    if raw_children and raw_children != 'nan':
        child_id_list = [c.strip() for c in raw_children.split(',')]
        
        # 3. تحميل البيانات المطلوبة للمقارنة
        df_all_grades = clean_data(load_sheet("Grades"))
        df_all_students = clean_data(load_sheet("Students"))
        
        st.subheader(f"Monitoring {len(child_id_list)} Student(s)")
        
        # 4. عرض بيانات كل ابن في "صندوق" منفصل
        for cid in child_id_list:
            # جلب اسم الابن
            student_info = df_all_students[df_all_students['ID'] == cid]
            s_name = student_info.iloc[0]['Name'] if not student_info.empty else f"Student {cid}"
            
            with st.expander(f"Student: {s_name} (ID: {cid})", expanded=True):
                child_grades = df_all_grades[df_all_grades['Student_ID'] == cid]
                
                if not child_grades.empty:
                    col_left, col_right = st.columns([1, 2])
                    
                    with col_left:
                        st.write("**Latest Grades:**")
                        st.dataframe(child_grades[['Exam_ID', 'Score']].tail(5), use_container_width=True)
                        avg = child_grades['Score'].mean()
                        st.metric("Overall Average", f"{avg:.1f}%")
                    
                    with col_right:
                        fig = px.bar(child_grades, x='Exam_ID', y='Score', 
                                   title=f"Progress: {s_name}",
                                   range_y=[0, 100], color='Score',
                                   color_continuous_scale='RdYlGn')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No grades recorded for {s_name} yet.")
    else:
        st.warning("No children linked to this account. Please contact the administrator.")
        st.info("Direct the admin to add Student IDs in 'Children_IDs' column in the Users sheet.")

# --- 9. Final Catch ---
else:
    st.warning("Please login to access this page.")
    if st.button("Back to Login"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
