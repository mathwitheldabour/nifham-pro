import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & Professional Styling ---
st.set_page_config(page_title="NIFHAM Pro | Math Education Platform", layout="wide")

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

# --- 2. Data Engine & Cleaning ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    # تنظيف المعرفات من أي .0 ناتج عن الإكسيل
    cols_to_clean = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Section_Name', 'Children_IDs']
    for col in cols_to_clean:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    # تحويل الدرجات لأرقام صحيحة للتحليل
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session State Management ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Main Application Logic ---

# --- A. LOGIN SCREEN ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - تسجيل الدخول</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID / المعرف").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                sheet_name = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_name))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    u_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': f_role})
                    st.rerun()
                else:
                    st.error("Invalid Login / بيانات الدخول غير صحيحة")

# --- B. TEACHER DASHBOARD ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Welcome, Mr. {st.session_state.user.get('Name')}")
    menu = st.sidebar.radio("Navigation", ["Results Matrix", "Full Analytics", "Exams Manager", "System Settings"])
    
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    
    # تحضير قائمة الشعب
    all_sec = sorted(df_stu['Section'].unique().tolist()) if not df_stu.empty else []

    if menu == "Results Matrix":
        st.header("Results Matrix")
        st.markdown("<span class='arabic-sub'>مصفوفة الدرجات التفصيلية</span>", unsafe_allow_html=True)
        if not df_stu.empty and not df_grd.empty:
            sel_sec = st.selectbox("Select Section", ["All"] + all_sec)
            filtered_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All" else df_stu
            merged = pd.merge(filtered_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
            else: st.info("No grades found.")

    elif menu == "Full Analytics":
        st.header("Performance Analytics")
        if not df_grd.empty and not df_stu.empty:
            df_an = pd.merge(df_grd, df_stu, left_on='Student_ID', right_on='ID')
            c1, c2, c3 = st.columns(3)
            c1.metric("Average Score", f"{df_grd['Score'].mean():.1f}%")
            c2.metric("Total Submissions", len(df_grd))
            c3.metric("Pass Rate", f"{(df_grd['Score'] >= PASSING_SCORE).mean()*100:.1f}%")
            
            st.plotly_chart(px.bar(df_an.groupby('Section')['Score'].mean().reset_index(), 
                                   x='Section', y='Score', title="Average by Section"), use_container_width=True)
        else: st.warning("Not enough data for analytics.")

    elif menu == "Exams Manager":
        st.header("Manage Exams")
        with st.form("add_exam"):
            e_id = st.text_input("Exam ID")
            e_ti = st.text_input("Title")
            e_se = st.multiselect("Sections", all_sec)
            e_du = st.number_input("Duration (Min)", value=60)
            e_ht = st.text_area("HTML Template (Supports VAR_A, VAR_B)")
            if st.form_submit_button("Publish Exam"):
                new_ex = pd.DataFrame([{"Exam_ID": e_id, "Title": e_ti, "Section": ",".join(e_se), "Duration": e_du, "HTML_Code": e_ht, "Status": "Active"}])
                conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                st.success("Published!"); st.rerun()

    elif menu == "System Settings":
        st.header("Settings")
        t1, t2 = st.tabs(["Add Section", "Register Student"])
        with t1:
            with st.form("sec_f"):
                ns = st.text_input("New Section Name")
                if st.form_submit_button("Save"):
                    old_sec = load_sheet("Sections")
                    conn.update(worksheet="Sections", data=pd.concat([old_sec, pd.DataFrame([{"Section_Name": ns}])], ignore_index=True))
                    st.success("Section Added!"); st.rerun()
        with t2:
            with st.form("stu_f"):
                sn, si = st.text_input("Full Name"), st.text_input("ID")
                ss = st.selectbox("Section", all_sec)
                sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])], ignore_index=True))
                    st.success("Registered!"); st.rerun()

# --- C. STUDENT DASHBOARD ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex_stu = clean_data(load_sheet("Exams"))
    df_gr_stu = clean_data(load_sheet("Grades"))
    my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is not None:
        # EXAM RUNNER
        ex = st.session_state.exam
        st.subheader(f"Exam: {ex['Title']}")
        rem = (int(float(ex.get('Duration', 60))) * 60) - (time.time() - st.session_state.start_t)
        if rem <= 0:
            st.error("Time Expired!"); st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(int(rem), 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            # Dynamic Injection & LaTeX Fix
            html = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID'])).replace("STUDENT_NAME_HERE", str(u['Name']))
            if "VAR_A" in html:
                random.seed(int(u['ID']) + int(ex['Exam_ID']))
                html = html.replace("VAR_A", str(random.randint(2, 9))).replace("VAR_B", str(random.randint(2, 5)))
                random.seed()
            st.components.v1.html(html.replace("\\", "\\\\"), height=850, scrolling=True)
            if st.button("Cancel & Exit"): st.session_state.exam = None; st.rerun()
    else:
        st.title(f"Welcome, {u['Name']} 👋")
        if st.sidebar.button("Logout"): st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

        t1, t2, t3 = st.tabs(["📋 Assigned", "✅ Grades", "📊 My Performance"])
        with t1:
            req = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
            taken = my_grades['Exam_ID'].unique().tolist()
            req = req[~req['Exam_ID'].astype(str).isin(map(str, taken))]
            for _, r in req.iterrows():
                st.markdown(f'<div class="exam-card"><b>{r["Title"]}</b></div>', unsafe_allow_html=True)
                if st.button(f"Start Exam", key=r['Exam_ID']):
                    st.session_state.exam = r.to_dict(); st.session_state.start_t = time.time(); st.rerun()
        with t2:
            st.table(my_grades[['Exam_ID', 'Score']])
            st.divider()
            if st.button("Generate Smart Practice"):
                if not my_grades.empty:
                    last = df_ex_stu[df_ex_stu['Exam_ID'] == my_grades.iloc[-1]['Exam_ID']].iloc[0]['HTML_Code']
                    st.session_state.practice_mode = str(last).replace("VAR_A", str(random.randint(2,9))).replace("VAR_B", str(random.randint(2,5))).replace("\\", "\\\\")
                    st.rerun()
            if 'practice_mode' in st.session_state:
                st.components.v1.html(st.session_state.practice_mode, height=500, scrolling=True)
                if st.button("Close Practice"): del st.session_state.practice_mode; st.rerun()
        with t3:
            if not my_grades.empty:
                st.plotly_chart(px.line(my_grades, x='Exam_ID', y='Score', markers=True))

# --- D. PARENT DASHBOARD ---
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"): st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
    u = st.session_state.user
    c_ids = str(u.get('Children_IDs', '')).split(',')
    df_g = clean_data(load_sheet("Grades"))
    df_s = clean_data(load_sheet("Students"))
    for cid in c_ids:
        cid = cid.strip()
        name = df_s[df_s['ID'] == cid]['Name'].iloc[0] if not df_s[df_s['ID'] == cid].empty else cid
        with st.expander(f"Student: {name}"):
            cg = df_g[df_g['Student_ID'] == cid]
            st.dataframe(cg[['Exam_ID', 'Score']], use_container_width=True)
            if not cg.empty: st.plotly_chart(px.bar(cg, x='Exam_ID', y='Score'))

# --- E. PROTECTION ---
else:
    st.warning("Access Denied. Please Login.")
    st.session_state.update({'auth': False, 'user': None, 'role': None})
