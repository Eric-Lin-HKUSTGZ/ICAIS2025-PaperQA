# ICAIS2025-PaperQA

文献问答API服务 - 基于直接pipeline流程的智能文献问答系统

## 文件结构

```
ICAIS2025-PaperQA/
├── api_service.py          # FastAPI主应用
├── config.py               # 配置管理
├── llm_client.py           # LLM客户端
├── embedding_client.py     # Embedding客户端
├── pdf_parser.py           # PDF解析模块
├── question_analyzer.py    # 问题分析模块
├── passage_retriever.py    # 段落检索模块
├── answer_generator.py     # 答案生成模块
├── prompt_template.py      # Prompt模板
├── test_api.py             # API测试脚本
├── requirements.txt        # 依赖包
├── Dockerfile              # Docker配置
├── docker-compose.yml      # Docker Compose配置
├── .env.example            # 环境变量示例
└── README.md               # 项目说明
```

## 系统概述

本系统是一个创新的文献问答API服务，通过5步直接pipeline流程，基于单篇PDF文档，生成高质量的问题答案。

### 核心特点

1. **直接pipeline流程**：区别于多智能体架构，采用无状态、一次性的直接流程
2. **单篇PDF问答**：专注于单篇PDF文档的问答，不需要检索外部论文
3. **智能段落检索**：基于embedding相似度检索最相关的段落作为证据
4. **语言自适应**：自动检测用户查询语言（中文/英文），所有输出适配用户语言
5. **心跳机制**：防止客户端请求超时，确保长时间任务正常完成

## 系统架构

```
用户问题 + PDF → PDF解析 → 问题理解 → 段落检索 → 证据筛选 → 答案生成
```

## API接口

### 端点

```
POST http://<agent_service_host>:3000/paper_qa
```

### 请求格式

```json
{
  "query": "Please carefully analyze and explain the reinforcement learning training methods used in this article.",
  "pdf_content": "base64_encoded_pdf_string"
}
```

### 响应格式

SSE流式输出，OpenAI兼容格式：

```
data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"..."}}]}
data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"..."}}]}
...
data: [DONE]
```

### 输出结构

```markdown
## 答案

[基于PDF内容的详细答案，包含引用和结构化格式]
```

## 环境配置

### 必需的环境变量

```bash
# LLM服务配置
SCI_MODEL_BASE_URL=https://api.example.com/v1
SCI_MODEL_API_KEY=your_api_key
SCI_LLM_MODEL=deepseek-ai/DeepSeek-V3
SCI_LLM_REASONING_MODEL=deepseek-ai/DeepSeek-Reasoner

# Embedding服务配置
SCI_EMBEDDING_BASE_URL=https://api.example.com/v1
SCI_EMBEDDING_API_KEY=your_embedding_api_key
SCI_EMBEDDING_MODEL=jinaai/jina-embeddings-v3
```

### 可选的环境变量

```bash
# 端口配置
HOST_PORT=3000

# 超时配置（秒）
PAPER_QA_TIMEOUT=900  # 15分钟总超时
PDF_PARSE_TIMEOUT=180
QUESTION_ANALYSIS_TIMEOUT=60
PASSAGE_RETRIEVAL_TIMEOUT=120
EVIDENCE_FILTERING_TIMEOUT=120
ANSWER_GENERATION_TIMEOUT=300

# 文本分块配置
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_PASSAGES=8
```

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制`.env.example`为`.env`并填写配置：

```bash
cp .env.example .env
# 编辑.env文件，填入你的API密钥等信息
```

### 3. 运行服务

```bash
python api_service.py
```

服务将在 `http://localhost:3000` 启动

## 测试

项目提供了 `test_api.py` 测试脚本，用于测试文献问答API的流式响应。

### 基本用法

```bash
# 使用默认查询测试
python test_api.py --txt test.pdf.txt

# 指定查询
python test_api.py --txt test.pdf.txt --query "What are the main contributions of this paper?"

# 使用中文查询
python test_api.py --txt test.pdf.txt --query "这篇论文的主要贡献是什么？"

# 指定API URL
python test_api.py --txt test.pdf.txt --url http://localhost:3000/paper_qa

# 保存响应到文件
python test_api.py --txt test.pdf.txt --output answer_result.txt

# 启用调试模式
python test_api.py --txt test.pdf.txt --debug
```

