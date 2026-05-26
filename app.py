import streamlit as st
import pandas as pd
import random
import html
import requests
import json

# 设置网页标题和布局（针对手机端优化）
st.set_page_config(
    page_title="极速无广告刷题库",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 强制注入手机端防卡顿、防闪烁的 CSS 样式
st.markdown("""
    <style>
    /* 减少手机端不必要的白边和内边距 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    /* 优化手机端按钮点击态 */
    button {
        active-background-color: #f0f2f6 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 我的专属无广告刷题库")

# ================= 1. 初始化 Session State =================
if "raw_questions" not in st.session_state:
    st.session_state.raw_questions = []  
if "questions" not in st.session_state:
    st.session_state.questions = []      
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "score_submitted" not in st.session_state:
    st.session_state.score_submitted = False
if "current_file_key" not in st.session_state:
    st.session_state.current_file_key = ""
if "current_mode" not in st.session_state:
    st.session_state.current_mode = ""
if "ai_explanations" not in st.session_state:
    st.session_state.ai_explanations = {}  

# ================= 2. 极致性能回调函数 =================
def prev_q():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

def next_q():
    if st.session_state.current_index < len(st.session_state.questions) - 1:
        st.session_state.current_index += 1

def save_ans_callback(idx, widget_key):
    st.session_state.user_answers[idx] = st.session_state[widget_key]

def challenge_ans_callback(idx, widget_key, correct_letter):
    selected_val = st.session_state[widget_key]
    st.session_state.user_answers[idx] = selected_val
    if selected_val:
        user_letter = selected_val[0]
        if user_letter == correct_letter:
            if st.session_state.current_index < len(st.session_state.questions) - 1:
                st.session_state.current_index += 1

def submit_exam_callback():
    st.session_state.score_submitted = True

# ================= 3. AI 中转站流式请求 =================
def get_ai_stream(api_key, base_url, model, prompt):
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {
                "role": "system", 
                "content": "你是一位拥有20年教学经验的星级金牌辅导老师，解析题目条理清晰、言简意赅。"
            },
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=15)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8').lstrip('data: ').strip()
                if decoded_line == '[DONE]':
                    break
                try:
                    json_data = json.loads(decoded_line)
                    delta = json_data['choices'][0]['delta']
                    if 'content' in delta:
                        yield delta['content']
                except Exception:
                    continue
    except Exception as e:
        yield f"❌ AI 解析调用失败。请确认API配置或网络。错误: {str(e)}"

# ================= 4. 解析 Excel 题库 (仅执行一次) =================
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库", type=["xlsx"])

if uploaded_file:
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    
    if st.session_state.current_file_key != file_key:
        with st.spinner("⚡ 正在极速解析题库..."):
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(col).strip() for col in df.columns]
            
            q_col = next((c for c in df.columns if "题干" in c), None)
            ans_col = next((c for c in df.columns if "正确答案" in c or "答案" in c), None)
            analysis_col = next((c for c in df.columns if "解析" in c), None)
            
            opt_cols = {}
            for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                col_name = next((c for c in df.columns if f"选项 {letter}" in c or f"选项{letter}" in c), None)
                if col_name:
                    opt_cols[letter] = col_name

            if not q_col: q_col = df.columns[0]
            if not ans_col: ans_col = df.columns[-1]

            cleaned_records = []
            for _, row in df.iterrows():
                def clean_text(val):
                    if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
                        return ""
                    return html.unescape(str(val).strip())

                item = {
                    "题目": clean_text(row.get(q_col, "")),
                    "答案": clean_text(row.get(ans_col, "")).upper(),
                    "解析": clean_text(row.get(analysis_col, "暂无解析")),
                }
                for letter, col_name in opt_cols.items():
                    item[letter] = clean_text(row.get(col_name, ""))
                cleaned_records.append(item)
            
            st.session_state.raw_questions = cleaned_records
            st.session_state.current_file_key = file_key
            st.session_state.questions = []
            st.session_state.current_index = 0
            st.session_state.user_answers = {}
            st.session_state.score_submitted = False
            st.session_state.ai_explanations = {}

    # ================= 5. 侧边栏刷题设置及 AI 配置 =================
    st.sidebar.header("⚙️ 刷题设置")
    
    mode = st.sidebar.radio(
        "选择刷题模式：", 
        ["📖 1. 背题模式 (直接看选项和答案)", 
         "🔥 2. 挑战模式 (即时答题反馈对错)", 
         "📝 3. 模拟考试 (统一交卷评测分)"]
    )
    
    if st.session_state.current_mode != mode:
        st.session_state.current_mode = mode
        st.session_state.questions = []
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        st.session_state.ai_explanations = {}

    if "模拟考试" in mode:
        exam_scope = st.sidebar.selectbox("考试范围选项：", ["随机抽题测试", "全量试卷测试"])
        if exam_scope == "随机抽题测试":
            num_questions = st.sidebar.number_input("抽取题目数量：", min_value=1, max_value=len(st.session_state.raw_questions), value=min(20, len(st.session_state.raw_questions)))
        else:
            num_questions = len(st.session_state.raw_questions)
    else:
        num_questions = len(st.session_state.raw_questions)
        order_opt = st.sidebar.selectbox("题目顺序：", ["顺序刷题", "打乱顺序"])

    st.sidebar.divider()
    st.sidebar.header("🤖 AI 智能解析助手")
    enable_ai = st.sidebar.checkbox("开启 AI 智能解析功能", value=False)
    
    api_key = ""
    base_url = ""
    model_name = ""
    
    if enable_ai:
        api_key = st.sidebar.text_input("AI API Key (密钥)：", type="password")
        base_url = st.sidebar.text_input("中转站 API Base URL：", value="https://api.openai.com/v1")
        model_name = st.sidebar.text_input("模型名称 (Model)：", value="gpt-4o-mini")

    if st.sidebar.button("🎯 确认/开始重置") or not st.session_state.questions:
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        st.session_state.ai_explanations = {}
        
        if "模拟考试" in mode:
            if exam_scope == "随机抽题测试":
                st.session_state.questions = random.sample(st.session_state.raw_questions, num_questions)
            else:
                st.session_state.questions = st.session_state.raw_questions.copy()
        else:
            if order_opt == "打乱顺序":
                st.session_state.questions = random.sample(st.session_state.raw_questions, len(st.session_state.raw_questions))
            else:
                st.session_state.questions = st.session_state.raw_questions.copy()
            
        st.sidebar.success(f"已成功加载 {len(st.session_state.questions)} 道题！")

    # ================= 6. 📱 手机端终极武器：核心局部渲染碎片 =================
    # 这一块被 @st.fragment 装饰后，点击切题、选项，整个侧边栏和上传组件都不会刷新，提速10倍！
    @st.fragment
    def render_quiz_area():
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        
        # 进度条
        progress = (idx + 1) / len(q_list)
        st.progress(progress)
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 题干
        st.info(f"**题目：** {q['题目']}")
        
        # 选项
        options = []
        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            val = q.get(opt, "")
            if val:
                options.append(f"{opt}. {val}")
        
        correct_letter = str(q.get('答案', '')).strip().upper()
        if correct_letter.endswith(".0"):
            correct_letter = correct_letter[0]

        show_ai_button = False  

        # 1. 背题模式
        if "背题模式" in mode:
            correct_index = next((i for i, o in enumerate(options) if o.startswith(correct_letter)), None)
            st.radio("题目选项：", options, index=correct_index, disabled=True, key=f"read_{idx}")
            st.success(f"🎯 **正确答案：** {correct_letter}")
            st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
            show_ai_button = True  

        # 2. 挑战模式
        elif "挑战模式" in mode:
            saved_ans = st.session_state.user_answers.get(idx, None)
            widget_key = f"challenge_{idx}"
            
            selected = st.radio(
                "请选择您的答案：", 
                options, 
                index=options.index(saved_ans) if saved_ans in options else None, 
                key=widget_key,
                on_change=challenge_ans_callback,
                args=(idx, widget_key, correct_letter)
            )
            
            if selected:
                user_letter = selected[0]
                if user_letter != correct_letter:
                    st.error(f"❌ 回答错误！您选择了 {user_letter}，正确答案是：{correct_letter}")
                    st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
                    show_ai_button = True  
                elif idx == len(q_list) - 1:
                    st.balloons()
                    st.success("🎉 恭喜您通关本套题库！")
                    st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
                    show_ai_button = True

        # 3. 模拟考试
        elif "模拟考试" in mode:
            saved_ans = st.session_state.user_answers.get(idx, None)
            widget_key = f"exam_{idx}"
            
            st.radio(
                "请选择您的答案：", 
                options, 
                index=options.index(saved_ans) if saved_ans in options else None, 
                key=widget_key,
                on_change=save_ans_callback,
                args=(idx, widget_key)
            )

        # 🤖 AI 解析模块
        if enable_ai and show_ai_button:
            st.write("---")
            if idx not in st.session_state.ai_explanations:
                if st.button("✨ 召唤 AI 名师深度解析", type="secondary", use_container_width=True):
                    if not api_key:
                        st.error("⚠️ 请先在侧边栏配置 AI API Key！")
                    else:
                        prompt = f"""
                        请深度解析以下选择题：
                        【题目】 {q['题目']}
                        【选项】 {"/".join(options)}
                        【正确答案】 {correct_letter}
                        【官方简析】 {q.get('解析', '无')}
                        请帮我拆解：1.核心考点 2.正确项剖析 3.错项分析 4.秒记绝招。
                        """
                        explanation_placeholder = st.empty()
                        full_response = ""
                        
                        for chunk in get_ai_stream(api_key, base_url, model_name, prompt):
                            full_response += chunk
                            explanation_placeholder.markdown(
                                f"""
                                <div style="background-color:#f0f8ff; padding:12px; border-radius:8px; border-left: 5px solid #1E90FF; font-size:14px;">
                                🤖 <b>AI 名师深度复盘中：</b><br><br>{full_response}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                        st.session_state.ai_explanations[idx] = full_response
            else:
                st.markdown(
                    f"""
                    <div style="background-color:#f0f8ff; padding:12px; border-radius:8px; border-left: 5px solid #1E90FF; font-size:14px;">
                    🤖 <b>AI 名师深度解析：</b><br><br>{st.session_state.ai_explanations[idx]}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

        st.write("") 

        # 底部翻页按键（轻量化事件触发）
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("⬅️ 上一题", on_click=prev_q, disabled=(idx == 0), use_container_width=True)
        with col2:
            st.button("➡️ 下一题", on_click=next_q, disabled=(idx == len(q_list) - 1), use_container_width=True)
        with col3:
            if "模拟考试" in mode and not st.session_state.score_submitted:
                st.button("📝 提交试卷", on_click=submit_exam_callback, type="primary", use_container_width=True)

    # 运行答题区组件
    if st.session_state.questions:
        render_quiz_area()

        # ================= 7. 模拟考试结算 (不在局部组件里，交卷后渲染) =================
        if "模拟考试" in mode and st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            correct_count = 0
            wrong_questions = []
            all_results = []
            q_list = st.session_state.questions
            
            for i, question in enumerate(q_list):
                user_ans = st.session_state.user_answers.get(i, "未作答")
                user_letter = user_ans[0] if user_ans != "未作答" else "无"
                
                c_letter = str(question.get('答案', '')).strip().upper()
                if c_letter.endswith(".0"):
                    c_letter = c_letter[0]
                
                is_correct = (user_letter == c_letter)
                if is_correct:
                    correct_count += 1
                
                result_item = {
                    "index": i + 1,
                    "question": question,
                    "user_letter": user_letter,
                    "correct_letter": c_letter,
                    "is_correct": is_correct
                }
                all_results.append(result_item)
                if not is_correct:
                    wrong_questions.append(result_item)

            score = round((correct_count / len(q_list)) * 100, 1)
            st.metric(
                label="最终得分", 
                value=f"{score} 分", 
                delta=f"答对 {correct_count} / {len(q_list)} 题 (答错/未答 {len(wrong_questions)} 题)"
            )
            
            items_per_page = 20
            tab1, tab2 = st.tabs(["❌ 错题本 (复习用)", "📖 完整试卷报告"])
            
            with tab1:
                if len(wrong_questions) == 0:
                    st.balloons()
                    st.success("太棒了！您拿到了满分！🎉")
                else:
                    total_wrongs = len(wrong_questions)
                    num_wrong_pages = (total_wrongs - 1) // items_per_page + 1
                    
                    if num_wrong_pages > 1:
                        w_page = st.selectbox(
                            "错题页码：", 
                            range(1, num_wrong_pages + 1), 
                            format_func=lambda x: f"第 {x} 页"
                        )
                    else:
                        w_page = 1
                    
                    start_w = (w_page - 1) * items_per_page
                    end_w = start_w + items_per_page
                    
                    for w in wrong_questions[start_w:end_w]:
                        with st.expander(f"🔴 第 {w['index']} 题 ( 选: {w['user_letter']} | 答: {w['correct_letter']} )"):
                            st.write(f"**题目：** {w['question']['题目']}")
                            for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                                if w['question'].get(opt):
                                    st.write(f"- {opt}: {w['question'][opt]}")
                            st.error(f"你的答案：`{w['user_letter']}` ❌")
                            st.success(f"正确答案：`{w['correct_letter']}` ✅")
                            st.warning(f"💡 解析：{w['question'].get('解析', '暂无解析')}")
            
            with tab2:
                total_all = len(all_results)
                num_all_pages = (total_all - 1) // items_per_page + 1
                
                if num_all_pages > 1:
                    a_page = st.selectbox(
                        "报告页码：", 
                        range(1, num_all_pages + 1), 
                        format_func=lambda x: f"第 {x} 页"
                    )
                else:
                    a_page = 1
                
                start_a = (a_page - 1) * items_per_page
                end_a = start_a + items_per_page
                
                for r in all_results[start_a:end_a]:
                    status_icon = "✅ 正确" if r['is_correct'] else "❌ 错误"
                    with st.expander(f"第 {r['index']} 题：{status_icon} (选: {r['user_letter']} | 答: {r['correct_letter']})"):
                        st.write(f"**题目：** {r['question']['题目']}")
                        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                            if r['question'].get(opt):
                                st.write(f"- {opt}: {r['question'][opt]}")
                        st.write(f"**您的答案：** {r['user_letter']} | **正确答案：** {r['correct_letter']}")
                        st.write(f"**解析：** {r['question'].get('解析', '暂无解析')}")
            
            def restart_exam():
                st.session_state.current_index = 0
                st.session_state.user_answers = {}
                st.session_state.score_submitted = False
                st.session_state.ai_explanations = {}
                
            st.button("🔄 重新开始考试", on_click=restart_exam, use_container_width=True)
