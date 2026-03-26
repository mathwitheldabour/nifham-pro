import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & Enhanced Styling ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

# Constants
PASSING_SCORE = 50

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    
    .arabic-sub { 
        font-family: 'Cairo', sans-serif; 
        font-size: 0.85em; 
        color: #6c757d; 
        display: block;
        direction: rtl;
    }
    
    .stButton>button { 
        width: 100%; border-radius: 8px; font-weight: bold; 
        height: 3em; background-color: #007bff; color: white; 
    }
    
    .exam-card { 
        background: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; 
        border-left: 5px solid #007bff; 
    }
    
    .timer-box { 
        font-size: 1.8rem; font-weight: bold; color: #d9534f; 
        text-align: center; background: #f8d7da; padding: 10px; 
        border-radius: 8px; border: 1px solid #f5c6cb; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    for col in ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session State ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Login Screen ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Select Role / اختر الصفة", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            
            submit = st.form_submit_button("Sign In / دخول")
            if submit:
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_target))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': user_data, 'role': f_role})
                    st.rerun()
                else:
                    st.error("Invalid Login / بيانات الدخول غير صحيحة")

# --- 5. Teacher Dashboard ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, {st.session_state.user.get('Name', 'Teacher')}")
    menu = st.sidebar.radio("Navigation Menu", 
                            ["Results Matrix", "Analytics", "Add New Exam", "Management"])
    
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    df_exams_info = load_sheet("Exams")

    # Get unique sections
    all_sections = sorted(df_students['Section'].unique().tolist()) if not df_students.empty else []

    # --- Results Matrix ---
    if menu == "Results Matrix":
        st.header("📊 Results Matrix")
        st.markdown("<span class='arabic-sub'>مصفوفة النتائج العامة</span>", unsafe_allow_html=True)
        
        if not df_students.empty and not df_grades.empty:
            sel_sec = st.selectbox("Filter by Section", ["All"] + all_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            
            df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
            if not df_merged['Exam_ID'].dropna().empty:
                matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
            else: st.info("No data recorded yet.")

    # --- Analytics Tab ---
    elif menu == "Analytics":
        st.header("📈 Performance Analytics")
        st.markdown("<span class='arabic-sub'>تحليلات الأداء للشعب والاختبارات</span>", unsafe_allow_html=True)
        
        if not df_grades.empty and not df_students.empty:
            df_full = pd.merge(df_grades, df_students, left_on='Student_ID', right_on='ID', how='inner')
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Students", len(df_students))
            m2.metric("Avg. Score", f"{df_grades['Score'].mean():.1f}%")
            m3.metric("Total Exams", len(df_grades['Exam_ID'].unique()))
            
            st.divider()
            
            col_a, col_b = st.columns(2)
            
            # Chart 1: Section Performance
            with col_a:
                sec_avg = df_full.groupby('Section')['Score'].mean().reset_index()
                fig1 = px.bar(sec_avg, x='Section', y='Score', title="Avg Score by Section", 
                             color='Score', color_continuous_scale='Viridis')
                st.plotly_chart(fig1, use_container_width=True)
                
            # Chart 2: Pass Rate by Exam
            with col_b:
                pass_data = df_full.groupby('Exam_ID')['Score'].apply(lambda x: (x >= PASSING_SCORE).mean() * 100).reset_index()
                fig2 = px.line(pass_data, x='Exam_ID', y='Score', title="Pass Rate % per Exam", markers=True)
                st.plotly_chart(fig2, use_container_width=True)
    # --- 5. Teacher Dashboard (Full Implementation) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, {st.session_state.user.get('Name', 'Teacher')}")
    menu = st.sidebar.radio("Navigation Menu", 
                            ["Results Matrix", "Analytics", "Add New Exam", "Management"])
    
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # Load All Necessary Data
    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    df_exams_info = load_sheet("Exams")
    
    # Logic to get all available sections for dropdowns
    all_sections_list = []
    if not df_students.empty: 
        all_sections_list.extend(df_students['Section'].unique().tolist())
    try:
        df_sec_tab = clean_data(load_sheet("Sections"))
        if not df_sec_tab.empty: 
            all_sections_list.extend(df_sec_tab['Section_Name'].unique().tolist())
    except: pass
    final_sections = sorted(list(set([s for s in all_sections_list if str(s) != 'nan' and str(s).strip() != ""])))

    # --- A. Results Matrix ---
    if menu == "Results Matrix":
        st.header("📊 Results Matrix")
        st.markdown("<span class='arabic-sub'>مصفوفة النتائج العامة</span>", unsafe_allow_html=True)
        
        if not df_students.empty and not df_grades.empty:
            sel_sec = st.selectbox("Filter by Section", ["All"] + final_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            
            df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
            if not df_merged['Exam_ID'].dropna().empty:
                matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
            else: st.info("No data recorded yet.")
        else: st.warning("No student or grade data found.")

    # --- B. Analytics ---
    elif menu == "Analytics":
        st.header("📈 Performance Analytics")
        st.markdown("<span class='arabic-sub'>تحليلات الأداء للشعب والاختبارات</span>", unsafe_allow_html=True)
        
        if not df_grades.empty and not df_students.empty:
            df_full = pd.merge(df_grades, df_students, left_on='Student_ID', right_on='ID', how='inner')
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Students", len(df_students))
            m2.metric("Avg. Score", f"{df_grades['Score'].mean():.1f}%")
            m3.metric("Total Exams", len(df_grades['Exam_ID'].unique()))
            
            col_a, col_b = st.columns(2)
            with col_a:
                sec_avg = df_full.groupby('Section')['Score'].mean().reset_index()
                fig1 = px.bar(sec_avg, x='Section', y='Score', title="Avg Score by Section", color='Score')
                st.plotly_chart(fig1, use_container_width=True)
            with col_b:
                exam_avg = df_full.groupby('Exam_ID')['Score'].mean().reset_index()
                fig2 = px.line(exam_avg, x='Exam_ID', y='Score', title="Avg Score per Exam", markers=True)
                st.plotly_chart(fig2, use_container_width=True)
        else: st.error("Not enough data for analytics.")

    # --- C. Add New Exam (FIXED) ---
    elif menu == "Add New Exam":
        st.header("📝 Create New Exam")
        st.markdown("<span class='arabic-sub'>إضافة اختبار جديد</span>", unsafe_allow_html=True)
        
        with st.form("exam_form_final"):
            c1, c2 = st.columns(2)
            with c1:
                e_id = st.text_input("Exam ID (Code)")
                e_ti = st.text_input("Exam Title")
                s_date = st.date_input("Start Date", datetime.now())
                s_time = st.time_input("Start Time", datetime.now().time())
            with c2:
                e_du = st.number_input("Duration (Minutes)", value=60)
                e_se = st.multiselect("Target Sections", final_sections)
                n_date = st.date_input("End Date", datetime.now())
                n_time = st.time_input("End Time", datetime.now().time())
            
            e_ht = st.text_area("HTML Code (The Exam Interface)")
            
            if st.form_submit_button("Save & Publish Exam"):
                if e_id and e_ti and e_se:
                    try:
                        old_ex = load_sheet("Exams")
                        new_row = pd.DataFrame([{
                            "Exam_ID": str(e_id).strip(), "Title": str(e_ti).strip(), 
                            "Section": ",".join(e_se), "Duration": e_du,
                            "Start_DateTime": f"{s_date} {s_time}",
                            "End_DateTime": f"{n_date} {n_time}",
                            "HTML_Code": e_ht, "Status": "Active"
                        }])
                        updated_ex = pd.concat([old_ex, new_row], ignore_index=True)
                        conn.update(worksheet="Exams", data=updated_ex)
                        st.success("Exam Published Successfully! / تم نشر الاختبار"); time.sleep(1); st.rerun()
                    except Exception as ex_err: st.error(f"Error: {ex_err}")
                else: st.error("Please fill all basic fields.")

    # --- D. Management (FIXED) ---
    elif menu == "Management":
        st.header("⚙️ Management")
        st.markdown("<span class='arabic-sub'>إدارة الطلاب والشعب</span>", unsafe_allow_html=True)
        
        t1, t2 = st.tabs(["Add Section / إضافة شعبة", "Add Student / إضافة طالب"])
        
        with t1:
            with st.form("sec_form"):
                n_s = st.text_input("New Section Name")
                if st.form_submit_button("Save Section"):
                    if n_s:
                        old = load_sheet("Sections")
                        upd = pd.concat([old, pd.DataFrame([{"Section_Name": n_s.strip()}])], ignore_index=True)
                        conn.update(worksheet="Sections", data=upd)
                        st.success("Section Added!"); time.sleep(1); st.rerun()
        
        with t2:
            with st.form("stu_form"):
                col1, col2 = st.columns(2)
                with col1:
                    s_n = st.text_input("Student Name")
                    s_i = st.text_input("Student ID")
                with col2:
                    s_s = st.selectbox("Select Section", final_sections)
                    s_p = st.text_input("Password", value=str(random.randint(1000, 9999)))
                
                if st.form_submit_button("Register Student"):
                    if s_n and s_i:
                        old = load_sheet("Students")
                        new_stu = pd.DataFrame([{"ID": str(s_i), "Name": s_n, "Password": str(s_p), "Section": s_s}])
                        upd = pd.concat([old, new_stu], ignore_index=True)
                        conn.update(worksheet="Students", data=upd)
                        st.success("Student Registered!"); time.sleep(1); st.rerun()

    # --- Management & Exams (Add sections/students/exams) ---
    # [Rest of Teacher Logic remains similar but with bilingual headers]

# --- 6. Student Dashboard ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = load_sheet("Exams")
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is None:
        st.title(f"Welcome, {u['Name']} 👋")
        st.markdown(f"<span class='arabic-sub'>شعبة: {u['Section']}</span>", unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📋 Pending Exams", "✅ Grade History", "📊 My Analytics"])

        with tab1:
            st.subheader("Assigned Exams")
            required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
            taken_ids = my_grades['Exam_ID'].unique().tolist()
            required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]

            if required.empty:
                st.success("No exams pending! / لا توجد اختبارات مطلوبة حالياً")
            else:
                for _, ex in required.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="exam-card">
                            <strong>{ex['Title']}</strong><br/>
                            <small class='arabic-sub'>{ex['Exam_ID']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("Start Exam / بدء الاختبار", key=ex['Exam_ID']):
                            st.session_state.exam = ex.to_dict()
                            st.session_state.start_t = time.time()
                            st.rerun()

        with tab2:
            st.subheader("Your Grades")
            if not my_grades.empty:
                st.table(my_grades[['Exam_ID', 'Score']])
            else: st.info("No records found.")

        with tab3:
            st.subheader("Learning Progress")
            if not my_grades.empty:
                # Compare student with section average
                all_stu_grades = pd.merge(df_gr_stu, load_sheet("Students")[['ID', 'Section']], left_on='Student_ID', right_on='ID')
                sec_avg = all_stu_grades[all_stu_grades['Section'] == u['Section']].groupby('Exam_ID')['Score'].mean().reset_index()
                
                # Plot
                plot_df = pd.merge(my_grades[['Exam_ID', 'Score']], sec_avg, on='Exam_ID', suffixes=('_Me', '_Section'))
                fig_progress = px.line(plot_df, x='Exam_ID', y=['Score_Me', '_Score_Section'], 
                                       title="My Progress vs Section Average", markers=True)
                st.plotly_chart(fig_progress, use_container_width=True)

# --- 7. Exam Engine (The Runner) ---
else:
    ex = st.session_state.exam
    st.subheader(f"Active Exam: {ex['Title']}")
    
    elapsed = time.time() - st.session_state.start_t
    remaining = (int(float(ex['Duration'])) * 60) - elapsed
    
    if remaining <= 0:
        st.error("Time is Up! / انتهى الوقت")
        if st.button("Close"): st.session_state.exam = None; st.rerun()
    else:
        mins, secs = divmod(int(remaining), 60)
        st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
        
        # HTML Injection
        final_html = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID']))
        st.components.v1.html(final_html, height=800, scrolling=True)
        
        if st.button("Exit Exam"): st.session_state.exam = None; st.rerun()
