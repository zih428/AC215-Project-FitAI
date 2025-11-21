#!/bin/bash

echo "🔍 Testing RAG service connectivity"
echo "================================"
echo ""

# Health check
echo "1. Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8002/health)
if [ $? -eq 0 ]; then
    echo "   ✅ Connected"
    echo "   📋 Response: $HEALTH_RESPONSE"
    
    # Validate response content
    if echo "$HEALTH_RESPONSE" | grep -q "rag-service"; then
        echo "   ✅ Confirmed RAG service"
    else
        echo "   ⚠️  Response format may be unexpected"
    fi
else
    echo "   ❌ Cannot connect to http://localhost:8002"
    echo "   Please ensure the RAG service is running"
    exit 1
fi

echo ""
echo "2. Testing chat endpoint..."
CHAT_RESPONSE=$(curl -s -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is strength training?",
    "method": "char-split",
    "n_results": 5
  }')

if [ $? -eq 0 ]; then
    echo "   ✅ Request succeeded"
    
    # Validate response structure
    if echo "$CHAT_RESPONSE" | grep -q '"status":"success"'; then
        echo "   ✅ Status: success"
        
        # Extract key fields
        if echo "$CHAT_RESPONSE" | grep -q '"response"'; then
            echo "   ✅ Contains response field"
        fi
        
        if echo "$CHAT_RESPONSE" | grep -q '"context_chunks_count"'; then
            CHUNKS=$(echo "$CHAT_RESPONSE" | grep -o '"context_chunks_count":[0-9]*' | grep -o '[0-9]*')
            echo "   ✅ Uses $CHUNKS context chunk(s)"
        fi
        
        echo ""
        echo "   📋 Response preview:"
        echo "$CHAT_RESPONSE" | head -c 200
        echo "..."
    else
        echo "   ⚠️  Response status is not success"
        echo "   📋 Full response:"
        echo "$CHAT_RESPONSE"
    fi
else
    echo "   ❌ Request failed"
    exit 1
fi

echo ""
echo "3. Checking ChromaDB collections..."
COLLECTIONS_RESPONSE=$(curl -s http://localhost:8002/collections)
if [ $? -eq 0 ]; then
    echo "   ✅ Collection list accessible"
    if echo "$COLLECTIONS_RESPONSE" | grep -q '"collections"'; then
        COLLECTION_COUNT=$(echo "$COLLECTIONS_RESPONSE" | grep -o '"name"' | wc -l | tr -d ' ')
        echo "   ✅ Found $COLLECTION_COUNT collection(s)"
    fi
else
    echo "   ⚠️  Unable to fetch collection list"
fi

echo ""
echo "================================"
echo "✅ Tests finished!"
echo ""
echo "If all tests passed, the frontend should:"
echo "  1. Show 'Connected to RAG service' status"
echo "  2. Send messages and receive replies from RAG"
echo "  3. Display the '✓ RAG' badge and chunk count on messages"
echo ""
echo "Open http://localhost:3000/ai-coach to view the UI"
