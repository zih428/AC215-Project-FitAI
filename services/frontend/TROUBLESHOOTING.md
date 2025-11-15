# 故障排查指南 - RAG Pipeline 连接问题

## 问题：显示 "Cannot connect to RAG Pipeline"

### 原因分析

前端显示 disconnected 通常是因为：
1. **RAG Pipeline 服务没有运行**（最常见）
2. **Docker 没有启动**
3. **端口被占用或配置错误**
4. **CORS 跨域问题**

---

## 解决方案

### 方案1：使用 Docker Compose 启动（推荐）

#### 步骤1：启动 Docker Desktop
- macOS: 打开 Docker Desktop 应用
- 等待 Docker 完全启动（状态栏显示 "Docker is running"）

#### 步骤2：启动所有服务
```bash
cd /Users/xuan/Desktop/Harvard-MIT-Course/AC215/AC215-Project-FitAI
docker compose up -d
```

#### 步骤3：检查服务状态
```bash
# 查看所有运行中的容器
docker ps

# 应该看到：
# - fitai-rag-pipeline (端口 8002)
# - llm-rag-chromadb (端口 8000)
```

#### 步骤4：检查服务日志
```bash
# 查看 RAG Pipeline 日志
docker logs fitai-rag-pipeline

# 如果看到错误，检查：
docker logs fitai-rag-pipeline -f
```

#### 步骤5：测试连接
```bash
# 测试健康检查
curl http://localhost:8002/health

# 应该返回：
# {"status":"ok","service":"rag_pipeline"}
```

---

### 方案2：只启动 RAG Pipeline 和 ChromaDB

如果只需要 RAG Pipeline 服务：

```bash
cd /Users/xuan/Desktop/Harvard-MIT-Course/AC215/AC215-Project-FitAI

# 只启动必要的服务
docker compose up -d rag_pipeline chromadb

# 检查状态
docker compose ps
```

---

### 方案3：直接运行 Python 服务（不使用 Docker）

如果 Docker 有问题，可以直接运行：

#### 前置要求
1. Python 3.12+
2. 安装依赖（使用 uv 或 pip）

#### 步骤1：安装依赖
```bash
cd services/rag_pipeline

# 如果有 uv
uv sync

# 或者使用 pip
pip install -r requirements.txt
# 注意：需要从 pyproject.toml 提取依赖
```

#### 步骤2：设置环境变量
```bash
export GOOGLE_APPLICATION_CREDENTIALS="../secrets/rich-access-471117-r0-f17d92fbf298.json"
export GCP_PROJECT="rich-access-471117-r0"
export CHROMADB_HOST="localhost"  # 如果 ChromaDB 在本地
export CHROMADB_PORT="8000"
```

#### 步骤3：启动 ChromaDB（如果还没运行）
```bash
# 使用 Docker 启动 ChromaDB
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/../../docker-volumes/chromadb:/data \
  -e IS_PERSISTENT=TRUE \
  chromadb/chroma:latest
```

#### 步骤4：启动 RAG Pipeline
```bash
cd services/rag_pipeline
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

---

## 常见问题

### 问题1：Docker 无法连接

**错误信息：**
```
Cannot connect to the Docker daemon
```

**解决方法：**
1. 打开 Docker Desktop
2. 等待完全启动
3. 检查 Docker Desktop 状态栏

### 问题2：端口已被占用

**检查端口：**
```bash
lsof -i :8002
```

**解决方法：**
- 停止占用端口的进程
- 或修改 `docker-compose.yml` 中的端口映射

### 问题3：CORS 错误

如果浏览器控制台显示 CORS 错误，需要添加 CORS 中间件。

**修改 `services/rag_pipeline/app.py`：**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FitAI RAG Pipeline", version="1.0.0")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题4：ChromaDB 连接失败

**检查 ChromaDB：**
```bash
# 检查 ChromaDB 是否运行
curl http://localhost:8000/api/v1/heartbeat

# 检查容器
docker ps | grep chromadb
```

**解决方法：**
```bash
# 重启 ChromaDB
docker compose restart chromadb
```

---

## 快速诊断命令

运行以下命令进行快速诊断：

```bash
# 1. 检查 Docker 是否运行
docker ps

# 2. 检查端口占用
lsof -i :8002
lsof -i :8000

# 3. 测试健康检查
curl http://localhost:8002/health

# 4. 查看服务日志
docker logs fitai-rag-pipeline --tail 50

# 5. 检查服务状态
docker compose ps
```

---

## 验证连接成功

连接成功后，你应该看到：

1. **前端页面：**
   - ✅ 绿色 "Connected to RAG Pipeline"
   - 可以发送消息并收到回复

2. **命令行测试：**
   ```bash
   curl http://localhost:8002/health
   # 返回: {"status":"ok","service":"rag_pipeline"}
   ```

3. **浏览器 Network 标签：**
   - 对 `localhost:8002/chat` 的请求返回 200
   - 响应包含 `status: "success"`

---

## 需要帮助？

如果以上方法都不行，请检查：
1. Docker Desktop 是否正常运行
2. 防火墙是否阻止了端口
3. 查看完整的错误日志：`docker logs fitai-rag-pipeline`

