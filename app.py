import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time, random

# --- Basic Config ---
st.set_page_config(page_title="NIFHAM Pro", layout="wide")
GAS_URL = "https://script.google.com/macros/s/AKfycbxnlYY1v1OY15rMBmkKECGfeTjfujDd3JpcoP6PD4HoFBNjfWa9RDslDB97kwNVPdFkJg/exec"

# --- Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password', 'Section_Name']
    for c in cols:
        if c in df.columns: df[c] = df[c].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns: df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

if 'auth' not in st.session_state: st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- Login System ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    role = st.selectbox("Login as", ["Student", "Teacher"])
    with st.form("login"):
        uid, upw = st.text_input("User ID").strip(), st.text_input("Password", type="password").strip()
        if st.form_submit_button("Sign In"):
            target = "Students" if role == "Student" else "Users"
            df_u = clean_data(load_sheet(target))
            match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': role.lower()})
                st.rerun()

# --- Teacher Dashboard (English Sidebar) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("Navigation", ["Results Matrix", "Student Performance", "Exams Library", "Exams Manager", "System Settings"])
    
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    active_secs = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    if menu == "Results Matrix":
        st.header("Class Results Matrix")
        sec = st.selectbox("Select Section", ["All"] + active_secs)
        f_stu = df_stu[df_stu['Section'] == sec] if sec != "All" else df_stu
        if 'Student_ID' in df_grd.columns:
            m = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if 'Exam_ID' in m.columns:
                st.dataframe(m.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-'), use_container_width=True)

    elif menu == "Student Performance":
        st.header("Individual Student Report")
        s_sec = st.selectbox("Section", ["Select"] + active_secs)
        if s_sec != "Select":
            names = df_stu[df_stu['Section'] == s_sec]['Name'].tolist()
            name = st.selectbox("Student Name", names)
            sid = df_stu[df_stu['Name'] == name]['ID'].values[0]
            st.table(df_grd[df_grd['Student_ID'] == str(sid)])

    elif menu == "Exams Library":
        st.header("Exams Library (Preview)")
        for _, r in df_exm.iterrows():
            with st.expander(f"📖 {r['Title']} ({r['Exam_ID']})"):
                st.link_button("Preview Exam", f"{GAS_URL}?sid=TEACHER&eid={r['Exam_ID']}&name=Mr_Ibrahim&mode=preview")

    elif menu == "Exams Manager":
        st.header("Exams Manager")
        with st.form("ex"):
            eid, et = st.text_input("Exam ID"), st.text_input("Title")
            es = st.multiselect("Sections", active_secs)
            eh = st.text_area("HTML Code (Column H)")
            if st.form_submit_button("Publish"):
                conn.update(worksheet="Exams", data=pd.concat([df_exm, pd.DataFrame([{"Exam_ID": eid, "Title": et, "Section": ",".join(es), "HTML_Code": eh}])], ignore_index=True))
                st.success("Published!"); st.rerun()

    elif menu == "System Settings":
        st.header("System Settings")
        c1, c2 = st.tabs(["Sections", "Register Students"])
        with c1:
            ns = st.text_input("New Section Name")
            if st.button("Save Section"):
                conn.update(worksheet="Sections", data=pd.concat([df_sec, pd.DataFrame([{"Section_Name": ns}])], ignore_index=True))
                st.rerun()
        with c2:
            with st.form("stu"):
                sn, si, ss = st.text_input("Student Name"), st.text_input("ID"), st.selectbox("Section", active_secs)
                if st.form_submit_button("Register"):
                    conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Section": ss, "Password": str(random.randint(1000, 9999))}])], ignore_index=True))
                    st.rerun()

# --- Student Dashboard ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex, df_gr = clean_data(load_sheet("Exams")), clean_data(load_sheet("Grades"))
    taken = df_gr[df_gr['Student_ID'] == str(u['ID'])]['Exam_ID'].unique().tolist() if 'Student_ID' in df_gr.columns else []

    st.title(f"Welcome, {u['Name']} 👋")
    t1, t2 = st.tabs(["📋 My Assignments", "✅ My Results"])
    with t1:
        pend = df_ex[~df_ex['Exam_ID'].astype(str).isin(map(str, taken))]
        for _, r in pend.iterrows():
            if str(u['Section']) in str(r['Section']):
                st.info(f"Exam: {r['Title']}")
                st.link_button("Start Exam", f"{GAS_URL}?sid={u['ID']}&eid={r['Exam_ID']}&name={u['Name']}&mode=exam")
    with t2:
        if 'Student_ID' in df_gr.columns:
            my_gr = df_gr[df_gr['Student_ID'] == str(u['ID'])]
            for _, s in my_gr.iterrows():
                st.write(f"✅ {s['Exam_ID']} | Score: {s['Score']}%")
                st.link_button("Review", f"{GAS_URL}?sid={u['ID']}&eid={s['Exam_ID']}&name={u['Name']}&mode=review")

if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
