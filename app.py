import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, time
import time as time_lib
import random

# --- 1. Basic Page Configuration ---
st.set_page_config(page_title="NIFHAM Pro | Mr. Ibrahim Eldabour", layout="wide")

# الرابط الخاص بك (تأكد أنه ينتهي بـ /exec)
GAS_URL = "https://script.google.com/macros/s/AKfycbxnlYY1v1OY15rMBmkKECGfeTjfujDd3JpcoP6PD4HoFBNjfWa9RDslDB97kwNVPdFkJg/exec"

# Custom CSS for styling
st.markdown("""
    <style>
    .arabic-text { direction: rtl; text-align: right; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Processing Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols_to_fix = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password', 'Section_Name']
    for col in df.columns:
        if col in cols_to_fix:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# Authentication Session
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- 3. Login Interface ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.subheader("Khalid Bin Al Waleed School")
    role_choice = st.selectbox("Login as", ["Student", "Teacher"])
    with st.form("login_gate"):
        u_id = st.text_input("User ID (رقم الهوية)").strip()
        u_pw = st.text_input("Password (كلمة المرور)", type="password").strip()
        if st.form_submit_button("Sign In"):
            target = "Students" if role_choice == "Student" else "Users"
            df_users = clean_data(load_sheet(target))
            if not df_users.empty:
                match = df_users[(df_users['ID'] == u_id) & (df_users['Password'] == u_pw)]
                if not match.empty:
                    st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': role_choice.lower()})
                    st.rerun()
                else: st.error("Invalid Credentials!")

# --- 4. Teacher Dashboard (English Sidebar) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("Navigation", ["Results Matrix", "Individual Performance", "Exams Library", "Exams Manager", "System Settings"])
    
    # Load and Clean Data
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    
    # Fetch active sections safely
    if not df_sec.empty and 'Section_Name' in df_sec.columns:
        active_sections = sorted(df_sec['Section_Name'].unique().tolist())
    else:
        active_sections = []

    # A- Results Matrix
    if menu == "Results Matrix":
        st.header("Results Matrix")
        sel_sec = st.selectbox("Filter by Section", ["All"] + active_sections)
        f_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All" else df_stu
        if 'Student_ID' in df_grd.columns:
            merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if 'Exam_ID' in merged.columns:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix, use_container_width=True)
            else: st.info("No exam data yet.")

    # B- Individual Performance
    elif menu == "Individual Performance":
        st.header("Student Report")
        s_sec = st.selectbox("Select Section", ["Choose..."] + active_sections)
        if s_sec != "Choose...":
            names = df_stu[df_stu['Section'] == s_sec]['Name'].tolist()
            s_name = st.selectbox("Select Student", names)
            if s_name:
                sid = df_stu[df_stu['Name'] == s_name]['ID'].values[0]
                personal = df_grd[df_grd['Student_ID'] == str(sid)]
                st.table(personal[['Date', 'Exam_ID', 'Score']])

    # C- Exams Library (Preview)
    elif menu == "Exams Library":
        st.header("Exams Library")
        for _, row in df_exm.iterrows():
            with st.expander(f"📖 {row['Title']} (Code: {row['Exam_ID']})"):
                st.write(f"Sections: {row['Section']}")
                st.write(f"Active from: {row.get('Start_DateTime', 'N/A')} to {row.get('End_DateTime', 'N/A')}")
                p_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                st.link_button("Preview Exam", p_url)

    # D- Exams Manager (Fixed: Added Date, Time & Sections)
    elif menu == "Exams Manager":
        st.header("Create New Exam")
        if not active_sections:
            st.error("Please add Sections first in System Settings.")
        else:
            with st.form("exam_creation"):
                e_id = st.text_input("Exam Code (ID)")
                e_title = st.text_input("Exam Title")
                col1, col2 = st.columns(2)
                with col1:
                    sd = st.date_input("Start Date")
                    st_time = st.time_input("Start Time", value=time(8, 0))
                with col2:
                    ed = st.date_input("End Date")
                    et_time = st.time_input("End Time", value=time(14, 0))
                
                e_secs = st.multiselect("Assign to Sections", active_sections)
                e_html = st.text_area("Question HTML Code (Column H)")
                
                if st.form_submit_button("Publish Exam"):
                    if e_id and e_secs:
                        new_ex = pd.DataFrame([{
                            "Exam_ID": e_id, 
                            "Title": e_title, 
                            "Section": ",".join(e_secs), 
                            "Start_DateTime": f"{sd} {st_time}", 
                            "End_DateTime": f"{ed} {et_time}", 
                            "HTML_Code": e_html,
                            "Status": "Active"
                        }])
                        conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                        st.success("Exam Published Successfully!"); time_lib.sleep(1); st.rerun()

    # E- System Settings (Manage Sections & Students)
    elif menu == "System Settings":
        st.header("Management Settings")
        t_sec, t_stu = st.tabs(["Add Section", "Register Student"])
        with t_sec:
            ns = st.text_input("New Section Name (e.g., 12A)")
            if st.button("Save Section"):
                if ns:
                    conn.update(worksheet="Sections", data=pd.concat([df_sec, pd.DataFrame([{"Section_Name": ns.strip()}])], ignore_index=True))
                    st.success("Section Added!"); st.rerun()
        with t_stu:
            with st.form("reg_stu"):
                sn, si = st.text_input("Full Name"), st.text_input("ID Number")
                ss = st.selectbox("Select Section", active_sections)
                if st.form_submit_button("Register Student"):
                    if sn and si:
                        pw = str(random.randint(1000, 9999))
                        conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Section": ss, "Password": pw}])], ignore_index=True))
                        st.success(f"Student registered! Password: {pw}"); st.rerun()

# --- 5. Student Dashboard ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    my_subs = df_gr[df_gr['Student_ID'] == str(u['ID'])] if 'Student_ID' in df_gr.columns else pd.DataFrame()
    taken_ids = my_subs['Exam_ID'].unique().tolist() if not my_subs.empty else []

    st.title(f"Welcome, {u['Name']} 👋")
    st.markdown(f"<p class='arabic-text'>شعبة: {u['Section']}</p>", unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📋 Assignments", "✅ History"])
    with t1:
        now = datetime.now()
        pending = df_ex[~df_ex['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        for _, row in pending.iterrows():
            if str(u['Section']) in str(row['Section']):
                # تحقق من الوقت
                try:
                    start_dt = datetime.strptime(str(row['Start_DateTime']), '%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.strptime(str(row['End_DateTime']), '%Y-%m-%d %H:%M:%S')
                except: start_dt = end_dt = now # لو مفيش وقت يظهر فوراً
                
                if start_dt <= now <= end_dt:
                    with st.container():
                        st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                        st.link_button("Start Exam", f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam")
                elif now < start_dt:
                    st.warning(f"Upcoming: {row['Title']} (Starts at {row['Start_DateTime']})")

    with t2:
        if not my_subs.empty:
            for _, sub in my_subs.iterrows():
                st.write(f"✅ {sub['Exam_ID']} | Score: {sub['Score']}%")
                st.link_button("Review", f"{GAS_URL}?sid={u['ID']}&eid={sub['Exam_ID']}&name={u['Name']}&mode=review")

if st.sidebar.button("Logout"):
    st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
