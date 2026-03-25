import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# --- 2. DATA ENGINE ---
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, dtype=str)

# --- 3. SESSION MANAGEMENT ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. LOGIN LOGIC ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        uid = st.text_input("User ID | الكود").strip()
        upass = st.text_input("Password | كلمة المرور", type="password").strip()
        if st.button("Login | دخول"):
            try:
                df_u = load_data("Users")
                admin = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                if not admin.empty:
                    st.session_state.role = 'teacher'
                    st.session_state.user = admin.iloc[0]
                    st.rerun()
                
                df_s = load_data("Students")
                user = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                if not user.empty:
                    st.session_state.role = user.iloc[0].get('Roll', 'student').lower().strip()
                    st.session_state.user = user.iloc[0]
                    st.rerun()
                st.error("Invalid Credentials")
            except: st.error("Database Error")

# --- 5. TEACHER DASHBOARD ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Admin Panel")
    menu = st.sidebar.radio("Navigation", ["Exams Preview", "Results Matrix", "Add Assessment", "Manage Students"])
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    # أ. شاشة العرض للشرح
    if menu == "Exams Preview":
        st.title("🖥️ Exam Preview & Explanation")
        df_exams = load_data("Exams")
        sel_exam = st.selectbox("Select Exam to Present", df_exams['Title'].unique())
        exam_data = df_exams[df_exams['Title'] == sel_exam].iloc[0]
        
        st.info(f"Presenting: {sel_exam} | Section: {exam_data['Section']}")
        components.html(exam_data['HTML_Code'], height=900, scrolling=True)

    # ب. مصفوفة النتائج لكل شعبة
    elif menu == "Results Matrix":
        st.title("📊 Results Matrix | مصفوفة النتائج")
        df_grades = load_data("Grades")
        df_students = load_data("Students")
        
        section = st.selectbox("Select Section", df_students['Section'].unique())
        filtered_students = df_students[df_students['Section'] == section]
        
        # دمج الدرجات مع بيانات الطلاب
        matrix_df = pd.merge(filtered_students[['ID', 'Name']], df_grades, left_on='ID', right_on='SID', how='left')
        
        # تحويل الجدول لمصفوفة (Pivot Table)
        if not matrix_df.empty:
            pivot_matrix = matrix_df.pivot_table(index='Name', columns='EID', values='Score', aggfunc='first').fillna('-')
            st.dataframe(pivot_matrix, use_container_width=True)
        else:
            st.write("No data for this section yet.")

# --- 6. STUDENT & PARENT DASHBOARD ---
elif st.session_state.role in ['student', 'parent']:
    user = st.session_state.user
    st.title(f"👋 Welcome, {user['Name']}")
    
    tab1, tab2 = st.tabs(["Active Assessments", "Skill Analysis & Reports"])
    
    with tab1:
        # عرض الاختبارات المتاحة للشعبة
        df_exams = load_data("Exams")
        my_exams = df_exams[(df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'All')]
        for _, ex in my_exams.iterrows():
            with st.expander(f"📝 {ex['Title']}"):
                if st.button("Start Exam", key=ex['Exam_ID']):
                    components.html(ex['HTML_Code'], height=800, scrolling=True)

    with tab2:
        st.header("🎯 Skills Mastery | تحليل المهارات")
        # مثال على رسم بياني للمهارات (Radar Chart)
        # ملاحظة: سنفترض وجود قيم للمهارات في شيت Grades لاحقاً
        categories = ['Factoring', 'Simplifying', 'Constants', 'Derivatives', 'Limits']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
              r=[80, 70, 90, 60, 85], # قيم تجريبية
              theta=categories,
              fill='toself',
              name='My Skills',
              marker=dict(color='#10b981')
        ))
        
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Exam History")
        df_grades = load_data("Grades")
        my_history = df_grades[df_grades['SID'] == str(user['ID'])]
        st.table(my_history[['EID', 'Score', 'Date']])
