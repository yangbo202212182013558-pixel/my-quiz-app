import streamlit as st
import pandas as pd
import random

# 设置网页标题和手机端布局自适应
st.set_page_config(
    page_title="极简免费刷题神器",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📝 我的专属无广告刷题库")

# 初始化 Session State（防止刷新网页导致进度丢失）
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_index = 0
    st.session_state.user_answers = {}
    st.session_state.score_submitted = False
    st.session_state.current_file_name = ""

# 1. 上传 Excel 题库
uploaded_file = st.file_uploader("第一步：上传你的 Excel 题库", type=["xlsx"])

if uploaded_file:
    # 如果上传了新文件，自动清空旧数据
    if st.session_state.current_file_name != uploaded_file.name:
        st.session_state.questions = []
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        st.session_state.current_file_name = uploaded_file.name

    # 读取 Excel 数据
    df = pd.read_excel(uploaded_file)
    
    # 【智能兼容表头】去除列名空格，并统一转为字符串
    df.columns = [str(col).strip() for col in df.columns]
    cols = list(df.columns)
    
    # --- 智能匹配算法 ---
    
    # 1. 寻找题目列
    q_col = next((c for c in cols if any(k in c for k in ["题目", "题干", "问题", "question", "q", "内容"])), None)
    if not q_col:
        # 排除掉明显的序号、答案、解析列，剩下的第一个可能就是题目
        possible_q = [c for c in cols if not any(k in c for k in ["序号", "ID", "id", "编号", "答案", "解析", "详解", "answer"])]
        q_col = possible_q[0] if possible_q else cols[0]

    # 2. 寻找答案列
    ans_col = next((c for c in cols if any(k in c for k in ["答案", "正确答案", "answer", "key", "正确项", "等"])), None)
    
    # 3. 寻找解析列
    analysis_col = next((c for c in cols if any(k in c for k in ["解析", "详解", "analysis", "explain", "说明"])), None)

    # 4. 智能寻找选项列 (A, B, C, D)
    other_cols = [c for c in cols if c not in [q_col, ans_col, analysis_col] and not any(k in c for k in ["序号", "ID", "id", "编号"])]
    
    a_col = next((c for c in other_cols if c.upper() == "A" or "选项A" in c or "选项a" in c or "A选项" in c or c.endswith("A") or c.startswith("A")), None)
    b_col = next((c for c in other_cols if c.upper() == "B" or "选项B" in c or "选项b" in c or "B选项" in c or c.endswith("B") or c.startswith("B")), None)
    c_col = next((c for c in other_cols if c.upper() == "C" or "选项C" in c or "选项c" in c or "C选项" in c or c.endswith("C") or c.startswith("C")), None)
    d_col = next((c for c in other_cols if c.upper() == "D" or "选项D" in c or "选项d" in c or "D选项" in c or c.endswith("D") or c.startswith("D")), None)

    # 【超级安全兜底机制】：如果通过名字没有找齐 A B C D，我们按顺序把剩下没被占用的列强制分配给 A, B, C, D
    assigned = [a_col, b_col, c_col, d_col]
    remaining_cols = [c for c in other_cols if c not in assigned]
    
    if not a_col and len(remaining_cols) > 0: a_col = remaining_cols.pop(0)
    if not b_col and len(remaining_cols) > 0: b_col = remaining_cols.pop(0)
    if not c_col and len(remaining_cols) > 0: c_col = remaining_cols.pop(0)
    if not d_col and len(remaining_cols) > 0: d_col = remaining_cols.pop(0)

    # 显示列名解析面板，帮助用户核对
    with st.expander("🔍 题库格式解析成功！(如果选项仍不显示，点此核对表头)"):
        st.write(f"**您的表格所有列：** `{', '.join(cols)}`")
        st.write(f"**系统识别出的对应关系：**")
        st.write(f"- ❓ 题目 ➡️ `{q_col}`")
        st.write(f"- 🅰️ 选项A ➡️ `{a_col}`")
        st.write(f"- 🅱️ 选项B ➡️ `{b_col}`")
        st.write(f"- 🆃 选项C ➡️ `{c_col}`")
        st.write(f"- 🅳 选项D ➡️ `{d_col}`")
        st.write(f"- 🎯 答案 ➡️ `{ans_col if ans_col else '未检测到'}`")

    # 重命名列，方便程序统一读取
    rename_dict = {}
    if q_col: rename_dict[q_col] = "题目"
    if a_col: rename_dict[a_col] = "A"
    if b_col: rename_dict[b_col] = "B"
    if c_col: rename_dict[c_col] = "C"
    if d_col: rename_dict[d_col] = "D"
    if ans_col: rename_dict[ans_col] = "答案"
    if analysis_col: rename_dict[analysis_col] = "解析"
    
    df = df.rename(columns=rename_dict)
    
    # 补齐缺失的选项和解析列，防止报错
    for col in ["A", "B", "C", "D", "解析"]:
        if col not in df.columns:
            df[col] = ""

    # 2. 侧边栏刷题设置
    st.sidebar.header("⚙️ 刷题设置")
    mode = st.sidebar.radio("选择模式：", ["顺序练习", "乱序练习（打乱顺序）", "模拟考试（随机抽题）"])
    
    if mode == "模拟考试（随机抽题）":
        num_questions = st.sidebar.number_input("抽取题目数量：", min_value=1, max_value=len(df), value=min(20, len(df)))
    
    # 初始化/重置按钮
    if st.sidebar.button("🎯 开始/重置刷题") or not st.session_state.questions:
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.score_submitted = False
        
        # 根据选择的模式对数据进行处理
        if mode == "顺序练习":
            st.session_state.questions = df.to_dict(orient="records")
        elif mode == "乱序练习（打乱顺序）":
            st.session_state.questions = df.sample(frac=1).to_dict(orient="records")
        elif mode == "模拟考试（随机抽题）":
            st.session_state.questions = df.sample(n=num_questions).to_dict(orient="records")
            
        st.sidebar.success(f"已成功加载 {len(st.session_state.questions)} 道题！")

    # 3. 刷题主界面
    if st.session_state.questions:
        q_list = st.session_state.questions
        idx = st.session_state.current_index
        q = q_list[idx]
        
        # 进度条
        progress = (idx + 1) / len(q_list)
        st.progress(progress)
        st.subheader(f"进度: {idx + 1} / {len(q_list)}")
        
        # 显示题目题干
        st.info(f"**题目：** {q['题目']}")
        
        # 整理选项
        options = []
        for opt in ['A', 'B', 'C', 'D']:
            val = q.get(opt, "")
            if pd.notna(val) and str(val).strip() != "":
                options.append(f"{opt}. {val}")
        
        # 获取用户之前保存过的答案
        saved_ans = st.session_state.user_answers.get(idx, None)
        
        # 渲染单选框
        selected = st.radio(
            "请选择您的答案：", 
            options, 
            index=options.index(saved_ans) if saved_ans in options else None, 
            key=f"q_{idx}"
        )
        
        # 保存用户选择的答案
        if selected:
            st.session_state.user_answers[idx] = selected

        st.write("")  # 留空一行美化布局

        # 底部导航控制按钮（上一题、下一题、提交）
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
            if not st.session_state.score_submitted:
                if st.button("📝 提交试卷", type="primary", use_container_width=True):
                    st.session_state.score_submitted = True
                    st.rerun()

        # 4. 显示考试结算报告
        if st.session_state.score_submitted:
            st.divider()
            st.header("📊 考试报告")
            
            correct_count = 0
            # 循环检查每一道题
            for i, question in enumerate(q_list):
                user_ans = st.session_state.user_answers.get(i, "未作答")
                user_letter = user_ans[0] if user_ans != "未作答" else "无"
                
                # 兼容处理 Excel 里的答案（去空格、转大写、防浮点数转字符串）
                raw_ans = question.get('答案', '')
                if pd.isna(raw_ans):
                    correct_letter = ""
                else:
                    correct_letter = str(raw_ans).strip().upper()
                    if correct_letter.endswith(".0"):
                        correct_letter = correct_letter[0]
                
                is_correct = (user_letter == correct_letter)
                if is_correct:
                    correct_count += 1
                
                # 折叠框：显示题目详情、答案和解析
                status_icon = "✅ 正确" if is_correct else "❌ 错误"
                with st.expander(f"第 {i+1} 题：{status_icon} (你选: {user_letter} | 答案: {correct_letter})"):
                    st.write(f"**题目：** {question['题目']}")
                    # 重新列出选项
                    for opt in ['A', 'B', 'C', 'D']:
                        if pd.notna(question.get(opt)) and str(question[opt]).strip() != "":
                            st.write(f"- {opt}: {question[opt]}")
                    st.write(f"**您的答案：** {user_letter} | **正确答案：** {correct_letter}")
                    st.write(f"**解析：** {question.get('解析', '暂无解析')}")
            
            # 计算得分
            score = round((correct_count / len(q_list)) * 100, 1)
            st.metric(
                label="最终得分", 
                value=f"{score} 分", 
                delta=f"答对 {correct_count} / {len(q_list)} 题"
            )
            
            # 重新开始按钮
            if st.button("🔄 重新开始刷题", use_container_width=True):
                st.session_state.current_index = 0
                st.session_state.user_answers = {}
                st.session_state.score_submitted = False
                st.rerun()
