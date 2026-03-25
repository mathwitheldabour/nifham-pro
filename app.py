import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. SETTINGS ---
st.set_page_config(page_title="NIFHAM Math PRO", layout="wide")

# --- 2. DATA ENGINE (The Bulletproof Way) ---
# بنجيب الـ ID من السيكرتس وبنحول الرابط لرابط تحميل مباشر
SHEET_ID = st.secrets["SHEET_ID"]

def load_data(sheet_name):
    # دي "الخلطة السرية" للربط المباشر بدون مكتبات معقدة
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

# --- 3. AUTH LOGIC ---
if 'role' not in st.session_state:
    st.session_state.role = None
    st.session_state.user = None

# واجهة الدخول
if st.session_state.role is None:
    st.markdown("<h1 style='text-align: center;'>NIFHAM Math PRO</h1>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("Bilingual Login | تسجيل الدخول")
            uid = st.text_input("User ID | الكود")
            upass = st.text_input("Password | كلمة المرور", type="password")
            
            if st.button("Login | دخول"):
                try:
                    # فحص الطلاب
                    df_s = load_data("Students")
                    user = df_s[(df_s['ID'].astype(str) == uid) & (df_s['Password'].astype(str) == upass)]
                    
                    if not user.empty:
                        st.session_state.role = 'student'
                        st.session_state.user = user.iloc[0]
                        st.rerun()
                    
                    # فحص المعلمين (من شيت Users)
                    df_u = load_data("Users")
                    admin = df_u[(df_u['ID'].astype(str) == uid) & (df_u['Password'].astype(str) == upass)]
                    if not admin.empty:
                        st.session_state.role = admin.iloc[0]['Role'].lower()
                        st.session_state.user = admin.iloc[0]
                        st.rerun()
                        
                    st.error("Check ID/Pass | تأكد من الكود والباسورد")
                except Exception as e:
                    st.error(f"Connection Error: تأكد من تسمية الشيتات بدقة")
                    st.warning("Hint: Make sure sheet tabs are named 'Students' and 'Users'")

# --- 4. TEACHER DASHBOARD ---
elif st.session_state.role == 'teacher':
    st.sidebar.success(f"Welcome, Mr. Ibrahim")
    menu = st.sidebar.selectbox("Menu", ["Dashboard", "Exams Control"])
    
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    if menu == "Dashboard":
        st.title("Teacher Analytics Dashboard")
        try:
            df_grades = load_data("Grades")
            fig = px.histogram(df_grades, x="Score", nbins=10, title="Distribution of Scores", color_discrete_sequence=['#10b981'])
            st.plotly_chart(fig)
        except:
            st.info("No grades recorded yet | لا يوجد درجات مسجلة بعد")

# --- 5. STUDENT DASHBOARD ---
elif st.session_state.role == 'student':
    user = st.session_state.user
    st.sidebar.write(f"Student: {user['Name']}")
    
    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    st.title(f"Hello, {user['Name']}!")
    tab1, tab2 = st.tabs(["Lessons", "Grades"])
    
    with tab2:
        try:
            df_all_grades = load_data("Grades")
            my_grades = df_all_grades[df_all_grades['SID'].astype(str) == str(user['ID'])]
            st.table(my_grades[['EID', 'Score', 'Date']])
        except:
            st.write("No grades yet.")
