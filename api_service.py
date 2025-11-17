import os
import json
import time
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import signal
import sys
import warnings

from config import Config
from llm_client import LLMClient
from embedding_client import EmbeddingClient
from pdf_parser import PDFParser
from question_analyzer import QuestionAnalyzer
from passage_retriever import PassageRetriever
from answer_generator import AnswerGenerator
from prompt_template import detect_language

# 抑制Pydantic警告
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


def load_env_file(env_file: str):
    """加载环境变量文件"""
    if not os.path.isabs(env_file):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(current_dir, env_file)
    
    if os.path.exists(env_file):
        print(f"✓ 找到 .env 文件: {env_file}")
        loaded_count = 0
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"\'')
                    loaded_count += 1
        print(f"✓ 成功加载 {loaded_count} 个环境变量")
        return True
    else:
        print(f"⚠️ 警告: 未找到 .env 文件: {env_file}")
        return False


# 加载环境变量
load_env_file(".env")

# 创建FastAPI应用
app = FastAPI(
    title="ICAIS2025-PaperQA API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.middleware("http")
async def simple_log_middleware(request, call_next):
    """简化的日志中间件"""
    start_time = time.time()
    path = request.url.path
    
    if not path.startswith("/health"):
        print(f"📥 [{time.strftime('%H:%M:%S')}] {request.method} {path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        if not path.startswith("/health"):
            print(f"📤 [{time.strftime('%H:%M:%S')}] {request.method} {path} - {response.status_code} ({process_time:.3f}s)")
        return response
    except Exception as e:
        print(f"❌ [{time.strftime('%H:%M:%S')}] 错误: {request.method} {path} - {e}")
        raise

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 设置全局超时
REQUEST_TIMEOUT = Config.PAPER_QA_TIMEOUT  # 15分钟总超时


class PaperQARequest(BaseModel):
    query: str
    pdf_content: str


def format_sse_data(content: str) -> str:
    """生成OpenAI格式的SSE数据"""
    data = {
        "object": "chat.completion.chunk",
        "choices": [{
            "delta": {
                "content": content
            }
        }]
    }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def format_sse_done() -> str:
    """生成SSE结束标记"""
    return "data: [DONE]\n\n"


def stream_message(message: str, chunk_size: int = 1):
    """将消息按字符流式输出（同步生成器）"""
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        yield format_sse_data(chunk)


async def run_with_heartbeat(task_func, *args, heartbeat_interval=25, timeout=None, **kwargs):
    """
    执行长时间任务，期间定期发送心跳数据
    
    Args:
        task_func: 要执行的同步函数
        *args, **kwargs: 传递给函数的参数
        heartbeat_interval: 心跳间隔（秒），默认25秒
    
    Yields:
        心跳数据（空格字符）或任务结果
    """
    start_time = time.time()
    last_heartbeat = start_time
    
    # 创建任务（使用asyncio.to_thread将同步函数转换为协程）
    task = asyncio.create_task(asyncio.to_thread(task_func, *args, **kwargs))
    
    # 在任务执行期间定期发送心跳
    while not task.done():
        await asyncio.sleep(1)  # 每秒检查一次
        now = time.time()
        elapsed = now - last_heartbeat
        
        # 如果超过心跳间隔，发送心跳数据
        if elapsed >= heartbeat_interval:
            yield format_sse_data(" ")  # 发送一个空格作为心跳
            last_heartbeat = now
        
        if timeout is not None and (now - start_time) > timeout:
            task.cancel()
            raise asyncio.TimeoutError(f"任务执行超过 {timeout} 秒，已取消")
        
        # 检查任务是否完成
        if task.done():
            break
    
    # 等待任务完成并返回结果
    try:
        result = await task
        yield ("RESULT", result)
    except Exception as e:
        print(f"⚠️  任务执行失败: {e}")
        import traceback
        print(traceback.format_exc())
        raise e


async def _generate_answer_internal(query: str, pdf_content: str) -> AsyncGenerator[str, None]:
    """内部生成器函数，执行实际的问答逻辑"""
    start_time = time.time()
    
    try:
        # 先检测语言，用于后续消息模板
        language = await asyncio.to_thread(detect_language, query)
        
        # 根据语言设置消息模板
        if language == 'zh':
            msg_templates = {
                'step1': "### 📄 步骤 1/5: PDF解析与结构化提取\n\n✅ 已完成\n\n",
                'step2': "### ❓ 步骤 2/5: 问题理解与关键词提取\n\n✅ 已完成\n\n",
                'step3': "### 🔍 步骤 3/5: 相关段落检索\n\n",
                'step4': "### 📊 步骤 4/5: 上下文构建与证据筛选\n\n",
                'step5': "### 📝 步骤 5/5: 答案生成\n\n",
                'final_title': "## 📄 答案\n\n",
                'error_config': "## ❌ 错误\n\n配置验证失败，请检查环境变量设置\n\n",
                'error_config_exception': lambda e: f"## ❌ 错误\n\n配置验证异常: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ 错误\n\nLLM客户端初始化失败: {e}\n\n",
                'error_embedding_init': lambda e: f"## ❌ 错误\n\nEmbedding客户端初始化失败: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ 错误\n\nPDF解析失败，无法继续: {e}\n\n",
                'error_question_analysis': lambda e: f"## ❌ 错误\n\n问题分析失败: {e}\n\n",
                'error_retrieval': lambda e: f"## ❌ 错误\n\n段落检索失败: {e}\n\n",
                'error_answer': lambda e: f"## ❌ 错误\n\n答案生成失败: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ 超时错误\n\n请求处理超过 {t} 秒，已自动终止\n\n",
                'error_general': lambda e: f"## ❌ 错误\n\n程序执行失败: {e}\n\n",
                'pdf_timeout': "⚠️ PDF解析超时，使用备用方法提取基本信息\n\n",
                'pdf_fallback': "基本信息提取完成\n\n"
            }
        else:
            msg_templates = {
                'step1': "### 📄 Step 1/5: PDF Parsing and Structure Extraction\n\n✅ Completed\n\n",
                'step2': "### ❓ Step 2/5: Question Understanding and Keyword Extraction\n\n✅ Completed\n\n",
                'step3': "### 🔍 Step 3/5: Relevant Passage Retrieval\n\n",
                'step4': "### 📊 Step 4/5: Context Building and Evidence Filtering\n\n",
                'step5': "### 📝 Step 5/5: Answer Generation\n\n",
                'final_title': "## 📄 Answer\n\n",
                'error_config': "## ❌ Error\n\nConfiguration validation failed. Please check environment variables.\n\n",
                'error_config_exception': lambda e: f"## ❌ Error\n\nConfiguration validation exception: {e}\n\n",
                'error_llm_init': lambda e: f"## ❌ Error\n\nLLM client initialization failed: {e}\n\n",
                'error_embedding_init': lambda e: f"## ❌ Error\n\nEmbedding client initialization failed: {e}\n\n",
                'error_pdf_parse': lambda e: f"## ❌ Error\n\nPDF parsing failed. Cannot continue: {e}\n\n",
                'error_question_analysis': lambda e: f"## ❌ Error\n\nQuestion analysis failed: {e}\n\n",
                'error_retrieval': lambda e: f"## ❌ Error\n\nPassage retrieval failed: {e}\n\n",
                'error_answer': lambda e: f"## ❌ Error\n\nAnswer generation failed: {e}\n\n",
                'error_timeout': lambda t: f"## ❌ Timeout Error\n\nRequest processing exceeded {t} seconds. Automatically terminated.\n\n",
                'error_general': lambda e: f"## ❌ Error\n\nProcess execution failed: {e}\n\n",
                'pdf_timeout': "⚠️ PDF parsing timeout, using fallback method to extract basic information\n\n",
                'pdf_fallback': "Basic information extraction completed\n\n"
            }
        
        # 验证配置
        try:
            config_valid = await asyncio.to_thread(Config.validate_config)
            if not config_valid:
                for chunk in stream_message(msg_templates['error_config']):
                    yield chunk
                return
        except Exception as e:
            for chunk in stream_message(msg_templates['error_config_exception'](e)):
                yield chunk
            return
        
        # 创建组件
        try:
            llm_client = LLMClient()
        except Exception as e:
            for chunk in stream_message(msg_templates['error_llm_init'](e)):
                yield chunk
            return
        
        try:
            embedding_client = EmbeddingClient()
        except Exception as e:
            # Embedding客户端失败不影响主要流程，只记录警告
            print(f"⚠️  Embedding客户端初始化失败: {e}，将跳过段落检索")
            embedding_client = None
        
        pdf_parser = PDFParser(llm_client)
        question_analyzer = QuestionAnalyzer(llm_client, language=language)
        passage_retriever = PassageRetriever(embedding_client) if embedding_client else None
        answer_generator = AnswerGenerator(llm_client, language=language)
        
        # 步骤1: PDF解析与结构化提取
        structured_info = None
        parse_timeout = Config.PDF_PARSE_TIMEOUT * 2
        heartbeat_interval = 20
        try:
            async for item in run_with_heartbeat(
                pdf_parser.parse,
                pdf_content,
                parse_timeout,
                language,
                heartbeat_interval=heartbeat_interval,
                timeout=parse_timeout + 10
            ):
                if isinstance(item, tuple) and item[0] == "RESULT":
                    structured_info = item[1]
                    break
                else:
                    yield item
        except asyncio.TimeoutError:
            for chunk in stream_message(msg_templates['pdf_timeout']):
                yield chunk
            # 超时时，尝试提取基本信息
            try:
                pdf_bytes = await asyncio.to_thread(pdf_parser.decode_base64_pdf, pdf_content)
                pdf_text = await asyncio.to_thread(pdf_parser.extract_text_from_pdf, pdf_bytes)
                structured_info = {
                    "raw_text": pdf_text[:10000],
                    "Title": "",
                    "Abstract": pdf_text[:500] if len(pdf_text) > 0 else "",
                    "error": "PDF结构化解析超时，已使用备用方法提取基本信息"
                }
                lines = pdf_text.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200:
                        structured_info["Title"] = line
                        break
                if not structured_info["Title"]:
                    structured_info["Title"] = pdf_text[:100].strip().replace('\n', ' ')
                for chunk in stream_message(msg_templates['pdf_fallback']):
                    yield chunk
            except Exception as e:
                for chunk in stream_message(msg_templates['error_pdf_parse'](e)):
                    yield chunk
                return
        except Exception as e:
            for chunk in stream_message(msg_templates['error_pdf_parse'](e)):
                yield chunk
            return
        
        if structured_info is None:
            for chunk in stream_message(msg_templates['error_pdf_parse']("PDF parsing returned empty result")):
                yield chunk
            return
        
        for chunk in stream_message(msg_templates['step1']):
            yield chunk
        
        # 步骤2: 问题理解与关键词提取
        question_analysis = None
        question_timeout = Config.QUESTION_ANALYSIS_TIMEOUT
        try:
            async for item in run_with_heartbeat(
                question_analyzer.analyze_question,
                query,
                heartbeat_interval=15,
                timeout=question_timeout + 5
            ):
                if isinstance(item, tuple) and item[0] == "RESULT":
                    question_analysis = item[1]
                    break
                else:
                    yield item
        except Exception as e:
            for chunk in stream_message(msg_templates['error_question_analysis'](e)):
                yield chunk
            return
        
        if question_analysis is None:
            for chunk in stream_message(msg_templates['error_question_analysis']("Question analysis returned empty result")):
                yield chunk
            return
        
        for chunk in stream_message(msg_templates['step2']):
            yield chunk
        
        # 步骤3: 相关段落检索（使用心跳机制）
        passages_with_scores = []
        for chunk in stream_message(msg_templates['step3']):
            yield chunk
        try:
            if passage_retriever:
                # 获取PDF原始文本
                pdf_text = structured_info.get("raw_text", "")
                if not pdf_text:
                    # 如果没有raw_text，尝试从其他字段构建
                    pdf_text = "\n".join([
                        structured_info.get("Abstract", ""),
                        structured_info.get("Introduction", ""),
                        structured_info.get("Methodology", ""),
                        structured_info.get("Results", ""),
                        structured_info.get("Conclusion", "")
                    ])
                
                if not pdf_text or len(pdf_text.strip()) < 100:
                    # 如果文本太短，使用全文
                    pdf_text = structured_info.get("raw_text", "")
                
                # 使用心跳机制执行段落检索
                async for item in run_with_heartbeat(
                    _retrieve_passages,
                    passage_retriever,
                    query,
                    pdf_text,
                    heartbeat_interval=25,
                    timeout=Config.PASSAGE_RETRIEVAL_TIMEOUT + 10
                ):
                    if isinstance(item, tuple) and item[0] == "RESULT":
                        passages_with_scores = item[1]
                        break
                    else:
                        yield item
            else:
                # 如果embedding客户端未初始化，使用全文作为上下文
                pdf_text = structured_info.get("raw_text", "")
                if pdf_text:
                    # 简单分块，不使用embedding
                    chunk_size = Config.CHUNK_SIZE
                    chunks = []
                    for i in range(0, len(pdf_text), chunk_size):
                        chunks.append(pdf_text[i:i+chunk_size])
                    # 返回前几个chunks
                    passages_with_scores = [(chunk, 0.0) for chunk in chunks[:Config.TOP_K_PASSAGES]]
        except Exception as e:
            for chunk in stream_message(msg_templates['error_retrieval'](e)):
                yield chunk
            # 如果检索失败，使用空列表
            passages_with_scores = []
        
        # 提取段落文本
        passages = [passage for passage, _ in passages_with_scores] if passages_with_scores else []
        
        # 步骤4: 上下文构建与证据筛选（使用心跳机制）
        for chunk in stream_message(msg_templates['step4']):
            yield chunk
        
        # 步骤5: 答案生成（使用心跳机制）
        for chunk in stream_message(msg_templates['step5']):
            yield chunk
        
        # 发送最终答案标题
        for chunk in stream_message(msg_templates['final_title']):
            yield chunk
        
        try:
            # 使用心跳机制生成答案
            async for item in run_with_heartbeat(
                answer_generator.generate_answer,
                query,
                structured_info,
                passages,
                heartbeat_interval=25,
                timeout=Config.ANSWER_GENERATION_TIMEOUT + 20
            ):
                if isinstance(item, tuple) and item[0] == "RESULT":
                    answer = item[1]
                    break
                else:
                    yield item
            
            # 流式输出答案
            if answer:
                for chunk in stream_message(answer):
                    yield chunk
            else:
                error_msg = msg_templates['error_answer']("生成的答案为空")
                for chunk in stream_message(error_msg):
                    yield chunk
        except Exception as e:
            for chunk in stream_message(msg_templates['error_answer'](e)):
                yield chunk
            return
        
        # 发送结束标记
        yield format_sse_done()
        
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        error_msg = msg_templates['error_timeout'](int(elapsed))
        for chunk in stream_message(error_msg):
            yield chunk
        yield format_sse_done()
    except Exception as e:
        error_msg = msg_templates['error_general'](str(e))
        for chunk in stream_message(error_msg):
            yield chunk
        yield format_sse_done()


def _retrieve_passages(passage_retriever, query: str, pdf_text: str):
    """检索段落的同步函数（用于run_with_heartbeat）"""
    if not passage_retriever:
        return []
    
    # 文本分块
    chunks = passage_retriever.chunk_text(pdf_text)
    
    # 检索相关段落
    passages_with_scores = passage_retriever.retrieve_relevant_passages(query, chunks)
    
    return passages_with_scores


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "ICAIS2025-PaperQA API"}


@app.post("/paper_qa")
async def paper_qa(request: PaperQARequest):
    """
    文献问答API端点
    
    Args:
        request: 包含query和pdf_content的请求对象
    
    Returns:
        SSE流式响应
    """
    try:
        # 验证输入
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.pdf_content or not request.pdf_content.strip():
            raise HTTPException(status_code=400, detail="PDF content cannot be empty")
        
        # 创建流式响应
        return StreamingResponse(
            _generate_answer_internal(request.query, request.pdf_content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("HOST_PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

