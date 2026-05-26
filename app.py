import streamlit as st
import pandas as pd
import random
import html
import requests
import json

# 设置网页标题和布局
st.set_page_config(
    page_title="极速无广告刷题库",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入手机端优化 CSS
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    div[data-testid="stMarkdownContainer"] p {
        font-size: 16px !important;
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

# 挑战模式单选/判断回调
def challenge_single_callback(idx, widget_key, correct_letter):
    selected_val = st.session_state[widget_key]
    if selected_val:
        user_letter = selected_val[0]
        st.session_state.user_answers[idx] = user_letter
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
            {"role": "system", "content": "你是一位拥有20年教学经验的金牌辅导老师，解析题目逻辑严密，直击考点。"},
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
        yield f"❌ AI 解析失败。错误: {str(e)}"

# ================= 4. 智能解析并清洗题库 =================
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库", type=["xlsx"])

if uploaded_file:
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    
    if st.session_state.current_file_key != file_key:
        with st.spinner("⚡ 正在极速解析并分类智能题型..."):
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

                raw_ans = clean_text(row.get(ans_col, "")).upper()
                
                # 1. 智能识别判断题
                is_tf = raw_ans in ["对", "错", "正确", "错误", "T", "F", "√", "×"]
                
                # 2. 获取选项内容，检查是否有预设选项
                opts = {}
                has_options = False
                for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                    val = clean_text(row.get(opt_cols.get(letter, ''), ""))
                    if val:
                        opts[letter] = val
                        has_options = True

                # 3. 确定最终题型
                if is_tf or not has_options:
                    q_type = "判断题"
                    # 规范化判断题答案：对/正确/T/√ -> A; 错/错误/F/× -> B
                    final_ans = "A" if raw_ans in ["对", "正确", "T", "√"] else "B"
                    if "A" not in opts or not opts["A"]:
                        opts["A"] = "正确"
                    if "B" not in opts or not opts["B"]:
                        opts["B"] = "错误"
                else:
                    # 清洗出纯净的字母答案集合
                    clean_letters = "".join([c for c in raw_ans if c in "ABCDEFGH"])
                    if len(clean_letters) > 1:
                        q_type = "多选题"
                        final_ans = "".join(sorted(list(set(clean_letters)))) # 去重排序，如 BCA -> ABC
                    else:
                        q_type = "单选题"
                        final_ans = clean_letters

                item = {
                    "题型": q_type,
                    "题目": clean_text(row.get(q_col, "")),
                    "答案": final_ans,
                    "解析": clean_text(row.get(analysis_col, "暂无解析")),
                }
                for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                    item[letter] = opts.get(letter, "")
                
                cleaned_records.append(item)
            
            st.session_state.raw_questions = cleaned_records
            st.session_state.current_file_key = file_key
            st.session_state.questions = []
            st.session_state.current_index = 0
            st.session_state.user_answers = {}
            st.session_state.score_submitted = False
            st.session_state.ai_explanations = {}

    # ================= 5. 侧边栏刷题设置 =================
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
        api_key = st.sidebar.text_input("AI API Key：", type="password")
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

    # ================= 6. 📱 局部渲染答题区 =================
    @st.fragment
    def render_quiz_area():
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        q_type = q.get("题型", "单选题")
        
        # 进度条
        progress = (idx + 1) / len(q_list)
        st.progress(progress)
        
        # 题型徽章展示
        badge_color = "#1E90FF" if q_type == "单选题" else ("#FF4500" if q_type == "多选题" else "#32CD32")
        st.markdown(f"<span style='background-color:{badge_color}; color:white; padding:3px 8px; border-radius:5px; font-size:12px; font-weight:bold;'>{q_type}</span>", unsafe_allow_html=True)
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 题干
        st.info(f"**题目：** {q['题目']}")
        
        # 整理选项
        options = []
        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            val = q.get(opt, "")
            if val:
                options.append(f"{opt}. {val}")
        
        correct_ans = str(q.get('答案', '')).strip().upper()
        show_ai_button = False  

        # ------------------ 📖 1. 背题模式 ------------------
        if "背题模式" in mode:
            if q_type == "多选题":
                # 展示所有选项，并禁用，正确选项默认打勾
                for opt in options:
                    letter = opt[0]
                    st.checkbox(opt, value=(letter in correct_ans), disabled=True, key=f"read_{idx}_{letter}")
            else:
                # 单选/判断
                correct_index = next((i for i, o in enumerate(options) if o.startswith(correct_ans)), None)
                st.radio("选项：", options, index=correct_index, disabled=True, key=f"read_{idx}")
            
            st.success(f"🎯 **正确答案：** {correct_ans}")
            st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
            show_ai_button = True  

        # ------------------ 🔥 2. 挑战模式 (核心重构) ------------------
        elif "挑战模式" in mode:
            saved_ans = st.session_state.user_answers.get(idx, "")
            
            if q_type == "多选题":
                is_confirmed = st.session_state.get(f"confirmed_{idx}", False)
                
                # 渲染复选框
                selected_letters = []
                for opt in options:
                    letter = opt[0]
                    # 如果已确认，则禁用复选框防止修改
                    chk = st.checkbox(opt, value=(letter in saved_ans), disabled=is_confirmed, key=f"challenge_{idx}_{letter}")
                    if chk:
                        selected_letters.append(letter)
                
                user_ans_str = "".join(sorted(selected_letters))
                
                if not is_confirmed:
                    # 提供确认答案按钮
                    if st.button("确认选择", type="primary", use_container_width=True, key=f"confirm_btn_{idx}"):
                        if not user_ans_str:
                            st.warning("⚠️ 请至少选择一个选项！")
                        else:
                            st.session_state.user_answers[idx] = user_ans_str
                            st.session_state[f"confirmed_{idx}"] = True
                            
                            # 答对直接切下一题，答错留在原地渲染结果
                            if user_ans_str == correct_ans:
                                if st.session_state.current_index < len(q_list) - 1:
                                    st.session_state.current_index += 1
                                else:
                                    st.balloons()
                            st.rerun()
                else:
                    # 已点击确认后的展示状态
                    if saved_ans == correct_ans:
                        st.success("✅ 回答正确！")
                        if idx == len(q_list) - 1:
                            st.balloons()
                            st.success("🎉 恭喜您通关本套题库！")
                    else:
                        st.error(f"❌ 回答错误！您的选择：{saved_ans}，正确答案是：{correct_ans}")
                        st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
                        show_ai_button = True
            
            else:
                # 单选 / 判断题
                widget_key = f"challenge_single_{idx}"
                selected = st.radio(
                    "请选择您的答案：", 
                    options, 
                    index=options.index(f"{saved_ans}. {q.get(saved_ans, '')}") if saved_ans and f"{saved_ans}. {q.get(saved_ans, '')}" in options else None, 
                    key=widget_key,
                    on_change=challenge_single_callback,
                    args=(idx, widget_key, correct_ans)
                )
                
                if selected:
                    user_letter = selected[0]
                    if user_letter != correct_ans:
                        st.error(f"❌ 回答错误！您选择了 {user_letter}，正确答案是：{correct_ans}")
                        st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")
                        show_ai_button = True
                    elif idx == len(q_list) - 1:
                        st.balloons()
                        st.success("🎉 恭喜您通关本套题库！")

        # ------------------ 📝 3. 模拟考试 ------------------
        elif "模拟考试" in mode:
            saved_ans = st.session_state.user_answers.get(idx, "")
            
            if q_type == "多选题":
                selected_letters = []
                for opt in options:
                    letter = opt[0]
                    chk = st.checkbox(opt, value=(letter in saved_ans), key=f"exam_multi_{idx}_{letter}")
                    if chk:
                        selected_letters.append(letter)
                # 即时保存多选题答案
                user_ans_str = "".join(sorted(selected_letters))
                st.session_state.user_answers[idx] = user_ans_str
            else:
                # 单选 / 判断
                widget_key = f"exam_single_{idx}"
                selected = st.radio(
                    "请选择您的答案：", 
                    options, 
                    index=options.index(f"{saved_ans}. {q.get(saved_ans, '')}") if saved_ans and f"{saved_ans}. {q.get(saved_ans, '')}" in options else None, 
                    key=widget_key,
                    on_change=save_ans_callback,
                    args=(idx, widget_key)
                )

        # 🤖 AI 智能解析块
        if enable_ai and show_ai_button:
            st.write("---")
            if idx not in st.session_state.ai_explanations:
                if st.button("✨ 召唤 AI 名师深度解析", type="secondary", use_container_width=True):
                    if not api_key:
                        st.error("⚠️ 请先在侧边栏配置 AI API Key！")
                    else:
                        prompt = f"""
                        请深度解析以下选择题：
                        【题型】 {q_type}
                        【题目】 {q['题目']}
                        【选项】 {"/".join(options)}
                        【正确答案】 {correct_ans}
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

        # 底部导航按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("⬅️ 上一题", on_click=prev_q, disabled=(idx == 0), use_container_width=True)
        with col2:
            st.button("➡️ 下一题", on_click=next_q, disabled=(idx == len(q_list) - 1), use_container_width=True)
        with col3:
            if "模拟考试" in mode and not st.session_state.score_submitted:
                st.button("📝 提交试卷", on_click=submit_exam_callback, type="primary", use_container_width=True)

    # 运行局部渲染区域
    if st.session_state.questions:
        render_quiz_area()

        # ================= 7. 模拟考试结算 =================
        if "模拟考试" in mode and st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            correct_count = 0
            wrong_questions = []
            all_results = []
            q_list = st.session_state.questions
            
            for i, question in enumerate(q_list):
                user_ans = st.session_state.user_answers.get(i, "")
                user_letter = user_ans if user_ans else "未作答"
                
                c_ans = str(question.get('答案', '')).strip().upper()
                
                is_correct = (user_letter == c_ans)
                if is_correct:
                    correct_count += 1
                
                result_item = {
                    "index": i + 1,
                    "question": question,
                    "user_letter": user_letter,
                    "correct_letter": c_ans,
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
                    
                    w_page = st.selectbox("错题页码：", range(1, num_wrong_pages + 1)) if num_wrong_pages > 1 else 1
                    start_w = (w_page - 1) * items_per_page
                    end_w = start_w + items_per_page
                    
                    for w in wrong_questions[start_w:end_w]:
                        with st.expander(f"🔴 第 {w['index']} 题 ( 选: {w['user_letter']} | 答: {w['correct_letter']} )"):
                            st.write(f"**【{w['question']['题型']}】** {w['question']['题目']}")
                            for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                                if w['question'].get(opt):
                                    st.write(f"- {opt}: {w['question'][opt]}")
                            st.error(f"你的答案：`{w['user_letter']}` ❌")
                            st.success(f"正确答案：`{w['correct_letter']}` ✅")
                            st.warning(f"💡 解析：{w['question'].get('解析', '暂无解析')}")
            
            with tab2:
                total_all = len(all_results)
                num_all_pages = (total_all - 1) // items_per_page + 1
                
                a_page = st.selectbox("报告页码：", range(1, num_all_pages + 1)) if num_all_pages > 1 else 1
                start_a = (a_page - 1) * items_per_page
                end_a = start_a + items_per_page
                
                for r in all_results[start_a:end_a]:
                    status_icon = "✅ 正确" if r['is_correct'] else "❌ 错误"
                    with st.expander(f"第 {r['index']} 题：{status_icon} (选: {r['user_letter']} | 答: {r['correct_letter']})"):
                        st.write(f"**【{r['question']['题型']}】** {r['question']['题目']}")
                        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                            if r['question'].get(opt):
                                if r['question'][opt]:
                                    st.write(f"- {opt}: {r['question'][opt]}")
                        st.write(f"**您的答案：** {r['user_letter']} | **正确答案：** {r['correct_letter']}")
                        st.write(f"**解析：** {r['question'].get('解析', '暂无解析')}")
            
            def restart_exam():
                st.session_state.current_index = 0
                st.session_state.user_answers = {}
                st.session_state.score_submitted = False
                st.session_state.ai_explanations = {}
                # 重置多选题状态
                for k in list(st.session_state.keys()):
                    if k.startswith("confirmed_") or k.startswith("challenge_") or k.startswith("exam_multi_"):
                        del st.session_state[k]
                
            st.button("🔄 重新开始考试", on_click=restart_exam, use_container_width=True)
