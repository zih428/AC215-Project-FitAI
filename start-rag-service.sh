#!/bin/bash

echo "🚀 启动 FitAI RAG Pipeline 服务"
echo "================================"
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行！"
    echo ""
    echo "请先启动 Docker Desktop，然后重新运行此脚本。"
    echo ""
    exit 1
fi

echo "✅ Docker 正在运行"
echo ""

# 检查服务是否已经在运行
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "⚠️  RAG Pipeline 服务已经在运行"
    echo "   访问: http://localhost:8002/health"
    echo ""
    read -p "是否要重启服务? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 重启服务..."
        docker compose restart rag_pipeline
    else
        echo "✅ 服务继续运行"
        exit 0
    fi
else
    echo "📦 启动 RAG Pipeline 和 ChromaDB 服务..."
    docker compose up -d rag_pipeline chromadb
    
    echo ""
    echo "⏳ 等待服务启动..."
    sleep 5
fi

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
echo ""

# 检查 RAG Pipeline
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8002/health)
    echo "✅ RAG Pipeline: 运行中"
    echo "   $HEALTH"
else
    echo "❌ RAG Pipeline: 未响应"
    echo "   查看日志: docker logs fitai-rag-pipeline"
fi

# 检查 ChromaDB
if curl -s http://localhost:8000/api/v1/heartbeat > /dev/null 2>&1; then
    echo "✅ ChromaDB: 运行中"
else
    echo "⚠️  ChromaDB: 可能未响应（这可能是正常的）"
fi

echo ""
echo "================================"
echo "✅ 启动完成！"
echo ""
echo "服务地址："
echo "  - RAG Pipeline: http://localhost:8002"
echo "  - ChromaDB: http://localhost:8000"
echo ""
echo "测试连接："
echo "  curl http://localhost:8002/health"
echo ""
echo "查看日志："
echo "  docker logs fitai-rag-pipeline -f"
echo ""

