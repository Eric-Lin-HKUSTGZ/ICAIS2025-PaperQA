"""
段落检索器 - 负责文本分块、embedding相似度计算、top-k段落检索
"""
from typing import List, Tuple
import numpy as np
from embedding_client import EmbeddingClient
from config import Config


class PassageRetriever:
    """段落检索器"""
    
    def __init__(self, embedding_client: EmbeddingClient):
        self.embedding_client = embedding_client
        self.config = Config
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """将文本分块
        
        Args:
            text: 原始文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小（字符数）
        
        Returns:
            文本块列表
        """
        chunk_size = chunk_size or self.config.CHUNK_SIZE
        overlap = overlap or self.config.CHUNK_OVERLAP
        
        if not text or len(text) <= chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # 尝试在句号、换行符等位置截断，避免截断句子
            if end < len(text):
                # 向后查找句号、换行符等，但优先查找段落分隔符（双换行）
                best_break = end
                found_paragraph_break = False
                
                # 首先查找段落分隔符（双换行），这是最好的截断点
                for i in range(min(500, len(text) - end)):
                    if end + i + 1 < len(text) and text[end + i:end + i + 2] == '\n\n':
                        best_break = end + i + 2
                        found_paragraph_break = True
                        break
                
                # 如果没有找到段落分隔符，查找单换行符
                if not found_paragraph_break:
                    for i in range(min(300, len(text) - end)):
                        if text[end + i] == '\n':
                            best_break = end + i + 1
                            break
                
                # 如果还是没有找到，查找句号、问号、感叹号
                if best_break == end:
                    for i in range(min(200, len(text) - end)):
                        if text[end + i] in ['.', '。', '!', '!', '?', '?']:
                            # 检查后面是否有空格或换行，确保是句子结束
                            if end + i + 1 < len(text) and text[end + i + 1] in [' ', '\n', '\t']:
                                best_break = end + i + 1
                                break
                
                end = best_break
                chunk = text[start:end]
            
            chunks.append(chunk.strip())
            
            # 移动到下一个块的起始位置（考虑overlap）
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def retrieve_relevant_passages(
        self, 
        query: str, 
        chunks: List[str], 
        top_k: int = None
    ) -> List[Tuple[str, float]]:
        """检索相关段落
        
        Args:
            query: 查询文本
            chunks: 文本块列表
            top_k: 返回top-k个最相关的段落
        
        Returns:
            (段落文本, 相似度分数) 的列表，按相似度从高到低排序
        """
        if not chunks:
            return []
        
        top_k = top_k or self.config.TOP_K_PASSAGES
        
        try:
            # 获取query的embedding
            query_embedding = self.embedding_client.encode(query)
            if query_embedding is None or len(query_embedding) == 0:
                # 如果embedding失败，返回前top_k个chunks
                return [(chunk, 0.0) for chunk in chunks[:top_k]]
            
            # 获取所有chunks的embeddings
            chunk_embeddings = self.embedding_client.encode(chunks)
            if chunk_embeddings is None or len(chunk_embeddings) == 0:
                return [(chunk, 0.0) for chunk in chunks[:top_k]]
            
            # 计算相似度（余弦相似度）
            similarities = []
            query_norm = np.linalg.norm(query_embedding)
            
            for i, chunk_embedding in enumerate(chunk_embeddings):
                if chunk_embedding is None or len(chunk_embedding) == 0:
                    similarities.append((i, 0.0))
                    continue
                
                # 计算余弦相似度
                chunk_norm = np.linalg.norm(chunk_embedding)
                if query_norm == 0 or chunk_norm == 0:
                    similarity = 0.0
                else:
                    dot_product = np.dot(query_embedding, chunk_embedding)
                    similarity = dot_product / (query_norm * chunk_norm)
                
                similarities.append((i, similarity))
            
            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # 返回top-k个最相关的段落
            result = []
            for idx, similarity in similarities[:top_k]:
                result.append((chunks[idx], similarity))
            
            return result
            
        except Exception as e:
            print(f"⚠️  段落检索失败: {e}，返回前{top_k}个段落")
            # 如果检索失败，返回前top_k个chunks
            return [(chunk, 0.0) for chunk in chunks[:top_k]]

