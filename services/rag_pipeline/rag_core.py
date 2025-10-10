import os
import pandas as pd
import json
import time
import hashlib
import chromadb
from io import StringIO

# Google Cloud
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors
from google.cloud import storage

# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from semantic_splitter import SemanticChunker

# Setup
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 256
GENERATIVE_MODEL = "gemini-2.0-flash-001"
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

# Initialize GCS client
gcs_client = storage.Client(project=GCP_PROJECT)

# Initialize the LLM Client
llm_client = genai.Client(
    vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)

# System instruction for fitness knowledge
SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in fitness and nutrition knowledge. Your responses are based solely on the information provided in the text chunks given to you. Do not use any external knowledge or make assumptions beyond what is explicitly stated in these chunks.

When answering a query:
1. Carefully read all the text chunks provided.
2. Identify the most relevant information from these chunks to address the user's question.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you don't have enough information to provide a complete answer.
5. Always maintain a professional and knowledgeable tone, befitting a fitness expert.
6. If there are contradictions in the provided chunks, mention this in your response and explain the different viewpoints presented.

Remember:
- You are an expert in fitness and nutrition, but your knowledge is limited to the information in the provided chunks.
- Do not invent information or draw from knowledge outside of the given text chunks.
- If asked about topics unrelated to fitness/nutrition, politely redirect the conversation back to fitness-related subjects.
- Be concise in your responses while ensuring you cover all relevant information from the chunks.

