import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# --- 2. محرك الربط ---
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    # تحويل الرابط لـ CSV وقراءة البيانات كنصوص
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, dtype=str)

# --- 3. إدارة الجلسة ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. واجهة تسجيل الدخول ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>مرحباً بك في نظام إدارة التعلم - مستر إبراهيم الدبور</p>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Login Portal | بوابة تسجيل الدخول")
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            
            if st.button("Login | دخول"):
                try:
                    # مصفوفة للبحث في الشيتات المتاحة
                    found = False
                    
                    # أ. محاولة البحث في شيت المستخدمين (للمعلم)
                    try:
                        df_u = load_data("Users")
                        match_u = df_u[(df_u['ID'].str.strip() == uid) & (df_u['Password'].str.strip() == upass)]
                        if not match_u.empty:
                            st.session_state.role = str(match_u.iloc[0]['Role']).lower().strip()
                            st.session_state.user = match_u.iloc[0]
                            found = True
                    except: pass

                    # ب. محاولة البحث في شيت الطلاب (للطالب وولي الأمر)
                    if not found:
                        try:
                            df_s = load_data("Students")
                            match_s = df_s[(df_s['ID'].str.strip() == uid) & (df_s['Password'].str.strip() == upass)]
                            if not match_s.empty:
                                # إذا لم يوجد عمود Role، نعتبره طالب افتراضياً
                                if 'Role' in match_s.columns:
                                    st.session_state.role = str(match_s.iloc[0]['Role']).lower().strip()
                                else:
                                    st.session_state.role = 'student'
                                st.session_state.user = match_s.iloc[0]
                                found = True
                        except: pass
                    
                    if found:
                        st.success(f"Logging in as {st.session_state.role}...")
                        st.rerun()
                    else:
                        st.error("Invalid ID/Password | البيانات غير صحيحة")
                        
                except Exception as e:
                    st.error("Connection Error | خطأ في الاتصال")
                    st.write(e)

# --- 5. لوحة التحكم (المعلم) ---
elif st.session_state.role == 'teacher':
    st.sidebar.success(f"Teacher: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("👨‍🏫 Teacher Command Center")
    st.markdown("---")
    # هنا سنضيف الرسوم البيانية المتطورة لاحقاً

# --- 6. لوحة التحكم (الطالب) ---
elif st.session_state.role == 'student':
    st.sidebar.info(f"Student: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("🎓 Student Portal")
    # محتوى الطالب

# --- 7. لوحة التحكم (ولي الأمر) ---
elif st.session_state.role == 'parent':
    st.sidebar.warning(f"Parent: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("🏠 Parent Dashboard")
    st.write("Welcome! Here you can track your child's progress.")
