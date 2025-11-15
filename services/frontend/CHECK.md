# 前端检查指南

## 1. 安装依赖

首先确保已安装所有依赖：

```bash
cd services/frontend
npm install
```

如果遇到问题，可以尝试：
```bash
rm -rf node_modules package-lock.json
npm install
```

## 2. 检查项目结构

确保以下文件存在：
- ✅ `package.json`
- ✅ `tsconfig.json`
- ✅ `tailwind.config.js`
- ✅ `next.config.js`
- ✅ `app/layout.tsx`
- ✅ `app/page.tsx`
- ✅ `app/ai-coach/page.tsx`
- ✅ `app/calendar/page.tsx`
- ✅ `components/Sidebar.tsx`

## 3. 启动开发服务器

```bash
npm run dev
```

应该看到类似输出：
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Ready in Xs
```

## 4. 检查页面

### 4.1 主页面（Dashboard）
访问：http://localhost:3000
- ✅ 应该看到左侧导航栏
- ✅ 应该看到 "Welcome back, Chenxi!" 标题

### 4.2 AI Coach 页面
访问：http://localhost:3000/ai-coach
- ✅ 应该看到聊天界面
- ✅ 应该看到输入框和发送按钮
- ✅ 左侧导航栏中 "AI Coach" 应该高亮显示

### 4.3 Calendar 页面
访问：http://localhost:3000/calendar
- ✅ 应该看到日历视图
- ✅ 应该看到月份导航按钮
- ✅ 左侧导航栏中 "Calendar" 应该高亮显示

## 5. 检查后端API连接

### 5.1 确保RAG Pipeline服务运行

```bash
# 检查服务是否运行
curl http://localhost:8002/health
```

应该返回：
```json
{"status":"ok","service":"rag_pipeline"}
```

### 5.2 测试API端点

```bash
# 测试chat端点
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the best workout for beginners?",
    "method": "char-split",
    "n_results": 10
  }'
```

应该返回包含 `response` 字段的JSON。

### 5.3 在浏览器中测试

1. 打开浏览器开发者工具（F12）
2. 切换到 Network（网络）标签
3. 在AI Coach页面发送一条消息
4. 检查是否有对 `http://localhost:8002/chat` 的请求
5. 查看响应是否正确

## 6. 常见问题排查

### 问题1: 端口3000已被占用
```bash
# 查找占用端口的进程
lsof -ti:3000
# 或者使用其他端口
PORT=3001 npm run dev
```

### 问题2: CORS错误
如果前端无法访问后端API，可能需要配置CORS。检查 `services/rag_pipeline/app.py` 是否允许跨域请求。

### 问题3: TypeScript错误
如果看到TypeScript错误，确保：
- 已安装所有依赖：`npm install`
- TypeScript版本正确：`npx tsc --version`

### 问题4: Tailwind样式不生效
确保：
- `tailwind.config.js` 配置正确
- `app/globals.css` 包含 Tailwind 指令
- 重启开发服务器

## 7. 快速检查脚本

运行以下命令进行快速检查：

```bash
# 检查Node.js版本（需要 >= 18）
node --version

# 检查npm版本
npm --version

# 检查依赖是否安装
ls node_modules | head -5

# 检查后端服务
curl -s http://localhost:8002/health || echo "后端服务未运行"
```

## 8. 构建检查

测试生产构建：

```bash
npm run build
npm start
```

访问 http://localhost:3000 检查生产版本是否正常。

