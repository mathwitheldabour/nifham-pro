import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & CSS ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

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
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Children_IDs']
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session State ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Main App Logic ---

# المحطة الأولى: شاشة الدخول (إذا لم يتم تسجيل الدخول)
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - الدخول</span>", unsafe_allow_html=True)
    
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
                    # تحديد الدور برمجياً
                    role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': role})
                    st.rerun()
                else:
                    st.error("Invalid Credentials / بيانات الدخول غير صحيحة")

# المحطة الثانية: لوحة المعلم
# --- 5. Teacher Dashboard (Full Professional Implementation) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, Mr. {st.session_state.user.get('Name', 'Teacher')}")
    st.sidebar.markdown(f"<span class='arabic-sub'>مرحباً أ. {st.session_state.user.get('Name')}</span>", unsafe_allow_html=True)
    
    # قائمة التنقل الجانبية
    menu = st.sidebar.radio("Navigation Menu", 
                            ["📊 Results Matrix", "📈 Analytics Dashboard", "📝 Create New Exam", "⚙️ Management"])
    
    if st.sidebar.button("Logout / تسجيل الخروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات الأساسية للمعلم
    with st.spinner("Updating records..."):
        df_students = clean_data(load_sheet("Students"))
        df_grades = clean_data(load_sheet("Grades"))
        df_exams = clean_data(load_sheet("Exams"))
        df_sections = clean_data(load_sheet("Sections"))

    # بناء قائمة الشعب المتاحة بدقة
    sections_list = []
    if not df_sections.empty: sections_list.extend(df_sections['Section_Name'].unique().tolist())
    if not df_students.empty: sections_list.extend(df_students['Section'].unique().tolist())
    final_sections = sorted(list(set([s for s in sections_list if str(s) != 'nan' and str(s).strip() != ""])))

    # --- A. Results Matrix (مصفوفة النتائج) ---
    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        st.markdown("<span class='arabic-sub'>مصفوفة النتائج العامة للطلاب والاختبارات</span>", unsafe_allow_html=True)
        
        if not df_students.empty and not df_grades.empty:
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                sel_sec = st.selectbox("Filter by Section", ["All Sections"] + final_sections)
            
            # فلترة الطلاب حسب الشعبة
            f_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All Sections" else df_students
            
            # دمج الدرجات مع أسماء الطلاب
            merged = pd.merge(f_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
            
            if not merged['Exam_ID'].dropna().empty:
                # إنشاء مصفوفة (الطلاب في الصفوف والاختبارات في الأعمدة)
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                
                # تلوين الدرجات العالية بالأخضر
                def color_high_scores(val):
                    try:
                        if float(val) >= 90: return 'background-color: #bbf7d0; color: #166534'
                        elif float(val) < 50: return 'background-color: #fecaca; color: #991b1b'
                        return ''
                    except: return ''

                st.dataframe(matrix.style.applymap(color_high_scores), use_container_width=True)
                st.caption("Tip: Green = 90%+, Red = Below 50%")
            else: st.info("No grades recorded for selected criteria.")
        else: st.warning("Please ensure you have Students and Grades in your database.")

    # --- B. Analytics Dashboard (تحليلات الأداء) ---
    elif menu == "📈 Analytics Dashboard":
        st.header("Analytics Dashboard")
        st.markdown("<span class='arabic-sub'>تحليل مستوى الشعب والاختبارات</span>", unsafe_allow_html=True)
        
        if not df_grades.empty and not df_students.empty:
            df_full = pd.merge(df_grades, df_students, left_on='Student_ID', right_on='ID', how='inner')
            
            # أرقام رئيسية
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Students", len(df_students))
            m2.metric("Total Exams", len(df_exams))
            m3.metric("Avg. Score", f"{df_grades['Score'].mean():.1f}%")
            m4.metric("Active Sections", len(final_sections))
            
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # متوسط الدرجات حسب الشعبة
                sec_avg = df_full.groupby('Section')['Score'].mean().reset_index()
                fig1 = px.bar(sec_avg, x='Section', y='Score', title="Average Score per Section", 
                             color='Score', color_continuous_scale='Blues')
                st.plotly_chart(fig1, use_container_width=True)
                
            with col_chart2:
                # توزيع النجاح والرسوب
                pass_count = (df_grades['Score'] >= 50).sum()
                fail_count = (df_grades['Score'] < 50).sum()
                fig2 = px.pie(values=[pass_count, fail_count], names=['Passed', 'Failed'], 
                             title="Overall Success Rate", color_discrete_sequence=['#28a745', '#dc3545'])
                st.plotly_chart(fig2, use_container_width=True)
        else: st.error("Not enough data to generate analytics.")

    # --- C. Create New Exam (إضافة اختبار) ---
    elif menu == "📝 Create New Exam":
        st.header("Create New Exam")
        st.markdown("<span class='arabic-sub'>إضافة ونشر اختبار جديد للطلاب</span>", unsafe_allow_html=True)
        
        with st.form("exam_creation_form"):
            c1, c2 = st.columns(2)
            with c1:
                e_id = st.text_input("Exam Code / ID (e.g., MATH-101)")
                e_title = st.text_input("Exam Title (English)")
                e_duration = st.number_input("Duration (Minutes)", min_value=1, value=60)
            with c2:
                e_sections = st.multiselect("Assign to Sections", final_sections)
                e_status = st.selectbox("Initial Status", ["Active", "Hidden"])
            
            e_html = st.text_area("Exam HTML Template (MathJax Supported)", height=300, 
                                 help="Use VAR_A and VAR_B for dynamic variables.")
            
            if st.form_submit_button("Publish Exam / نشر الاختبار"):
                if e_id and e_title and e_sections:
                    new_ex = pd.DataFrame([{
                        "Exam_ID": e_id, "Title": e_title, "Section": ",".join(e_sections),
                        "Duration": e_duration, "HTML_Code": e_html, "Status": e_status
                    }])
                    conn.update(worksheet="Exams", data=pd.concat([df_exams, new_ex], ignore_index=True))
                    st.success("Exam Published Successfully!"); time.sleep(1); st.rerun()
                else: st.error("Please fill all required fields.")

    # --- D. Management (إدارة الطلاب والشعب) ---
    elif menu == "⚙️ Management":
        st.header("System Management")
        st.markdown("<span class='arabic-sub'>إدارة بيانات الطلاب والشعب الدراسية</span>", unsafe_allow_html=True)
        
        tab_sec, tab_stu = st.tabs(["Manage Sections", "Register Students"])
        
        with tab_sec:
            st.subheader("Add New Section")
            with st.form("add_section_form"):
                new_sec_name = st.text_input("Section Name (e.g., 12-Advanced-A)")
                if st.form_submit_button("Save Section"):
                    if new_sec_name:
                        new_s_df = pd.DataFrame([{"Section_Name": new_sec_name.strip()}])
                        conn.update(worksheet="Sections", data=pd.concat([df_sections, new_s_df], ignore_index=True))
                        st.success("Section Added!"); time.sleep(1); st.rerun()

        with tab_stu:
            st.subheader("Register New Student")
            with st.form("add_student_form"):
                sc1, sc2 = st.columns(2)
                with sc1:
                    st_name = st.text_input("Student Full Name")
                    st_id = st.text_input("Student ID (Unique)")
                with sc2:
                    st_sec = st.selectbox("Assign to Section", final_sections)
                    st_pass = st.text_input("Login Password", value=str(random.randint(1000, 9999)))
                
                if st.form_submit_button("Register Student"):
                    if st_name and st_id:
                        new_st_df = pd.DataFrame([{"ID": st_id, "Name": st_name, "Password": st_pass, "Section": st_sec}])
                        conn.update(worksheet="Students", data=pd.concat([df_students, new_st_df], ignore_index=True))
                        st.success(f"Student {st_name} registered successfully!"); time.sleep(1); st.rerun()
                        
# المحطة الثالثة: لوحة الطالب
elif st.session_state.role == 'student':
    u = st.session_state.user
    
    # --- 1. Load Student Data ---
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    # --- 2. Exam Runner Mode ---
    if st.session_state.exam is not None:
        ex = st.session_state.exam
        st.subheader(f"Exam: {ex['Title']}")
        
        # Timer Logic
        elapsed = time.time() - st.session_state.start_t
        rem_sec = (int(float(ex.get('Duration', 60))) * 60) - elapsed
        
        if rem_sec <= 0:
            st.error("Time Expired! / انتهى الوقت")
            if st.button("Close"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem_sec), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            
            # --- Dynamic Injection & LaTeX Fix ---
            html_content = str(ex['HTML_Code'])
            
            # Replace basic info
            html_content = html_content.replace("STUDENT_ID_HERE", str(u['ID']))
            html_content = html_content.replace("STUDENT_NAME_HERE", str(u['Name']))
            html_content = html_content.replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            
            # Smart Variable Injection (for dynamic math questions)
            if "VAR_A" in html_content:
                # Seed ensures variables stay same if page refreshes
                try:
                    random.seed(int(u['ID']) + int(ex['Exam_ID']))
                    html_content = html_content.replace("VAR_A", str(random.randint(2, 9)))
                    html_content = html_content.replace("VAR_B", str(random.randint(2, 5)))
                    random.seed() # Reset seed
                except: pass

            # CRITICAL: Escape backslashes for MathJax
            # This turns \frac into \\frac so the browser sees it correctly
            html_final = html_content.replace("\\", "\\\\")
            
            # Render Exam
            st.components.v1.html(html_final, height=850, scrolling=True)
            
            if st.button("Cancel & Exit / خروج"): 
                st.session_state.exam = None
                st.rerun()

    # --- 3. Main Dashboard Mode ---
    else:
        st.title(f"Welcome, {u['Name']} 👋")
        st.markdown(f"<span class='arabic-sub'>مرحباً بك، {u['Name']} | الشعبة: {u['Section']}</span>", unsafe_allow_html=True)
        
        if st.sidebar.button("Logout"):
            st.session_state.update({'auth': False, 'user': None, 'role': None})
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["📋 Assigned Exams", "✅ Grade History", "📊 Analytics"])

        # TAB 1: Pending Exams
        with tab1:
            st.subheader("Assigned Exams")
            if not df_ex_stu.empty:
                # Filter Active + Section Match + Not Taken
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                taken_ids = my_grades['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]

                if required.empty:
                    st.success("No pending exams! Well done.")
                else:
                    for _, row in required.iterrows():
                        with st.container():
                            st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b><br><small>Time: {row["Duration"]} min</small></div>', unsafe_allow_html=True)
                            if st.button(f"Start: {row['Title']}", key=row['Exam_ID']):
                                st.session_state.exam = row.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()

        # TAB 2: Grades & Smart Practice
        with tab2:
            st.subheader("Your Grades")
            if not my_grades.empty:
                st.dataframe(my_grades[['Exam_ID', 'Score']], use_container_width=True)
                
                st.divider()
                st.subheader("💡 Smart Practice")
                st.markdown("<span class='arabic-sub'>تدرب على أفكار مشابهة للاختبارات السابقة بنفس التنسيق</span>", unsafe_allow_html=True)
                
                if st.button("Generate Smart Practice / تدريب ذكي"):
                    # Use last taken exam as template
                    last_id = my_grades.iloc[-1]['Exam_ID']
                    tmpl_row = df_ex_stu[df_ex_stu['Exam_ID'] == last_id]
                    if not tmpl_row.empty:
                        tmpl_html = str(tmpl_row.iloc[0]['HTML_Code'])
                        # New random variables for practice
                        v1, v2 = random.randint(2, 9), random.randint(2, 5)
                        practice_html = tmpl_html.replace("VAR_A", str(v1)).replace("VAR_B", str(v2))
                        # Fix LaTeX backslashes
                        st.session_state.practice_mode = practice_html.replace("\\", "\\\\")
                        st.rerun()

                if 'practice_mode' in st.session_state:
                    st.info("Dynamic Practice Mode Active")
                    st.components.v1.html(st.session_state.practice_mode, height=600, scrolling=True)
                    if st.button("Close Practice"): 
                        del st.session_state.practice_mode
                        st.rerun()
            else:
                st.info("Complete your first exam to unlock Smart Practice.")

        # TAB 3: Analytics
        with tab3:
            st.subheader("Performance Analytics")
            if not my_grades.empty:
                fig = px.line(my_grades, x='Exam_ID', y='Score', title="Score Progress", markers=True)
                fig.update_layout(yaxis_range=[0, 105])
                st.plotly_chart(fig, use_container_width=True)
                
                avg = my_grades['Score'].mean()
                st.metric("Overall Average", f"{avg:.1f}%")
# المحطة الرابعة: لوحة ولي الأمر
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
    # (كود ولي الأمر المعتمد على Children_IDs)
    st.info("Parent monitoring dashboard is active.")

# المحطة الأخيرة: Catch-all
else:
    st.warning("Please login to continue.")
    st.session_state.update({'auth': False, 'user': None, 'role': None})
