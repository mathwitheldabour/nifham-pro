import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import time, random

st.set_page_config(page_title="NIFHAM Pro", layout="wide")
PASSING_SCORE = 50

# --- الاتصال بالبيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(name): return conn.read(worksheet=name, ttl=0)

def clean(df):
    if df.empty: return df
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Section_Name']
    for c in cols:
        if c in df.columns: df[c] = df[c].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns: df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

if 'auth' not in st.session_state: st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- تسجيل الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role_choice = st.selectbox("Login as", ["Student", "Teacher"])
    with st.form("login"):
        uid, upw = st.text_input("User ID"), st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            df_u = clean(get_data("Students" if role_choice=="Student" else "Users"))
            match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': role_choice.lower()})
                st.rerun()

# --- لوحة المعلم المكتملة ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, Mr. Ibrahim")
    st.sidebar.markdown(f"<span class='arabic-sub'>أهلاً بك في غرفة التحكم</span>", unsafe_allow_html=True)
    
    # القائمة الجانبية المتطورة
    menu = st.sidebar.radio("Navigation Menu", 
                            ["📊 Results Matrix", "📈 Analytics Dashboard", "📝 Exams Manager", "⚙️ System Settings"])
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات الأساسية
    with st.spinner("Fetching Data..."):
        df_stu = clean_data(load_sheet("Students"))
        df_grd = clean_data(load_sheet("Grades"))
        df_exm = clean_data(load_sheet("Exams"))
        df_sec = clean_data(load_sheet("Sections"))
        
    all_sections = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    # --- 1. مصفوفة النتائج (Results Matrix) ---
    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        st.markdown("<span class='arabic-sub'>عرض شامل لنتائج الطلاب في جميع الاختبارات</span>", unsafe_allow_html=True)
        
        if not all_sections:
            st.warning("Please add sections in 'System Settings' first.")
        else:
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                sel_sec = st.selectbox("Filter by Section", ["All Sections"] + all_sections)
            
            # فلترة الطلاب حسب الشعبة
            f_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All Sections" else df_stu
            
            # دمج الدرجات مع الأسماء
            merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                
                # تنسيق الجدول (تلوين)
                def highlight_grades(val):
                    try:
                        v = float(val)
                        if v >= 90: return 'background-color: #d1fae5; color: #065f46'
                        if v < 50: return 'background-color: #fee2e2; color: #991b1b'
                    except: pass
                    return ''

                st.dataframe(matrix.style.applymap(highlight_grades), use_container_width=True)
                st.caption("🟢 Green: 90%+ | 🔴 Red: Below 50%")
            else:
                st.info("No exam submissions found for this criteria.")

    # --- 2. تحليلات الشعب (Analytics Dashboard) ---
    elif menu == "📈 Analytics Dashboard":
        st.header("Analytics Dashboard")
        if not df_grd.empty and not df_stu.empty:
            # دمج البيانات للتحليل المتقدم
            df_full = pd.merge(df_grd, df_stu, left_on='Student_ID', right_on='ID', how='inner')
            
            # كروت الإحصائيات
            m1, m2, m3 = st.columns(3)
            m1.metric("Global Avg. Score", f"{df_grd['Score'].mean():.1f}%")
            m2.metric("Overall Success Rate", f"{(df_grd['Score'] >= 50).mean()*100:.1f}%")
            m3.metric("Total Submissions", len(df_grd))
            
            st.divider()
            
            c_left, c_right = st.columns(2)
            with c_left:
                # أداء الشعب
                sec_perf = df_full.groupby('Section')['Score'].mean().reset_index()
                fig1 = px.bar(sec_perf, x='Section', y='Score', title="Average Performance per Section", color='Score')
                st.plotly_chart(fig1, use_container_width=True)
            
            with c_right:
                # توزيع النجاح
                fig2 = px.pie(values=[(df_grd['Score'] >= 50).sum(), (df_grd['Score'] < 50).sum()], 
                              names=['Pass', 'Fail'], title="Overall Pass/Fail Ratio",
                              color_discrete_sequence=['#10b981', '#ef4444'])
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.error("Not enough data to generate charts.")

    # --- 3. إضافة وبرمجة الاختبارات (Exams Manager) ---
    elif menu == "📝 Exams Manager":
        st.header("Exams Manager")
        st.markdown("<span class='arabic-sub'>إضافة اختبار جديد وتحديد المواعيد</span>", unsafe_allow_html=True)
        
        if not all_sections:
            st.error("Step 1: Add a Section in 'System Settings' first!")
        else:
            with st.form("create_exam"):
                e_id = st.text_input("Exam Code (e.g., MATH-CH5)")
                e_title = st.text_input("Exam Title")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st_date = st.date_input("Start Date")
                    st_time = st.time_input("Start Time")
                with col_d2:
                    en_date = st.date_input("End Date")
                    en_time = st.time_input("End Time")
                
                e_dur = st.number_input("Duration (Minutes)", min_value=5, value=60)
                e_sec_list = st.multiselect("Assign to Sections", all_sections)
                e_html = st.text_area("Exam HTML Code (MathJax/VAR_A Supported)", height=250)
                
                if st.form_submit_button("🚀 Publish Exam"):
                    if e_id and e_title and e_sec_list:
                        new_ex = pd.DataFrame([{
                            "Exam_ID": e_id, "Title": e_title, "Section": ",".join(e_sec_list),
                            "Duration": e_dur, "HTML_Code": e_html, "Status": "Active",
                            "Start_Time": f"{st_date} {st_time}", "End_Time": f"{en_date} {en_time}"
                        }])
                        conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                        st.success("Exam Published Successfully!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Please fill all required fields.")

    # --- 4. إدارة النظام (System Settings) ---
    elif menu == "⚙️ System Settings":
        st.header("System Settings")
        t_sec, t_stu = st.tabs(["Manage Sections", "Register Students"])
        
        with t_sec:
            st.subheader("Add New Section")
            with st.form("add_section"):
                new_s = st.text_input("Section Name (e.g., 12-ADV-A)")
                if st.form_submit_button("Save Section"):
                    if new_s:
                        new_s_df = pd.DataFrame([{"Section_Name": new_s.strip()}])
                        conn.update(worksheet="Sections", data=pd.concat([df_sec, new_s_df], ignore_index=True))
                        st.success("Section Added!"); time.sleep(1); st.rerun()

        with t_stu:
            st.subheader("Register New Student")
            if not all_sections:
                st.warning("Add a section first.")
            else:
                with st.form("add_student"):
                    s_name = st.text_input("Full Name")
                    s_id = st.text_input("Student ID (Unique)")
                    s_sec = st.selectbox("Assign to Section", all_sections)
                    s_pass = st.text_input("Password", value=str(random.randint(1000, 9999)))
                    if st.form_submit_button("Register"):
                        new_st_df = pd.DataFrame([{"ID": s_id, "Name": s_name, "Password": s_pass, "Section": s_sec}])
                        conn.update(worksheet="Students", data=pd.concat([df_stu, new_st_df], ignore_index=True))
                        st.success("Student Registered!"); time.sleep(1); st.rerun()
