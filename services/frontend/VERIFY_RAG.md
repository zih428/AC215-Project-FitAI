# 如何验证 AI Coach 是否使用了 RAG Pipeline

## 方法1: 查看页面上的连接状态指示器

1. 打开 AI Coach 页面：http://localhost:3000/ai-coach
2. 查看页面顶部的连接状态：
   - ✅ **绿色 "Connected to RAG Pipeline"** = 已连接
   - ⚠️ **黄色 "Checking..."** = 正在检查
   - ❌ **红色 "Cannot connect..."** = 未连接

## 方法2: 查看消息标签

每条AI回复消息下方会显示：
- **✓ RAG** (绿色标签) = 来自 RAG Pipeline 的真实响应
- **⚠ Fallback** (黄色标签) = 连接失败，显示错误信息
- **X chunks** = 显示使用了多少个文档块（context chunks）

## 方法3: 使用调试模式

1. 点击页面右上角的 **"Show Debug"** 按钮
2. 查看调试信息：
   - API Endpoint: http://localhost:8002/chat
   - Health Check: http://localhost:8002/health
   - 连接状态

## 方法4: 浏览器开发者工具

1. 打开浏览器开发者工具（F12）
2. 切换到 **Network（网络）** 标签
3. 在 AI Coach 页面发送一条消息
4. 查找对 `http://localhost:8002/chat` 的请求
5. 查看请求详情：
   - **Request Payload**: 应该包含你的查询
   - **Response**: 应该包含 `status: "success"` 和 `response` 字段

## 方法5: 命令行测试

### 测试健康检查
```bash
curl http://localhost:8002/health
```
应该返回：
```json
{"status":"ok","service":"rag_pipeline"}
```

### 测试聊天端点
```bash
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the best workout for beginners?",
    "method": "char-split",
    "n_results": 10
  }'
```

应该返回：
```json
{
  "status": "success",
  "query": "...",
  "method": "char-split",
  "response": "...",
  "context_chunks_count": 10
}
```

## 方法6: 检查后端日志

查看 RAG Pipeline 容器的日志：
```bash
docker logs fitai-rag-pipeline -f
```

发送消息时，应该看到：
- 查询请求
- 向量检索过程
- LLM 生成响应

## 验证要点

✅ **确认使用 RAG Pipeline 的迹象：**
1. 连接状态显示 "Connected to RAG Pipeline"
2. 消息标签显示 "✓ RAG"
3. 显示 context_chunks_count（如 "10 chunks"）
4. 响应内容与你的查询相关且详细
5. 浏览器 Network 标签显示对 localhost:8002 的请求成功

❌ **未使用 RAG Pipeline 的迹象：**
1. 连接状态显示 "Cannot connect..."
2. 消息标签显示 "⚠ Fallback"
3. 显示错误信息而不是实际回答
4. 浏览器 Network 标签显示请求失败（红色）

## 故障排查

如果显示未连接：

1. **检查服务是否运行**
   ```bash
   docker ps | grep rag_pipeline
   ```

2. **启动服务**
   ```bash
   docker compose up -d rag_pipeline
   ```

3. **检查端口**
   ```bash
   lsof -i :8002
   ```

4. **检查 ChromaDB**
   ```bash
   curl http://localhost:8000/api/v1/heartbeat
   ```

5. **检查集合是否存在**
   ```bash
   curl http://localhost:8002/collections
   ```

## 测试问题示例

尝试发送这些问题来验证 RAG 是否工作：

1. "What are the benefits of strength training?"
2. "How should I structure my workout routine?"
3. "What is the optimal rest time between sets?"

如果 RAG Pipeline 正常工作，回答应该：
- 基于科学文献（从 ChromaDB 检索）
- 详细且专业
- 包含具体的建议

