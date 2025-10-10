# FitAI RAG Pipeline - 快速启动指南

## 🚀 概述

FitAI RAG Pipeline 是一个基于Google Cloud Storage (GCS) 的云端RAG服务，提供智能的fitness和nutrition知识问答功能。

### ✨ 核心特性
- **云端存储**: 直接从GCS读取和处理txt文件
- **智能分块**: 支持字符分割、递归分割、语义分割
- **向量搜索**: 基于Google Vertex AI的嵌入向量
- **LLM对话**: 使用Gemini 2.0 Flash进行智能问答
- **持久化**: ChromaDB向量数据库持久化存储

## 🏗️ 架构说明

```
GCS文件 → 下载到内存 → 分块 → 生成嵌入向量 → 存储到ChromaDB → 智能问答
```

### 📊 数据流程
1. **GCS存储**: 原始txt文件存储在Google Cloud Storage
2. **内存处理**: 文件下载到内存进行分块和向量化
3. **向量存储**: 嵌入向量存储在ChromaDB中
4. **智能检索**: 基于语义相似度检索相关文档
5. **LLM生成**: 使用检索到的上下文生成专业回答

### 🔧 技术栈
- **FastAPI**: RESTful API服务
- **ChromaDB**: 向量数据库
- **Google Vertex AI**: 嵌入生成和LLM
- **Google Cloud Storage**: 文件存储
- **Docker**: 容器化部署

## 📡 API端点总览

| 端点 | 方法 | 描述 | 用途 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 检查服务状态 |
| `/process-gcs` | POST | 一键处理GCS文件 | 从GCS下载→分块→嵌入→存储 |
| `/query` | POST | 向量搜索 | 检索相关文档 |
| `/chat` | POST | LLM聊天 | 基于上下文的对话 |
| `/collections` | GET | 列出集合 | 查看可用数据集合 |




## 快速启动
### 1. 启动所有服务
```bash
# 在项目根目录运行
docker-compose up -d
```

### 2. 检查服务状态
```bash
docker-compose ps

# 检查RAG pipeline服务日志
docker-compose logs rag_pipeline
```

### 3. 测试API
```bash
# 检查服务健康状态
curl http://localhost:8002/health

# 查看可用集合
curl http://localhost:8002/collections
```


## 🚀 交互流程

### 步骤1: 准备GCS数据
确保txt文件已上传到Google Cloud Storage bucket中。

### 步骤2: 一键处理GCS文件
```bash
# 从GCS一键处理到ChromaDB
curl -X POST "http://localhost:8002/process-gcs" \
  -H "Content-Type: application/json" \
  -d '{
    "bucket_name": "fitai-data-bucket",
    "folder_path": "fitness-docs/",
    "method": "char-split"
  }'
```

**参数说明**:
- `bucket_name`: GCS存储桶名称
- `folder_path`: 文件夹路径（可选，留空表示根目录）
- `method`: 分块方法 (`char-split`, `recursive-split`, `semantic-split`)

### 步骤3: 智能问答
```bash
# 基于fitness知识的智能问答
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings about resistance training progression?",
    "method": "char-split",
    "n_results": 10
  }'
```

### 步骤4: 向量搜索
```bash
# 搜索相关文档片段
curl -X POST "http://localhost:8002/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "resistance training for beginners",
    "method": "char-split",
    "n_results": 5
  }'
```

