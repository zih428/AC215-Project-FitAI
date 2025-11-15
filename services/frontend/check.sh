#!/bin/bash

echo "🔍 FitAI Frontend 检查脚本"
echo "================================"
echo ""

# 检查Node.js
echo "1. 检查 Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "   ✅ Node.js: $NODE_VERSION"
else
    echo "   ❌ Node.js 未安装"
    exit 1
fi

# 检查npm
echo ""
echo "2. 检查 npm..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "   ✅ npm: $NPM_VERSION"
else
    echo "   ❌ npm 未安装"
    exit 1
fi

# 检查依赖
echo ""
echo "3. 检查依赖..."
if [ -d "node_modules" ]; then
    echo "   ✅ node_modules 目录存在"
    MODULE_COUNT=$(ls node_modules | wc -l | tr -d ' ')
    echo "   ✅ 已安装 $MODULE_COUNT 个包"
else
    echo "   ⚠️  node_modules 不存在，运行 'npm install'"
fi

# 检查关键文件
echo ""
echo "4. 检查关键文件..."
FILES=(
    "package.json"
    "tsconfig.json"
    "tailwind.config.js"
    "next.config.js"
    "app/layout.tsx"
    "app/page.tsx"
    "app/ai-coach/page.tsx"
    "app/calendar/page.tsx"
    "components/Sidebar.tsx"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file 缺失"
    fi
done

# 检查后端服务
echo ""
echo "5. 检查后端服务..."
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "   ✅ RAG Pipeline 服务运行中 (http://localhost:8002)"
    HEALTH=$(curl -s http://localhost:8002/health)
    echo "   📋 响应: $HEALTH"
else
    echo "   ⚠️  RAG Pipeline 服务未运行 (http://localhost:8002)"
    echo "   请确保后端服务已启动: docker compose up -d rag_pipeline"
fi

# 检查端口
echo ""
echo "6. 检查端口占用..."
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "   ⚠️  端口 3000 已被占用"
    echo "   进程信息:"
    lsof -ti:3000 | xargs ps -p
else
    echo "   ✅ 端口 3000 可用"
fi

echo ""
echo "================================"
echo "✅ 检查完成！"
echo ""
echo "下一步："
echo "  1. 如果依赖未安装，运行: npm install"
echo "  2. 启动开发服务器: npm run dev"
echo "  3. 访问: http://localhost:3000"

