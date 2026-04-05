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
    st.sidebar.title("Teacher Dashboard")
    menu = st.sidebar.radio("Navigation", ["📊 Results Matrix", "📈 Full Analytics", "📝 Exams Manager", "⚙️ Settings"])
    
    df_stu, df_grd, df_exm, df_sec = clean(get_data("Students")), clean(get_data("Grades")), clean(get_data("Exams")), clean(get_data("Sections"))
    all_sec = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        sel = st.selectbox("Section", ["All"] + all_sec)
        f_stu = df_stu[df_stu['Section'] == sel] if sel != "All" else df_stu
        merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
        if not merged['Exam_ID'].dropna().empty:
            matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
            st.dataframe(matrix, use_container_width=True)

    elif menu == "📈 Full Analytics":
        st.header("Analytics Dashboard")
        if not df_grd.empty:
            df_an = pd.merge(df_grd, df_stu, left_on='Student_ID', right_on='ID')
            c1, c2 = st.columns(2)
            c1.metric("Global Average", f"{df_grd['Score'].mean():.1f}%")
            c2.plotly_chart(px.bar(df_an.groupby('Section')['Score'].mean().reset_index(), x='Section', y='Score', title="Avg by Section"))

    elif menu == "📝 Exams Manager":
        st.header("Exams Scheduler")
        with st.form("new_ex"):
            eid, etitle = st.text_input("Exam ID"), st.text_input("Title")
            col1, col2 = st.columns(2)
            with col1: sd, stm = st.date_input("Start Date"), st.time_input("Start Time")
            with col2: ed, etm = st.date_input("End Date"), st.time_input("End Time")
            ese = st.multiselect("Sections", all_sec)
            if st.form_submit_button("Publish Exam"):
                new_row = pd.DataFrame([{"Exam_ID": eid, "Title": etitle, "Section": ",".join(ese), "Status": "Active", "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}"}])
                conn.update(worksheet="Exams", data=pd.concat([df_exm, new_row], ignore_index=True))
                st.success("Published!"); st.rerun()

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
                gas_url = "https://script.google.com/macros/s/AKfycbylUWgKoKqdM4MUtkm7TN5OYD9uUEZc0MzS6Im7rd9YifqiJiFIb8ByPzgnjwQYeE49/exec"
                full_link = f"{gas_url}?sid={u['ID']}&eid={r['Exam_ID']}&name={u['Name']}"
                st.markdown(f'<a href="{full_link}" target="_blank" style="text-decoration:none;"><button style="background:#28a745; color:white; border:none; padding:15px; border-radius:10px; cursor:pointer; width:100%;">Start Exam</button></a>', unsafe_allow_html=True)

if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
