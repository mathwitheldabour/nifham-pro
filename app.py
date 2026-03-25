import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. إعدادات الصفحة والتنسيق الاحترافي ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# CSS لتعديل القائمة الجانبية ودعم الطباعة
st.markdown("""
    <style>
    /* تعديل القائمة الجانبية لتكون فاتحة والخط واضح */
    [data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] * {
        color: #0f172a !important; /* لون الخط داكن جداً */
        font-weight: 500;
    }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    
    /* تنسيق الطباعة */
    @media print {
        .no-print { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        .main { width: 100% !important; }
    }
    
    .status-wanted { background-color: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    .status-done { background-color: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 6px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات ---
SHEET_ID = st.secrets.get("SHEET_ID", "18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY")

def load_data(sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        df = pd.read_csv(url, dtype=str).fillna("")
        return df
    except:
        return pd.DataFrame()

# --- 3. إدارة الجلسة (Login Fix) ---
if 'role' not in st.session_state:
    st.session_state.role = None
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 4. واجهة تسجيل الدخول (Instant Login) ---
if not st.session_state.role:
    st.markdown("<h1 style='text-align: center;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.container(border=True):
            st.markdown("<h4 style='text-align: center;'>تسجيل الدخول</h4>", unsafe_allow_html=True)
            uid = st.text_input("كود المستخدم").strip()
            upass = st.text_input("كلمة المرور", type="password").strip()
            
            if st.button("دخول الممنصة", use_container_width=True):
                # فحص المعلمين
                df_u = load_data("Users")
                if not df_u.empty and 'ID' in df_u.columns:
                    match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                    if not match.empty:
                        st.session_state.role = 'teacher'
                        st.session_state.user = match.iloc[0]
                        st.rerun()

                # فحص الطلاب
                df_s = load_data("Students")
                if not df_s.empty and 'ID' in df_s.columns:
                    match = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                    if not match.empty:
                        # تحديد الرتبة (طالب أو ولي أمر)
                        st.session_state.role = str(match.iloc[0].get('Roll', 'student')).lower()
                        st.session_state.user = match.iloc[0]
                        st.rerun()
                
                st.error("خطأ في البيانات، حاول مرة أخرى.")

# --- 5. لوحة المعلم ---
elif st.session_state.role == 'teacher':
    with st.sidebar:
        st.markdown(f"### أهلاً مستر إبراهيم")
        menu = st.radio("القائمة الرئيسية", ["مصفوفة النتائج", "عرض الاختبارات للشرح", "إضافة اختبار جديد"])
        if st.button("تسجيل الخروج"):
            st.session_state.role = None
            st.rerun()

    if menu == "مصفوفة النتائج":
        st.title("📊 مصفوفة نتائج الطلاب")
        df_s = load_data("Students")
        df_g = load_data("Grades")
        
        if not df_s.empty and not df_g.empty:
            all_sections = ["الكل"] + list(df_s['Section'].unique())
            selected_sec = st.selectbox("اختر الشعبة لعرض النتائج", all_sections)
            
            # فلترة الطلاب حسب الشعبة
            if selected_sec != "الكل":
                df_s = df_s[df_s['Section'] == selected_sec]
            
            # دمج البيانات
            df_g['Score'] = pd.to_numeric(df_g['Score'], errors='coerce')
            merged = pd.merge(df_s[['ID', 'Name']], df_g[['SID', 'EID', 'Score']], left_on='ID', right_on='SID', how='left')
            
            # إنشاء المصفوفة
            matrix = merged.pivot_table(index='Name', columns='EID', values='Score', aggfunc='max').fillna("-")
            
            st.markdown(f"### نتائج شعبة: {selected_sec}")
            st.dataframe(matrix, use_container_width=True)
            
            # زر الطباعة
            if st.button("🖨️ طباعة التقرير / حفظ PDF"):
                st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        else:
            st.info("لا توجد بيانات درجات مسجلة حالياً.")

    elif menu == "عرض الاختبارات للشرح":
        df_ex = load_data("Exams")
        sel = st.selectbox("اختر الاختبار", df_ex['Title'].unique() if not df_ex.empty else [])
        if sel:
            code = df_ex[df_ex['Title'] == sel].iloc[0]['HTML_Code']
            components.html(code, height=800, scrolling=True)

    elif menu == "إضافة اختبار جديد":
        st.title("➕ إضافة تقييم جديد")
        with st.form("exam_add"):
            st.text_input("كود الاختبار (EID)")
            st.text_input("العنوان")
            st.text_input("اسم الدرس")
            st.selectbox("الشعبة", ["12A", "12B", "12C", "الكل"])
            st.date_input("تاريخ الانتهاء")
            st.text_area("كود HTML")
            st.form_submit_button("حفظ")

# --- 6. لوحة الطالب (Fixing White Screen) ---
elif st.session_state.role in ['student', 'parent']:
    user = st.session_state.user
    st.sidebar.markdown(f"### {user['Name']}")
    if st.sidebar.button("خروج"):
        st.session_state.role = None
        st.rerun()

    st.title("📚 مساري التعليمي")
    
    # تحميل البيانات بأمان
    df_exams = load_data("Exams")
    df_grades = load_data("Grades")
    
    if not df_exams.empty:
        # تصفية شعبة الطالب
        u_sec = user.get('Section', '')
        my_exams = df_exams[(df_exams['Section'] == u_sec) | (df_exams['Section'] == 'الكل')]
        
        lessons = my_exams['Lesson'].unique()
        for lesson in lessons:
            with st.expander(f"📖 درس: {lesson}"):
                l_ex = my_exams[my_exams['Lesson'] == lesson]
                for _, ex in l_ex.iterrows():
                    c1, c2, c3 = st.columns([3, 1, 1.5])
                    c1.write(ex['Title'])
                    
                    # فحص هل الطالب حل الاختبار؟
                    is_done = False
                    if not df_grades.empty:
                        attempt = df_grades[(df_grades['SID'] == user['ID']) & (df_grades['EID'] == ex['Exam_ID'])]
                        is_done = not attempt.empty
                    
                    if is_done:
                        c2.markdown("<span class='status-done'>DONE</span>", unsafe_allow_html=True)
                        if str(ex.get('Show_Answers', '')).upper() == "TRUE":
                            if c3.button("مراجعة", key=f"rev_{ex['Exam_ID']}"):
                                components.html(ex['HTML_Code'], height=600)
                    else:
                        c2.markdown("<span class='status-wanted'>WANTED</span>", unsafe_allow_html=True)
                        if c3.button("بدء الآن", key=f"start_{ex['Exam_ID']}"):
                            components.html(ex['HTML_Code'], height=600)
    else:
        st.info("لا توجد اختبارات منشورة حالياً.")
