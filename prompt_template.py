"""
Prompt模板 - 用于文献问答系统的各个阶段
"""
import re


def detect_language(text: str) -> str:
    """检测文本语言，返回'zh'（中文）或'en'（英文）"""
    if not text:
        return 'en'
    
    # 统计中文字符数量
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 统计总字符数量（排除空格和标点）
    total_chars = len(re.findall(r'[a-zA-Z\u4e00-\u9fff]', text))
    
    if total_chars == 0:
        return 'en'
    
    # 如果中文字符占比超过30%，认为是中文
    if chinese_chars / total_chars > 0.3:
        return 'zh'
    else:
        return 'en'


def get_pdf_parse_prompt(pdf_text: str, language: str = 'en') -> str:
    """PDF结构化解析Prompt"""
    if language == 'zh':
        prompt = f"""你是一位学术论文分析专家。你的任务是从以下PDF文本中提取结构化信息。

请提取并组织以下信息为结构化格式：

1. **Title（标题）**: 论文标题
2. **Authors（作者）**: 作者列表
3. **Abstract（摘要）**: 摘要文本
4. **Keywords（关键词）**: 关键词（如果有）
5. **Introduction（引言）**: 引言部分的主要观点
6. **Methodology（方法论）**: 使用的方法/方法描述
7. **Experiments（实验）**: 实验设置和程序
8. **Results（结果）**: 主要结果和发现
9. **Conclusion（结论）**: 主要结论
10. **References（参考文献）**: 参考文献列表（如果有）
11. **Paper Type（论文类型）**: 分类为以下之一：理论性、实验性、综述/评论或其他
12. **Core Contributions（核心贡献）**: 列出本文的3-5个主要贡献
13. **Technical Approach（技术方法）**: 技术方法/方法论的简要描述

PDF文本：
{pdf_text[:20000]}

请以清晰、有组织的形式提供结构化信息。如果任何部分缺失，请注明"未找到"。

请使用中文回答。所有输出内容都必须是中文。"""
    else:
        prompt = f"""You are an expert at analyzing academic papers. Your task is to extract structured information from the following PDF text.

Please extract and organize the following information in a structured format:

1. **Title**: The paper title
2. **Authors**: List of authors
3. **Abstract**: The abstract text
4. **Keywords**: Key terms (if available)
5. **Introduction**: Main points from the introduction section
6. **Methodology**: Description of the methods/approach used
7. **Experiments**: Experimental setup and procedures
8. **Results**: Key results and findings
9. **Conclusion**: Main conclusions
10. **References**: List of references (if available)
11. **Paper Type**: Classify as one of: Theoretical, Experimental, Survey/Review, or Other
12. **Core Contributions**: List 3-5 main contributions of this paper
13. **Technical Approach**: Brief description of the technical approach/methodology

PDF Text:
{pdf_text[:20000]}

Please provide the structured information in a clear, organized format. If any section is missing, indicate "Not found"."""
    
    return prompt


def get_question_analysis_prompt(query: str, language: str = 'en') -> str:
    """问题理解与关键词提取Prompt"""
    if language == 'zh':
        prompt = f"""你是一位学术问答专家。请仔细分析以下用户问题，理解问题意图并提取关键信息。

用户问题：{query}

请完成以下任务：
1. **问题类型识别**：判断问题类型（事实性、分析性、比较性、解释性等）
2. **关键词提取**：提取问题中的3-5个核心关键词或关键概念
3. **问题意图理解**：简要说明用户想要了解什么
4. **回答重点**：指出回答这个问题需要重点关注哪些方面

请以结构化的方式输出分析结果。"""
    else:
        prompt = f"""You are an expert in academic Q&A. Please carefully analyze the following user question, understand the question intent, and extract key information.

User Question: {query}

Please complete the following tasks:
1. **Question Type Identification**: Determine the question type (factual, analytical, comparative, explanatory, etc.)
2. **Keyword Extraction**: Extract 3-5 core keywords or key concepts from the question
3. **Question Intent Understanding**: Briefly explain what the user wants to know
4. **Answer Focus**: Indicate which aspects should be emphasized when answering this question

Please output the analysis results in a structured format."""
    
    return prompt


