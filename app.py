import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random

# --- 1. Page Configuration / إعدادات الصفحة ---
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

# --- 2. Data Engine / محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    return conn.read(worksheet=name, ttl=0)

def clean_login_data(df):
    """تنظيف بيانات الدخول"""
    for col in ['ID', 'Password']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    return df

# --- 3. Session State / إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Login Screen / شاشة الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown('<h3 class="arabic-text">تسجيل الدخول للمنصة</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            
            if st.form_submit_button("Sign In / دخول"):
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_users = clean_login_data(load_sheet(sheet_target))
                
                user_match = df_users[(df_users['ID'] == str(u_id)) & (df_users['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    final_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent')
                    st.session_state.update({'auth': True, 'user': user_data, 'role': final_role})
                    st.success(f"Welcome / مرحباً بك: {user_data['Name']}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 5. Teacher Dashboard / لوحة المعلم ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Teacher Tools")
    # القائمة الجانبية
    menu = st.sidebar.radio("Menu / القائمة", ["Exams Matrix", "Student Analysis", "Management", "Add Exam"])
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات المطلوبة
    df_exams = load_sheet("Exams")
    df_students = load_sheet("Students")
    df_grades = load_sheet("Grades")
    
    # محاولة جلب الشعب من شيت Sections
    try:
        df_all_sections = load_sheet("Sections")
        available_sections = df_all_sections['Section_Name'].unique().tolist()
    except:
        available_sections = []

    # --- 1. إضافة اختبار جديد ---
    if menu == "Add Exam":
        st.header("📝 Create New Exam / إضافة اختبار جديد")
        with st.form("new_exam_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_id = st.text_input("Exam ID / رمز الاختبار")
                e_title = st.text_input("Exam Title / العنوان")
                e_lesson = st.text_input("Lesson / الدرس")
                st.markdown("---")
                st.subheader("Start Period / فترة البدء")
                s_date = st.date_input("Start Date / تاريخ البدء", datetime.now())
                s_time = st.time_input("Start Time / وقت البدء", datetime.now().time())
            
            with col2:
                e_dur = st.number_input("Duration / المدة (دقيقة)", min_value=1, value=60)
                e_status = st.selectbox("Status / الحالة", ["Active", "Hidden"])
                all_sec = st.checkbox("Assign to all sections / لكل الشعب")
                target_sec = st.multiselect("Select Sections", available_sections) if not all_sec else ["All"]
                st.markdown("---")
                st.subheader("End Period / فترة الانتهاء")
                n_date = st.date_input("End Date / تاريخ الانتهاء", datetime.now())
                n_time = st.time_input("End Time / وقت الانتهاء", datetime.now().time())

            e_html = st.text_area("HTML Code / كود الأسئلة")
            show_ans = st.selectbox("Show Answers? / مسموح بالمراجعة؟", ["No", "Yes"])

            if st.form_submit_button("Save Exam / حفظ الاختبار"):
                start_dt = f"{s_date} {s_time}"
                end_dt = f"{n_date} {n_time}"
                new_row = pd.DataFrame([{
                    "Exam_ID": str(e_id).strip(), "Title": str(e_title).strip(),
                    "Lesson": str(e_lesson).strip(), "Section": ",".join(map(str, target_sec)),
                    "Duration": int(e_dur), "Start_DateTime": start_dt,
                    "End_DateTime": end_dt, "HTML_Code": e_html,
                    "Status": e_status, "Show_Answers": show_ans
                }])
                conn.create(worksheet="Exams", data=new_row)
                st.success("Exam saved successfully! / تم الحفظ بنجاح")

    # --- 2. الإدارة (شعب وطلاب) ---
    elif menu == "Management":
        st.header("⚙️ Management / الإدارة")
        tab1, tab2 = st.tabs(["Add Section / إضافة شعبة", "Add Student / إضافة طالب"])
        
        # --- 1. تبويب إضافة شعبة ---
        with tab1:
            st.subheader("Create New Section")
            with st.form("sec_form"):
                new_sec_name = st.text_input("Section Name / اسم الشعبة")
                if st.form_submit_button("Create Section"):
                    if new_sec_name:
                        try:
                            # جلب البيانات الحالية أو إنشاء داتا فريم جديد
                            try:
                                df_existing_sec = load_sheet("Sections")
                            except:
                                df_existing_sec = pd.DataFrame(columns=["Section_Name"])
                            
                            new_row = pd.DataFrame([{"Section_Name": str(new_sec_name).strip()}])
                            updated_df = pd.concat([df_existing_sec, new_row], ignore_index=True)
                            conn.update(worksheet="Sections", data=updated_df)
                            
                            st.success(f"Section '{new_sec_name}' added successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving section: {e}")
                    else:
                        st.warning("Please enter a section name!")

        # --- 2. تبويب إضافة طالب (المعالج لإصلاح الاختفاء) ---
        with tab2:
            st.subheader("Register New Student")
            
            # محاولة جلب الشعب بشكل آمن تماماً
            list_of_sections = []
            try:
                df_sec_load = load_sheet("Sections")
                if not df_sec_load.empty and "Section_Name" in df_sec_load.columns:
                    list_of_sections = df_sec_load["Section_Name"].dropna().unique().tolist()
            except Exception as e:
                # لو فشل في القراءة، نترك القائمة فارغة ولا نجعل الصفحة تختفي
                pass

            if not list_of_sections:
                st.warning("⚠️ No sections found. Please add a Section in the first tab first!")
                st.info("تنبيه: يجب إضافة شعبة أولاً في التبويب الآخر لتتمكن من إضافة طلاب بداخلها.")
            else:
                with st.form("stu_form"):
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        s_name = st.text_input("Full Name / اسم الطالب")
                        s_id = st.text_input("Student ID / الرقم التعريفي")
                    with col_s2:
                        s_sec = st.selectbox("Select Section / اختر الشعبة", list_of_sections)
                        # توليد كلمة سر تلقائية
                        import random
                        gen_pass = str(random.randint(100000, 999999))
                        s_pass = st.text_input("Password / كلمة المرور", value=gen_pass)
                    
                    if st.form_submit_button("Register / تسجيل الطالب"):
                        if s_name and s_id:
                            try:
                                # جلب بيانات الطلاب الحالية للإضافة عليها
                                try:
                                    df_existing_stu = load_sheet("Students")
                                except:
                                    df_existing_stu = pd.DataFrame(columns=["ID", "Name", "Password", "Section"])
                                
                                new_stu_row = pd.DataFrame([{
                                    "ID": str(s_id).strip(),
                                    "Name": str(s_name).strip(),
                                    "Password": str(s_pass).strip(),
                                    "Section": str(s_sec).strip()
                                }])
                                
                                updated_stu_df = pd.concat([df_existing_stu, new_stu_row], ignore_index=True)
                                conn.update(worksheet="Students", data=updated_stu_df)
                                
                                st.success(f"Student '{s_name}' registered successfully!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving student: {e}")
                        else:
                            st.error("Please fill all fields / يرجى ملء جميع الحقول")
                            
    # --- 3. مصفوفة النتائج ---
# --- القسم الثالث: مصفوفة النتائج (المطور) ---
    elif menu == "Exams Matrix":
        st.header("📊 Results Matrix / مصفوفة النتائج")
        
        if not df_grades.empty and not df_students.empty:
            # 1. فلتر اختيار الشعبة
            available_sections = df_students['Section'].unique().tolist()
            selected_section = st.selectbox("Select Section / اختر الشعبة", ["All / الجميع"] + available_sections)
            
            # 2. ربط بيانات الدرجات ببيانات الطلاب للحصول على "الشعبة" لكل درجة
            # نقوم بدمج Grades مع Students بناءً على ID الطالب
            df_merged = pd.merge(
                df_grades, 
                df_students[['ID', 'Section']], 
                left_on='Student_ID', 
                right_on='ID', 
                how='left'
            )
            
            # 3. تطبيق الفلترة حسب الشعبة المختارة
            if selected_section != "All / الجميع":
                df_filtered = df_merged[df_merged['Section'] == selected_section]
            else:
                df_filtered = df_merged

            if not df_filtered.empty:
                # 4. إنشاء المصفوفة (Pivot Table)
                # الصفوف: Student_Name، الأعمدة: Exam_ID (أو Title)، القيم: Score
                matrix = df_filtered.pivot_table(
                    index='Student_Name', 
                    columns='Exam_ID', 
                    values='Score', 
                    aggfunc='max' # في حال قدم الطالب أكثر من مرة نأخذ الدرجة الأعلى
                )
                
                # ملء الفراغات (الطلاب الذين لم يختبروا) بكلمة "N/A" أو "-"
                matrix = matrix.fillna('-')
                
                # 5. عرض المصفوفة بتنسيق جميل
                st.markdown(f"**Showing results for: {selected_section}**")
                st.dataframe(
                    matrix.style.highlight_max(axis=0, color='lightgreen') # تمييز الدرجة الأعلى في كل امتحان
                    .highlight_min(axis=0, color='#ffcccc') # تمييز الدرجة الأقل
                    , use_container_width=True
                )
                
                # إحصائية سريعة
                st.caption(f"Number of students in view: {len(matrix)}")
            else:
                st.warning("No grades found for this section / لا توجد درجات مسجلة لهذه الشعبة")
        else:
            st.info("No grades or students found yet / لا توجد بيانات طلاب أو درجات حالياً")

    # --- 4. تحليل مستوى الطالب ---
    elif menu == "Student Analysis":
        st.header("👤 Individual Analysis / تحليل المستوى")
        if not df_students.empty:
            selected_stu = st.selectbox("Select Student", df_students['Name'].unique())
            stu_data = df_grades[df_grades['Student_Name'] == selected_stu]
            if not stu_data.empty:
                fig = px.line(stu_data, x='Date', y='Score', title=f"Progress: {selected_stu}")
                st.plotly_chart(fig)
            else:
                st.warning("No data for this student.")

# --- 6. Student Dashboard / لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    if st.session_state.exam is None:
        st.title(f"Welcome, {u['Name']}")
        tab1, tab2 = st.tabs(["📋 To-do / الاختبارات", "✅ Completed / المنجزة"])
        
        df_exams = load_sheet("Exams")
        df_grades = load_sheet("Grades")
        
        with tab1:
            # --- إصلاح الخطأ الجوهري هنا ---
            # تحويل عمود الشعبة لنصوص قبل البحث
            df_exams['Section'] = df_exams['Section'].astype(str)
            student_section = str(u.get('Section', ''))
            
            todo = df_exams[
                (df_exams['Status'] == 'Active') & 
                (df_exams['Section'].str.contains(student_section, na=False) | (df_exams['Section'] == "All"))
            ]
            
            if todo.empty:
                st.info("No active exams for your section / لا توجد امتحانات حالياً")
            else:
                for _, ex in todo.iterrows():
                    with st.container():
                        st.markdown(f'<div class="exam-card"><h4>{ex["Title"]}</h4><p>{ex["Lesson"]} | {ex["Duration"]} min</p></div>', unsafe_allow_html=True)
                        if st.button("Start / ابدأ", key=ex['Exam_ID']):
                            st.session_state.update({'exam': ex.to_dict(), 'start_t': time.time()})
                            st.rerun()

        with tab2:
            if not df_grades.empty:
                my_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
                st.dataframe(my_grades, use_container_width=True)
    else:
        # مشغل الامتحان
        ex = st.session_state.exam
        rem = (int(ex['Duration']) * 60) - int(time.time() - st.session_state.start_t)
        if rem <= 0:
            st.error("Time Up!")
            if st.button("Exit"): st.session_state.exam = None; st.rerun()
        else:
            m, s = divmod(rem, 60)
            st.markdown(f'<div class="timer-box">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
            st.components.v1.html(ex['HTML_Code'], height=800, scrolling=True)
            if st.button("Submit / تسليم"):
                new_g = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d %H:%M"), "Student_ID": u['ID'], "Student_Name": u['Name'], "Exam_ID": ex['Exam_ID'], "Score": 10}])
                conn.create(worksheet="Grades", data=new_g)
                st.success("Submitted!"); time.sleep(2); st.session_state.exam = None; st.rerun()

# --- 7. Parent Dashboard / لوحة ولي الأمر ---
elif st.session_state.role == 'parent':
    st.title("👪 Parent Portal")
    u = st.session_state.user
    st.info(f"Report for Student ID: {u['ID']}")
    df_grades = load_sheet("Grades")
    if not df_grades.empty:
        my_child_grades = df_grades[df_grades['Student_ID'].astype(str) == str(u['ID'])]
        if not my_child_grades.empty:
            fig = px.bar(my_child_grades, x='Exam_ID', y='Score', title="Grades History")
            st.plotly_chart(fig)
