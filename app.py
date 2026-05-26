import streamlit as st
import pandas as pd
import random
import html  # 用于修复 &quot; 等 HTML 乱码字符

# 设置网页标题和手机端布局自适应
st.set_page_config(
    page_title="我的专属无广告刷题库",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📝 我的专属无广告刷题库")

# 初始化 Session State
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_index = 0
    st.session_state.user_answers = {}
    st.session_state.score_submitted = False
    st.session_state.current_file_name = ""
    st.session_state.current_mode = ""

# 1. 上传 Excel 题库
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库", type=["xlsx"])

if uploaded_file:
    # 避免重复加载
    if st.session_state.current_file_name != uploaded_file.name:
        st.session_state.questions = []
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        st.session_state.current_file_name = uploaded_file.name

    # 读取 Excel
    df = pd.read_excel(uploaded_file, dtype=str)
    
    # 清理列名的空格
    df.columns = [str(col).strip() for col in df.columns]
    
    # --- 精准匹配表头 ---
    q_col = next((c for c in df.columns if "题干" in c), None)
    ans_col = next((c for c in df.columns if "正确答案" in c or "答案" in c), None)
    analysis_col = next((c for c in df.columns if "解析" in c), None)
    
    opt_cols = {}
    for letter in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        col_name = next((c for c in df.columns if f"选项 {letter}" in c or f"选项{letter}" in c), None)
        if col_name:
            opt_cols[letter] = col_name

    # 兜底识别
    if not q_col: q_col = df.columns[0]
    if not ans_col: ans_col = df.columns[-1]

    # 清洗数据
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

    # 2. 侧边栏刷题设置
    st.sidebar.header("⚙️ 刷题设置")
    
    # 选择三大新模式
    mode = st.sidebar.radio(
        "选择刷题模式：", 
        ["📖 1. 背题模式 (直接看选项和答案)", 
         "🔥 2. 挑战模式 (即时答题反馈对错)", 
         "📝 3. 模拟考试 (统一交卷评测分)"]
    )
    
    # 检测模式是否发生切换
    if st.session_state.current_mode != mode:
        st.session_state.current_mode = mode
        st.session_state.questions = []
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False

    # 抽取题目范围设置 (仅在考试模式下提供随机抽题选项，背题/挑战默认为全部或打乱)
    if "模拟考试" in mode:
        exam_scope = st.sidebar.selectbox("考试范围选项：", ["随机抽题测试", "全量试卷测试"])
        if exam_scope == "随机抽题测试":
            num_questions = st.sidebar.number_input("抽取题目数量：", min_value=1, max_value=len(cleaned_records), value=min(20, len(cleaned_records)))
        else:
            num_questions = len(cleaned_records)
    else:
        num_questions = len(cleaned_records)
        order_opt = st.sidebar.selectbox("题目顺序：", ["顺序刷题", "打乱顺序"])

    # 初始化/重置刷题按钮
    if st.sidebar.button("🎯 确认/开始重置") or not st.session_state.questions:
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        
        # 模式数据初始化
        if "模拟考试" in mode:
            if exam_scope == "随机抽题测试":
                st.session_state.questions = random.sample(cleaned_records, num_questions)
            else:
                st.session_state.questions = cleaned_records.copy()
        else:
            if order_opt == "打乱顺序":
                st.session_state.questions = random.sample(cleaned_records, len(cleaned_records))
            else:
                st.session_state.questions = cleaned_records.copy()
            
        st.sidebar.success(f"已成功加载 {len(st.session_state.questions)} 道题！")

    # 3. 刷题主界面
    if st.session_state.questions:
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        
        # 进度指示器
        progress = (idx + 1) / len(q_list)
        st.progress(progress)
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 显示题目题干
        st.info(f"**题目：** {q['题目']}")
        
        # 整理选项（只展示有内容的选项，如 E、F 没填就不显示）
        options = []
        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            val = q.get(opt, "")
            if val:
                options.append(f"{opt}. {val}")
        
        # 获取正确答案字母
        correct_letter = str(q.get('答案', '')).strip().upper()
        if correct_letter.endswith(".0"):
            correct_letter = correct_letter[0]

        # ---------------- 模式 1：背题模式 ----------------
        if "背题模式" in mode:
            # 渲染禁用状态的单选项，默认点亮正确答案
            correct_index = next((i for i, o in enumerate(options) if o.startswith(correct_letter)), None)
            st.radio(
                "题目选项：", 
                options, 
                index=correct_index, 
                disabled=True, 
                key=f"read_{idx}"
            )
            # 直接显示答案和解析
            st.success(f"🎯 **正确答案：** {correct_letter}")
            st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")

        # ---------------- 模式 2：挑战模式 ----------------
        elif "挑战模式" in mode:
            saved_ans = st.session_state.user_answers.get(idx, None)
            
            # 渲染单选按钮供选择
            selected = st.radio(
                "请选择您的答案：", 
                options, 
                index=options.index(saved_ans) if saved_ans in options else None, 
                key=f"challenge_{idx}"
            )
            
            if selected:
                st.session_state.user_answers[idx] = selected
                user_letter = selected[0]
                
                # 即时反馈正确答案
                if user_letter == correct_letter:
                    st.success("✅ 恭喜您，回答正确！")
                else:
                    st.error(f"❌ 回答错误！您选择了 {user_letter}，正确答案是：{correct_letter}")
                
                st.warning(f"💡 **解析：** {q.get('解析', '暂无解析')}")

        # ---------------- 模式 3：模拟考试 ----------------
        elif "模拟考试" in mode:
            saved_ans = st.session_state.user_answers.get(idx, None)
            
            # 渲染正常单选，交卷前不给出任何提示
            selected = st.radio(
                "请选择您的答案：", 
                options, 
                index=options.index(saved_ans) if saved_ans in options else None, 
                key=f"exam_{idx}"
            )
            
            if selected:
                st.session_state.user_answers[idx] = selected

        st.write("")  # 留空美化布局

        # 底部控制区（上一题、下一题、提交）
        col1, col2, col3 = st.columns(3)
        with col1:
            if idx > 0:
                if st.button("⬅️ 上一题", use_container_width=True):
                    st.session_state.current_index -= 1
                    st.rerun()
        with col2:
            if idx < len(q_list) - 1:
                if st.button("➡️ 下一题", use_container_width=True):
                    st.session_state.current_index += 1
                    st.rerun()
        with col3:
            # 仅在“模拟考试”模式下显示“提交试卷”按钮
            if "模拟考试" in mode and not st.session_state.score_submitted:
                if st.button("📝 提交试卷", type="primary", use_container_width=True):
                    st.session_state.score_submitted = True
                    st.rerun()

        # 4. 模拟考试交卷后的成绩单和错题复盘
        if "模拟考试" in mode and st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            # 1. 统计分数和错题
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

            # 2. 显示得分看板
            score = round((correct_count / len(q_list)) * 100, 1)
            st.metric(
                label="最终得分", 
                value=f"{score} 分", 
                delta=f"答对 {correct_count} / {len(q_list)} 题 (答错/未答 {len(wrong_questions)} 题)"
            )
            
            # 3. 分类呈现报告（Tab 页视图，更高级清晰）
            tab1, tab2 = st.tabs(["❌ 错题本 (复习用)", "📖 完整试卷报告"])
            
            # 错题标签页 (只显示错题，突出对比)
            with tab1:
                if len(wrong_questions) == 0:
                    st.balloons()
                    st.success("太棒了！您拿到了满分，没有错题！🎉")
                else:
                    st.subheader(f"共发现 {len(wrong_questions)} 道错题，请重点巩固：")
                    for w in wrong_questions:
                        with st.expander(f"🔴 第 {w['index']} 题 ( 您的选择: {w['user_letter']} | 正确答案: {w['correct_letter']} )"):
                            st.write(f"**题目：** {w['question']['题目']}")
                            for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                                if w['question'].get(opt):
                                    st.write(f"- {opt}: {w['question'][opt]}")
                            st.error(f"你的答案：`{w['user_letter']}` ❌")
                            st.success(f"正确答案：`{w['correct_letter']}` ✅")
                            st.warning(f"💡 解析：{w['question'].get('解析', '暂无解析')}")
            
            # 完整试卷报告页
            with tab2:
                for r in all_results:
                    status_icon = "✅ 正确" if r['is_correct'] else "❌ 错误"
                    with st.expander(f"第 {r['index']} 题：{status_icon} (您选: {r['user_letter']} | 答案: {r['correct_letter']})"):
                        st.write(f"**题目：** {r['question']['题目']}")
                        for opt in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                            if r['question'].get(opt):
                                st.write(f"- {opt}: {r['question'][opt]}")
                        st.write(f"**您的答案：** {r['user_letter']} | **正确答案：** {r['correct_letter']}")
                        st.write(f"**解析：** {r['question'].get('解析', '暂无解析')}")
            
            # 重新开始
            if st.button("🔄 重新开始考试", use_container_width=True):
                st.session_state.current_index = 0
                st.session_state.user_answers = {}
                st.session_state.score_submitted = False
                st.rerun()