# --- لوحة الطالب المكتملة ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex, df_gr = clean(get_data("Exams")), clean(get_data("Grades"))
    my_taken = df_gr[df_gr['Student_ID'] == str(u['ID'])]['Exam_ID'].unique().tolist()
    
    st.title(f"Welcome, {u['Name']} 👋")
    tab1, tab2 = st.tabs(["📋 Assigned Exams", "✅ History"])
    
    with tab1:
        now = datetime.now()
        req = df_ex[(df_ex['Status'] == 'Active') & (df_ex['Section'].str.contains(str(u['Section']), na=False))]
        pending = req[~req['Exam_ID'].astype(str).isin(map(str, my_taken))]
        
        for _, r in pending.iterrows():
            try:
                st_t = datetime.strptime(str(r['Start_Time']), '%Y-%m-%d %H:%M:%S')
                en_t = datetime.strptime(str(r['End_Time']), '%Y-%m-%d %H:%M:%S')
            except: st_t = en_t = now
            
            if st_t <= now <= en_t:
                st.info(f"Exam: {r['Title']} | Deadline: {en_t.strftime('%H:%M')}")
                # استبدل الرابط برابط الـ GAS الخاص بك
                gas_url = "https://script.google.com/macros/s/AKfycbxlvZt14hSJE2IDa-CnILEtCzbdDS9zs-VrL15EKHYvMbwNFD7xlOJrCOw8zBoUtUzBqg/exec"
                full_link = f"{gas_url}?sid={u['ID']}&eid={r['Exam_ID']}&name={u['Name']}"
                st.markdown(f'<a href="{full_link}" target="_blank" style="text-decoration:none;"><button style="background:#28a745; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; width:100%;">Start Exam</button></a>', unsafe_allow_html=True)

if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
