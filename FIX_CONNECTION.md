# 修复 RAG Pipeline 连接问题

## 当前状态
- ✅ Docker 正在运行
- ✅ RAG Pipeline 容器正在运行（端口 8002）
- ✅ ChromaDB 容器正在运行（端口 8000）
- ✅ 服务健康检查通过：`curl http://localhost:8002/health` 返回成功
- ✅ CORS 配置已添加
- ❌ 前端仍显示 "disconnected"

## 解决步骤

### 步骤 1: 重启 RAG Pipeline 容器（已执行）
```bash
docker compose restart rag_pipeline
```

### 步骤 2: 清除浏览器缓存并硬刷新
1. 打开浏览器开发者工具（F12）
2. 右键点击刷新按钮
3. 选择 "清空缓存并硬性重新加载"（Empty Cache and Hard Reload）
4. 或者按 `Cmd+Shift+R` (Mac) / `Ctrl+Shift+R` (Windows)

### 步骤 3: 检查浏览器控制台
1. 打开开发者工具（F12）
2. 切换到 "Console" 标签
3. 查看是否有错误信息，特别是：
   - CORS 错误
   - Network 错误
   - Fetch 错误

### 步骤 4: 检查 Network 标签
1. 打开开发者工具（F12）
2. 切换到 "Network" 标签
3. 刷新页面
4. 查找对 `localhost:8002/health` 的请求
5. 点击请求查看：
   - Status Code（应该是 200）
   - Response Headers（应该包含 CORS 头）
   - Response Body（应该包含 `{"status":"ok","service":"rag_pipeline"}`）

### 步骤 5: 使用测试页面
打开测试页面来诊断问题：
```bash
# 在浏览器中打开
open services/frontend/test-connection.html
# 或直接访问文件路径
```

### 步骤 6: 重启前端开发服务器
如果前端代码已更新，需要重启：
```bash
cd services/frontend
# 停止当前服务器（Ctrl+C）
# 然后重新启动
npm run dev
```

### 步骤 7: 验证服务
```bash
# 1. 检查容器状态
docker ps | grep rag

# 2. 测试健康检查
curl http://localhost:8002/health

# 3. 测试 CORS
curl -H "Origin: http://localhost:3000" http://localhost:8002/health

# 4. 查看容器日志
docker logs fitai-rag-pipeline --tail 50
```

## 常见问题

### 问题 1: CORS 错误
**症状：** 浏览器控制台显示 "CORS policy" 错误

**解决：** 
- 确认 `app.py` 中已添加 CORS 中间件
- 重启容器：`docker compose restart rag_pipeline`

### 问题 2: 网络错误
**症状：** "Failed to fetch" 或 "NetworkError"

**解决：**
- 确认服务正在运行：`docker ps`
- 确认端口正确：`lsof -i :8002`
- 检查防火墙设置

### 问题 3: 响应格式错误
**症状：** 连接成功但显示 "not responding correctly"

**解决：**
- 检查响应格式：`curl http://localhost:8002/health`
- 应该返回：`{"status":"ok","service":"rag_pipeline"}`

## 快速修复命令

```bash
# 1. 重启所有相关服务
cd /Users/xuan/Desktop/Harvard-MIT-Course/AC215/AC215-Project-FitAI
docker compose restart rag_pipeline chromadb

# 2. 等待服务启动
sleep 5

# 3. 验证服务
curl http://localhost:8002/health

# 4. 如果前端在运行，重启它
cd services/frontend
# 停止当前进程（Ctrl+C），然后：
npm run dev
```

## 如果仍然不行

1. **检查 Docker 容器日志：**
   ```bash
   docker logs fitai-rag-pipeline -f
   ```

2. **检查代码是否已更新：**
   ```bash
   # 确认 app.py 包含 CORS 配置
   grep -A 10 "CORSMiddleware" services/rag_pipeline/app.py
   ```

3. **尝试直接访问 API：**
   在浏览器中打开：http://localhost:8002/health
   应该看到 JSON 响应

4. **检查端口冲突：**
   ```bash
   lsof -i :8002
   ```

5. **完全重启：**
   ```bash
   docker compose down
   docker compose up -d rag_pipeline chromadb
   ```

