import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from datetime import datetime
import plotly.express as px
import random
import numpy as np # تم إضافة numpy للعمليات الحسابية

# --- 1. إعدادات الصفحة والتنسيق ---
st.set_page_config(page_title="NIFHAM Pro | منصة نفهم التعليمية", layout="wide")

# درجة النجاح (يمكن تغييرها)
PASSING_SCORE = 50

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl;}
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .arabic-text { direction: rtl; text-align: right; color: #555; }
    .exam-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border-right: 5px solid #007bff; direction: rtl; text-align: right;}
    .timer-box { font-size: 2rem; font-weight: bold; color: #d9534f; text-align: center; background: #fff; padding: 10px; border-radius: 10px; border: 2px solid #d9534f; }
    /* تنسيق خاص للـ Tabs لتظهر بشكل أوضح */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 10px 10px 0 0; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. محرك البيانات ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_sheet(name):
    try:
        # ttl=0 تضمن تحميل أحدث البيانات دائماً عند التحديث
        return conn.read(worksheet=name, ttl=0)
    except:
        return pd.DataFrame()

def clean_data(df):
    for col in ['ID', 'Password', 'Section', 'Student_ID', 'Section_Name', 'Exam_ID']:
        if col in df.columns:
            # تنظيف البيانات: تحويل لنصوص، حذف المسافات، وحذف الـ .0 الزائدة
            df[col] = df[col].astype(str).str.strip().str.replace('.0', '', regex=False)
    # تحويل الدرجات لأرقام
    if 'Score' in df.columns:
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    return df

# --- 3. وظائف التحليل والاحصاء ---
def calculate_pass_rate(scores):
    if len(scores) == 0: return 0
    passed = (scores >= PASSING_SCORE).sum()
    return (passed / len(scores)) * 100

# --- 4. إدارة الجلسة ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': None, 'role': None, 'exam': None, 'start_t': None})

# --- 5. شاشة الدخول ---
if not st.session_state.auth:
    st.title("🚀 NIFHAM Math Platform | منصة نفهم للرياضيات")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        role_choice = st.selectbox("Login as / الدخول كـ", ["Student / طالب", "Teacher / معلم", "Parent / ولي أمر"])
        with st.form("login_form"):
            u_id = st.text_input("ID / الرقم التعريفي").strip()
            u_pass = st.text_input("Password / كلمة المرور", type="password").strip()
            if st.form_submit_button("Sign In / دخول"):
                sheet_target = "Students" if "Student" in role_choice else "Users"
                df_u = clean_data(load_sheet(sheet_target))
                
                # التحقق من المستخدم
                user_match = df_u[(df_u['ID'] == str(u_id)) & (df_u['Password'] == str(u_pass))]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0].to_dict()
                    f_role = "student" if "Student" in role_choice else user_data.get('Roll', 'parent')
                    st.session_state.update({'auth': True, 'user': user_data, 'role': f_role.lower()})
                    st.rerun()
                else:
                    st.error("Invalid credentials / بيانات الدخول غير صحيحة")

# --- 6. لوحة المعلم (Teacher Dashboard) ---
elif st.session_state.role == 'teacher':
    st.sidebar.title(f"مرحباً أ. {st.session_state.user.get('Name', 'المعلم')}")
    menu = st.sidebar.radio("القائمة الرئيسية", ["مصفوفة النتائج", "التحليلات والإحصائيات", "إضافة اختبار جديد", "إدارة النظام"])
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.update({'auth': False, 'user': None, 'role': None})
        st.rerun()

    # تحميل البيانات الأساسية
    df_exams = load_sheet("Exams")
    df_students = clean_data(load_sheet("Students"))
    df_grades = clean_data(load_sheet("Grades"))
    
    # بناء قائمة الشعب الشاملة
    all_sections = set()
    if not df_students.empty: all_sections.update(df_students['Section'].unique().tolist())
    try:
        df_sec_tab = clean_data(load_sheet("Sections"))
        if not df_sec_tab.empty: all_sections.update(df_sec_tab['Section_Name'].unique().tolist())
    except: pass
    final_sections = sorted([s for s in all_sections if str(s).lower() != 'nan' and str(s).strip() != ""])

    # --- مصفوفة النتائج ---
    if menu == "مصفوفة النتائج":
        st.header("📊 مصفوفة النتائج العامة")
        if not df_students.empty and not df_grades.empty:
            sel_sec = st.selectbox("تصفية حسب الشعبة", ["الكل"] + final_sections)
            filtered_stu = df_students[df_students['Section'] == sel_sec] if sel_sec != "الكل" else df_students
            
            # دمج الطلاب مع الدرجات
            df_merged = pd.merge(filtered_stu[['ID', 'Name']], df_grades, left_on='ID', right_on='Student_ID', how='left')
            
            if not df_merged['Exam_ID'].dropna().empty:
                # إنشاء المصفوفة (Pivot Table)
                matrix = df_merged.pivot_table(index='Name', columns='Exam_ID', values='Score', aggfunc='max').fillna('-')
                
                # تلوين الخلفية لأعلى درجات
                def highlight_max(s):
                    is_max = s == s.max() if s.dtype == np.number else [False]*len(s)
                    return ['background-color: #bbf7d0' if v else '' for v in is_max]

                st.dataframe(matrix.style.apply(highlight_max, axis=0), use_container_width=True)
                st.caption("تم تمييز الدرجة الأعلى في كل اختبار باللون الأخضر.")
            else: st.info("لم يتم تقديم أي اختبارات بعد.")
        else: st.warning("البيانات غير كافية لعرض المصفوفة (تأكد من وجود طلاب ودرجات).")

    # --- NEW: التحليلات والإحصائيات ---
    elif menu == "التحليلات والإحصائيات":
        st.header("📈 تحليلات الأداء للشعب والاختبارات")
        
        if not df_students.empty and not df_grades.empty:
            # دمج البيانات كاملة للتحليل
            df_full = pd.merge(df_grades, df_students, left_on='Student_ID', right_on='ID', how='inner')
            
            # --- الإحصائيات العامة (Key Metrics) ---
            st.subheader("أرقام رئيسية")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("عدد الطلاب", len(df_students))
            c2.metric("عدد الشعب", len(final_sections))
            c3.metric("عدد الاختبارات", len(df_grades['Exam_ID'].unique()))
            c4.metric("متوسط الدرجات العام", f"{df_grades['Score'].mean():.1f}")
            
            st.divider()
            
            t1, t2 = st.tabs(["تحليل الشعب الدراسيّة", "تحليل الاختبارات"])
            
            with t1:
                st.subheader("مقارنة أداء الشعب")
                
                # تجميع البيانات حسب الشعبة
                sec_analysis = df_full.groupby('Section').agg(
                    متوسط_الدرجة=('Score', 'mean'),
                    عدد_الطلاب=('ID', 'count'),
                    نسبة_النجاح=('Score', calculate_pass_rate)
                ).reset_index()
                
                chart_col1, chart_col2 = st.columns(2)
                
                # الرسم البياني 1: متوسط الدرجات حسب الشعبة (عمودي)
                with chart_col1:
                    fig_avg = px.bar(sec_analysis, x='Section', y='متوسط_الدرجة', 
                                    title='متوسط درجات الطلاب حسب الشعبة',
                                    labels={'متوسط_الدرجة': 'الدرجة (من 100)', 'Section': 'الشعبة'},
                                    text_auto='.1f',
                                    color='متوسط_الدرجة',
                                    color_continuous_scale=px.colors.sequential.Teal)
                    fig_avg.update_layout(xaxis_title="الشعبة الدراسيّة")
                    st.plotly_chart(fig_avg, use_container_width=True)
                
                # الرسم البياني 2: نسبة النجاح حسب الشعبة (أفقي)
                with chart_col2:
                    fig_pass = px.bar(sec_analysis, y='Section', x='نسبة_النجاح', 
                                     title='نسبة النجاح حسب الشعبة (%)',
                                     orientation='h',
                                     labels={'نسبة_النجاح': 'نسبة النجاح (%)', 'Section': 'الشعبة'},
                                     text_auto='.1f')
                    # إضافة خط أحمر عند درجة النجاح
                    fig_pass.add_vline(x=PASSING_SCORE, line_dash="dash", line_color="red", annotation_text="درجة النجاح")
                    st.plotly_chart(fig_pass, use_container_width=True)
                    
            with t2:
                st.subheader("تحليل الاختبارات")
                # تجميع البيانات حسب الاختبار
                exam_analysis = df_full.groupby('Exam_ID').agg(
                    المتوسط=('Score', 'mean'),
                    الأعلى=('Score', 'max'),
                    الأدنى=('Score', 'min'),
                    عدد_المتقدمين=('ID', 'count')
                ).reset_index()
                
                # تصفية لتنظيف أسماء الاختبارات
                exam_names = load_sheet("Exams")[['Exam_ID', 'Title']]
                exam_names['Exam_ID'] = exam_names['Exam_ID'].astype(str)
                exam_analysis = pd.merge(exam_analysis, exam_names, on='Exam_ID', how='left')
                exam_analysis['Title'] = exam_analysis['Title'].fillna(exam_analysis['Exam_ID'])

                # الرسم البياني 3: توزيع الدرجات في كل اختبار (Scatter plot/Box)
                fig_spread = px.scatter(df_full, x='Exam_ID', y='Score', color='Section',
                                      title='توزيع درجات الطلاب في الاختبارات حسب الشعب',
                                      labels={'Score': 'الدرجة', 'Exam_ID': 'رمز الاختبار'},
                                      hover_data=['Name'],
                                      opacity=0.6)
                st.plotly_chart(fig_spread, use_container_width=True)

        else: st.error("لا توجد بيانات درجات كافية لإجراء التحليل.")

    # --- إضافة اختبار جديد ---
    elif menu == "إضافة اختبار جديد":
        st.header("📝 إنشاء اختبار جديد")
        with st.form("exam_form_final"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_id = st.text_input("رمز الاختبار (Exam ID)")
                e_ti = st.text_input("عنوان الاختبار (Title)")
                s_date = st.date_input("تاريخ البدء", datetime.now())
                s_time = st.time_input("وقت البدء", datetime.now().time())
            with col_e2:
                e_du = st.number_input("المدة الزمنية (بالدقائق)", value=60)
                e_se = st.multiselect("الشعب المستهدفة", final_sections)
                n_date = st.date_input("تاريخ الانتهاء", datetime.now())
                n_time = st.time_input("وقت الانتهاء", datetime.now().time())
            
            e_ht = st.text_area("كود الاختبار (HTML Code)")
            if st.form_submit_button("حفظ الاختبار ونشره"):
                if not e_id or not e_ti or not e_se:
                    st.error("يرجى ملء كافة البيانات الأساسية (رمز، عنوان، وشعبة).")
                else:
                    try:
                        old_ex = load_sheet("Exams")
                        new_row = pd.DataFrame([{
                            "Exam_ID": str(e_id).strip(), "Title": str(e_ti).strip(), 
                            "Section": ",".join(e_se), "Duration": e_du,
                            "Start_DateTime": f"{s_date} {s_time}",
                            "End_DateTime": f"{n_date} {n_time}",
                            "HTML_Code": e_ht, "Status": "Active"
                        }])
                        updated_ex = pd.concat([old_ex, new_row], ignore_index=True)
                        conn.update(worksheet="Exams", data=updated_ex)
                        st.success("تم حفظ الاختبار بنجاح!"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"حدث خطأ أثناء الحفظ: {e}")

    # --- إدارة النظام (شعب وطلاب) ---
    elif menu == "إدارة النظام":
        st.header("⚙️ إدارة الطلاب والشعب")
        t1, t2 = st.tabs(["➕ إضافة شعبة جديدة", "👤 تسجيل طالب جديد"])
        with t1:
            with st.form("sec"):
                n_s = st.text_input("اسم الشعبة الجديدة")
                if st.form_submit_button("حفظ الشعبة"):
                    if n_s:
                        old = load_sheet("Sections")
                        upd = pd.concat([old, pd.DataFrame([{"Section_Name": n_s.strip()}])], ignore_index=True)
                        conn.update(worksheet="Sections", data=upd)
                        st.success("تمت الإضافة!"); time.sleep(1); st.rerun()
        with t2:
            with st.form("stu"):
                col1, col2 = st.columns(2)
                with col1:
                    s_n = st.text_input("اسم الطالب")
                    s_i = st.text_input("الرقم التعريفي (ID)")
                with col2:
                    s_s = st.selectbox("الشعبة", final_sections)
                    s_p = st.text_input("كلمة المرور", value=str(random.randint(100000, 999999)))
                if st.form_submit_button("تسجيل الطالب"):
                    if s_n and s_i:
                        old = load_sheet("Students")
                        if not old.empty and s_i in old['ID'].astype(str).tolist():
                            st.error("الرقم التعريفي موجود مسبقاً.")
                        else:
                            upd = pd.concat([old, pd.DataFrame([{"ID": s_i, "Name": s_n, "Password": s_p, "Section": s_s}])], ignore_index=True)
                            conn.update(worksheet="Students", data=upd)
                            st.success("تم تسجيل الطالب بنجاح!"); time.sleep(1); st.rerun()

# --- 7. لوحة الطالب ---
elif st.session_state.role == 'student':
    u = st.session_state.user
    # تحميل البيانات
    with st.spinner("جاري تحميل بياناتك..."):
        df_ex_stu = load_sheet("Exams")
        df_gr_stu = clean_data(load_sheet("Grades"))
        
        # تصفية الدرجات الخاصة بهذا الطالب
        my_grades = df_gr_stu[df_gr_stu['Student_ID'] == str(u['ID'])]

    if st.session_state.exam is None:
        st.title(f"👋 مرحباً بك، {u['Name']}")
        st.caption(f"الشعبة: {u['Section']}")
        
        # أزرار سريعة
        col_log1, col_log2 = st.sidebar.columns(2)
        with col_log2:
            if st.sidebar.button("تسجيل الخروج"):
                st.session_state.update({'auth': False, 'user': None, 'role': None})
                st.rerun()

        tab1, tab2, tab3 = st.tabs(["📋 الاختبارات المطلوبة", "✅ الاختبارات السابقة", "📊 تحليل مستواي"])

        with tab1:
            st.subheader("الاختبارات المتاحة حالياً")
            if not df_ex_stu.empty:
                # فلترة ذكية: حالة "نشط" + شعبة الطالب موجودة في قائمة شعب الاختبار
                required = df_ex_stu[(df_ex_stu['Status'] == 'Active') & (df_ex_stu['Section'].str.contains(str(u['Section']), na=False))]
                
                # منع تكرار الاختبار (حذف الاختبارات التي تم تقديمها بالفعل)
                taken_ids = my_grades['Exam_ID'].unique().tolist()
                required = required[~required['Exam_ID'].astype(str).isin(map(str, taken_ids))]

                if required.empty:
                    st.success("🎉 أحسنت! لقد أنجزت جميع الاختبارات المطلوبة حالياً.")
                else:
                    for _, ex in required.iterrows():
                        with st.container():
                            st.markdown(f'<div class="exam-card"><h4>{str(ex["Title"])}</h4></div>', unsafe_allow_html=True)
                            if st.button("بدء الاختبار الآن 🚀", key=ex['Exam_ID']):
                                st.session_state.exam = ex.to_dict()
                                st.session_state.start_t = time.time()
                                st.rerun()
            else: st.info("لا توجد اختبارات مجدولة حالياً.")

        with tab2:
            st.subheader("سجل اختباراتك المنتهية")
            if not my_grades.empty:
                # تجميل الجدول قليلاً
                display_grades = my_grades.copy()
                # جلب عناوين الاختبارات
                if not df_ex_stu.empty:
                    display_grades = pd.merge(display_grades, df_ex_stu[['Exam_ID', 'Title']], on='Exam_ID', how='left')
                
                # ترتيب حسب الأحدث
                st.dataframe(display_grades[['Title', 'Score']].sort_index(ascending=False), use_container_width=True)
            else: st.info("لم تقم بتأدية أي اختبارات بعد.")
            
        # --- NEW: تحليل مستواى الطالب ---
        with tab3:
            st.subheader("تحليل الأداء والتطور")
            
            if not my_grades.empty and not df_gr_stu.empty:
                # 1. تنظيف ودمج البيانات للحصول على عناوين الاختبارات وتواريخها
                analysis_grades = my_grades.copy()
                analysis_grades['Score'] = pd.to_numeric(analysis_grades['Score'])
                
                # جلب التواريخ من ورقة الاختبارات (إذا توفرت)
                exams_dates = df_ex_stu[['Exam_ID', 'Start_DateTime']].copy()
                exams_dates['Exam_ID'] = exams_dates['Exam_ID'].astype(str)
                analysis_grades = pd.merge(analysis_grades, exams_dates, on='Exam_ID', how='left')
                
                # ترتيب البيانات حسب التاريخ (أو حسب الـ index إذا لم يتوفر التاريخ)
                if 'Start_DateTime' in analysis_grades.columns and not analysis_grades['Start_DateTime'].isna().all():
                     analysis_grades = analysis_grades.sort_values('Start_DateTime')
                
                # 2. حساب المتوسط العام للشعبة (للمقارنة)
                # دمج كل الدرجات مع بيانات الطلاب لمعرفة الشعب
                all_students_grades = pd.merge(df_gr_stu, load_sheet("Students")[['ID', 'Section']], left_on='Student_ID', right_on='ID', how='inner')
                my_section_grades = all_students_grades[all_students_grades['Section'] == u['Section']]
                
                # حساب متوسط كل اختبار في شعبة الطالب
                sec_exam_means = my_section_grades.groupby('Exam_ID')['Score'].mean().reset_index().rename(columns={'Score': 'Section_Average'})
                
                # دمج متوسط الشعبة مع درجات الطالب
                analysis_final = pd.merge(analysis_grades, sec_exam_means, on='Exam_ID', how='left')

                # --- الإحصائيات الرئيسية للطالب ---
                c1, c2, c3 = st.columns(3)
                c1.metric("عدد الاختبارات", len(analysis_final))
                c2.metric("متوسط درجتك", f"{analysis_final['Score'].mean():.1f}")
                
                # تحديد مستوى
                avg_score = analysis_final['Score'].mean()
                status = "ممتاز" if avg_score >= 90 else "جيد جداً" if avg_score >= 75 else "جيد" if avg_score >= PASSING_SCORE else "يحتاج تحسين"
                c3.metric("المستوى التقريبي", status)
                
                st.divider()
                
                # --- الرسم البياني للطالب: خط الزمن ---
                # نستخدم عنوان الاختبار (أو الرمز إذا لم يوجد) للمحور الأفقي
                exam_titles = df_ex_stu[['Exam_ID', 'Title']].copy()
                analysis_final = pd.merge(analysis_final, exam_titles, on='Exam_ID', how='left')
                analysis_final['Title'] = analysis_final['Title'].fillna(analysis_final['Exam_ID'])

                # إعادة تشكيل البيانات لسهولة رسم خطين
                long_df = pd.melt(analysis_final, id_vars=['Title'], value_vars=['Score', 'Section_Average'],
                                  var_name='Type', value_name='Value')
                
                long_df['Type'] = long_df['Type'].map({'Score': 'درجتك', 'Section_Average': 'متوسط الشعبة'})

                # رسم بياني خطي
                fig_timeline = px.line(long_df, x='Title', y='Value', color='Type',
                                      title='تطور مستواك مقارنة بمتوسط زملائك في الشعبة',
                                      markers=True,
                                      labels={'Value': 'الدرجة', 'Title': 'الاختبار', 'Type': 'البيان'},
                                      color_discrete_map={'درجتك': '#007bff', 'متوسط الشعبة': '#d9534f'}) # أزرق للطلاب، أحمر للمتوسط
                
                fig_timeline.update_layout(yaxis_range=[0, 105]) # تثبيت المحور الرأسي
                
                st.plotly_chart(fig_timeline, use_container_width=True)

            else:
                st.info("لا توجد بيانات درجات كافية لعرض التحليل البياني.")

    # --- 8. مشغل الامتحان (HTML Viewer & Timer) ---
    else:
        ex = st.session_state.exam
        st.title(f"الاختبار: {str(ex['Title'])}")
        
        # حساب الوقت المتبقي
        elapsed = time.time() - st.session_state.start_t
        duration_seconds = int(float(ex['Duration'])) * 60
        remaining = duration_seconds - elapsed
        
        if remaining <= 0:
            st.error("⚠️ انتهى الوقت المحدد للاختبار!")
            st.components.v1.html("<h2>انتهى الوقت، يرجى إغلاق الصفحة. (تأكد من ضغط 'إرسال' داخل نموذج الاختبار إذا كان متاحاً)</h2>", height=200)
            if st.button("العودة للرئيسية"): st.session_state.exam = None; st.rerun()
        else:
            # عرض المؤقت
            mins, secs = divmod(int(remaining), 60)
            st.markdown(f'<div class="timer-box">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            
            # حقن بيانات الطالب والدراسة في كود الـ HTML
            # الـ HTML يجب أن يحتوي على هذه الكلمات الدلالية لتمكين الاستبدال
            final_html = str(ex['HTML_Code']).replace("STUDENT_ID_HERE", str(u['ID']))
            final_html = final_html.replace("STUDENT_NAME_HERE", str(u['Name']))
            final_html = final_html.replace("EXAM_ID_HERE", str(ex['Exam_ID']))
            
            # عرض الاختبار داخل IFrame
            st.components.v1.html(final_html, height=800, scrolling=True)
            
            st.info("💡 يتم تسجيل درجتك أوتوماتيكياً في قاعدة البيانات بمجرد ضغط زر 'إرسال' داخل نافذة الاختبار.")
            if st.button("⬅️ خروج من الاختبار دون تسليم (للضرورة)"): 
                if st.confirm("هل أنت متأكد من الخروج؟ قد يؤثر ذلك على فرصتك في تأدية الاختبار."):
                    st.session_state.exam = None; st.rerun()
