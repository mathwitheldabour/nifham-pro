import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# --- 2. محرك الربط ---
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url, dtype=str)

# --- 3. إدارة الجلسة ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. واجهة تسجيل الدخول ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>بوابة الدخول الموحدة - مستر إبراهيم الدبور</p>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Bilingual Login | تسجيل الدخول")
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            
            if st.button("Login | دخول"):
                try:
                    found = False
                    
                    # أ. محاولة البحث في شيت Users (للمعلم وولي الأمر كما في الصورة)
                    try:
                        df_u = load_data("Users")
                        # تنظيف البيانات
                        df_u['ID'] = df_u['ID'].str.strip()
                        df_u['Password'] = df_u['Password'].str.strip()
                        
                        match_u = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                        
                        if not match_u.empty:
                            # البحث عن الرتبة سواء كان اسمها Roll أو Role
                            col_name = 'Roll' if 'Roll' in df_u.columns else 'Role'
                            st.session_state.role = str(match_u.iloc[0][col_name]).lower().strip()
                            st.session_state.user = match_u.iloc[0]
                            found = True
                    except Exception as e:
                        st.write(f"Users sheet error: {e}")

                    # ب. محاولة البحث في شيت Students (للطالب)
                    if not found:
                        try:
                            df_s = load_data("Students")
                            df_s['ID'] = df_s['ID'].str.strip()
                            df_s['Password'] = df_s['Password'].str.strip()
                            
                            match_s = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                            if not match_s.empty:
                                st.session_state.role = 'student'
                                st.session_state.user = match_s.iloc[0]
                                found = True
                        except: pass
                    
                    if found:
                        st.success("Success! Redirecting...")
                        st.rerun()
                    else:
                        st.error("Invalid ID/Password | البيانات غير صحيحة")
                        
                except Exception as e:
                    st.error("Connection Error | خطأ في الاتصال")

# --- 5. لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.success(f"Teacher: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("👨‍🏫 Teacher Command Center")
    st.write("أهلاً بك يا مستر إبراهيم.. لوحة التحكم جاهزة.")
    # هنا هنحط أول رسم بياني ليك

# --- 6. لوحة ولي الأمر ---
elif st.session_state.role == 'parent':
    st.sidebar.warning(f"Parent: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("🏠 Parent Dashboard")
    st.write(f"مرحباً بك ولي أمر الطالب: {st.session_state.user['Name']}")

# --- 7. لوحة الطالب ---
elif st.session_state.role == 'student':
    st.sidebar.info(f"Student: {st.session_state.user['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()
    st.title("🎓 Student Portal")
