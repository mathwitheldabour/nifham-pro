import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# --- 2. محرك الربط (المساعد load_data) ---
# التأكد من وجود SHEET_ID في السيكرتس
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    # الوظيفة اللي كانت ناقصة وسببت الخطأ
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

# --- 3. إدارة الجلسة ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# --- 4. واجهة تسجيل الدخول ---
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center; color: #0f172a;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>تسجيل دخول المعلم والطلاب - مدرسة خالد بن الوليد</p>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Bilingual Login | تسجيل الدخول")
            uid = st.text_input("User ID | الكود").strip()
            upass = st.text_input("Password | كلمة المرور", type="password").strip()
            
            if st.button("Login | دخول"):
                try:
                    # فحص الطلاب
                    df_s = load_data("Students")
                    df_s['ID'] = df_s['ID'].astype(str).str.strip()
                    df_s['Password'] = df_s['Password'].astype(str).str.strip()
                    
                    student_match = df_s[(df_s['ID'] == uid) & (df_s['Password'] == upass)]
                    
                    if not student_match.empty:
                        st.session_state.role = 'student'
                        st.session_state.user = student_match.iloc[0]
                        st.rerun()
                    
                    # فحص المعلمين (شيت Users)
                    df_u = load_data("Users")
                    df_u['ID'] = df_u['ID'].astype(str).str.strip()
                    df_u['Password'] = df_u['Password'].astype(str).str.strip()
                    
                    admin_match = df_u[(df_u['ID'] == uid) & (df_u['Password'] == upass)]
                    
                    if not admin_match.empty:
                        raw_role = str(admin_match.iloc[0]['Role']).strip().lower()
                        st.session_state.role = raw_role
                        st.session_state.user = admin_match.iloc[0]
                        st.rerun()
                        
                    st.error("Invalid ID/Password | خطأ في الكود أو الباسورد")
                except Exception as e:
                    st.error(f"خطأ في الوصول للبيانات: {e}")

# --- 5. لوحات التحكم (المعلم والطالب) ---
elif st.session_state.role == 'teacher':
    st.title("Teacher Dashboard | لوحة المعلم")
    st.sidebar.success(f"Welcome Mr. {st.session_state.user['Name']}")
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()
    # هنا هنحط الرسوم البيانية في الخطوة الجاية
    st.write("Analytics and control will appear here.")

elif st.session_state.role == 'student':
    st.title(f"Hello, {st.session_state.user['Name']}!")
    st.sidebar.info(f"Section: {st.session_state.user['Section']}")
    if st.sidebar.button("Logout | خروج"):
        st.session_state.role = None
        st.rerun()
