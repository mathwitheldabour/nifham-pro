import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. التأكد من حالة الجلسة (Session State) ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 2. إعدادات الصفحة (يجب أن تكون بعد الـ Imports مباشرة) ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# بقية الكود اللي كتبناه للتحقق من الدخول والربط...
# --- 3. AUTH LOGIC (Improved for Teacher Login) ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p class='ar-text' style='text-align: center;'>تسجيل دخول المعلم والطلاب</p>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Bilingual Login | تسجيل الدخول")
            # تنظيف المدخلات فوراً
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            
            if st.button("Login | دخول"):
                try:
                    # 1. فحص الطلاب أولاً
                    df_s = load_data("Students")
                    # تنظيف بيانات الشيت من أي مسافات مخفية
                    df_s['ID'] = df_s['ID'].astype(str).str.strip()
                    df_s['Password'] = df_s['Password'].astype(str).str.strip()
                    
                    student_match = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                    
                    if not student_match.empty:
                        st.session_state.role = 'student'
                        st.session_state.user = student_match.iloc[0]
                        st.rerun()
                    
                    # 2. فحص المعلمين (من شيت Users)
                    df_u = load_data("Users")
                    # تنظيف بيانات المعلمين
                    df_u['ID'] = df_u['ID'].astype(str).str.strip()
                    df_u['Password'] = df_u['Password'].astype(str).str.strip()
                    
                    admin_match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                    
                    if not admin_match.empty:
                        # التأكد من قراءة الرتبة (Role) بشكل سليم
                        raw_role = str(admin_match.iloc[0]['Role']).strip().lower()
                        st.session_state.role = raw_role
                        st.session_state.user = admin_match.iloc[0]
                        st.success(f"Welcome {raw_role}!")
                        st.rerun()
                        
                    st.error("Invalid Credentials | بيانات الدخول غير صحيحة")
                    
                except Exception as e:
                    st.error(f"Error accessing 'Users' sheet: {e}")
                    st.info("Check if sheet tab is named 'Users' and has columns: ID, Name, Password, Role")
