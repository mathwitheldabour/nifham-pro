import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. التنسيق والجماليات (Bilingual & Clean UI) ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

st.markdown("""
    <style>
    /* القائمة الجانبية واضحة جداً */
    [data-testid="stSidebar"] { background-color: #f8fafc !important; border-right: 2px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #0f172a !important; font-weight: 600; font-size: 16px; }
    
    /* تنسيق النصوص العربية */
    .ar { direction: rtl; text-align: right; font-family: 'Cairo', sans-serif; }
    .en { direction: ltr; text-align: left; }
    
    /* بطاقات الحالة */
    .status-wanted { background-color: #fff7ed; color: #c2410c; padding: 4px 10px; border-radius: 8px; font-weight: bold; border: 1px solid #fdba74; }
    .status-done { background-color: #f0fdf4; color: #15803d; padding: 4px 10px; border-radius: 8px; font-weight: bold; border: 1px solid #86efac; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (Data Engine) ---
SHEET_ID = st.secrets.get("SHEET_ID", "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY")

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        return pd.read_csv(url, dtype=str).fillna("")
    except:
        return pd.DataFrame()

# --- 3. إدارة الجلسة ---
if 'role' not in st.session_state: st.session_state.role = None
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. واجهة تسجيل الدخول (Instant & Bilingual) ---
if not st.session_state.role:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>Login | تسجيل الدخول</h3>", unsafe_allow_html=True)
            u_id = st.text_input("User ID | كود المستخدم").strip()
            u_pass = st.text_input("Password | كلمة المرور", type="password").strip()
            
            if st.button("Enter Platform | دخول المنصة", use_container_width=True):
                # فحص المعلمين
                df_u = load_data("Users")
                if not df_u.empty:
                    match = df_u[(df_u['ID'].astype(str) == u_id) & (df_u['Password'].astype(str) == u_pass)]
                    if not match.empty:
                        st.session_state.role = 'teacher'
                        st.session_state.user = match.iloc[0]
                        st.rerun()

                # فحص الطلاب
                df_s = load_data("Students")
                if not df_s.empty:
                    match_s = df_s[(df_s['ID'].astype(str) == u_id) & (df_s['Password'].astype(str) == u_pass)]
                    if not match_s.empty:
                        st.session_state.role = str(match_s.iloc[0].get('Roll', 'student')).lower()
                        st.session_state.user = match_s.iloc[0]
                        st.rerun()
                st.error("Invalid Credentials | بيانات غير صحيحة")

# --- 5. واجهة المعلم (Teacher Control) ---
elif st.session_state.role == 'teacher':
    with st.sidebar:
        st.markdown(f"### أهلاً مستر إبراهيم 👋")
        menu = st.radio("القائمة | Menu", ["📊 Dashboard", "📝 Results Matrix", "🖥️ Preview Exam", "➕ Add Assessment"])
        if st.button("Logout | خروج"):
            st.session_state.role = None
            st.rerun()

    if menu == "📊 Dashboard":
        st.title("📈 Performance Analytics")
        df_g = load_data("Grades")
        df_s = load_data("Students")
        if not df_g.empty:
            sel_sec = st.selectbox("Filter by Section | تصفية حسب الشعبة", ["All"] + list(df_s['Section'].unique()))
            if sel_sec != "All":
                relevant_ids = df_s[df_s['Section'] == sel_sec]['ID'].tolist()
                df_g = df_g[df_g['SID'].isin(relevant_ids)]
            
            df_g['Score'] = pd.to_numeric(df_g['Score'], errors='coerce')
            c1, c2 = st.columns(2)
            c1.metric("Attempts | المحاولات", len(df_g))
            c2.metric("Avg Score | المتوسط", f"{df_g['Score'].mean():.1f}%")
            st.plotly_chart(px.histogram(df_g, x="Score", title="توزيع الدرجات", color_discrete_sequence=['#10b981']))

    elif menu == "📝 Results Matrix":
        st.title("📝 Student Grades Matrix")
        df_s = load_data("Students")
        df_g = load_data("Grades")
        sec = st.selectbox("Select Section", df_s['Section'].unique())
        # دمج لعرض الأسماء
        merged = pd.merge(df_s[df_s['Section'] == sec][['ID', 'Name']], df_g, left_on='ID', right_on='SID', how='left')
        if not merged.empty:
            matrix = merged.pivot_table(index='Name', columns='EID', values='Score', aggfunc='first').fillna("-")
            st.dataframe(matrix, use_container_width=True)
            if st.button("🖨️ Print Report"): st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

    elif menu == "➕ Add Assessment":
        st.title("➕ Create New Exam / Assignment")
        with st.form("add_ex"):
            e_id = st.text_input("Exam ID (EID)")
            e_title = st.text_input("Title")
            e_lesson = st.text_input("Lesson Name")
            e_sec = st.selectbox("Section", ["12A", "12B", "12C", "All"])
            e_end = st.date_input("End Date")
            e_html = st.text_area("HTML Code")
            if st.form_submit_button("Publish"): st.success("Data ready! Update your sheet.")

    elif menu == "🖥️ Preview Exam":
        df_ex = load_data("Exams")
        sel = st.selectbox("Choose Exam", df_ex['Title'].unique() if not df_ex.empty else [])
        if sel: components.html(df_ex[df_ex['Title'] == sel].iloc[0]['HTML_Code'], height=800, scrolling=True)

# --- 6. واجهة الطالب (Student Path) ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.sidebar.markdown(f"### {user['Name']}")
    if st.sidebar.button("خروج"):
        st.session_state.role = None
        st.rerun()

    st.title("📚 My Assessments | اختباراتي")
    df_ex = load_data("Exams")
    df_g = load_data("Grades")
    my_exams = df_ex[(df_ex['Section'] == user['Section']) | (df_ex['Section'] == 'All')]
    
    for lesson in my_exams['Lesson'].unique():
        with st.expander(f"📖 {lesson}"):
            for _, ex in my_exams[my_exams['Lesson'] == lesson].iterrows():
                c1, c2, c3 = st.columns([3, 1, 1.5])
                c1.write(f"**{ex['Title']}**")
                attempt = df_g[(df_g['SID'] == user['ID']) & (df_g['EID'] == ex['Exam_ID'])]
                if not attempt.empty:
                    c2.markdown("<span class='status-done'>DONE ✅</span>", unsafe_allow_html=True)
                    if str(ex.get('Show_Answers')).upper() == "TRUE":
                        if c3.button("Review", key=f"rev_{ex['Exam_ID']}"): components.html(ex['HTML_Code'], height=600)
                else:
                    c2.markdown("<span class='status-wanted'>WANTED 🔔</span>", unsafe_allow_html=True)
                    if c3.button("Start", key=f"st_{ex['Exam_ID']}"): components.html(ex['HTML_Code'], height=800, scrolling=True)
