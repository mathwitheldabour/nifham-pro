import streamlit as st
import random
import time
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. إعداد الصفحة وتجهيز الحالة
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Math Quiz - Calculus", layout="wide")

# تهيئة المتغيرات
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True
    st.session_state['current_q_index'] = 0
    st.session_state['answers'] = {} 
    st.session_state['quiz_submitted'] = False
    st.session_state['start_time'] = datetime.now()
    
    # --- بنك الأسئلة ---
    raw_questions = [
        {
            "type": "Polynomial",
            "latex": r"f(x) = x^3 - 3x^2 + 5",
            "q_en": "Determine the intervals where the graph is concave upward.",
            "q_ar": "حدد الفترات التي يكون فيها منحنى الدالة مقعراً لأعلى.",
            "options": [
                r"(1, \infty)", 
                r"(-\infty, 1)", 
                r"(-\infty, \infty)", 
                r"(0, 2)"
            ],
            "correct_option": r"(1, \infty)"
        },
        {
            "type": "Rational",
            "latex": r"f(x) = \frac{1}{x^2 + 1}",
            "q_en": "Find the x-coordinates of the inflection points.",
            "q_ar": "أوجد الإحداثيات السينية لنقاط الانقلاب.",
            "options": [
                r"x = \pm \frac{1}{\sqrt{3}}", 
                r"x = \pm 1", 
                r"x = 0", 
                r"\text{No inflection points}"
            ],
            "correct_option": r"x = \pm \frac{1}{\sqrt{3}}"
        },
        {
            "type": "Exponential",
            "latex": r"f(x) = x e^x",
            "q_en": "Determine the interval where the function is concave downward.",
            "q_ar": "حدد الفترة التي تكون فيها الدالة مقعرة لأسفل.",
            "options": [
                r"(-\infty, -2)", 
                r"(-2, \infty)", 
                r"(-1, \infty)", 
                r"(-\infty, 0)"
            ],
            "correct_option": r"(-\infty, -2)"
        },
        {
            "type": "Radical",
            "latex": r"f(x) = \sqrt[3]{x} - 1",
            "q_en": "Identify the inflection point.",
            "q_ar": "حدد نقطة الانقلاب.",
            "options": [
                r"(0, -1)", 
                r"(1, 0)", 
                r"(0, 0)", 
                r"\text{Undefined}"
            ],
            "correct_option": r"(0, -1)"
        },
        {
            "type": "Polynomial",
            "latex": r"f(x) = x^4 - 4x^3",
            "q_en": "Find the intervals of downward concavity.",
            "q_ar": "أوجد فترات التقعر لأسفل.",
            "options": [
                r"(0, 2)", 
                r"(-\infty, 0) \cup (2, \infty)", 
                r"(2, \infty)", 
                r"(-\infty, 2)"
            ],
            "correct_option": r"(0, 2)"
        }
    ]
    
    random.shuffle(raw_questions)
    
    processed_questions = []
    for q in raw_questions:
        opts = q['options'].copy()
        random.shuffle(opts)
        processed_questions.append({
            "latex": q['latex'],
            "q_en": q['q_en'],
            "q_ar": q['q_ar'],
            "options": opts,
            "correct_val": q['correct_option']
        })
    
    st.session_state['questions'] = processed_questions

questions = st.session_state['questions']
total_q = len(questions)

# -----------------------------------------------------------------------------
# 2. CSS Styles
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
    }
    .bilingual-header {
        display: flex;
        justify_content: space-between;
        align-items: center;
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
    }
    .text-left { text-align: left; width: 48%; direction: ltr; font-weight: bold; }
    .text-right { text-align: right; width: 48%; direction: rtl; font-weight: bold; }
    
    .math-box {
        text-align: center;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        background-color: #fff;
    }
    
    .floating-timer {
        position: fixed; top: 60px; right: 20px;
        background-color: #ff4b4b; color: white;
        padding: 8px 16px; border-radius: 20px;
        font-weight: bold; z-index: 9999;
    }
    
    /* تنسيق خاص لبطاقات الاختيار */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border-radius: 10px;
        transition: transform 0.2s;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Timer Logic
# -----------------------------------------------------------------------------
QUIZ_DURATION = 10 * 60 

def get_time_remaining():
    elapsed = (datetime.now() - st.session_state['start_time']).total_seconds()
    remaining = QUIZ_DURATION - elapsed
    return max(0, int(remaining))

time_left = get_time_remaining()
mins, secs = divmod(time_left, 60)
timer_display = f"{mins:02d}:{secs:02d}"

st.markdown(f'<div class="floating-timer">⏱ {timer_display}</div>', unsafe_allow_html=True)

