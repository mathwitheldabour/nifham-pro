import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px
import time
import random

# --- 1. إعدادات الصفحة والتنسيق (CSS) ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide", initial_sidebar_state="expanded")

# رابط السكريبت الخاص بك (الجسر)
GAS_URL = "https://script.google.com/macros/s/AKfycbzZvxhGjYN-nOm8Fgz1IZUAJJyjlwYu8sOtDXqU--P_Sohb7qT-mjSr5WLgICGMYLYYlA/exec"

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', 'Cairo', sans-serif; }
    .arabic-sub { direction: rtl; text-align: right; color: #6c757d; font-size: 0.85em; display: block; margin-top: -10px; margin-bottom: 10px; }
    .exam-card { background: #ffffff; padding: 20px; border-radius: 15px; border-left: 6px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .sidebar-user { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 10px; margin-bottom: 20px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (Data Engine) ---
# يجب تعريف هذه الدالات في البداية لتجنب أخطاء NameError
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    """تحميل البيانات من ورقة عمل محددة"""
    try:
        return conn.read(worksheet=name, ttl=0)
    except Exception:
        return pd.DataFrame()

def clean_data(df):
    """تنظيف وتنسيق البيانات لضمان دقة المقارنة"""
    if df is None or df.empty:
        return pd.DataFrame()
    # إزالة المسافات الزائدة وتحويل المعرفات لنصوص
    cols_to_fix = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password', 'Section_Name']
    for col in df.columns:
        if col in cols_to_fix:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    # تحويل الدرجات لأرقام
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. إدارة الجلسة (Auth Session) ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- 4. نظام تسجيل الدخول (Login System) ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - تسجيل الدخول</span>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        role_select = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم"])
        with st.form("login_form"):
            user_id = st.text_input("User ID / المعرف").strip()
            password = st.text_input("Password / كلمة المرور", type="password").strip()
            
            if st.form_submit_button("Sign In / دخول"):
                sheet_name = "Students" if "Student" in role_select else "Users"
                raw_users = load_sheet(sheet_name)
                df_users = clean_data(raw_users)
                
                if not df_users.empty:
                    match = df_users[(df_users['ID'] == user_id) & (df_users['Password'] == password)]
                    if not match.empty:
                        u_data = match.iloc[0].to_dict()
                        f_role = "student" if "Student" in role_select else "teacher"
                        st.session_state.update({'auth': True, 'user': u_data, 'role': f_role})
                        st.rerun()
                    else:
                        st.error("Invalid Credentials / بيانات غير صحيحة")
                else:
                    st.error("System Error: User database not found.")

# --- 5. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    # الشريط الجانبي للمعلم
    with st.sidebar:
        st.markdown(f'<div class="sidebar-user"><b>Mr. Ibrahim Eldabour</b><br><small>Khalid Bin Al Waleed School</small></div>', unsafe_allow_html=True)
        menu = st.sidebar.radio("Navigation", ["📊 Results Matrix", "📚 Exams Library", "📝 Exams Manager", "⚙️ System Settings"])
        if st.sidebar.button("Logout / خروج"):
            st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

    # تحميل البيانات للمعلم
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    active_sections = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    # أ- مصفوفة النتائج
    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        if not active_sections: st.warning("Please add sections first.")
        else:
            sel_sec = st.selectbox("Filter by Section", ["All"] + active_sections)
            filtered_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All" else df_stu
            merged = pd.merge(filtered_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
            else: st.info("No scores found yet.")

    # ب- مكتبة الاختبارات (Review & Preview)
    elif menu == "📚 Exams Library":
        st.header("Exams Library")
        if df_exm.empty: st.info("No exams published yet.")
        else:
            for _, row in df_exm.iterrows():
                with st.expander(f"📖 {row['Title']} (ID: {row['Exam_ID']})"):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**Target Sections:** {row['Section']} | **Status:** {row['Status']}")
                    # رابط المعاينة للمعلم
                    preview_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                    c2.markdown(f'<a href="{preview_url}" target="_blank"><button style="background:#007bff; color:white; border:none; padding:8px; border-radius:5px; width:100%; cursor:pointer;">👁️ Preview</button></a>', unsafe_allow_html=True)

    # ج- مدير الاختبارات (Scheduler)
    elif menu == "📝 Exams Manager":
        st.header("Exams Manager")
        with st.form("new_exam"):
            e_id = st.text_input("Exam Code (e.g., T3-MATH-01)")
            e_title = st.text_input("Exam Title")
            col_t1, col_t2 = st.columns(2)
            with col_t1: sd = st.date_input("Start Date"); stm = st.time_input("Start Time")
            with col_t2: ed = st.date_input("End Date"); etm = st.time_input("End Time")
            e_sections = st.multiselect("Assign to Sections", active_sections)
            e_html = st.text_area("HTML Content (Optional)")
            if st.form_submit_button("Publish Exam"):
                if e_id and e_title and e_sections:
                    new_ex_data = pd.DataFrame([{"Exam_ID": e_id, "Title": e_title, "Section": ",".join(e_sections), "Status": "Active", "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}", "HTML_Code": e_html}])
                    conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex_data], ignore_index=True))
                    st.success("Exam Published!"); time.sleep(1); st.rerun()

    # د- الإعدادات (Sections & Students)
    elif menu == "⚙️ System Settings":
        st.header("System Settings")
        t_sec, t_stu = st.tabs(["Sections", "Register Students"])
        with t_sec:
            new_s = st.text_input("New Section Name")
            if st.button("Add Section"):
                if new_s:
                    conn.update(worksheet="Sections", data=pd.concat([df_sec, pd.DataFrame([{"Section_Name": new_s.strip()}])], ignore_index=True))
                    st.success("Added!"); st.rerun()
        with t_stu:
            with st.form("reg_stu"):
                sn, si = st.text_input("Student Name"), st.text_input("ID")
                ss = st.selectbox("Section", active_sections)
                sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])], ignore_index=True))
                    st.success("Registered!"); st.rerun()

