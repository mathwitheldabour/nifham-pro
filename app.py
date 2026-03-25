import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="NIFHAM Math | منصة نفهم", layout="centered")

# --- الربط مع جوجل شيت ---
# سنقوم هنا بتعريف الرابط مباشرة داخل الكود احتياطياً إذا كان هناك مشكلة في الـ Secrets
SHEET_URL = "https://docs.google.com/spreadsheets/d/18z5rEvxgPy2wZxqbnZ4fU7yp_rQ8qD9BpJy4BjWAdJY/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        # قراءة البيانات مع تحديد الرابط مباشرة لضمان الاتصال
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
        return df
    except Exception as e:
        st.error(f"Error loading {sheet_name}: {e}")
        return pd.DataFrame()

# --- إدارة حالة المستخدم ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_data = None
    st.session_state.active_exam = None

# --- واجهة الدخول ---
if not st.session_state.authenticated:
    st.title("Student Login")
    st.markdown('<p style="direction:rtl; text-align:right; color:gray;">تسجيل دخول الطالب</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        sid = st.text_input("Student ID / رقم الطالب").strip() # حذف أي مسافات زائدة
        spass = st.text_input("Password / كلمة المرور", type="password").strip()
        
        if st.form_submit_button("Login / دخول"):
            df_students = load_data("Students")
            
            if not df_students.empty:
                # --- خطوة "تنظيف البيانات" الجوهرية ---
                # تحويل كل الأعمدة لنصوص وحذف أي مسافات فارغة حولها
                df_students['ID'] = df_students['ID'].astype(str).str.strip().str.replace('.0', '', regex=False)
                df_students['Password'] = df_students['Password'].astype(str).str.strip().str.replace('.0', '', regex=False)
                
                # البحث عن الطالب
                user = df_students[(df_students['ID'] == sid) & (df_students['Password'] == spass)]
                
                if not user.empty:
                    st.session_state.authenticated = True
                    st.session_state.user_data = user.iloc[0].to_dict()
                    st.success("Success! Redirecting... / تم الدخول بنجاح")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid ID or Password / بيانات الدخول غير صحيحة")
                    # تنبيه للمدرس للتأكد من أسماء الأعمدة
                    with st.expander("Debug Info (For Teacher)"):
                        st.write("Columns found in sheet:", df_students.columns.tolist())
                        st.write("Sample IDs in sheet:", df_students['ID'].head().tolist())
            else:
                st.error("Could not read students data / لا يمكن الوصول لبيانات الطلاب")

# --- بعد الدخول ---
else:
    u = st.session_state.user_data
    st.sidebar.title(f"Hi, {u['Name']}")
    if st.sidebar.button("Logout / خروج"):
        st.session_state.authenticated = False
        st.rerun()
    
    st.write(f"Logged in to Section: {u['Section']}")
    st.info("Everything is working! / المنصة تعمل الآن بنجاح")
    # يمكنك إضافة بقية كود عرض الامتحانات هنا كما في السابق
