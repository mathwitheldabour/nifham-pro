import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. SETTINGS & LUXURY UI ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# تصميم مخصص لصفحة دخول احترافية وقائمة جانبية واضحة
st.markdown("""
    <style>
    /* القائمة الجانبية - فاتحة وراقية */
    [data-testid="stSidebar"] {
        background-color: #f8fafc !important;
        border-right: 2px solid #e2e8f0;
    }
    [data-testid="stSidebar"] * { color: #1e293b !important; font-weight: 600; }
    
    /* خلفية التطبيق */
    .stApp { background-color: #ffffff; }

    /* كارت تسجيل الدخول */
    .login-box {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    
    /* الأزرار */
    .stButton>button {
        border-radius: 12px;
        padding: 10px 24px;
        font-weight: bold;
        transition: 0.3s;
    }
    
    .status-wanted { background-color: #fff7ed; color: #c2410c; padding: 5px 12px; border-radius: 8px; font-weight: bold; border: 1px solid #fdba74; }
    .status-done { background-color: #f0fdf4; color: #15803d; padding: 5px 12px; border-radius: 8px; font-weight: bold; border: 1px solid #86efac; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
SHEET_ID = st.secrets.get("SHEET_ID", "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY")

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        return pd.read_csv(url, dtype=str).fillna("")
    except:
        return pd.DataFrame()

# --- 3. SESSION LOGIC ---
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. AUTHENTICATION (REBUILT FOR STUDENTS) ---
if not st.session_state.role:
    # تنسيق صفحة الدخول
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("""
            <div style='text-align: center;'>
                <h1 style='color: #0f172a; font-size: 3rem; margin-bottom: 0;'>NIFHAM</h1>
                <p style='color: #64748b; font-weight: bold;'>Math Management System</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>تسجيل الدخول</h3>", unsafe_allow_html=True)
            u_id = st.text_input("كود المستخدم", placeholder="مثلاً: 111").strip()
            u_pass = st.text_input("كلمة المرور", type="password", placeholder="••••••••").strip()
            
            if st.button("دخول المنصة 🚀", use_container_width=True):
                # 1. البحث في شيت المعلمين
                df_u = load_data("Users")
                if not df_u.empty:
                    match = df_u[(df_u['ID'].astype(str) == u_id) & (df_u['Password'].astype(str) == u_pass)]
                    if not match.empty:
                        st.session_state.role = 'teacher'
                        st.session_state.user = match.iloc[0]
                        st.rerun()

                # 2. البحث في شيت الطلاب (الإصلاح الجذري هنا)
                df_s = load_data("Students")
                if not df_s.empty:
                    match_s = df_s[(df_s['ID'].astype(str) == u_id) & (df_s['Password'].astype(str) == u_pass)]
                    if not match_s.empty:
                        st.session_state.role = str(match_s.iloc[0].get('Roll', 'student')).lower()
                        st.session_state.user = match_s.iloc[0]
                        st.rerun()
                
                st.error("الكود أو كلمة المرور غير صحيحة")

# --- 5. TEACHER INTERFACE (WITH SMART DASHBOARD) ---
elif st.session_state.role == 'teacher':
    with st.sidebar:
        st.markdown(f"### أهلاً مستر إبراهيم 👋")
        menu = st.radio("انتقل إلى:", ["📊 لوحة الإحصائيات", "📝 مصفوفة النتائج", "🖥️ شاشة عرض الدروس", "➕ إضافة اختبار"])
        if st.button("خروج"):
            st.session_state.role = None
            st.rerun()

    if menu == "📊 لوحة الإحصائيات":
        st.title("📊 داشبورد أداء الشُعب")
        df_grades = load_data("Grades")
        df_students = load_data("Students")
        
        if not df_grades.empty and not df_students.empty:
            # اختيار الشعبة للتحليل
            sections = ["كل الطلاب"] + list(df_students['Section'].unique())
            sel_sec = st.selectbox("اختر الشعبة لعرض إحصائياتها", sections)
            
            # تصفية البيانات
            if sel_sec != "كل الطلاب":
                relevant_ids = df_students[df_students['Section'] == sel_sec]['ID'].tolist()
                df_filtered = df_grades[df_grades['SID'].isin(relevant_ids)].copy()
            else:
                df_filtered = df_grades.copy()

            df_filtered['Score'] = pd.to_numeric(df_filtered['Score'], errors='coerce')
            
            # كروت الإحصائيات
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("عدد المحاولات", len(df_filtered))
            with c2: st.metric("متوسط الدرجات", f"{df_filtered['Score'].mean():.1f}%")
            with c3: st.metric("أعلى درجة", f"{df_filtered['Score'].max()}%")
            
            # رسم بياني
            fig = px.histogram(df_filtered, x="Score", nbins=10, title=f"توزيع الدرجات - {sel_sec}", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات كافية لعرض الإحصائيات.")

    elif menu == "📝 مصفوفة النتائج":
        st.title("📝 سجل درجات الطلاب")
        df_s = load_data("Students")
        df_g = load_data("Grades")
        
        sec = st.selectbox("اختر الشعبة", df_s['Section'].unique())
        df_s_filtered = df_s[df_s['Section'] == sec]
        
        merged = pd.merge(df_s_filtered[['ID', 'Name']], df_g, left_on='ID', right_on='SID', how='left')
        if not merged.empty:
            matrix = merged.pivot_table(index='Name', columns='EID', values='Score', aggfunc='first').fillna("-")
            st.dataframe(matrix, use_container_width=True)
            if st.button("🖨️ تجهيز للطباعة"):
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

# --- 6. STUDENT INTERFACE ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.sidebar.markdown(f"### الطالب: {user['Name']}")
    st.sidebar.info(f"الشعبة: {user['Section']}")
    if st.sidebar.button("خروج"):
        st.session_state.role = None
        st.rerun()

    st.title("📚 دروسي واختباراتي")
    df_exams = load_data("Exams")
    df_grades = load_data("Grades")
    
    # فلترة شعبة الطالب
    my_exams = df_exams[(df_exams['Section'] == user['Section']) | (df_exams['Section'] == 'الكل')]
    
    for lesson in my_exams['Lesson'].unique():
        with st.expander(f"📖 {lesson}"):
            l_ex = my_exams[my_exams['Lesson'] == lesson]
            for _, ex in l_ex.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1.5])
                c1.write(f"**{ex['Title']}**")
                
                # التحقق من الحالة
                attempt = df_grades[(df_grades['SID'] == user['ID']) & (df_grades['EID'] == ex['Exam_ID'])]
                
                if not attempt.empty:
                    c2.markdown("<span class='status-done'>تم الحل ✅</span>", unsafe_allow_html=True)
                    if str(ex['Show_Answers']).upper() == "TRUE":
                        if c3.button("مراجعة", key=f"rev_{ex['Exam_ID']}"):
                            components.html(ex['HTML_Code'], height=600, scrolling=True)
                else:
                    c2.markdown("<span class='status-wanted'>مطلوب 🔔</span>", unsafe_allow_html=True)
                    if c3.button("بدء الاختبار", key=f"start_{ex['Exam_ID']}"):
                        components.html(ex['HTML_Code'], height=800, scrolling=True)
