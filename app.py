import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. إعدادات الصفحة والتنسيق (Bilingual Styling) ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

PASSING_SCORE = 50

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { font-family: 'Cairo', sans-serif; font-size: 0.85em; color: #6c757d; display: block; direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #007bff; }
    .timer-box { font-size: 2rem; font-weight: bold; color: #d9534f; text-align: center; background: #f8d7da; padding: 10px; border-radius: 10px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (Data Engine) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Children_IDs', 'Section_Name']
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. إدارة الجلسة (Session State) ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. منطق التطبيق (Application Logic) ---

# المحطة الأولى: شاشة الدخول
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - تسجيل الدخول</span>", unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID / المعرف").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_users = clean_data(load_sheet(sheet_target))
                match = df_users[(df_users['ID'] == str(u_id)) & (df_users['Password'] == str(u_pass))]
                
                if not match.empty:
                    u_data = match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': f_role})
                    st.rerun()
                else: st.error("Invalid Credentials / بيانات الدخول خاطئة")

# --- 5. Teacher Dashboard (Management Flow Optimized) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Mr. {st.session_state.user.get('Name')}")
    menu = st.sidebar.radio("Navigation", ["Results Matrix", "Analytics", "Exams Manager", "System Settings"])
    
    if st.sidebar.button("Logout"): 
        st.session_state.update({'auth': False})
        st.rerun()

    # تحميل البيانات
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec_tab = clean_data(load_sheet("Sections")) # الشيت الأساسي للشعب

    # جلب قائمة الشعب من شيت Sections حصراً لضمان دقة البيانات
    final_sections = sorted(df_sec_tab['Section_Name'].unique().tolist()) if not df_sec_tab.empty else []

    # --- مصفوفة النتائج والتحليلات (نفس المنطق السابق) ---
    if menu == "Results Matrix":
        st.header("Results Matrix")
        if not final_sections:
            st.warning("No sections found. Please add sections in 'System Settings' first.")
        else:
            sel_sec = st.selectbox("Filter by Section", ["All"] + final_sections)
            # ... باقي كود المصفوفة ...

    # --- إدارة الاختبارات (تعتمد على وجود شعب) ---
    elif menu == "Exams Manager":
        st.header("Exams Scheduler")
        if not final_sections:
            st.error("⚠️ Stop! You must add a Section first in 'System Settings' before creating exams.")
        else:
            with st.form("add_ex"):
                e_id = st.text_input("Exam ID")
                e_ti = st.text_input("Title")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    sd = st.date_input("Start Date"); stm = st.time_input("Start Time")
                with col_t2:
                    ed = st.date_input("End Date"); etm = st.time_input("End Time")
                
                # اختيار الشعبة من القائمة المسجلة مسبقاً
                e_se = st.multiselect("Assign to Sections", final_sections)
                e_du = st.number_input("Duration (Min)", value=60)
                e_ht = st.text_area("HTML Code")
                
                if st.form_submit_button("Publish Exam"):
                    if e_id and e_ti and e_se:
                        new_ex = pd.DataFrame([{
                            "Exam_ID": e_id, "Title": e_ti, "Section": ",".join(e_se), 
                            "Duration": e_du, "HTML_Code": e_ht, "Status": "Active", 
                            "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}"
                        }])
                        conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                        st.success("Exam Published!"); st.rerun()
                    else: st.error("Please fill all fields and select at least one section.")

    # --- الإدارة (System Settings) - هنا يتم فرض التسلسل ---
    elif menu == "System Settings":
        st.header("System Management")
        tab_sec, tab_stu = st.tabs(["1. Manage Sections (Start Here)", "2. Register Students"])
        
        # الجزء الأول: إضافة الشعبة (الأولوية القصوى)
        with tab_sec:
            st.subheader("Add New Section")
            st.info("Step 1: Define your classes/sections here.")
            with st.form("sec_f"):
                ns = st.text_input("Section Name (e.g., 12-Adv-A)")
                if st.form_submit_button("Save Section"):
                    if ns:
                        new_s_df = pd.DataFrame([{"Section_Name": ns.strip()}])
                        conn.update(worksheet="Sections", data=pd.concat([df_sec_tab, new_s_df], ignore_index=True))
                        st.success(f"Section '{ns}' added successfully!"); time.sleep(1); st.rerun()

        # الجزء الثاني: إضافة الطالب (يفتح فقط إذا وجدت شعب)
        with tab_stu:
            st.subheader("Register New Student")
            if not final_sections:
                st.warning("⚠️ You cannot register students yet. Please go to 'Manage Sections' and add a section first.")
            else:
                st.info("Step 2: Assign students to the sections you created.")
                with st.form("stu_f"):
                    sn, si = st.text_input("Student Name"), st.text_input("Student ID")
                    ss = st.selectbox("Assign to Section", final_sections)
                    sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                    
                    if st.form_submit_button("Register Student"):
                        if sn and si:
                            new_st_df = pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])
                            conn.update(worksheet="Students", data=pd.concat([df_stu, new_st_df], ignore_index=True))
                            st.success(f"Student {sn} registered in section {ss}!"); time.sleep(1); st.rerun()