if time_left == 0 and not st.session_state['quiz_submitted']:
    st.warning("انتهى الوقت!")
    st.session_state['quiz_submitted'] = True
    st.rerun()

# -----------------------------------------------------------------------------
# 4. Main App Logic
# -----------------------------------------------------------------------------
st.title("📝 Calculus Quiz: Concavity & Inflection Points")
st.markdown("---")

# Navigation Functions
def go_to_question(index):
    st.session_state['current_q_index'] = index

def select_option(q_idx, option_val):
    st.session_state['answers'][q_idx] = option_val

def submit_quiz():
    st.session_state['quiz_submitted'] = True

# Navigation Bar
if not st.session_state['quiz_submitted']:
    st.write("**Navigation / تصفح الأسئلة:**")
    cols = st.columns(total_q)
    for i in range(total_q):
        label = f"Q{i+1}"
        if i in st.session_state['answers']:
            label += " ✅"
        
        # Highlight current question
        type_ = "primary" if i == st.session_state['current_q_index'] else "secondary"
        if cols[i].button(label, key=f"nav_{i}", type=type_, use_container_width=True):
            go_to_question(i)
            st.rerun()
    st.markdown("---")

# -----------------------------------------------------------------------------
# 5. Question Display (The Fix)
# -----------------------------------------------------------------------------

if st.session_state['quiz_submitted']:
    # --- Results View ---
    st.header("النتائج النهائية | Final Results")
    
    score = 0
    for i, q in enumerate(questions):
        user_ans = st.session_state['answers'].get(i, None)
        correct_ans = q['correct_val']
        is_correct = (user_ans == correct_ans)
        if is_correct: score += 1
            
        st.markdown(f"### Question {i+1}")
        st.latex(q['latex'])
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("Your Answer:")
            if user_ans: st.latex(user_ans)
            else: st.write("No Answer")
        with c2:
            if is_correct: st.success("Correct Answer:")
            else: st.error("Correct Answer:")
            st.latex(correct_ans)
        st.divider()
    
    pct = (score / total_q) * 100
    st.metric("Final Score", f"{pct}%", f"{score}/{total_q}")
    
    if st.button("Start New Quiz"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

else:
    # --- Current Question View ---
    curr_idx = st.session_state['current_q_index']
    curr_q = questions[curr_idx]
    
    # 1. Header
    st.markdown(f"""
    <div class="bilingual-header">
        <div class="text-left">Q{curr_idx+1}: {curr_q['q_en']}</div>
        <div class="text-right">{curr_q['q_ar']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Equation
    st.markdown('<div class="math-box">', unsafe_allow_html=True)
    st.latex(curr_q['latex'])
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 3. Options (Using Card Layout for MathJax Support)
    st.write("### اختر الإجابة الصحيحة | Select the correct answer:")
    
    # نستخدم شبكة 2x2
    col1, col2 = st.columns(2)
    opt_cols = [col1, col2] # للتبديل بين العمودين
    
    current_selection = st.session_state['answers'].get(curr_idx)
    
    for idx, option in enumerate(curr_q['options']):
        # تحديد العمود (يسار ثم يمين)
        with opt_cols[idx % 2]:
            # هل هذا الخيار هو المختار حالياً؟
            is_selected = (current_selection == option)
            
            # نستخدم Container لعمل إطار حول الخيار
            # إذا كان مختاراً، نستخدم حدوداً مميزة (سنحاكي ذلك بلون الزر)
            border_color = "red" if is_selected else "grey"
            
            with st.container(border=True):
                # 1. عرض المعادلة بشكل نظيف جداً باستخدام st.latex
                st.latex(option)
                
                # 2. زر الاختيار أسفل المعادلة
                btn_label = "✅ تم الاختيار" if is_selected else "اختيار | Select"
                btn_type = "primary" if is_selected else "secondary"
                
                # مفتاح فريد لكل زر
                if st.button(btn_label, key=f"q{curr_idx}_opt{idx}", type=btn_type, use_container_width=True):
                    select_option(curr_idx, option)
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Footer Navigation
    c1, c2, c3 = st.columns([1, 2, 1])
    if curr_idx > 0:
        if c1.button("⬅️ Previous", use_container_width=True):
            go_to_question(curr_idx - 1)
            st.rerun()
    if curr_idx < total_q - 1:
        if c3.button("Next ➡️", use_container_width=True):
            go_to_question(curr_idx + 1)
            st.rerun()
            
    st.markdown("---")
    if st.button("Submit Quiz | إنهاء الاختبار", type="primary", use_container_width=True):
        submit_quiz()
        st.rerun()