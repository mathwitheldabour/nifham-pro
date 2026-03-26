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
    for col in ['ID', 'Password', 'Section', 'Student_ID', 'Section_Name']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    return df

# --- 3. إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. شاشة الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
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

    df_exams = load_sheet("Exams")
    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    
    # بناء قائمة الشعب الشاملة
    all_sections = set()
    if not df_students.empty: all_sections.update(df_students['Section'].unique().tolist())
    try:
        df_sec_tab = clean_data(load_sheet("Sections"))
        if not df_sec_tab.empty: all_sections.update(df_sec_tab['Section_Name'].unique().tolist())
    except: pass
    final_sections = sorted([s for s in all_sections if str(s).lower() != 'nan' and str(s).strip() != ""])

    # --- مصفوفة النتائج ---
    if menu == "Exams Matrix":
        st.header("📊 Results Matrix / مصفوفة النتائج")
        if not df_students.empty:
            sel_sec = st.selectbox("Select Section", ["All"] + final_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            if not df_grades.empty:
                df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
                if not df_merged['Exam_ID'].dropna().empty:
                    matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                    st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
                else: st.info("No exams taken yet.")
            else: st.warning("No grades found.")
        else: st.error("No students registered.")

    # --- إضافة اختبار جديد ---
    elif menu == "Add Exam":
        st.header("📝 Create New Exam")
        with st.form("exam_form_final"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_id = st.text_input("Exam ID")
                e_ti = st.text_input("Title")
                s_date = st.date_input("Start Date", datetime.now())
                s_time = st.time_input("Start Time", datetime.now().time())
            with col_e2:
                e_du = st.number_input("Duration (Min)", value=60)
                e_se = st.multiselect("Sections", final_sections)
                n_date = st.date_input("End Date", datetime.now())
                n_time = st.time_input("End Time", datetime.now().time())
            
            e_ht = st.text_area("HTML Code")
            if st.form_submit_button("Save Exam"):
                try:
                    old_ex = load_sheet("Exams")
                    new_row = pd.DataFrame([{
                        "Exam_ID": str(e_id), "Title": str(e_ti), 
                        "Section": ",".join(e_se), "Duration": e_du,
                        "Start_DateTime": f"{s_date} {s_time}",
                        "End_DateTime": f"{n_date} {n_time}",
                        "HTML_Code": e_ht, "Status": "Active"
                    }])
                    updated_ex = pd.concat([old_ex, new_row], ignore_index=True)
                    conn.update(worksheet="Exams", data=updated_ex)
                    st.success("Exam Saved!"); time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- الإدارة (شعب وطلاب) ---
    elif menu == "Management":
        st.header("⚙️ Management")
        t1, t2 = st.tabs(["Add Section", "Add Student"])
        with t1:
            with st.form("sec"):
                n_s = st.text_input("New Section Name")
                if st.form_submit_button("Save Section"):
                    old = load_sheet("Sections")
                    upd = pd.concat([old, pd.DataFrame([{"Section_Name": n_s}])], ignore_index=True)
                    conn.update(worksheet="Sections", data=upd)
                    st.success("Done!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("stu"):
                s_n = st.text_input("Name"); s_i = st.text_input("ID")
                s_s = st.selectbox("Section", final_sections)
                s_p = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    old = load_sheet("Students")
                    upd = pd.concat([old, pd.DataFrame([{"ID": s_i, "Name": s_n, "Password": s_p, "Section": s_s}])], ignore_index=True)
                    conn.update(worksheet="Students", data=upd)
                    st.success("Registered!"); time.sleep(1); st.rerun()

# --- 6. لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = load_sheet("Exams")
    df_gr_stu = clean_data(load_sheet("Grades"))

    if st.session_state.exam is None:
        st.title(f"مرحباً بك، {u['Name']}")
        tab1, tab2, tab3 = st.tabs(["📋 الاختبارات المطلوبة", "✅ الاختبارات السابقة", "📊 التحليل"])

        with tab1:
            st.subheader("Current Assignments")
            if not df_ex_stu.empty:
                # فلترة ذكية: شعبة الطالب + غير مكرر
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                taken_ids = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]

                if required.empty:
                    st.success("أحسنت! لا توجد اختبارات حالياً.")
                else:
                    for _, ex in required.iterrows():
                        with st.container():
                            st.markdown(f'<div class="exam-card"><h4>{str(ex["Title"]).replace(".0", "")}</h4></div>', unsafe_allow_html=True)
                            if st.button("بدء الاختبار الآن", key=ex['Exam_ID']):
                                st.session_state.exam = ex.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()
        with tab2:
            st.table(df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])])
    
    # --- 7. مشغل الامتحان (المصحح والوحيد) ---
    else:
        ex = st.session_state.exam
        st.title(f"الاختبار: {str(ex['Title']).replace('.0', '')}")
        
        elapsed = time.time() - st.session_state.start_t
        remaining = (int(float(ex['Duration'])) * 60) - elapsed
        
        if remaining <= 0:
            st.error("⚠️ انتهى الوقت!")
            if st.button("خروج"): st.session_state.exam = None; st.rerun()
        else:
            mins, secs = divmod(int(remaining), 60)
            st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # حقن البيانات في الـ HTML
            final_html = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID']))
            final_html = final_html.replace("STUDENT_NAME_HERE", str(u['Name']))
            final_html = final_html.replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            
            st.components.v1.html(final_html, height=800, scrolling=True)
            st.info("💡 يتم تسجيل درجتك أوتوماتيكياً بمجرد ضغط 'إرسال' داخل نافذة الامتحان.")
            if st.button("⬅️ العودة للرئيسية"): st.session_state.exam = None; st.rerun()