# المحطة الثالثة: لوحة الطالب (Student Dashboard)
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is not None:
        # --- EXAM RUNNER ---
        ex = st.session_state.exam
        st.subheader(f"Active Exam: {ex['Title']}")
        rem = (int(float(ex.get('Duration', 60))) * 60) - (time.time() - st.session_state.start_t)
        
        if rem <= 0:
            st.error("Time Expired!"); st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            
            # Injection & LaTeX Fix
            html_raw = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID'])).replace("STUDENT_NAME_HERE", str(u['Name']))
            if "VAR_A" in html_raw:
                # Safe Seed for non-numeric IDs
                seed_val = sum(ord(c) for c in (str(u['ID']) + str(ex['Exam_ID'])))
                random.seed(seed_val)
                html_raw = html_raw.replace("VAR_A", str(random.randint(2,9))).replace("VAR_B", str(random.randint(2,5)))
                random.seed()
            
            st.components.v1.html(html_raw.replace("\\", "\\\\"), height=850, scrolling=True)
            if st.button("Exit Exam"): st.session_state.exam = None; st.rerun()

    else:
        # --- STUDENT HOME ---
        st.title(f"Welcome, {u['Name']} 👋")
        if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()

        t1, t2, t3 = st.tabs(["📋 Assigned", "✅ History", "📊 Analytics"])
        with t1:
            st.subheader("Pending Exams")
            now = datetime.now()
            req = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
            taken = my_grades['Exam_ID'].unique().tolist()
            req = req[~req['Exam_ID'].astype(str).isin(map(str, taken))]
            
            for _, r in req.iterrows():
                try:
                    st_t = datetime.strptime(str(r['Start_Time']), '%Y-%m-%d %H:%M:%S')
                    en_t = datetime.strptime(str(r['End_Time']), '%Y-%m-%d %H:%M:%S')
                except: st_t, en_t = now, now
                
                if st_t <= now <= en_t:
                    st.markdown(f'<div class="exam-card"><b>{r["Title"]}</b><br><small>Ends: {en_t.strftime("%H:%M")}</small></div>', unsafe_allow_html=True)
                    if st.button(f"Start Exam", key=r['Exam_ID']):
                        st.session_state.exam = r.to_dict(); st.session_state.start_t = time.time(); st.rerun()
                elif now < st_t:
                    st.info(f"Upcoming: {r['Title']} at {st_t.strftime('%H:%M')}")
        
        with t2:
            st.table(my_grades[['Exam_ID', 'Score']])
            st.divider()
            if st.button("Generate Smart Practice / تدريب ذكي"):
                if not my_grades.empty:
                    last_id = my_grades.iloc[-1]['Exam_ID']
                    tmpl = df_ex_stu[df_ex_stu['Exam_ID'] == last_id].iloc[0]['HTML_Code']
                    st.session_state.practice_mode = str(tmpl).replace("VAR_A", str(random.randint(2,9))).replace("VAR_B", str(random.randint(2,5))).replace("\\", "\\\\")
                    st.rerun()
            if 'practice_mode' in st.session_state:
                st.components.v1.html(st.session_state.practice_mode, height=500, scrolling=True)
                if st.button("Close Practice"): del st.session_state.practice_mode; st.rerun()
        
        with t3:
            if not my_grades.empty:
                st.plotly_chart(px.line(my_grades, x='Exam_ID', y='Score', markers=True))

# المحطة الرابعة: لوحة ولي الأمر
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
    u = st.session_state.user
    c_ids = str(u.get('Children_IDs', '')).split(',')
    df_g = clean_data(load_sheet("Grades"))
    df_s = clean_data(load_sheet("Students"))
    for cid in c_ids:
        cid = cid.strip()
        name = df_s[df_s['ID'] == cid]['Name'].iloc[0] if not df_s[df_s['ID'] == cid].empty else cid
        with st.expander(f"Child: {name}"):
            cg = df_g[df_g['Student_ID'] == cid]
            st.dataframe(cg[['Exam_ID', 'Score']], use_container_width=True)
            if not cg.empty: st.plotly_chart(px.bar(cg, x='Exam_ID', y='Score', range_y=[0,100]))

# الحماية النهائية
else:
    st.warning("Please Login.")
    st.session_state.update({'auth': False})
