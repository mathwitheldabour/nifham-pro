import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random

# --- 1. إعدادات الصفحة والتنسيق ---
st.set_page_config(page_title="NIFHAM Pro | منصة نفهم التعليمية", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .arabic-text { direction: rtl; text-align: right; color: #555; }
    .exam-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border-right: 5px solid #007bff; direction: rtl; }
    .timer-box { font-size: 2rem; font-weight: bold; color: #d9534f; text-align: center; background: #fff; padding: 10px; border-radius: 10px; border: 2px solid #d9534f; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

def clean_data(df):
    for col in ['ID', 'Password', 'Section', 'Student_ID', 'Section_Name']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    return df

# --- 3. إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. شاشة الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_target))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent')
                    st.session_state.update({'auth': True, 'user': user_data, 'role': f_role})
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 5. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات
    df_exams = load_sheet("Exams")
    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    
    # بناء قائمة الشعب (القديم والجديد)
    all_sections = set()
    if not df_students.empty: all_sections.update(df_students['Section'].unique().tolist())
    try:
        df_sec_tab = clean_data(load_sheet("Sections"))
        if not df_sec_tab.empty: all_sections.update(df_sec_tab['Section_Name'].unique().tolist())
    except: pass
    final_sections = sorted([s for s in all_sections if str(s).lower() != 'nan' and str(s).strip() != ""])

    # --- القسم الأول: مصفوفة النتائج ---
    if menu == "Exams Matrix":
        st.header("📊 Results Matrix / مصفوفة النتائج")
        if not df_students.empty:
            sel_sec = st.selectbox("Select Section", ["All"] + final_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "All" else df_students
            if not df_grades.empty:
                df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
                if not df_merged['Exam_ID'].dropna().empty:
                    matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                    st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)
                else: st.info("No exams taken yet.")
            else: st.warning("No grades found.")
        else: st.error("No students registered.")

    # --- القسم الثاني: تحليل مستوى الطالب ---
    elif menu == "Student Analysis":
        st.header("👤 Individual Analysis")
        if not df_students.empty:
            c1, c2 = st.columns(2)
            with c1: sel_s = st.selectbox("Choose Section", final_sections)
            with c2:
                stu_list = df_students[df_students['Section'] == sel_s]
                sel_name = st.selectbox("Choose Student", stu_list['Name'].unique())
            curr_stu = stu_list[stu_list['Name'] == sel_name].iloc[0]
            if not df_grades.empty:
                stu_results = df_grades[df_grades['Student_ID'] == str(curr_stu['ID'])]
                if not stu_results.empty:
                    st.subheader(f"Performance for: {sel_name}")
                    st.table(stu_results[['Date', 'Exam_ID', 'Score']])
                else: st.warning("No grades recorded.")

    # --- القسم الثالث: الإدارة ---
    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        t1, t2 = st.tabs(["Add Section", "Add Student"])
        with t1:
            with st.form("add_sec"):
                n_sec = st.text_input("New Section Name")
                if st.form_submit_button("Save Section"):
                    old_sec = load_sheet("Sections")
                    updated_sec = pd.concat([old_sec, pd.DataFrame([{"Section_Name": n_sec}])], ignore_index=True)
                    conn.update(worksheet="Sections", data=updated_sec)
                    st.success("Section Added!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("add_stu"):
                s_n = st.text_input("Name"); s_i = st.text_input("ID")
                s_s = st.selectbox("Section", final_sections)
                s_p = st.text_input("Password", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("Register"):
                    old_stu = load_sheet("Students")
                    updated_stu = pd.concat([old_stu, pd.DataFrame([{"ID": s_i, "Name": s_n, "Password": s_p, "Section": s_s}])], ignore_index=True)
                    conn.update(worksheet="Students", data=updated_stu)
                    st.success("Student Added!"); time.sleep(1); st.rerun()

    # --- القسم الرابع: إضافة اختبار (تم إصلاح التاريخ والوقت والشعب) ---
    elif menu == "Add Exam":
        st.header("📝 Create New Exam")
        with st.form("exam_form_final"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_id = st.text_input("Exam ID (e.g., E101)")
                e_ti = st.text_input("Exam Title")
                e_le = st.text_input("Lesson")
                st.markdown("---")
                st.subheader("📅 Start Period")
                s_date = st.date_input("Start Date", datetime.now())
                s_time = st.time_input("Start Time", datetime.now().time())
            
            with col_e2:
                e_du = st.number_input("Duration (Minutes)", min_value=1, value=60)
                e_se = st.multiselect("Target Sections", options=final_sections)
                if not final_sections:
                    st.warning("⚠️ No sections found. Please add a Section in Management first.")
                
                st.markdown("---")
                st.subheader("📅 End Period")
                n_date = st.date_input("End Date", datetime.now())
                n_time = st.time_input("End Time", datetime.now().time())

            e_ht = st.text_area("HTML Code (Questions)")
            e_ans = st.selectbox("Show Answers After Finish?", ["No", "Yes"])
            
            if st.form_submit_button("Save Exam / حفظ الاختبار"):
                if not e_id or not e_se:
                    st.error("Please fill Exam ID and select at least one Section.")
                else:
                    try:
                        old_ex = load_sheet("Exams")
                        new_row = pd.DataFrame([{
                            "Exam_ID": str(e_id), "Title": str(e_ti), "Lesson": str(e_le),
                            "Section": ",".join(map(str, e_se)), "Duration": int(e_du),
                            "Start_DateTime": f"{s_date} {s_time}",
                            "End_DateTime": f"{n_date} {n_time}",
                            "HTML_Code": e_ht, "Status": "Active", "Show_Answers": e_ans
                        }])
                        updated_ex = pd.concat([old_ex, new_row], ignore_index=True)
                        conn.update(worksheet="Exams", data=updated_ex)
                        st.success("Exam Published Successfully!"); time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error saving exam: {e}")


# --- 6. لوحة الطالب المتكاملة (منع التكرار + تسجيل النتيجة) ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    
    # 1. تحميل البيانات وتأمينها
    df_ex_stu = load_sheet("Exams")
    df_gr_stu = clean_data(load_sheet("Grades"))
    
    # تحضير قائمة الامتحانات التي أداها الطالب (لمنع التكرار)
    taken_exam_ids = []
    if not df_gr_stu.empty:
        taken_exam_ids = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]['Exam_ID'].unique().tolist()

    if st.session_state.exam is None:
        st.title(f"مرحباً بك، {u['Name']}")
        
        tab1, tab2, tab3 = st.tabs(["📋 الاختبارات المطلوبة", "✅ الاختبارات السابقة", "📊 التحليل والدرجات"])

        with tab1:
            st.subheader("Current Assignments / المهام الحالية")
            
            # 1. جلب بيانات الدرجات الحالية للتفتيش فيها
            df_gr_check = clean_data(load_sheet("Grades"))
            
            if not df_ex_stu.empty:
                # 2. فلترة الاختبارات حسب الشعبة أولاً
                required = df_ex_stu[
                    (df_ex_stu['Status'] == 'Active') & 
                    (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))
                ]
                
                # 3. المنطق الذكي: استبعاد أي امتحان له سجل درجة لهذا الطالب
                if not df_gr_check.empty:
                    # تحويل الأكواد لنصوص لضمان دقة المقارنة
                    finished_exam_ids = df_gr_check[df_gr_check['Student_ID'] == str(u['ID'])]['Exam_ID'].astype(str).tolist()
                    # عرض فقط الاختبارات التي "ليست" في قائمة المنتهية
                    required = required[~required['Exam_ID'].astype(str).isin(finished_exam_ids)]

                # 4. عرض الاختبارات المتبقية فقط
                if required.empty:
                    st.success("✅ أحسنت يا بطل! لقد أتممت جميع اختباراتك الحالية.")
                    st.balloons() # حركة احتفالية بسيطة للطالب
                else:
                    for _, ex in required.iterrows():
                        with st.container():
                            st.markdown(f"""<div class="exam-card">
                                <h4>{str(ex['Title']).replace('.0', '')}</h4>
                                <p>الدرس: {ex['Lesson']} | المدة: {ex['Duration']} دقيقة</p>
                            </div>""", unsafe_allow_html=True)
                            
                            if st.button("بدء الاختبار الآن", key=f"btn_{ex['Exam_ID']}"):
                                st.session_state.exam = ex.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()
            else:
                st.info("لا توجد اختبارات مضافة حالياً.")

        with tab2:
            st.subheader("Previous Exams")
            my_done = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]
            if not my_done.empty:
                st.table(my_done[['Date', 'Exam_ID', 'Score']])
            else:
                st.info("لم تؤدِ أي اختبارات بعد.")

        with tab3:
            st.subheader("Analysis")
            st.info("سيظهر تحليلك البياني هنا فور رصد درجاتك.")

    # --- 7. مشغل الامتحان (تسجيل النتيجة) ---
    else:
        ex = st.session_state.exam
        st.title(f"الاختبار: {str(ex['Title']).replace('.0', '')}")
        
        # حساب التايمر
        elapsed = time.time() - st.session_state.start_t
        remaining = (int(float(ex['Duration'])) * 60) - elapsed
        
        if remaining <= 0:
            st.error("⚠️ انتهى الوقت!")
            if st.button("خروج"): st.session_state.exam = None; st.rerun()
        else:
            # --- 7. مشغل الامتحان المطور (بدون إدخال يدوي) ---
    else:
        ex = st.session_state.exam
        
        # زر العودة للرئيسية
        if st.button("⬅️ إنهاء الجلسة والعودة للوحة التحكم"):
            st.session_state.exam = None
            st.rerun()

        st.title(f"الاختبار: {str(ex['Title']).replace('.0', '')}")
        
        # التايمر
        elapsed = time.time() - st.session_state.start_t
        remaining = (int(float(ex['Duration'])) * 60) - elapsed
        
        if remaining <= 0:
            st.error("⚠️ انتهى الوقت!")
            if st.button("خروج"): st.session_state.exam = None; st.rerun()
        else:
            mins, secs = divmod(int(remaining), 60)
            st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # --- حقن بيانات الطالب في كود الـ HTML أوتوماتيكياً ---
            raw_html = str(ex['HTML_Code'])
            final_html = raw_html.replace("STUDENT_ID_HERE", str(u['ID']))
            final_html = final_html.replace("STUDENT_NAME_HERE", str(u['Name']))
            final_html = final_html.replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            
            # عرض الاختبار
            st.components.v1.html(final_html, height=800, scrolling=True)
            
            # (تم حذف مربع إدخال الدرجة اليدوي بناءً على طلبك)
            st.info("💡 بمجرد ضغطك على 'إرسال' داخل نافذة الاختبار، سيتم تسجيل درجتك فوراً.")
