"""
问题分析器 - 负责问题理解、关键词提取、问题类型识别
"""
from typing import Dict, List
from llm_client import LLMClient
from prompt_template import get_question_analysis_prompt
from config import Config


class QuestionAnalyzer:
    """问题分析器"""
    
    def __init__(self, llm_client: LLMClient, language: str = 'en'):
        self.llm_client = llm_client
        self.language = language
        self.config = Config
    
    def analyze_question(self, query: str) -> Dict[str, str]:
        """分析问题，提取关键词和问题类型
        
        Args:
            query: 用户问题
        
        Returns:
            问题分析结果字典，包含问题类型、关键词、意图理解等
        """
        prompt = get_question_analysis_prompt(query, self.language)
        
        # 使用推理模型进行深度理解
        response = self.llm_client.get_response(
            prompt=prompt,
            use_reasoning_model=True,
            timeout=self.config.QUESTION_ANALYSIS_TIMEOUT * 2
        )
        
        # 解析响应，提取结构化信息
        analysis_result = self._parse_analysis_response(response)
        
        return analysis_result
    
    def _parse_analysis_response(self, response: str) -> Dict[str, str]:
        """解析分析响应，提取结构化信息"""
        analysis_result = {
            "raw_response": response,
            "question_type": "",
            "keywords": [],
            "intent": "",
            "answer_focus": ""
        }
        
        # 尝试提取各个字段
        lines = response.split('\n')
        current_field = None
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # 检查是否是字段标题
            if '问题类型' in line_stripped or 'Question Type' in line_stripped:
                if current_field:
                    analysis_result[current_field] = "\n".join(current_content).strip()
                current_field = "question_type"
                current_content = []
                # 提取内容
                parts = line_stripped.split(':', 1)
                if len(parts) > 1:
                    current_content.append(parts[1].strip())
            elif '关键词' in line_stripped or 'Keyword' in line_stripped:
                if current_field:
                    analysis_result[current_field] = "\n".join(current_content).strip()
                current_field = "keywords"
                current_content = []
                parts = line_stripped.split(':', 1)
                if len(parts) > 1:
                    current_content.append(parts[1].strip())
            elif '意图' in line_stripped or 'Intent' in line_stripped:
                if current_field:
                    analysis_result[current_field] = "\n".join(current_content).strip()
                current_field = "intent"
                current_content = []
                parts = line_stripped.split(':', 1)
                if len(parts) > 1:
                    current_content.append(parts[1].strip())
            elif '重点' in line_stripped or 'Focus' in line_stripped:
                if current_field:
                    analysis_result[current_field] = "\n".join(current_content).strip()
                current_field = "answer_focus"
                current_content = []
                parts = line_stripped.split(':', 1)
                if len(parts) > 1:
                    current_content.append(parts[1].strip())
            elif current_field:
                current_content.append(line_stripped)
        
        # 保存最后一个字段
        if current_field:
            analysis_result[current_field] = "\n".join(current_content).strip()
        
        # 解析关键词列表
        if analysis_result.get("keywords"):
            keywords_text = analysis_result["keywords"]
            # 尝试按逗号分割
            keywords = [kw.strip() for kw in keywords_text.split(',')]
            keywords = [kw for kw in keywords if kw]
            analysis_result["keywords"] = keywords[:5]  # 最多5个关键词
        
        return analysis_result