# --- 6. لوحة الطالب (Student Dashboard) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_subs = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]
    taken_ids = my_subs['Exam_ID'].unique().tolist()

    st.title(f"Welcome, {u['Name']} 👋")
    st.markdown(f"<span class='arabic-sub'>مرحباً بك | شعبة: {u['Section']}</span>", unsafe_allow_html=True)
    
    if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()

    tab_pending, tab_history = st.tabs(["📋 Assignments", "✅ Completed"])

    with tab_pending:
        now = datetime.now()
        # فلترة الاختبارات النشطة للطالب
        active_for_me = df_ex_stu[df_ex_stu['Section'].str.contains(str(u['Section']), na=False)]
        pending = active_for_me[~active_for_me['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        
        if pending.empty: st.success("No pending exams! / لا توجد اختبارات مطلوبة حالياً")
        for _, row in pending.iterrows():
            try:
                st_dt = datetime.strptime(str(row['Start_Time']), '%Y-%m-%d %H:%M:%S')
                en_dt = datetime.strptime(str(row['End_Time']), '%Y-%m-%d %H:%M:%S')
            except: st_dt = en_dt = now

            if st_dt <= now <= en_dt:
                with st.container():
                    st.markdown(f'''<div class="exam-card"><h3>{row['Title']}</h3><p>Ends at: {en_dt.strftime('%H:%M')}</p></div>''', unsafe_allow_html=True)
                    # رابط الامتحان (Mode: Exam)
                    exam_url = f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam"
                    st.markdown(f'<a href="{exam_url}" target="_blank"><button style="background:#28a745; color:white; border:none; padding:12px; border-radius:10px; width:100%; font-weight:bold; cursor:pointer;">Start Exam / بدء الاختبار</button></a>', unsafe_allow_html=True)
            elif now < st_dt:
                st.warning(f"Upcoming: {row['Title']} (Starts at {st_dt.strftime('%I:%M %p')})")

    with tab_history:
        if my_subs.empty: st.info("No completed exams yet.")
        else:
            for _, sub in my_subs.iterrows():
                with st.container():
                    c_h1, c_h2 = st.columns([3, 1])
                    c_h1.write(f"**Exam:** {sub['Exam_ID']} | **Score:** {sub['Score']}%")
                    # رابط المراجعة (Mode: Review)
                    review_url = f"{GAS_URL}?sid={u['ID']}&eid={sub['Exam_ID']}&name={u['Name']}&mode=review"
                    c_h2.markdown(f'<a href="{review_url}" target="_blank">Review Answers</a>', unsafe_allow_html=True)
