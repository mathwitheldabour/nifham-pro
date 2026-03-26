import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. Page Config & CSS (Professional Bilingual) ---
st.set_page_config(page_title="NIFHAM Pro | Math Hub", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { font-family: 'Cairo', sans-serif; font-size: 0.85em; color: #6c757d; display: block; direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #007bff; }
    .timer-box { font-size: 2rem; font-weight: bold; color: #d9534f; text-align: center; background: #f8d7da; padding: 10px; border-radius: 10px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df.empty: return df
    cols = ['ID', 'Password', 'Section', 'Student_ID', 'Exam_ID', 'Children_IDs', 'Section_Name']
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. Session Management ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. Main Application Flow ---

# المحطة 1: شاشة الدخول (Login)
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>منصة نفهم للرياضيات - تسجيل الدخول</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("User ID / المعرف").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                sheet_name = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_name))
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    u_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else u_data.get('Roll', 'parent').lower()
                    st.session_state.update({'auth': True, 'user': u_data, 'role': f_role})
                    st.rerun()
                else: st.error("Invalid Credentials / بيانات الدخول غير صحيحة")

# المحطة 2: لوحة المعلم (Teacher)
elif st.session_state.role == 'teacher':
    # --- 1. Sidebar & Navigation ---
    st.sidebar.title(f"Welcome, Mr. {st.session_state.user.get('Name', 'Teacher')}")
    st.sidebar.markdown(f"<span class='arabic-sub'>مرحباً أ. {st.session_state.user.get('Name')}</span>", unsafe_allow_html=True)
    
    menu = st.sidebar.radio("Navigation Menu", 
                            ["📊 Results Matrix", "📈 Analytics", "📝 Exams Manager", "⚙️ System Settings"])
    
    if st.sidebar.button("Logout / تسجيل الخروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # --- 2. Load & Sync Data ---
    with st.spinner("Syncing with Google Sheets..."):
        df_stu = clean_data(load_sheet("Students"))
        df_grd = clean_data(load_sheet("Grades"))
        df_exm = clean_data(load_sheet("Exams"))
        df_sec_tab = clean_data(load_sheet("Sections"))

    # جلب قائمة الشعب من جدول "Sections" لضمان دقة الربط
    final_sections = sorted(df_sec_tab['Section_Name'].unique().tolist()) if not df_sec_tab.empty else []

    # --- 3. Results Matrix (مصفوفة النتائج) ---
    if menu == "📊 Results Matrix":
        st.header("Results Matrix")
        st.markdown("<span class='arabic-sub'>عرض تفصيلي لدرجات الطلاب في كافة الاختبارات</span>", unsafe_allow_html=True)
        
        if not final_sections:
            st.warning("⚠️ No sections found. Please add sections in 'System Settings' first.")
        elif df_grd.empty:
            st.info("No grades have been recorded yet.")
        else:
            sel_sec = st.selectbox("Filter by Section", ["All Sections"] + final_sections)
            # فلترة الطلاب
            f_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All Sections" else df_stu
            
            # دمج البيانات
            merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                
                # تلوين الدرجات تلقائياً (أخضر للمرتفع، أحمر للمنخفض)
                def color_scores(val):
                    try:
                        v = float(val)
                        if v >= 90: return 'background-color: #bbf7d0'
                        if v < 50: return 'background-color: #fecaca'
                    except: pass
                    return ''
                
                st.dataframe(matrix.style.applymap(color_scores), use_container_width=True)
            else:
                st.info("No grades found for the selected section.")

    # --- 4. Analytics (تحليلات الأداء) ---
    elif menu == "📈 Analytics":
        st.header("Analytics Dashboard")
        if not df_grd.empty and not df_stu.empty:
            df_an = pd.merge(df_grd, df_stu, left_on='Student_ID', right_on='ID')
            
            # أرقام رئيسية (Metrics)
            m1, m2, m3 = st.columns(3)
            m1.metric("Average Score", f"{df_grd['Score'].mean():.1f}%")
            m2.metric("Pass Rate", f"{(df_grd['Score'] >= PASSING_SCORE).mean()*100:.1f}%")
            m3.metric("Total Submissions", len(df_grd))
            
            st.divider()
            
            # الرسوم البيانية
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                sec_avg = df_an.groupby('Section')['Score'].mean().reset_index()
                st.plotly_chart(px.bar(sec_avg, x='Section', y='Score', title="Avg Score per Section", color='Score'), use_container_width=True)
            
            with col_c2:
                fig_pie = px.pie(values=[(df_grd['Score'] >= 50).sum(), (df_grd['Score'] < 50).sum()], 
                                names=['Passed', 'Failed'], title="Overall Success Ratio",
                                color_discrete_sequence=['#28a745', '#dc3545'])
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.error("Not enough data to generate visual analytics.")

    # --- 5. Exams Manager (إدارة وجدولة الاختبارات) ---
    elif menu == "📝 Exams Manager":
        st.header("Exams Scheduler")
        if not final_sections:
            st.error("⚠️ Stop! Add a Section in 'System Settings' before creating exams.")
        else:
            with st.form("add_exam_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_id = st.text_input("Exam ID (e.g., MATH-101)")
                    e_ti = st.text_input("Exam Title")
                    e_du = st.number_input("Duration (Minutes)", value=60)
                with col_e2:
                    e_se = st.multiselect("Assign to Sections", final_sections)
                    sd = st.date_input("Start Date"); stm = st.time_input("Start Time")
                    ed = st.date_input("End Date"); etm = st.time_input("End Time")
                
                e_ht = st.text_area("HTML Code (Use VAR_A, VAR_B for dynamics)", height=250)
                
                if st.form_submit_button("Publish Exam / نشر الاختبار"):
                    if e_id and e_ti and e_se:
                        new_ex = pd.DataFrame([{
                            "Exam_ID": e_id, "Title": e_ti, "Section": ",".join(e_se), 
                            "Duration": e_du, "HTML_Code": e_ht, "Status": "Active",
                            "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}"
                        }])
                        conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                        st.success("Exam published successfully!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Please complete all fields.")

    # --- 6. System Settings (إدارة الطلاب والشعب) ---
    elif menu == "⚙️ System Settings":
        st.header("Management Center")
        t_sec, t_stu = st.tabs(["1. Manage Sections (START HERE)", "2. Register Students"])
        
        with t_sec:
            st.subheader("Add New Section")
            with st.form("sec_f"):
                ns = st.text_input("New Section Name (e.g., 12-Advanced-A)")
                if st.form_submit_button("Save Section"):
                    if ns:
                        new_s = pd.DataFrame([{"Section_Name": ns.strip()}])
                        conn.update(worksheet="Sections", data=pd.concat([df_sec_tab, new_s], ignore_index=True))
                        st.success(f"Section '{ns}' added!"); time.sleep(1); st.rerun()
        
        with t_stu:
            st.subheader("Register New Student")
            if not final_sections:
                st.warning("⚠️ You must add a Section first in the 'Manage Sections' tab.")
            else:
                with st.form("stu_f"):
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        sn, si = st.text_input("Full Name"), st.text_input("Student ID")
                    with sc2:
                        ss = st.selectbox("Assign to Section", final_sections)
                        sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                    
                    if st.form_submit_button("Register"):
                        if sn and si:
                            new_st = pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])
                            conn.update(worksheet="Students", data=pd.concat([df_stu, new_st], ignore_index=True))
                            st.success(f"Student {sn} registered!"); time.sleep(1); st.rerun()
                            
# المحطة 3: لوحة الطالب (Student)
elif st.session_state.role == 'student':
    u = st.session_state.user
    
    # --- 1. تحميل البيانات وتصفيتها ---
    with st.spinner("Loading your dashboard..."):
        df_ex_stu = clean_data(load_sheet("Exams"))
        df_gr_stu = clean_data(load_sheet("Grades"))
        # تصفية درجات الطالب الحالي فقط
        my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    # --- 2. وضع مشغل الامتحان (Exam Runner Mode) ---
    if st.session_state.exam is not None:
        ex = st.session_state.exam
        st.subheader(f"Exam: {ex['Title']}")
        
        # منطق التوقيت (Timer)
        elapsed = time.time() - st.session_state.start_t
        duration_sec = int(float(ex.get('Duration', 60))) * 60
        remaining = duration_sec - elapsed
        
        if remaining <= 0:
            st.error("Time Expired! / انتهى الوقت المحدد للاختبار")
            if st.button("Return to Dashboard"):
                st.session_state.exam = None
                st.rerun()
        else:
            # عرض عداد الوقت التفاعلي
            mins, secs = divmod(int(remaining), 60)
            st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # --- معالجة وحقن البيانات (The Smart Injection) ---
            html_content = str(ex['HTML_Code'])
            
            # استبدال كلمات الهوية
            html_content = html_content.replace("STUDENT_ID_HERE", str(u['ID']))
            html_content = html_content.replace("STUDENT_NAME_HERE", str(u['Name']))
            html_content = html_content.replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            
            # توليد أرقام عشوائية ثابتة لهذا الطالب في هذا الامتحان (Seed)
            if "VAR_A" in html_content:
                # نستخدم مجموع قيم الحروف لضمان رقم صحيح دائماً من المعرفات النصية
                safe_seed = sum(ord(c) for c in (str(u['ID']) + str(ex['Exam_ID'])))
                random.seed(safe_seed)
                html_content = html_content.replace("VAR_A", str(random.randint(2, 9)))
                html_content = html_content.replace("VAR_B", str(random.randint(2, 5)))
                random.seed() # إعادة تصفير البذرة
            
            # --- إصلاح الـ LaTeX لضمان عمل MathJax ---
            # نقوم بمضاعفة العلامات المائلة لكي تصل للمتصفح بشكل سليم \ -> \\
            html_final = html_content.replace("\\", "\\\\")
            
            # عرض نافذة الامتحان
            st.components.v1.html(html_final, height=850, scrolling=True)
            
            st.info("💡 Do not refresh the page until you submit. / لا تقم بتحديث الصفحة حتى تنهي الإرسال.")
            if st.button("Cancel & Exit / خروج"):
                st.session_state.exam = None
                st.rerun()

    # --- 3. وضع اللوحة الرئيسية (Dashboard Mode) ---
    else:
        st.title(f"Welcome, {u['Name']} 👋")
        st.markdown(f"<span class='arabic-sub'>مرحباً بك، {u['Name']} | الشعبة: {u['Section']}</span>", unsafe_allow_html=True)
        
        if st.sidebar.button("Log out"):
            st.session_state.update({'auth': False, 'user': None, 'role': None})
            st.rerun()

        # التبويبات الثلاثة
        tab1, tab2, tab3 = st.tabs(["📋 Assigned Exams", "✅ Grade History", "📊 My Performance"])

        # التبويب الأول: الاختبارات المجدولة
        with tab1:
            st.subheader("Current Assignments")
            now = datetime.now()
            
            if not df_ex_stu.empty:
                # فلترة: نشط + الشعبة صحيحة + لم يسبق حله
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                taken_ids = my_grades['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]

                valid_count = 0
                for _, ex_row in required.iterrows():
                    # فحص وقت البداية والنهاية
                    try:
                        start_dt = datetime.strptime(str(ex_row['Start_Time']), '%Y-%m-%d %H:%M:%S')
                        end_dt = datetime.strptime(str(ex_row['End_Time']), '%Y-%m-%d %H:%M:%S')
                    except:
                        start_dt = end_dt = now # حالة احتياطية

                    if start_dt <= now <= end_dt:
                        valid_count += 1
                        with st.container():
                            st.markdown(f"""
                            <div class="exam-card">
                                <strong>{ex_row['Title']}</strong><br/>
                                <small>Deadline: {end_dt.strftime('%Y-%m-%d %I:%M %p')}</small>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"Start: {ex_row['Title']}", key=f"start_{ex_row['Exam_ID']}"):
                                st.session_state.exam = ex_row.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()
                    elif now < start_dt:
                        st.warning(f"🕒 Upcoming Exam: {ex_row['Title']} (Starts at {start_dt.strftime('%I:%M %p')})")

                if valid_count == 0 and now >= start_dt:
                    st.success("All caught up! No active exams. / لا توجد اختبارات حالياً")
            else:
                st.info("No exams have been published yet.")

        # التبويب الثاني: السجل والتدريب الذكي
        with tab2:
            st.subheader("Your Academic Record")
            if not my_grades.empty:
                st.dataframe(my_grades[['Exam_ID', 'Score']].sort_index(ascending=False), use_container_width=True)
                
                st.divider()
                st.subheader("💡 Smart Practice")
                st.write("Generate a similar test based on your previous performance.")
                
                if st.button("Generate Smart Practice / إنشاء تدريب ذكي"):
                    # نأخذ آخر اختبار تم حله كقالب
                    last_id = my_grades.iloc[-1]['Exam_ID']
                    tmpl_row = df_ex_stu[df_ex_stu['Exam_ID'] == last_id]
                    
                    if not tmpl_row.empty:
                        tmpl_html = str(tmpl_row.iloc[0]['HTML_Code'])
                        # توليد أرقام عشوائية للتدريب
                        v1, v2 = random.randint(2, 9), random.randint(2, 5)
                        practice_html = tmpl_html.replace("VAR_A", str(v1)).replace("VAR_B", str(v2))
                        # إصلاح الـ LaTeX
                        st.session_state.practice_mode = practice_html.replace("\\", "\\\\")
                        st.rerun()

                if 'practice_mode' in st.session_state:
                    st.info("Practice Mode: Same concepts, different values.")
                    st.components.v1.html(st.session_state.practice_mode, height=600, scrolling=True)
                    if st.button("Close Practice Window"):
                        del st.session_state.practice_mode
                        st.rerun()
            else:
                st.info("No grades recorded yet. Complete an exam to unlock Smart Practice!")

        # التبويب الثالث: تحليلات الطالب
        with tab3:
            st.subheader("Performance Analytics")
            if not my_grades.empty:
                # رسم بياني لتطور المستوى
                fig = px.line(my_grades, x='Exam_ID', y='Score', title="Your Progress Index", markers=True)
                fig.update_layout(yaxis_range=[0, 105], xaxis_title="Exam ID", yaxis_title="Score (%)")
                st.plotly_chart(fig, use_container_width=True)
                
                # أرقام سريعة
                avg = my_grades['Score'].mean()
                st.metric("Cumulative Average", f"{avg:.1f}%")
            else:
                st.warning("Take your first exam to see your progress chart!")
                
# المحطة 4: لوحة ولي الأمر
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
    u = st.session_state.user
    c_ids = str(u.get('Children_IDs', '')).split(',')
    df_g = clean_data(load_sheet("Grades"))
    df_s = clean_data(load_sheet("Students"))
    for cid in [x.strip() for x in c_ids]:
        name = df_s[df_s['ID'] == cid]['Name'].iloc[0] if not df_s[df_s['ID'] == cid].empty else cid
        with st.expander(f"Child: {name}"):
            cg = df_g[df_g['Student_ID'] == cid]
            st.dataframe(cg[['Exam_ID', 'Score']], use_container_width=True)

# المحطة الأخيرة: حماية
else:
    st.warning("Please Login.")
    st.session_state.update({'auth': False})