Your goal is to provide accurate, helpful information about fitness and nutrition based solely on the content of the text chunks you receive with each query.
"""

# GCS Helper functions
def download_text_from_gcs(bucket_name: str, file_path: str) -> str:
    """从GCS下载文本文件内容"""
    try:
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        content = blob.download_as_text()
        return content
    except Exception as e:
        raise Exception(f"Failed to download file from GCS: {str(e)}")

def list_txt_files_from_gcs(bucket_name: str, folder_path: str = "") -> list:
    """从GCS列出所有txt文件"""
    try:
        bucket = gcs_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=folder_path)
        
        txt_files = []
        for blob in blobs:
            if blob.name.endswith('.txt') and not blob.name.endswith('/'):
                txt_files.append({
                    "name": blob.name,
                    "bucket": bucket_name,
                    "size": blob.size
                })
        
        return txt_files
    except Exception as e:
        raise Exception(f"Failed to list files from GCS: {str(e)}")

# Helper functions
def generate_query_embedding(query):
    kwargs = {
        "output_dimensionality": EMBEDDING_DIMENSION
    }
    response = llm_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(**kwargs)
    )
    return response.embeddings[0].values

def generate_text_embeddings(chunks, dimensionality: int = 256, batch_size=250, max_retries=5, retry_delay=5):
    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = llm_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        output_dimensionality=dimensionality),
                )
                all_embeddings.extend(
                    [embedding.values for embedding in response.embeddings])
                break
            except errors.APIError as e:
                retry_count += 1
                if retry_count > max_retries:
                    raise Exception(f"Failed to generate embeddings after {max_retries} attempts: {str(e)}")
                wait_time = retry_delay * (2 ** (retry_count - 1))
                time.sleep(wait_time)
    return all_embeddings

def load_text_embeddings(df, collection, batch_size=500):
    df["id"] = df.index.astype(str)
    hashed_sources = df["source"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    df["id"] = hashed_sources + "-" + df["id"]
    
    total_inserted = 0
    for i in range(0, df.shape[0], batch_size):
        batch = df.iloc[i:i+batch_size].copy().reset_index(drop=True)
        ids = batch["id"].tolist()
        documents = batch["chunk"].tolist()
        metadatas = [{"source": s} for s in batch["source"].tolist()]
        embeddings = batch["embedding"].tolist()
        
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
        total_inserted += len(batch)
    return total_inserted

# API功能函数
def api_process_gcs_to_chromadb(bucket_name: str, folder_path: str = "", method: str = "char-split"):
    """一键处理：从GCS下载文件 -> 分块 -> 生成嵌入 -> 存储到ChromaDB"""
    try:
        # 从GCS获取txt文件列表
        txt_files = list_txt_files_from_gcs(bucket_name, folder_path)
        
        if not txt_files:
            raise Exception(f"No txt files found in GCS bucket '{bucket_name}' with prefix '{folder_path}'")
        
        processed_files = []
        all_chunks = []
        
        for file_info in txt_files:
            file_path = file_info["name"]
            filename = os.path.basename(file_path)
            source_name = os.path.splitext(filename)[0]
            
            # 从GCS下载文件内容
            input_text = download_text_from_gcs(bucket_name, file_path)
            
            text_chunks = None
            if method == "char-split":
                chunk_size = 350
                chunk_overlap = 20
                text_splitter = CharacterTextSplitter(
                    chunk_size=chunk_size, chunk_overlap=chunk_overlap, separator='', strip_whitespace=False)
                text_chunks = text_splitter.create_documents([input_text])
                text_chunks = [doc.page_content for doc in text_chunks]
                
            elif method == "recursive-split":
                chunk_size = 350
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size)
                text_chunks = text_splitter.create_documents([input_text])
                text_chunks = [doc.page_content for doc in text_chunks]
                
            elif method == "semantic-split":
                text_splitter = SemanticChunker(embedding_function=generate_text_embeddings)
                text_chunks = text_splitter.create_documents([input_text])
                text_chunks = [doc.page_content for doc in text_chunks]
            
            if text_chunks is not None:
                # 添加元数据
                for chunk in text_chunks:
                    all_chunks.append({
                        "chunk": chunk,
                        "source": source_name,
                        "gcs_path": file_path,
                        "bucket": bucket_name
                    })
                
                processed_files.append({
                    "filename": filename,
                    "source_name": source_name,
                    "gcs_path": file_path,
                    "chunks_count": len(text_chunks),
                    "file_size": file_info["size"]
                })
        
        # 生成嵌入向量
        chunks_text = [item["chunk"] for item in all_chunks]
        
        if method == "semantic-split":
            embeddings = generate_text_embeddings(chunks_text, EMBEDDING_DIMENSION, batch_size=15)
        else:
            embeddings = generate_text_embeddings(chunks_text, EMBEDDING_DIMENSION, batch_size=100)
        
        # 准备数据
        data_df = pd.DataFrame(all_chunks)
        data_df["embedding"] = embeddings
        
        # 连接ChromaDB
        chromadb.api.client.SharedSystemClient.clear_system_cache()
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        
        collection_name = f"{method}-collection"
        
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass  # Collection doesn't exist
        
        collection = client.create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"})
        
        # 加载到ChromaDB
        total_inserted = load_text_embeddings(data_df, collection)
        
        return {
            "status": "success",
            "method": method,
            "bucket_name": bucket_name,
            "folder_path": folder_path,
            "chunking": {
                "total_files": len(txt_files),
                "total_chunks": len(all_chunks),
                "processed_files": processed_files
            },
            "embedding": {
                "collection_name": collection_name,
                "total_inserted": total_inserted,
                "embeddings_generated": len(embeddings)
            }
        }
    except Exception as e:
        raise Exception(str(e))

def api_query_vector_db(query: str, method: str = "char-split", n_results: int = 5):
    """API版本的查询功能"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection_name = f"{method}-collection"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            raise Exception(f"Collection '{collection_name}' not found. Please run /load first.")
        
        # 将query 向量化
        query_embedding = generate_query_embedding(query)

        # 余弦相似度 (cosine similarity)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return {
            "status": "success",
            "query": query,
            "method": method,
            "results": {
                "documents": results["documents"][0],
                "distances": results["distances"][0],
                "metadatas": results["metadatas"][0],
                "ids": results["ids"][0]
            }
        }
    except Exception as e:
        raise Exception(str(e))

def api_chat_with_llm(query: str, method: str = "char-split", n_results: int = 10):
    """API版本的聊天功能"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection_name = f"{method}-collection"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            raise Exception(f"Collection '{collection_name}' not found. Please run /load first.")
        
        query_embedding = generate_query_embedding(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 将查询结果拼接成上下文
        context_chunks = "\n\n---\n".join(results["documents"][0])
        
        # 构建prompt
        input_prompt = f"""
        System: {SYSTEM_INSTRUCTION}
        
        User question:
        {query}
        
        Context from retrieved text:
        {context_chunks}
        """
        
        #将prompt 传给llm 生成回答（我们用的是Gemini 2.0 Flash）
        response = llm_client.models.generate_content(
            model=GENERATIVE_MODEL, contents=input_prompt
        )
        
        return {
            "status": "success",
            "query": query,
            "method": method,
            "response": response.text,
            "context_chunks_count": len(results["documents"][0])
        }
    except Exception as e:
        raise Exception(str(e))

def api_list_collections():
    """API版本的列出集合功能"""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collections = client.list_collections()
        
        return {
            "status": "success",
            "collections": [{"name": col.name, "id": col.id} for col in collections]
        }
    except Exception as e:
        raise Exception(str(e))