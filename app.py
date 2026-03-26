import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np

# --- 1. إعدادات الصفحة والثوابت (Global Constants) ---
st.set_page_config(page_title="NIFHAM Pro | Math Platform", layout="wide")

# هذا السطر هو حل مشكلة الـ NameError التي ظهرت في الصورة
PASSING_SCORE = 50 

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Cairo:wght@300;600&display=swap');
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .arabic-sub { font-family: 'Cairo', sans-serif; font-size: 0.85em; color: #6c757d; display: block; direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 5px solid #007bff; }
    .timer-box { font-size: 1.8rem; font-weight: bold; color: #d9534f; text-align: center; background: #f8d7da; padding: 10px; border-radius: 8px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات (Data Engine) ---
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

# --- 3. إدارة الجلسة (Session Management) ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 4. شاشة الدخول (Login System) ---
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

# --- 5. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"Mr. {st.session_state.user.get('Name')}")
    menu = st.sidebar.radio("Navigation", ["Results Matrix", "Analytics", "Exams Manager", "System Settings"])
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()

    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec_tab = clean_data(load_sheet("Sections"))
    final_sections = sorted(df_sec_tab['Section_Name'].unique().tolist()) if not df_sec_tab.empty else []

    if menu == "Results Matrix":
        st.header("Results Matrix")
        if not final_sections: st.warning("Please add Sections first in 'System Settings'.")
        else:
            sel_sec = st.selectbox("Select Section", ["All"] + final_sections)
            filtered_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All" else df_stu
            merged = pd.merge(filtered_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
            if not merged['Exam_ID'].dropna().empty:
                matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                st.dataframe(matrix.style.highlight_max(axis=0, color='#bbf7d0'), use_container_width=True)

    elif menu == "Analytics":
        st.header("Analytics Dashboard")
        if not df_grd.empty and not df_stu.empty:
            # دمج البيانات للتحليل
            df_full_an = pd.merge(df_grd, df_stu, left_on='Student_ID', right_on='ID')
            
            m1, m2 = st.columns(2)
            m1.metric("Average Score", f"{df_grd['Score'].mean():.1f}%")
            # تم إصلاح الخطأ هنا باستخدام PASSING_SCORE المعرفة في الأعلى
            pass_rate = (df_grd['Score'] >= PASSING_SCORE).mean() * 100
            m2.metric("Pass Rate", f"{pass_rate:.1f}%")
            
            st.plotly_chart(px.bar(df_full_an.groupby('Section')['Score'].mean().reset_index(), 
                                   x='Section', y='Score', title="Avg Score per Section", color='Score'), use_container_width=True)
        else: st.info("Not enough data for analytics.")

    elif menu == "Exams Manager":
        st.header("Exams Scheduler")
        if not final_sections: st.error("⚠️ Add a Section first in System Settings.")
        else:
            with st.form("add_ex"):
                e_id, e_ti = st.text_input("Exam ID"), st.text_input("Title")
                c_t1, c_t2 = st.columns(2)
                with c_t1: sd = st.date_input("Start Date"); stm = st.time_input("Start Time")
                with c_t2: ed = st.date_input("End Date"); etm = st.time_input("End Time")
                e_se = st.multiselect("Assign to Sections", final_sections)
                e_du = st.number_input("Duration (Min)", value=60)
                e_ht = st.text_area("HTML Code")
                if st.form_submit_button("Publish"):
                    new_ex = pd.DataFrame([{"Exam_ID": e_id, "Title": e_ti, "Section": ",".join(e_se), "Duration": e_du, "HTML_Code": e_ht, "Status": "Active", "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}"}])
                    conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                    st.success("Published!"); st.rerun()

    elif menu == "System Settings":
        st.header("Management Center")
        tab_sec, tab_stu = st.tabs(["1. Manage Sections (START HERE)", "2. Register Students"])
        with tab_sec:
            with st.form("sec_f"):
                ns = st.text_input("New Section Name")
                if st.form_submit_button("Save Section"):
                    if ns:
                        conn.update(worksheet="Sections", data=pd.concat([df_sec_tab, pd.DataFrame([{"Section_Name": ns.strip()}])], ignore_index=True))
                        st.success("Section Added!"); st.rerun()
        with tab_stu:
            if not final_sections: st.warning("Add a section first.")
            else:
                with st.form("stu_f"):
                    sn, si = st.text_input("Name"), st.text_input("ID")
                    ss = st.selectbox("Section", final_sections)
                    sp = st.text_input("Password", value=str(random.randint(1000, 9999)))
                    if st.form_submit_button("Register"):
                        conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])], ignore_index=True))
                        st.success("Registered!"); st.rerun()