### 命令行参数

- `--url`: API端点URL（默认: `http://localhost:3000/paper_qa`）
- `--txt`: 包含base64编码PDF的txt文件路径（必需）
- `--query`: 查询字符串
- `--output`: 输出文件路径（可选，保存完整响应到文件）
- `--debug`: 启用调试模式，显示原始SSE数据和解析过程

## 容器化部署

系统支持使用 Docker 和 Docker Compose 进行容器化部署。

### 前置要求

1. **Docker 和 Docker Compose**：确保已安装并运行
   - 如果使用 colima，确保 colima 已启动：`colima start`
   - 如果使用 Docker Desktop，确保 Docker Desktop 正在运行

2. **基础镜像**：已通过 colima 拉取华为云镜像
   ```bash
   docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-bookworm
   ```

3. **创建标签**：通过docker tag将华为云 SWR 的镜像重新打标签为 Docker Hub 官方格式
   ```bash
   docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-bookworm python:3.12-slim-bookworm
   ```

### 部署步骤

#### 1. 配置环境变量

确保已创建 `.env` 文件并配置了必要的环境变量（参考上方"环境配置"章节）。

#### 2. 构建 Docker 镜像

```bash
docker-compose build
```

**说明**：
- Dockerfile 已配置使用华为云镜像：`python:3.12-slim-bookworm`
- 构建过程会自动安装 Python 依赖（使用清华镜像源加速）

#### 3. 启动服务

```bash
docker-compose up -d
```

**说明**：
- `-d` 参数表示后台运行
- 服务将在端口 3000 上启动（可通过 `HOST_PORT` 环境变量修改）

#### 4. 查看服务状态

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看最近 100 行日志
docker-compose logs --tail=100
```

#### 5. 验证服务

**健康检查**：
```bash
curl http://localhost:3000/health
```

预期响应：
```json
{
  "status": "ok",
  "service": "ICAIS2025-PaperQA API"
}
```

**查看 API 文档**：
访问：http://localhost:3000/docs

**测试 API 端点**：
```bash
curl -X POST http://localhost:3000/paper_qa \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main contributions?",
    "pdf_content": "base64_encoded_pdf_content"
  }' \
  --no-buffer
```

### 常用操作

#### 停止服务
```bash
docker-compose down
```

#### 重启服务
```bash
docker-compose restart
```

#### 重新构建并启动
```bash
docker-compose up -d --build
```

#### 查看实时日志
```bash
docker-compose logs -f app
```

#### 进入容器
```bash
docker-compose exec app /bin/bash
```

#### 清理资源
```bash
# 停止并删除容器
docker-compose down

# 停止并删除容器、网络、卷
docker-compose down -v

# 删除镜像（谨慎使用）
docker rmi icais2025-paperqa:latest
```

### 容器配置说明

#### 端口配置

默认端口映射：`3000:3000`（主机端口:容器端口）

可通过环境变量修改：
```bash
# 在 .env 文件中设置
HOST_PORT=8080
```

或在 `docker-compose.yml` 中直接修改：
```yaml
ports:
  - "8080:3000"  # 主机端口:容器端口
```

#### 环境变量

所有配置通过 `.env` 文件管理，支持的环境变量请参考上方"环境配置"章节。

**重要环境变量**：
- `SCI_MODEL_BASE_URL`：LLM API 端点（必需）
- `SCI_MODEL_API_KEY`：LLM API 密钥（必需）
- `SCI_LLM_MODEL`：LLM 模型名称
- `SCI_LLM_REASONING_MODEL`：推理模型名称
- `SCI_EMBEDDING_BASE_URL`：Embedding API 端点
- `SCI_EMBEDDING_API_KEY`：Embedding API 密钥
- `SCI_EMBEDDING_MODEL`：Embedding 模型名称
- `HOST_PORT`：主机端口（默认：3000）

#### 资源限制

如需限制容器资源使用，可在 `docker-compose.yml` 中添加：

```yaml
services:
  app:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### 故障排除

#### 常见问题

