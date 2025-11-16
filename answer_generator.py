"""
答案生成器 - 基于问题、PDF信息和证据段落生成答案
"""
from typing import List, Dict
from llm_client import LLMClient
from prompt_template import get_answer_generation_prompt, get_evidence_filtering_prompt
from config import Config


class AnswerGenerator:
    """答案生成器"""
    
    def __init__(self, llm_client: LLMClient, language: str = 'en'):
        self.llm_client = llm_client
        self.language = language
        self.config = Config
    
    def filter_evidence(self, query: str, passages: List[str]) -> List[str]:
        """筛选证据段落
        
        Args:
            query: 用户问题
            passages: 检索到的段落列表
        
        Returns:
            筛选后的段落列表
        """
        if not passages:
            return []
        
        try:
            prompt = get_evidence_filtering_prompt(query, passages, self.language)
            
            # 使用推理模型进行证据筛选
            response = self.llm_client.get_response(
                prompt=prompt,
                use_reasoning_model=True,
                timeout=self.config.EVIDENCE_FILTERING_TIMEOUT * 2
            )
            
            # 解析响应，提取选中的段落
            filtered_passages = self._parse_filtering_response(response, passages)
            
            return filtered_passages if filtered_passages else passages[:5]  # 如果解析失败，返回前5个
            
        except Exception as e:
            print(f"⚠️  证据筛选失败: {e}，使用所有段落")
            return passages[:8]  # 如果筛选失败，返回前8个段落
    
    def _parse_filtering_response(self, response: str, original_passages: List[str]) -> List[str]:
        """解析筛选响应，提取选中的段落"""
        # 尝试从响应中提取段落编号
        import re
        
        # 查找段落编号（如"段落1"、"段落 1"、"Passage 1"等）
        pattern = r'段落\s*(\d+)|Passage\s*(\d+)'
        matches = re.findall(pattern, response)
        
        selected_indices = []
        for match in matches:
            idx = int(match[0] or match[1]) - 1  # 转换为0-based索引
            if 0 <= idx < len(original_passages):
                selected_indices.append(idx)
        
        # 去重并保持顺序
        selected_indices = list(dict.fromkeys(selected_indices))
        
        # 返回选中的段落
        if selected_indices:
            return [original_passages[i] for i in selected_indices]
        
        # 如果无法解析，返回前5个段落
        return original_passages[:5]
    
    def generate_answer(self, query: str, pdf_info: Dict[str, str], passages: List[str]) -> str:
        """生成答案
        
        Args:
            query: 用户问题
            pdf_info: PDF结构化信息
            passages: 证据段落列表
        
        Returns:
            生成的答案（Markdown格式）
        """
        # 先筛选证据段落
        try:
            filtered_passages = self.filter_evidence(query, passages)
        except Exception as e:
            print(f"⚠️  证据筛选失败: {e}，使用所有段落")
            filtered_passages = passages[:8] if passages else []
        
        # 如果没有段落，使用PDF信息
        if not filtered_passages:
            # 尝试从PDF信息中提取一些文本作为上下文
            context_parts = []
            if pdf_info.get("Abstract"):
                context_parts.append(pdf_info["Abstract"][:500])
            if pdf_info.get("Introduction"):
                context_parts.append(pdf_info["Introduction"][:500])
            if pdf_info.get("Methodology"):
                context_parts.append(pdf_info["Methodology"][:500])
            if context_parts:
                filtered_passages = context_parts
        
        # 生成答案
        prompt = get_answer_generation_prompt(query, pdf_info, filtered_passages, self.language)
        
        # 使用推理模型生成高质量答案
        answer = self.llm_client.get_response(
            prompt=prompt,
            use_reasoning_model=True,
            timeout=self.config.ANSWER_GENERATION_TIMEOUT * 2
        )
        
        return answer

