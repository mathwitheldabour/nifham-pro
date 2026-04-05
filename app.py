import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time, random

# --- 1. الإعدادات الأساسية ---
st.set_page_config(page_title="NIFHAM Pro | Mr. Ibrahim Eldabour", layout="wide")

# الرابط الخاص بك (تأكد أنه ينتهي بـ /exec)
GAS_URL = "https://script.google.com/macros/s/AKfycbzZvxhGjYN-nOm8Fgz1IZUAJJyjlwYu8sOtDXqU--P_Sohb7qT-mjSr5WLgICGMYLYYlA/exec"

# التنسيق (CSS)
st.markdown("""
    <style>
    .arabic-sub { direction: rtl; text-align: right; color: #6c757d; font-size: 0.9em; display: block; margin-bottom: 10px; }
    .exam-card { background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #007bff; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try: return conn.read(worksheet=name, ttl=0)
    except: return pd.DataFrame()

def clean_data(df):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    cols_to_fix = ['ID', 'Student_ID', 'Exam_ID', 'Section', 'Password', 'Section_Name']
    for col in df.columns:
        if col in cols_to_fix:
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# إدارة الجلسة
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None})

# --- 3. نظام تسجيل الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform")
    st.markdown("<span class='arabic-sub'>إدارة منصة الرياضيات | أ. إبراهيم الدبور</span>", unsafe_allow_html=True)
    role_choice = st.selectbox("تسجيل الدخول كـ", ["Student / طالب", "Teacher / معلم"])
    with st.form("login_gate"):
        u_id = st.text_input("User ID").strip()
        u_pw = st.text_input("Password", type="password").strip()
        if st.form_submit_button("دخول"):
            target = "Students" if "Student" in role_choice else "Users"
            df_u = clean_data(load_sheet(target))
            match = df_u[(df_u['ID'] == u_id) & (df_u['Password'] == u_pw)]
            if not match.empty:
                st.session_state.update({'auth': True, 'user': match.iloc[0].to_dict(), 'role': 'student' if "Student" in role_choice else 'teacher'})
                st.rerun()
            else: st.error("Wrong ID or Password!")

# --- 4. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title("Mr. Ibrahim Eldabour")
    menu = st.sidebar.radio("القائمة الرئيسية", ["📊 مصفوفة الدرجات", "👤 نتائج الطلاب الفردية", "📚 مكتبة المعاينة", "📝 مدير الاختبارات", "⚙️ الإعدادات"])

    # تحميل البيانات
    df_stu = clean_data(load_sheet("Students"))
    df_grd = clean_data(load_sheet("Grades"))
    df_exm = clean_data(load_sheet("Exams"))
    df_sec = clean_data(load_sheet("Sections"))
    active_sections = sorted(df_sec['Section_Name'].unique().tolist()) if not df_sec.empty else []

    # أ- مصفوفة الدرجات
    if menu == "📊 مصفوفة الدرجات":
        st.header("Results Matrix / مصفوفة الدرجات")
        if not active_sections: st.warning("قم بإضافة شعب أولاً من الإعدادات.")
        else:
            sel_sec = st.selectbox("اختر الشعبة", ["All"] + active_sections)
            f_stu = df_stu[df_stu['Section'] == sel_sec] if sel_sec != "All" else df_stu
            if 'Student_ID' in df_grd.columns:
                merged = pd.merge(f_stu[['ID', 'Name']], df_grd, left_on='ID', right_on='Student_ID', how='left')
                if 'Exam_ID' in merged.columns:
                    matrix = merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                    st.dataframe(matrix, use_container_width=True)
                else: st.info("لا توجد اختبارات مسجلة لهذه الشعبة.")

    # ب- النتائج الفردية (حل مشكلة KeyError)
    elif menu == "👤 نتائج الطلاب الفردية":
        st.header("Individual Student Report")
        s_sec = st.selectbox("اختر الشعبة", ["Select Section"] + active_sections)
        
        if s_sec != "Select Section":
            students_in_sec = df_stu[df_stu['Section'] == s_sec]['Name'].tolist()
            if students_in_sec:
                s_name = st.selectbox("اختر اسم الطالب", students_in_sec)
                student_id = df_stu[df_stu['Name'] == s_name]['ID'].values[0]
                personal_grd = df_grd[df_grd['Student_ID'] == str(student_id)]
                if not personal_grd.empty:
                    st.subheader(f"سجل درجات: {s_name}")
                    st.table(personal_grd[['Date', 'Exam_ID', 'Score']])
                else: st.info("هذا الطالب لم يقم بأداء أي اختبارات.")
            else: st.warning("لا يوجد طلاب مسجلين في هذه الشعبة.")

    # ج- مكتبة المعاينة
    elif menu == "📚 مكتبة المعاينة":
        st.header("Exams Library / معاينة الاختبارات")
        if df_exm.empty: st.info("لا توجد اختبارات منشورة.")
        else:
            for _, row in df_exm.iterrows():
                with st.expander(f"📖 {row['Title']} (Code: {row['Exam_ID']})"):
                    st.write(f"**الشعب المستهدفة:** {row['Section']}")
                    preview_url = f"{GAS_URL}?sid=TEACHER&eid={row['Exam_ID']}&name=Mr_Ibrahim&mode=preview"
                    st.link_button("معاينة الاختبار 👁️", preview_url)

    # د- مدير الاختبارات (إضافة التاريخ والزمن)
    elif menu == "📝 مدير الاختبارات":
        st.header("Exams Manager / إضافة اختبار جديد")
        with st.form("exam_creation"):
            eid = st.text_input("كود الاختبار (Exam ID)")
            etitle = st.text_input("عنوان الاختبار")
            col1, col2 = st.columns(2)
            with col1: sd = st.date_input("تاريخ البدء"); stm = st.time_input("ساعة البدء")
            with col2: ed = st.date_input("تاريخ الانتهاء"); etm = st.time_input("ساعة الانتهاء")
            esections = st.multiselect("تخصيص للشعب", active_sections)
            ehtml = st.text_area("كود الـ HTML الخاص بالسؤال (العمود H)")
            if st.form_submit_button("نشر الاختبار 🚀"):
                if eid and esections:
                    new_ex = pd.DataFrame([{"Exam_ID": eid, "Title": etitle, "Section": ",".join(esections), "Status": "Active", "Start_Time": f"{sd} {stm}", "End_Time": f"{ed} {etm}", "HTML_Code": ehtml}])
                    conn.update(worksheet="Exams", data=pd.concat([df_exm, new_ex], ignore_index=True))
                    st.success("تم نشر الاختبار بنجاح!"); st.rerun()

    # هـ- الإعدادات (تفعيل إدارة الشعب والطلاب)
    elif menu == "⚙️ الإعدادات":
        st.header("Settings / إدارة النظام")
        tab_sec, tab_stu = st.tabs(["إدارة الشعب", "إضافة طالب جديد"])
        
        with tab_sec:
            new_sec = st.text_input("اسم الشعبة الجديدة (مثل: 12-ADV-A)")
            if st.button("حفظ الشعبة"):
                if new_sec:
                    conn.update(worksheet="Sections", data=pd.concat([df_sec, pd.DataFrame([{"Section_Name": new_sec.strip()}])], ignore_index=True))
                    st.success("تمت إضافة الشعبة!"); st.rerun()
        
        with tab_stu:
            with st.form("new_student"):
                sn = st.text_input("اسم الطالب الرباعي")
                si = st.text_input("رقم الهوية / ID")
                ss = st.selectbox("الشعبة", active_sections)
                sp = st.text_input("كلمة المرور", value=str(random.randint(1000, 9999)))
                if st.form_submit_button("تسجيل الطالب"):
                    if sn and si:
                        conn.update(worksheet="Students", data=pd.concat([df_stu, pd.DataFrame([{"ID": si, "Name": sn, "Password": sp, "Section": ss}])], ignore_index=True))
                        st.success("تم تسجيل الطالب!"); st.rerun()

# --- 5. لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    df_ex = clean_data(load_sheet("Exams"))
    df_gr = clean_data(load_sheet("Grades"))
    my_subs = df_gr[df_gr['Student_ID'] == str(u['ID'])] if 'Student_ID' in df_gr.columns else pd.DataFrame()
    taken_ids = my_subs['Exam_ID'].unique().tolist() if not my_subs.empty else []

    st.title(f"أهلاً {u['Name']} 👋")
    st.markdown(f"<span class='arabic-sub'>شعبة: {u['Section']}</span>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["📋 الاختبارات المطلوبة", "✅ مراجعة إنجازاتي"])

    with t1:
        now = datetime.now()
        pending = df_ex[~df_ex['Exam_ID'].astype(str).isin(map(str, taken_ids))]
        for _, row in pending.iterrows():
            if str(u['Section']) in str(row['Section']):
                with st.container():
                    st.markdown(f'<div class="exam-card"><b>{row["Title"]}</b></div>', unsafe_allow_html=True)
                    exam_url = f"{GAS_URL}?sid={u['ID']}&eid={row['Exam_ID']}&name={u['Name']}&mode=exam"
                    st.link_button("ابدأ الاختبار الآن", exam_url)

    with t2:
        if not my_subs.empty:
            for _, sub in my_subs.iterrows():
                st.write(f"✅ اختبار: **{sub['Exam_ID']}** | درجتك: **{sub['Score']}%**")
                rev_url = f"{GAS_URL}?sid={u['ID']}&eid={sub['Exam_ID']}&name={u['Name']}&mode=review"
                st.link_button("مراجعة الإجابات", rev_url)

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.update({'auth': False, 'user': None, 'role': None}); st.rerun()