1. **端口已被占用**
   - 错误：`bind: address already in use`
   - 解决：修改 `HOST_PORT` 环境变量或停止占用端口的服务

2. **容器无法启动**
   - 检查日志：`docker-compose logs app`
   - 检查环境变量配置是否正确
   - 确认 `.env` 文件存在且格式正确

3. **依赖安装失败**
   - 检查网络连接
   - 确认 Dockerfile 中的镜像源配置正确
   - 尝试手动构建：`docker build -t icais2025-paperqa:latest .`

4. **服务响应超时**
   - 检查容器资源使用：`docker stats`
   - 增加超时配置（在 `.env` 文件中）
   - 检查 LLM 和 Embedding API 的连接状态

5. **API调用失败**
   - 检查环境变量中的API密钥是否正确
   - 检查网络连接是否正常
   - 查看容器日志：`docker-compose logs -f app`

### 更新服务

当代码更新后，需要重新构建并启动服务：

```bash
# 停止当前服务
docker-compose down

# 重新构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

或使用一条命令：
```bash
docker-compose up -d --build
```

**注意**：如果只修改了环境变量（`.env` 文件），只需重启服务即可，无需重新构建：
```bash
docker-compose restart
```

### 生产环境建议

1. **使用反向代理**：建议使用 Nginx 或 Traefik 作为反向代理
2. **配置 HTTPS**：使用 SSL/TLS 证书保护 API 端点
3. **监控和日志**：配置日志收集和监控系统
4. **资源限制**：根据实际负载设置合理的资源限制
5. **健康检查**：配置容器健康检查，自动重启异常容器
6. **备份配置**：定期备份 `.env` 配置文件

## 系统流程

### 步骤1: PDF解析与结构化提取

- 解码Base64编码的PDF
- 提取PDF文本内容
- 使用LLM进行结构化解析（标题、摘要、章节等）
- 输出：结构化的PDF信息

### 步骤2: 问题理解与关键词提取

- 分析用户问题，理解问题意图
- 提取问题中的关键概念和关键词
- 识别问题类型（事实性、分析性、比较性等）
- 输出：问题分析结果、关键词列表

### 步骤3: 相关段落检索

- 将PDF文本分块（chunking）
- 使用embedding计算问题与每个文本块的相似度
- 检索最相关的段落（top-k）
- 输出：相关段落列表及其相似度分数

### 步骤4: 上下文构建与证据筛选

- 整合检索到的相关段落
- 使用LLM对段落进行重新评分和筛选
- 构建包含上下文的prompt
- 输出：筛选后的证据段落

### 步骤5: 答案生成

- 基于问题、PDF结构化信息和证据段落生成答案
- 使用reasoning model确保答案质量
- 生成Markdown格式的结构化答案
- 输出：完整的答案（包含引用）

## 关键设计

### 1. 文本分块与检索

- **分块策略**：将PDF文本分块（chunk_size=1000, overlap=200）
- **相似度计算**：使用embedding计算余弦相似度
- **Top-K检索**：检索最相关的段落（默认top-8）

### 2. 语言自动识别

- 基于中文字符占比自动检测语言
- 所有LLM调用自动使用相应语言
- 确保输入输出语言一致

### 3. 心跳机制

- 在步骤3、4、5（耗时较长的步骤）使用心跳机制
- 每25秒发送空数据chunk（`" "`）防止客户端超时
- 确保长时间任务能够正常完成

### 4. 错误处理与超时

- PDF解析超时：使用fallback方法提取基本信息
- 段落检索失败：使用全文作为上下文
- 所有错误消息都适配用户语言

## 与paper-qa的区别

1. **架构差异**：直接pipeline vs 多智能体架构
2. **状态管理**：无状态API vs 会话管理
3. **执行方式**：一次性完成 vs 分阶段交互
4. **数据范围**：单篇PDF vs 多论文检索
5. **工具系统**：固定流程 vs 动态工具调用

## 技术栈

- **Web框架**：FastAPI
- **流式响应**：SSE (Server-Sent Events)
- **异步处理**：asyncio
- **LLM集成**：自定义API端点
- **Embedding**：OpenAI兼容API
- **PDF处理**：pdfplumber
- **容器化**：Docker + Docker Compose

## 许可证

本项目仅供学习和研究使用。