elif st.session_state.role == 'student':
    u = st.session_state.user
    
    # --- 1. تحميل البيانات (Data Sync) ---
    with st.spinner("Syncing NIFHAM Dashboard..."):
        df_ex_stu = clean_data(load_sheet("Exams"))
        df_gr_stu = clean_data(load_sheet("Grades"))
        my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    # --- 2. الشريط الجانبي (Sidebar) ---
    st.sidebar.title("NIFHAM Math")
    st.sidebar.markdown(f"**User:** {u['Name']}")
    st.sidebar.markdown(f"**Section:** {u['Section']}")
    
    if st.sidebar.button("Logout / خروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # --- 3. الواجهة الرئيسية (Main UI) ---
    st.title(f"Welcome, {u['Name']} 👋")
    st.markdown("<span class='arabic-sub'>مرحباً بك في منصة نفهم للرياضيات | لوحة متابعة الطالب</span>", unsafe_allow_html=True)

    # التبويبات الثلاثة
    tab1, tab2, tab3 = st.tabs(["📋 Assigned Exams", "✅ Grade History", "📊 My Performance"])

    # --- TAB 1: الاختبارات المجدولة (Portal Logic) ---
    with tab1:
        st.subheader("Current Assignments")
        now = datetime.now()
        
        if not df_ex_stu.empty:
            # فلترة: نشط + الشعبة صحيحة + لم يتم حله سابقاً
            req = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
            taken_ids = my_grades['Exam_ID'].unique().tolist()
            req = req[~req['Exam_ID'].astype(str).isin(map(str, taken_ids))]

            valid_count = 0
            for _, row in req.iterrows():
                try:
                    st_dt = datetime.strptime(str(row['Start_Time']), '%Y-%m-%d %H:%M:%S')
                    en_dt = datetime.strptime(str(row['End_Time']), '%Y-%m-%d %H:%M:%S')
                except:
                    st_dt = en_dt = now

                if st_dt <= now <= en_dt:
                    valid_count += 1
                    with st.container():
                        st.markdown(f"""
                        <div class="exam-card">
                            <h3 style="margin:0; color:#007bff;">{row['Title']}</h3>
                            <p style="margin:5px 0; color:#555;">Duration: {row['Duration']} Minutes</p>
                            <small style="color:#d9534f;">Deadline: {en_dt.strftime('%I:%M %p')}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # --- الرابط السحري لفتح امتحان GAS ---
                        # استبدل هذا الرابط برابط الـ Deployment الخاص بك من Google Apps Script
                        gas_web_app_url = "رابط_الـ_Web_App_الخاص_بك_هنا"
                        full_exam_url = f"https://script.google.com/macros/s/AKfycbz8yAfV-3V-W8Qp19CPSZ8Nl9gHvCIJLOI23SQuQwpRpDT0DVRH9kpjoAdg3TFIoHzQ/exec"
                        
                        st.markdown(f"""
                            <a href="{full_exam_url}" target="_blank" style="text-decoration: none;">
                                <div style="background-color: #28a745; color: white; padding: 12px; text-align: center; border-radius: 8px; font-weight: bold; margin-top: 10px;">
                                    Start Exam in New Window / بدء الاختبار في نافذة جديدة
                                </div>
                            </a>
                        """, unsafe_allow_html=True)
                        st.caption("Note: Equations will render perfectly in the new window.")
                
                elif now < st_dt:
                    st.info(f"🕒 Upcoming: **{row['Title']}** (Available at {st_dt.strftime('%I:%M %p')})")

            if valid_count == 0 and not any(now < datetime.strptime(str(r['Start_Time']), '%Y-%m-%d %H:%M:%S') for _, r in req.iterrows() if 'Start_Time' in r):
                st.success("You are all caught up! No active exams. / لا توجد اختبارات مطلوبة حالياً")
        else:
            st.info("No exams published yet.")

    # --- TAB 2: سجل الدرجات والتدريب ---
    with tab2:
        st.subheader("Your Academic Record")
        if not my_grades.empty:
            st.dataframe(my_grades[['Exam_ID', 'Score']].sort_index(ascending=False), use_container_width=True)
            
            st.divider()
            st.subheader("💡 Smart Practice")
            if st.button("Generate Practice for Last Concept / تدريب على آخر فكرة"):
                # نأخذ آخر امتحان أداه كقالب للتدريب
                last_id = my_grades.iloc[-1]['Exam_ID']
                st.info(f"Generating practice based on {last_id}... Please check the assignments tab.")
                # هنا يمكن توجيه الطالب لفتح رابط GAS مخصص للتدريب (Practice Mode)
        else:
            st.info("No grades found yet. Complete an exam to see your history.")

    # --- TAB 3: التحليلات (Analytics) ---
    with tab3:
        st.subheader("Learning Progress")
        if not my_grades.empty:
            # رسم بياني خطي لتطور الدرجات
            fig = px.line(my_grades, x='Exam_ID', y='Score', title="My Progress Graph", markers=True)
            fig.update_layout(yaxis_range=[0, 105], template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
            # عرض المتوسط الحسابي كبطاقة
            avg = my_grades['Score'].mean()
            st.metric("Overall Average Score", f"{avg:.1f}%")
        else:
            st.warning("No data available for analytics yet.")
                
# --- 7. لوحة ولي الأمر (Parent Dashboard) ---
elif st.session_state.role == 'parent':
    st.title("👨‍👩‍👦 Parent Portal")
    if st.sidebar.button("Logout"): st.session_state.update({'auth': False}); st.rerun()
    u = st.session_state.user
    c_ids = str(u.get('Children_IDs', '')).split(',')
    df_g = clean_data(load_sheet("Grades"))
    df_s = clean_data(load_sheet("Students"))
    for cid in [x.strip() for x in c_ids]:
        if not cid: continue
        name = df_s[df_s['ID'] == cid]['Name'].iloc[0] if not df_s[df_s['ID'] == cid].empty else cid
        with st.expander(f"Child: {name}"):
            cg = df_g[df_g['Student_ID'] == cid]
            st.dataframe(cg[['Exam_ID', 'Score']], use_container_width=True)
            if not cg.empty: st.plotly_chart(px.bar(cg, x='Exam_ID', y='Score', range_y=[0,100]))

# الحماية النهائية
else:
    st.warning("Please Login.")
    st.session_state.update({'auth': False})
