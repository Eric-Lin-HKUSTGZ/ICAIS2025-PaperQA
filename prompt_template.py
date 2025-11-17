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
    import re
    
    # 构建PDF信息摘要
    pdf_summary = ""
    if pdf_info.get("Title"):
        pdf_summary += f"标题: {pdf_info['Title']}\n"
    if pdf_info.get("Abstract"):
        pdf_summary += f"摘要: {pdf_info['Abstract'][:500]}\n"
    if pdf_info.get("Core Contributions"):
        pdf_summary += f"核心贡献: {pdf_info['Core Contributions']}\n"
    
    # 构建证据段落文本，并提取所有Section、Table、Figure信息
    passages_text = ""
    all_sections = set()
    all_tables = set()
    all_figures = set()
    
    for i, passage in enumerate(passages, 1):
        passages_text += f"\n[段落 {i}]:\n{passage}\n"
        
        # 提取Section信息（如Section 1, Section 3.2, Section 3.3.1等）
        section_pattern = r'Section\s+(\d+(?:\.\d+)*)'
        sections = re.findall(section_pattern, passage, re.IGNORECASE)
        for section in sections:
            all_sections.add(f"Section {section}")
        
        # 提取Table信息（如Table 1, Table 3等）
        table_pattern = r'Table\s+(\d+)'
        tables = re.findall(table_pattern, passage, re.IGNORECASE)
        for table in tables:
            all_tables.add(f"Table {table}")
        
        # 提取Figure信息（如Figure 1, Figure 2等）
        figure_pattern = r'Figure\s+(\d+)'
        figures = re.findall(figure_pattern, passage, re.IGNORECASE)
        for figure in figures:
            all_figures.add(f"Figure {figure}")
    
    # 构建提取到的引用信息列表（中英文版本）
    citation_info_zh = ""
    citation_info_en = ""
    if all_sections or all_tables or all_figures:
        # 中文版本
        citation_info_zh = "\n\n**从证据段落中提取到的具体引用位置（必须在答案中使用这些引用）：**\n"
        if all_sections:
            sorted_sections = sorted(all_sections, key=lambda x: [int(i) for i in x.split()[1].split('.')])
            citation_info_zh += f"- **Section引用**: {', '.join(sorted_sections)}\n"
        if all_tables:
            sorted_tables = sorted(all_tables, key=lambda x: int(x.split()[1]))
            citation_info_zh += f"- **Table引用**: {', '.join(sorted_tables)}\n"
        if all_figures:
            sorted_figures = sorted(all_figures, key=lambda x: int(x.split()[1]))
            citation_info_zh += f"- **Figure引用**: {', '.join(sorted_figures)}\n"
        citation_info_zh += "\n**重要**：以上是从证据段落中提取到的所有具体引用位置。在生成答案时，必须使用这些具体的引用位置，不能使用模糊的引用（如只引用'Section 3'而不引用'Section 3.2, Section 3.3'）。\n"
        
        # 英文版本
        citation_info_en = "\n\n**Specific Citation Locations Extracted from Evidence Passages (MUST use these citations in your answer):**\n"
        if all_sections:
            sorted_sections = sorted(all_sections, key=lambda x: [int(i) for i in x.split()[1].split('.')])
            citation_info_en += f"- **Section Citations**: {', '.join(sorted_sections)}\n"
        if all_tables:
            sorted_tables = sorted(all_tables, key=lambda x: int(x.split()[1]))
            citation_info_en += f"- **Table Citations**: {', '.join(sorted_tables)}\n"
        if all_figures:
            sorted_figures = sorted(all_figures, key=lambda x: int(x.split()[1]))
            citation_info_en += f"- **Figure Citations**: {', '.join(sorted_figures)}\n"
        citation_info_en += "\n**Important**: The above are all specific citation locations extracted from the evidence passages. When generating the answer, you MUST use these specific citation locations, and cannot use vague citations (e.g., citing only 'Section 3' instead of 'Section 3.2, Section 3.3').\n"
    
    citation_info = citation_info_zh if language == 'zh' else citation_info_en
    
    if language == 'zh':
        prompt = f"""你是一位学术问答专家。请基于以下论文信息和相关证据段落，回答用户的问题。

用户问题：{query}

论文信息：
{pdf_summary}

相关证据段落：
{passages_text}
{citation_info}

**重要提示**：以上段落是从PDF中提取的相关内容。请仔细分析每个段落，提取其中的Section、Table、Figure、Page等具体位置信息。在生成答案时，**必须使用这些具体位置进行引用，绝对不要使用"段落1"、"Passage 1"等模糊引用**。

**引用要求示例（必须严格遵守）**：
- 如果段落中提到"Section 3.2"、"Section 3.3"、"Section 3.3.1"、"Section 3.3.3"等，必须在答案中引用这些具体的子章节号
- 如果段落中提到"Table 1"、"Table 3"、"Figure 1"、"Figure 2"等，必须在答案中引用这些具体的表格和图表号
- 引用示例："(Section 1)"、"在Section 3.2中"、"Section 3.3, Section 3.3.1"、"如表1所示"、"如图2所示"、"Table 1, Table 3"等
- **绝对禁止**：只引用"Section 3"而不引用"Section 3.2"、"Section 3.3"等子章节；只引用"Section"而不引用具体的章节号

请生成一个详细、准确、结构化的答案，必须遵循以下要求（参考Modex风格的最佳实践）：

## 核心要求

1. **精炼准确的研究问题表述**：
   - **第一句话必须直接、精炼地回答研究问题**，避免冗长的介绍性文字
   - 研究问题或核心内容的表述必须精炼准确，一句话概括核心
   - 如果问题包含多个部分（如"研究问题"和"简要总结"），请分别清晰回答，但每个部分都要精炼

2. **结构清晰但不过度结构化**：
   - 使用Markdown格式，合理使用标题、子标题、列表等
   - 如果问题包含多个部分，使用明确的标题分隔（如"### 主要研究问题"、"### 论文简要总结"）
   - **但不要过度使用标题层级**，保持逻辑流畅，层次分明
   - 确保段落之间的逻辑连贯，自然过渡

3. **内容完整且突出核心创新**：
   - 全面回答用户的问题，包括必要的细节和解释
   - **必须突出论文的核心创新点和贡献**，明确说明论文的独特价值
   - 如果问题涉及研究方法，请详细描述方法的具体操作类型、步骤或机制
   - 如果问题涉及实验结果，请包含具体的数据、指标和数值

4. **引用具体且自然（严格要求，必须严格遵守）**：
   - **禁止使用Passage引用**（如"Passage 1"、"证据段落1"等），因为Passage引用不准确且模糊
   - **必须使用具体的章节、表格、图表或页面引用**：在答案中引用具体的Section、Table、Figure、Page等位置
   - **优先引用Section，包括子章节**（如Section 1、Section 3.2、Section 3.3、Section 3.3.1、Section 3.3.3、Section 4等），这是最准确和最有价值的引用方式
   - **如果证据段落中包含章节号、表格号、图表号或页面号**（如Section 3.3、Section 3.3.1、Table 1、Table 3、Figure 1、Figure 2、Page 5等），**必须在答案中引用这些具体位置，包括子章节号**
   - **引用要全面且具体**：
     - 如果段落中提到"Section 3.2"、"Section 3.3"、"Section 3.3.1"、"Section 3.3.3"等，**必须全部引用这些具体的子章节号**，不能只引用"Section 3"
     - 如果段落中提到"Table 1"、"Table 3"、"Figure 1"、"Figure 2"等，**必须全部引用这些具体的表格和图表号**
     - 示例：如果段落中提到"Section 3.2"和"Section 3.3"，答案中应该引用"Section 3.2, Section 3.3"，而不是只引用"Section 3"
   - 引用应该自然融入答案，不要生硬，例如："(Section 1)"、"在Section 3.2中"、"Section 3.3, Section 3.3.1"、"如表1所示"、"如图2所示"、"Table 1, Table 3"等
   - **如果证据段落中没有明确的Section、Table、Figure等信息，请仔细分析段落内容，尝试推断或提取可能的章节位置**，或者直接描述内容而不使用模糊的Passage引用
   - **检查清单**：生成答案后，请检查是否：
     - 引用了所有在段落中出现的具体Section号（包括子章节号）
     - 引用了所有在段落中出现的Table号和Figure号
     - 没有使用模糊的"Section 3"而应该使用"Section 3.2, Section 3.3"等具体引用

5. **数据完整且具体（严格要求）**：
   - 如果论文中包含具体的实验数据、性能指标、百分比等，**必须在答案中包含这些具体数值**
   - **必须包含所有关键数据**，包括但不限于：
     - 性能指标：medal rate（如36.4%）、gold medal rate（如18.7%）、valid submission rate（如96.4%）等
     - 实验设置：benchmark规模（如75 tasks）、时间预算（如12-hour budget）等
     - 对比数据：与baseline的对比结果、ablation study的结果等
   - **不要遗漏任何关键数据**：如果论文中提到了多个性能指标或实验数据，应该全部包含在答案中
   - 数据应该准确，不能编造，必须与论文中的数值完全一致
   - **数据引用要具体**：如果数据来自特定的Table或Figure，应该同时引用（如"Table 1显示..."、"如图2所示..."）

6. **方法描述详细且具体（严格要求）**：
   - 如果问题涉及方法，请详细描述方法的具体操作类型、步骤或机制
   - **必须说明方法的具体操作类型**，例如：如果涉及搜索算法，请说明具体的操作类型（如primary expansion、intra-branch evolution、cross-branch reference、multi-branch aggregation等）
   - **如果方法有多个组件或操作类型，必须全部列出并详细说明**（如使用编号列表：1) Primary expansion (standard parent-child generation), 2) Intra-branch evolution (learning from a branch's own history), 3) Cross-branch reference (learning from top nodes in other branches), 4) Multi-branch aggregation (fusing insights from multiple branches to spawn a new solution branch)）
   - **必须说明技术细节**：
     - 如果方法涉及graph structure，必须说明graph structure的定义和组成（如primary edges用于credit assignment，reference edges用于knowledge flow）
     - 如果方法涉及算法扩展（如从MCTS扩展到MCGS），必须说明扩展的具体机制（如"embedding a graph structure into the expansion phase"）
     - 如果方法涉及多个组件，必须说明每个组件的具体功能和贡献（如fine-grained operators：Draft, Debug, Improve, Fusion等）
   - **必须引用相应的章节**：描述方法时，必须引用相关的Section（如"Section 3.2"、"Section 3.3"、"Section 3.3.1"等）
   - **方法描述要完整**：不仅要说明"是什么"，还要说明"如何工作"和"为什么这样设计"

7. **分析深入且逻辑清晰**：
   - 不仅描述"是什么"，还要解释"为什么"和"如何"
   - 如果涉及实验结果，请分析成功和失败的模式
   - 如果涉及方法比较，请说明与现有方法的本质区别
   - **确保逻辑流畅**，从问题识别→解决方案→实验验证，形成完整的逻辑链

8. **禁止内容（严格禁止）**：
   - **绝对不要**包含工作流步骤信息（如"Step 1/5"、"步骤1/5"等）
   - **绝对不要**包含PDF解析过程信息（如"PDF decoded"、"Parsed pages"等）
   - **绝对不要**包含关于写作过程的元评论（如"我将..."、"让我..."等）
   - **绝对不要**使用冗长的介绍性短语（如"Based on a comprehensive analysis..."、"Based on the paper content..."、"根据提供的材料..."等）
   - **直接开始回答**，第一句话就应该是答案的核心内容

## 输出格式要求

- **直接开始回答**，不要任何介绍性文字（如"Based on..."、"根据..."等）
- 使用Markdown格式，合理使用标题、列表、加粗等
- 确保答案清晰、专业、易读
- **参考Modex风格**：精炼准确、引用具体、数据完整、方法详细、结构清晰

请现在开始生成答案。"""
    else:
        prompt = f"""You are an expert in academic Q&A. Please answer the user's question based on the following paper information and relevant evidence passages.

User Question: {query}

Paper Information:
{pdf_summary}

Relevant Evidence Passages:
{passages_text}
{citation_info}

**Important Note**: The above passages are relevant content extracted from the PDF. Please carefully analyze each passage and extract specific location information such as Section, Table, Figure, Page, etc. When generating the answer, **MUST use these specific locations for citations, NEVER use vague citations like "段落1" or "Passage 1"**.

**Citation Requirements Examples (Must Strictly Follow)**:
- If passages mention "Section 3.2", "Section 3.3", "Section 3.3.1", "Section 3.3.3", etc., MUST cite these specific subsection numbers in the answer
- If passages mention "Table 1", "Table 3", "Figure 1", "Figure 2", etc., MUST cite these specific table and figure numbers in the answer
- Citation examples: "(Section 1)", "in Section 3.2", "Section 3.3, Section 3.3.1", "as shown in Table 1", "as shown in Figure 2", "Table 1, Table 3", etc.
- **STRICTLY PROHIBITED**: Citing only "Section 3" without citing subsections like "Section 3.2", "Section 3.3"; citing only "Section" without specific section numbers

Please generate a detailed, accurate, and structured answer that MUST follow these requirements (following Modex-style best practices):

## Core Requirements

1. **Concise and Accurate Research Question Statement**:
   - **The first sentence MUST directly and concisely answer the research question**, avoiding verbose introductory text
   - Research questions or core content must be stated concisely and accurately, summarizing the core in one sentence
   - If the question contains multiple parts (e.g., "research question" and "brief summary"), answer each part clearly, but each part should be concise

2. **Clear Structure Without Over-Structuring**:
   - Use Markdown format with appropriate headings, subheadings, lists, etc.
   - If the question contains multiple parts, use clear headings to separate them (e.g., "### Main Research Problem", "### Brief Summarization")
   - **But do not overuse heading levels**, maintain logical flow and clear hierarchy
   - Ensure logical coherence between paragraphs with natural transitions

3. **Complete Content Highlighting Core Innovations**:
   - Comprehensively answer the user's question, including necessary details and explanations
   - **MUST highlight the paper's core innovations and contributions**, clearly stating the paper's unique value
   - If the question involves research methods, provide detailed descriptions of specific operation types, steps, or mechanisms
   - If the question involves experimental results, include specific data, metrics, and numerical values

4. **Specific and Natural Citations (Strict Requirements, Must Strictly Follow)**:
   - **NEVER use Passage citations** (e.g., "Passage 1", "证据段落1", etc.), as Passage citations are inaccurate and vague
   - **MUST use specific section, table, figure, or page citations**: Cite specific Section, Table, Figure, Page locations in the answer
   - **Prioritize Section citations, including subsections** (e.g., Section 1, Section 3.2, Section 3.3, Section 3.3.1, Section 3.3.3, Section 4, etc.), as this is the most accurate and valuable citation method
   - **If evidence passages contain section numbers, table numbers, figure numbers, or page numbers** (e.g., Section 3.3, Section 3.3.1, Table 1, Table 3, Figure 1, Figure 2, Page 5), **MUST cite these specific locations in the answer, including subsection numbers**
   - **Citations must be comprehensive and specific**:
     - If passages mention "Section 3.2", "Section 3.3", "Section 3.3.1", "Section 3.3.3", etc., **MUST cite all these specific subsection numbers**, not just "Section 3"
     - If passages mention "Table 1", "Table 3", "Figure 1", "Figure 2", etc., **MUST cite all these specific table and figure numbers**
     - Example: If passages mention "Section 3.2" and "Section 3.3", the answer should cite "Section 3.2, Section 3.3", not just "Section 3"
   - Citations should be naturally integrated into the answer, not forced, e.g., "(Section 1)", "in Section 3.2", "Section 3.3, Section 3.3.1", "as shown in Table 1", "as shown in Figure 2", "Table 1, Table 3", etc.
   - **If evidence passages do not contain explicit Section, Table, Figure information, carefully analyze the passage content to infer or extract possible section locations**, or directly describe the content without using vague Passage citations
   - **Checklist**: After generating the answer, please check:
     - Have you cited all specific Section numbers (including subsection numbers) that appear in the passages?
     - Have you cited all Table and Figure numbers that appear in the passages?
     - Have you avoided vague citations like "Section 3" when you should use "Section 3.2, Section 3.3"?

5. **Complete and Specific Data (Strict Requirements)**:
   - If the paper contains specific experimental data, performance metrics, percentages, etc., **MUST include these specific numerical values in the answer**
   - **MUST include all key data**, including but not limited to:
     - Performance metrics: medal rate (e.g., 36.4%), gold medal rate (e.g., 18.7%), valid submission rate (e.g., 96.4%), etc.
     - Experimental settings: benchmark scale (e.g., 75 tasks), time budget (e.g., 12-hour budget), etc.
     - Comparison data: comparison results with baselines, ablation study results, etc.
   - **Do not omit any key data**: If the paper mentions multiple performance metrics or experimental data, all should be included in the answer
   - Data must be accurate and cannot be fabricated, must exactly match the values in the paper
   - **Data citations must be specific**: If data comes from specific Tables or Figures, cite them (e.g., "as shown in Table 1...", "Figure 2 demonstrates...")

6. **Detailed and Specific Method Descriptions (Strict Requirements)**:
   - If the question involves methods, provide detailed descriptions of specific operation types, steps, or mechanisms
   - **MUST explain specific operation types**, e.g., if involving search algorithms, explain specific operation types (e.g., primary expansion, intra-branch evolution, cross-branch reference, multi-branch aggregation, etc.)
   - **If the method has multiple components or operation types, MUST list and explain all of them in detail** (e.g., using numbered lists: 1) Primary expansion (standard parent-child generation), 2) Intra-branch evolution (learning from a branch's own history), 3) Cross-branch reference (learning from top nodes in other branches), 4) Multi-branch aggregation (fusing insights from multiple branches to spawn a new solution branch))
   - **MUST explain technical details**:
     - If the method involves graph structure, MUST explain the definition and composition of the graph structure (e.g., primary edges for credit assignment, reference edges for knowledge flow)
     - If the method involves algorithm extensions (e.g., from MCTS to MCGS), MUST explain the specific extension mechanism (e.g., "embedding a graph structure into the expansion phase")
     - If the method involves multiple components, MUST explain the specific function and contribution of each component (e.g., fine-grained operators: Draft, Debug, Improve, Fusion, etc.)
   - **MUST cite corresponding sections**: When describing methods, MUST cite relevant Sections (e.g., "Section 3.2", "Section 3.3", "Section 3.3.1", etc.)
   - **Method descriptions must be complete**: Not only explain "what" but also "how it works" and "why it is designed this way"

7. **In-Depth Analysis with Clear Logic**:
   - Not only describe "what" but also explain "why" and "how"
   - If involving experimental results, analyze patterns of success and failure
   - If involving method comparisons, explain the essential differences from existing methods
   - **Ensure logical flow**, forming a complete logical chain from problem identification → solution → experimental validation

8. **Prohibited Content (Strictly Prohibited)**:
   - **NEVER** include workflow step information (e.g., "Step 1/5", "步骤1/5", etc.)
   - **NEVER** include PDF parsing process information (e.g., "PDF decoded", "Parsed pages", etc.)
   - **NEVER** include meta-commentary about the writing process (e.g., "I will...", "Let me...", etc.)
   - **NEVER** use verbose introductory phrases (e.g., "Based on a comprehensive analysis...", "Based on the paper content...", "According to the provided materials...", etc.)
   - **Start answering directly**, the first sentence should be the core content of the answer

## Output Format Requirements

- **Start answering directly** without any introductory text (e.g., "Based on...", "According to...", etc.)
- Use Markdown format with appropriate headings, lists, bold, etc.
- Ensure the answer is clear, professional, and readable
- **Follow Modex style**: concise and accurate, specific citations, complete data, detailed methods, clear structure

Please now generate the answer."""
    
    return prompt

