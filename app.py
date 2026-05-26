import streamlit as st
import pandas as pd
import random
import html

# 设置网页标题和布局
st.set_page_config(
    page_title="我的专属无广告刷题库",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📝 我的专属无广告刷题库")

# ================= 1. 初始化 Session State (内存高速公路) =================
if "raw_questions" not in st.session_state:
    st.session_state.raw_questions = []  # 缓存解析后的原始数据，避免重复读取Excel
if "questions" not in st.session_state:
    st.session_state.questions = []      # 当前模式正在使用的题目集
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

# ================= 2. 极致性能回调函数 (Callbacks) =================
# 点击上一题
def prev_q():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1

# 点击下一题
def next_q():
    if st.session_state.current_index < len(st.session_state.questions) - 1:
        st.session_state.current_index += 1

# 选中选项时即时存入内存，零延迟
def save_ans_callback(idx, widget_key):
    st.session_state.user_answers[idx] = st.session_state[widget_key]

# 提交试卷
def submit_exam_callback():
    st.session_state.score_submitted = True

# ================= 3. 读取并解析 Excel (仅在上传新文件时运行一次) =================
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库", type=["xlsx"])

if uploaded_file:
    file_key = f"{uploaded_file.name}_{uploaded_file.size}"
    
    # 只有当上传了新文件时，才进行解析，避免每次点击都重复读取
    if st.session_state.current_file_key != file_key:
        with st.spinner("⚡ 正在为您极速加载并解析题库，仅需一次..."):
            df = pd.read_excel(uploaded_file, dtype=str)
            df.columns = [str(col).strip() for col in df.columns]
            
            # 表头精准匹配
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
            
            # 存入极速内存
            st.session_state.raw_questions = cleaned_records
            st.session_state.current_file_key = file_key
            st.session_state.questions = []
            st.session_state.current_index = 0
            st.session_state.user_answers = {}
            st.session_state.score_submitted = False

    # ================= 4. 侧边栏刷题设置 =================
    st.sidebar.header("⚙️ 刷题设置")
    
    mode = st.sidebar.radio(
        "选择刷题模式：", 
        ["📖 1. 背题模式 (直接看选项和答案)", 
         "🔥 2. 挑战模式 (即时答题反馈对错)", 
         "📝 3. 模拟考试 (统一交卷评测分)"]
    )
    
    # 切换模式时自动重置状态
    if st.session_state.current_mode != mode:
        st.session_state.current_mode = mode
        st.session_state.questions = []
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False

    # 参数配置
    if "模拟考试" in mode:
        exam_scope = st.sidebar.selectbox("考试范围选项：", ["随机抽题测试", "全量试卷测试"])
        if exam_scope == "随机抽题测试":
            num_questions = st.sidebar.number_input("抽取题目数量：", min_value=1, max_value=len(st.session_state.raw_questions), value=min(20, len(st.session_state.raw_questions)))
        else:
            num_questions = len(st.session_state.raw_questions)
    else:
        num_questions = len(st.session_state.raw_questions)
        order_opt = st.sidebar.selectbox("题目顺序：", ["顺序刷题", "打乱顺序"])

    # 开始/重置刷题（纯内存操作，极速响应）
    if st.sidebar.button("🎯 确认/开始重置") or not st.session_state.questions:
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        
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

    # ================= 5. 刷题主界面 =================
    if st.session_state.questions:
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        
        # 进度指示器
        progress = (idx + 1) / len(q_list)
        st.progress(progress)
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 显示题目
        st.info(f"**题目：** {q['题目']}")
        
        # 整理选项
        options = []
        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            val = q.get(opt, "")
            if val:
                options.append(f"{opt}. {val}")
        
        correct_letter = str(q.get('答案', '')).strip().upper()
        if correct_letter.endswith(".0"):
            correct_letter = correct_letter[0]

        # ---------------- 模式 1：背题模式 ----------------
        if "背题模式" in mode:
            correct_index = next((i for i, o in enumerate(options) if o.startswith(correct_letter)), None)
            st.radio(
                "题目选项：", 
                options, 
                index=correct_index, 
                disabled=True, 
                key=f"read_{idx}"
            )
            st.success(f"🎯 **正确答案：** {correct_letter}")
            st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")

        # ---------------- 模式 2：挑战模式 (即时反馈) ----------------
        elif "挑战模式" in mode:
            saved_ans = st.session_state.user_answers.get(idx, None)
            widget_key = f"challenge_{idx}"
            
            selected = st.radio(
                "请选择您的答案：", 
                options, 
                index=options.index(saved_ans) if saved_ans in options else None, 
                key=widget_key,
                on_change=save_ans_callback,
                args=(idx, widget_key)
            )
            
            if selected:
                user_letter = selected[0]
                if user_letter == correct_letter:
                    st.success("✅ 恭喜您，回答正确！")
                else:
                    st.error(f"❌ 回答错误！您选择了 {user_letter}，正确答案是：{correct_letter}")
                st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")

        # ---------------- 模式 3：模拟考试 ----------------
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

        st.write("") 

        # 底部导航按钮（绑定 Callback，实现零延迟翻页）
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("⬅️ 上一题", on_click=prev_q, disabled=(idx == 0), use_container_width=True)
        with col2:
            st.button("➡️ 下一题", on_click=next_q, disabled=(idx == len(q_list) - 1), use_container_width=True)
        with col3:
            if "模拟考试" in mode and not st.session_state.score_submitted:
                st.button("📝 提交试卷", on_click=submit_exam_callback, type="primary", use_container_width=True)

        # ---------------- 6. 模拟考试结算（智能分页技术，防卡顿） ----------------
        if "模拟考试" in mode and st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            # 计算得分
            correct_count = 0
            wrong_questions = []
            all_results = []
            
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
            
            # 分页器配置（每页展示 20 道题，防止 DOM 过载卡死浏览器）
            items_per_page = 20
            
            tab1, tab2 = st.tabs(["❌ 错题本 (复习用)", "📖 完整试卷报告"])
            
            # 错题本标签页（带分页）
            with tab1:
                if len(wrong_questions) == 0:
                    st.balloons()
                    st.success("太棒了！您拿到了满分，没有错题！🎉")
                else:
                    total_wrongs = len(wrong_questions)
                    num_wrong_pages = (total_wrongs - 1) // items_per_page + 1
                    
                    if num_wrong_pages > 1:
                        w_page = st.selectbox(
                            "错题页码：", 
                            range(1, num_wrong_pages + 1), 
                            format_func=lambda x: f"第 {x} 页 (错题第 {(x-1)*items_per_page+1} - {min(x*items_per_page, total_wrongs)} 题)"
                        )
                    else:
                        w_page = 1
                    
                    start_w = (w_page - 1) * items_per_page
                    end_w = start_w + items_per_page
                    
                    for w in wrong_questions[start_w:end_w]:
                        with st.expander(f"🔴 第 {w['index']} 题 ( 您的选择: {w['user_letter']} | 正确答案: {w['correct_letter']} )"):
                            st.write(f"**题目：** {w['question']['题目']}")
                            for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                                if w['question'].get(opt):
                                    st.write(f"- {opt}: {w['question'][opt]}")
                            st.error(f"你的答案：`{w['user_letter']}` ❌")
                            st.success(f"正确答案：`{w['correct_letter']}` ✅")
                            st.warning(f"💡 解析：{w['question'].get('解析', '暂无解析')}")
            
            # 完整试卷报告页（带分页）
            with tab2:
                total_all = len(all_results)
                num_all_pages = (total_all - 1) // items_per_page + 1
                
                if num_all_pages > 1:
                    a_page = st.selectbox(
                        "报告页码：", 
                        range(1, num_all_pages + 1), 
                        format_func=lambda x: f"第 {x} 页 (第 {(x-1)*items_per_page+1} - {min(x*items_per_page, total_all)} 题)"
                    )
                else:
                    a_page = 1
                
                start_a = (a_page - 1) * items_per_page
                end_a = start_a + items_per_page
                
                for r in all_results[start_a:end_a]:
                    status_icon = "✅ 正确" if r['is_correct'] else "❌ 错误"
                    with st.expander(f"第 {r['index']} 题：{status_icon} (您选: {r['user_letter']} | 答案: {r['correct_letter']})"):
                        st.write(f"**题目：** {r['question']['题目']}")
                        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                            if r['question'].get(opt):
                                st.write(f"- {opt}: {r['question'][opt]}")
                        st.write(f"**您的答案：** {r['user_letter']} | **正确答案：** {r['correct_letter']}")
                        st.write(f"**解析：** {r['question'].get('解析', '暂无解析')}")
            
            # 重置考试按钮
            def restart_exam():
                st.session_state.current_index = 0
                st.session_state.user_answers = {}
                st.session_state.score_submitted = False
                
            st.button("🔄 重新开始考试", on_click=restart_exam, use_container_width=True)
