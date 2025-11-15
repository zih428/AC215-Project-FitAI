#!/bin/bash

echo "🔍 测试 RAG Pipeline 连接"
echo "================================"
echo ""

# 测试健康检查
echo "1. 测试健康检查端点..."
HEALTH_RESPONSE=$(curl -s http://localhost:8002/health)
if [ $? -eq 0 ]; then
    echo "   ✅ 连接成功"
    echo "   📋 响应: $HEALTH_RESPONSE"
    
    # 检查响应内容
    if echo "$HEALTH_RESPONSE" | grep -q "rag_pipeline"; then
        echo "   ✅ 确认是 RAG Pipeline 服务"
    else
        echo "   ⚠️  响应格式可能不正确"
    fi
else
    echo "   ❌ 无法连接到 http://localhost:8002"
    echo "   请确保 RAG Pipeline 服务正在运行"
    exit 1
fi

echo ""
echo "2. 测试聊天端点..."
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is strength training?",
    "method": "char-split",
    "n_results": 5
  }')

if [ $? -eq 0 ]; then
    echo "   ✅ 请求成功"
    
    # 检查响应格式
    if echo "$CHAT_RESPONSE" | grep -q '"status":"success"'; then
        echo "   ✅ 响应状态: success"
        
        # 提取关键信息
        if echo "$CHAT_RESPONSE" | grep -q '"response"'; then
            echo "   ✅ 包含 response 字段"
        fi
        
        if echo "$CHAT_RESPONSE" | grep -q '"context_chunks_count"'; then
            CHUNKS=$(echo "$CHAT_RESPONSE" | grep -o '"context_chunks_count":[0-9]*' | grep -o '[0-9]*')
            echo "   ✅ 使用了 $CHUNKS 个文档块 (context chunks)"
        fi
        
        echo ""
        echo "   📋 响应预览:"
        echo "$CHAT_RESPONSE" | head -c 200
        echo "..."
    else
        echo "   ⚠️  响应状态不是 success"
        echo "   📋 完整响应:"
        echo "$CHAT_RESPONSE"
    fi
else
    echo "   ❌ 请求失败"
    exit 1
fi

echo ""
echo "3. 检查 ChromaDB 集合..."
COLLECTIONS_RESPONSE=$(curl -s http://localhost:8002/collections)
if [ $? -eq 0 ]; then
    echo "   ✅ 可以访问集合列表"
    if echo "$COLLECTIONS_RESPONSE" | grep -q '"collections"'; then
        COLLECTION_COUNT=$(echo "$COLLECTIONS_RESPONSE" | grep -o '"name"' | wc -l | tr -d ' ')
        echo "   ✅ 找到 $COLLECTION_COUNT 个集合"
    fi
else
    echo "   ⚠️  无法获取集合列表"
fi

echo ""
echo "================================"
echo "✅ 测试完成！"
echo ""
echo "如果所有测试都通过，你的前端应该能够："
echo "  1. 显示 'Connected to RAG Pipeline' 状态"
echo "  2. 发送消息并收到来自 RAG 的回复"
echo "  3. 在消息上看到 '✓ RAG' 标签和 chunks 数量"
echo ""
echo "访问 http://localhost:3000/ai-coach 查看前端界面"

