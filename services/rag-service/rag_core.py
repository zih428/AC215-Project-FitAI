import os
import pandas as pd
import json
import time
import hashlib
import chromadb
from io import StringIO
from typing import Optional

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
GENERATIVE_MODEL = "projects/767605785387/locations/us-central1/endpoints/7589646192049389568"
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

General Behavior:
- If the user greets you (e.g., "hi", "hello", "hey", "how are you"), respond naturally and conversationally.
- If the user asks about topics unrelated to fitness or nutrition, politely redirect the conversation back to fitness-related subjects.
- Your expertise is limited to fitness and nutrition, and further limited to what appears in the provided text chunks.

When answering a fitness or nutrition query:
1. Carefully read all the text chunks provided.
2. Identify the most relevant information from these chunks to address the user's question.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you do not have enough information to provide a complete answer.
5. Always maintain a professional and knowledgeable tone, befitting a fitness expert.
6. If there are contradictions in the provided chunks, mention this in your response and explain the different viewpoints presented.

Important Constraints:
- Please write the answer in plain text only. Do not use any Markdown formatting, such as asterisks, hash symbols, backticks, bullet points, or code blocks. The response should contain no Markdown characters at all.
- You are an expert in fitness and nutrition, but your knowledge is limited strictly to the information in the provided chunks.
- Do not invent information or draw from knowledge outside of the provided chunks.
- If the query is unrelated to fitness/nutrition, redirect politely.
- Be concise in your responses while ensuring you cover all relevant information from the chunks.
- If the user profile is provided, you may personalize tone or framing, but factual content must still come only from the chunks.

Your goal is to provide accurate, helpful information about fitness and nutrition based solely on the content of the text chunks you receive with each query, while still being able to handle general greetings and politely decline off-topic questions.
"""

# GCS Helper functions
def download_text_from_gcs(bucket_name: str, file_path: str) -> str:
    """Download text file content from GCS."""
    try:
        bucket = gcs_client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        content = blob.download_as_text()
        return content
    except Exception as e:
        raise Exception(f"Failed to download file from GCS: {str(e)}")

def list_txt_files_from_gcs(bucket_name: str, folder_path: str = "") -> list:
    """List all .txt files under the given prefix in GCS."""
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

# API helper functions
def api_process_gcs_to_chromadb(bucket_name: str, folder_path: str = "", method: str = "semantic-split"):
    """End-to-end: download from GCS -> chunk -> embed -> store in ChromaDB."""
    try:
        # Get txt file list from GCS
        txt_files = list_txt_files_from_gcs(bucket_name, folder_path)
        
        if not txt_files:
            raise Exception(f"No txt files found in GCS bucket '{bucket_name}' with prefix '{folder_path}'")
        
        processed_files = []
        all_chunks = []
        
        for file_info in txt_files:
            file_path = file_info["name"]
            filename = os.path.basename(file_path)
            source_name = os.path.splitext(filename)[0]
            
            # Download file content from GCS
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
                # Add metadata for storage
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
        
        # Generate embeddings
        chunks_text = [item["chunk"] for item in all_chunks]
        
        if method == "semantic-split":
            embeddings = generate_text_embeddings(chunks_text, EMBEDDING_DIMENSION, batch_size=15)
        else:
            embeddings = generate_text_embeddings(chunks_text, EMBEDDING_DIMENSION, batch_size=100)
        
        # Prepare data frame
        data_df = pd.DataFrame(all_chunks)
        data_df["embedding"] = embeddings
        
        # Connect to ChromaDB
        chromadb.api.client.SharedSystemClient.clear_system_cache()
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        
        collection_name = f"{method}-collection"
        
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass  # Collection doesn't exist
        
        collection = client.create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"})
        
        # Load into ChromaDB
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
    """Query function for the vector database."""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collection_name = f"{method}-collection"
        
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            raise Exception(f"Collection '{collection_name}' not found. Please run /load first.")
        
        # Embed the query
        query_embedding = generate_query_embedding(query)

        # Cosine similarity search
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

def format_user_profile_prompt(profile: dict) -> str:
    """Format user profile dict into natural language snippet."""
    parts = []
    if not profile:
        return ""
    name = profile.get("full_name")
    if name:
        parts.append(f"Full Name: {name}")
    age = profile.get("age_years")
    if age is not None:
        parts.append(f"Age: {age} years")
    height = profile.get("height_cm")
    if height is not None:
        parts.append(f"Height: {height} cm")
    weight = profile.get("weight_kg")
    if weight is not None:
        parts.append(f"Weight: {weight} kg")
    body_type = profile.get("body_type")
    if body_type:
        parts.append(f"Body Type: {body_type}")
    gender = profile.get("gender")
    if gender:
        parts.append(f"Gender: {gender}")
    goal = profile.get("training_goal")
    if goal:
        parts.append(f"Training Goal: {goal}")
    if not parts:
        return ""
    return "\n".join(parts)


def api_chat_with_llm(query: str, method: str = "char-split", n_results: int = 10, user_profile: Optional[dict] = None):
    """Chat API that retrieves context and calls the LLM."""
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
        
        # Build context from retrieved documents
        context_chunks = "\n\n---\n".join(results["documents"][0])
        
        user_profile_prompt = format_user_profile_prompt(user_profile or {})
        profile_section = (
            f"\nUser profile information:\n{user_profile_prompt}\n"
            if user_profile_prompt
            else "\n"
        )
        input_prompt = f"""
        System: {SYSTEM_INSTRUCTION}
        {profile_section}
        User question:
        {query}
        
        Context from retrieved text:
        {context_chunks}
        """
        
        # 🔥 Print which model (SFT or base Gemini) is being called
        print(">>> DEBUG - Calling model:", GENERATIVE_MODEL, flush=True)

        # Send the prompt to the LLM (using Gemini 2.0 Flash endpoint)
        response = llm_client.models.generate_content(
            model=GENERATIVE_MODEL, contents=input_prompt
        )
        
         # 🔥 Print returned model_version (helps confirm SFT)
        print(">>> DEBUG - Model returned:", response.model_version, flush=True)
        
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
    """List available collections via the API."""
    try:
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collections = client.list_collections()
        
        return {
            "status": "success",
            "collections": [{"name": col.name, "id": col.id} for col in collections]
        }
    except Exception as e:
        raise Exception(str(e))
