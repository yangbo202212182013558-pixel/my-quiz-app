import streamlit as st
import pandas as pd
import random

# 设置网页标题和手机端自适应
st.set_page_config(page_title="极简免费刷题神器", layout="centered")

st.title("📝 我的专属无广告刷题库")

# 初始化 Session State（防止刷新网页导致进度丢失）
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_index = 0
    st.session_state.user_answers = {}
    st.session_state.score_submitted = False

# 1. 上传 Excel 题库
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库 (包含列：题目, A, B, C, D, 答案, 解析)", type=["xlsx"])

if uploaded_file:
    # 读取数据
    df = pd.read_excel(uploaded_file)
    
    # 2. 刷题设置
    st.sidebar.header("⚙️ 刷题设置")
    mode = st.sidebar.radio("选择模式：", ["顺序练习", "乱序练习（打乱顺序）", "模拟考试（随机抽题）"])
    
    if mode == "模拟考试（随机抽题）":
        num_questions = st.sidebar.number_input("抽取题目数量：", min_value=1, max_value=len(df), value=min(20, len(df)))
    
    # 初始化题目
    if st.sidebar.button("🎯 开始/重置刷题"):
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        
        # 根据模式处理题目
        if mode == "顺序练习":
            st.session_state.questions = df.to_dict(orient="records")
        elif mode == "乱序练习（打乱顺序）":
            st.session_state.questions = df.sample(frac=1).to_dict(orient="records")
        elif mode == "模拟考试（随机抽题）":
            st.session_state.questions = df.sample(n=num_questions).to_dict(orient="records")
            
        st.success(f"成功加载 {len(st.session_state.questions)} 道题目！")

    # 3. 开始刷题界面
    if st.session_state.questions:
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 显示题目
        st.info(f"**题目：** {q['题目']}")
        
        # 显示选项
        options = []
        for opt in ['A', 'B', 'C', 'D']:
            if pd.notna(q.get(opt)):
                options.append(f"{opt}. {q[opt]}")
        
        # 用户选择答案（记忆历史选择）
        saved_ans = st.session_state.user_answers.get(idx, None)
        selected = st.radio("请选择答案：", options, index=options.index(saved_ans) if saved_ans in options else None, key=f"q_{idx}")
        
        if selected:
            st.session_state.user_answers[idx] = selected

        # 底部导航按钮（上一题、下一题、交卷）
        col1, col2, col3 = st.columns(3)
        with col1:
            if idx > 0:
                if st.button("⬅️ 上一题"):
                    st.session_state.current_index -= 1
                    st.rerun()
        with col2:
            if idx < len(q_list) - 1:
                if st.button("➡️ 下一题"):
                    st.session_state.current_index += 1
                    st.rerun()
        with col3:
            if not st.session_state.score_submitted:
                if st.button("📝 提交试卷"):
                    st.session_state.score_submitted = True
                    st.rerun()

        # 显示考试结果
        if st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            correct_count = 0
            for i, question in enumerate(q_list):
                user_ans = st.session_state.user_answers.get(i, "未作答")
                # 提取用户选的 A/B/C/D 字母
                user_letter = user_ans[0] if user_ans != "未作答" else "无"
                correct_letter = str(question['答案']).strip().upper()
                
                is_correct = user_letter == correct_letter
                if is_correct:
                    correct_count += 1
                
                # 展开查看错题
                with st.expander(f"第 {i+1} 题：{'✅ 正确' if is_correct else '❌ 错误'} (你选: {user_letter} | 答案: {correct_letter})"):
                    st.write(f"**题目：** {question['题目']}")
                    st.write(f"**解析：** {question.get('解析', '无解析')}")
            
            score = round((correct_count / len(q_list)) * 100, 1)
            st.metric(label="最终得分", value=f"{score} 分", delta=f"答对 {correct_count}/{len(q_list)} 题")