def get_evidence_filtering_prompt(query: str, passages: list, language: str = 'en') -> str:
    """证据筛选Prompt"""
    passages_text = ""
    for i, passage in enumerate(passages, 1):
        passages_text += f"\n段落 {i}:\n{passage}\n"
    
    if language == 'zh':
        prompt = f"""你是一位学术问答专家。请根据用户问题，从以下检索到的段落中筛选出最相关、最有价值的证据段落。

用户问题：{query}

检索到的段落：
{passages_text}

请完成以下任务：
1. **相关性评分**：评估每个段落与问题的相关性（1-10分）
2. **证据筛选**：选择最相关、最有价值的段落（最多选择5-8个）
3. **证据排序**：按照相关性从高到低排序
4. **简要说明**：简要说明为什么选择这些段落作为证据

请以结构化的方式输出筛选结果，包括选中的段落编号和简要说明。"""
    else:
        prompt = f"""You are an expert in academic Q&A. Please filter the most relevant and valuable evidence passages from the following retrieved passages based on the user's question.

User Question: {query}

Retrieved Passages:
{passages_text}

Please complete the following tasks:
1. **Relevance Scoring**: Evaluate the relevance of each passage to the question (1-10 points)
2. **Evidence Filtering**: Select the most relevant and valuable passages (select at most 5-8 passages)
3. **Evidence Ranking**: Rank the selected passages by relevance from high to low
4. **Brief Explanation**: Briefly explain why these passages are selected as evidence

Please output the filtering results in a structured format, including the selected passage numbers and brief explanations."""
    
    return prompt


def get_answer_generation_prompt(query: str, pdf_info: dict, passages: list, language: str = 'en') -> str:
    """答案生成Prompt"""
    # 构建PDF信息摘要
    pdf_summary = ""
    if pdf_info.get("Title"):
        pdf_summary += f"标题: {pdf_info['Title']}\n"
    if pdf_info.get("Abstract"):
        pdf_summary += f"摘要: {pdf_info['Abstract'][:500]}\n"
    if pdf_info.get("Core Contributions"):
        pdf_summary += f"核心贡献: {pdf_info['Core Contributions']}\n"
    
    # 构建证据段落文本
    passages_text = ""
    for i, passage in enumerate(passages, 1):
        passages_text += f"\n证据段落 {i}:\n{passage}\n"
    
    if language == 'zh':
        prompt = f"""你是一位学术问答专家。请基于以下论文信息和相关证据段落，回答用户的问题。

用户问题：{query}

论文信息：
{pdf_summary}

相关证据段落：
{passages_text}

请生成一个详细、准确、结构化的答案，要求：
1. **准确性**：答案必须基于论文中的实际内容，不能编造信息
2. **完整性**：答案应该全面回答用户的问题，包括必要的细节和解释
3. **结构化**：使用Markdown格式，合理使用标题、列表等格式
4. **引用**：在答案中引用具体的证据段落（例如："根据段落1..."或"如段落2所示..."）
5. **清晰性**：答案应该清晰易懂，逻辑连贯

请直接开始回答，不要包含"根据"、"基于"等介绍性短语，也不要包含关于写作过程的元评论。"""
    else:
        prompt = f"""You are an expert in academic Q&A. Please answer the user's question based on the following paper information and relevant evidence passages.

User Question: {query}

Paper Information:
{pdf_summary}

Relevant Evidence Passages:
{passages_text}

Please generate a detailed, accurate, and structured answer with the following requirements:
1. **Accuracy**: The answer must be based on the actual content in the paper, and cannot fabricate information
2. **Completeness**: The answer should comprehensively answer the user's question, including necessary details and explanations
3. **Structure**: Use Markdown format with appropriate headings, lists, etc.
4. **Citations**: Cite specific evidence passages in the answer (e.g., "According to Passage 1..." or "As shown in Passage 2...")
5. **Clarity**: The answer should be clear, understandable, and logically coherent

Please start answering directly, without introductory phrases like "Based on" or "According to", and without meta-commentary about the writing process."""
    
    return prompt

