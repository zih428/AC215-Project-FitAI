import os
import argparse
import pandas as pd
import json
import time
import glob
import hashlib
import chromadb

# Vertex AI
from google import genai
from google.genai import types
from google.genai.types import Content, Part, GenerationConfig, ToolConfig
from google.genai import errors

# Langchain
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from semantic_splitter import SemanticChunker
import agent_tools

# Setup
GCP_PROJECT = os.environ["GCP_PROJECT"]
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 256
GENERATIVE_MODEL = "gemini-2.0-flash-001"
INPUT_FOLDER = "input-datasets"
OUTPUT_FOLDER = "outputs"
CHROMADB_HOST = os.getenv("CHROMADB_HOST", "chromadb")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

#############################################################################
#                       Initialize the LLM Client                           #
llm_client = genai.Client(
    vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)
#############################################################################

# Initialize the GenerativeModel with specific system instructions
SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in cheese knowledge. Your responses are based solely on the information provided in the text chunks given to you. Do not use any external knowledge or make assumptions beyond what is explicitly stated in these chunks.

When answering a query:
1. Carefully read all the text chunks provided.
2. Identify the most relevant information from these chunks to address the user's question.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you don't have enough information to provide a complete answer.
5. Always maintain a professional and knowledgeable tone, befitting a cheese expert.
6. If there are contradictions in the provided chunks, mention this in your response and explain the different viewpoints presented.

Remember:
- You are an expert in cheese, but your knowledge is limited to the information in the provided chunks.
- Do not invent information or draw from knowledge outside of the given text chunks.
- If asked about topics unrelated to cheese, politely redirect the conversation back to cheese-related subjects.
- Be concise in your responses while ensuring you cover all relevant information from the chunks.

Your goal is to provide accurate, helpful information about cheese based solely on the content of the text chunks you receive with each query.
"""

# book_mappings = {
#     "Cheese and its economical uses in the diet": {"author": "C. F. Langworthy and Caroline Louisa Hunt", "year": 2023},
#     "Cottage Cheese Recipe Book": {"author": "Milk Industry Foundation", "year": 2021},
#     "Dairying exemplified, or, The business of cheese-making": {"author": "J. Twamley", "year": 2023},
#     "Hand-book on cheese making": {"author": "George E. Newell", "year": 2023},
#     "Hints on cheese-making, for the dairyman, the factoryman, and the manufacturer": {"author": "T. D. Curtis", "year": 2013},
#     "The Book of Cheese": {"author": "Charles Thom and W. W. Fisk", "year": 2012},
#     "The book of The Cheese Being traits and stories of Ye Olde Cheshire Cheese": {"author": "Thomas Wilson Reid", "year": 2023},
#     "The Complete Book of Cheese": {"author": "Bob Brown", "year": 2024},
#     "Theres Pippins and Cheese to Come": {"author": "Charles S. Brooks", "year": 2003},
#     "Womans Institute Library of Cookery. Volume 2_ Milk, Butter and Cheese Eggs Vegetables": {"author": "Woman's Institute of Domestic Arts and Sciences", "year": 2006},
#     "Tolminc Cheese": {"author": "Pavlos Protopapas", "year": 2024}
# }


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
    # Max batch size is 250 for Vertex AI
    all_embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # Retry logic with exponential backoff
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
                    print(
                        f"Failed to generate embeddings after {max_retries} attempts. Last error: {str(e)}")
                    raise

                # Calculate delay with exponential backoff
                wait_time = retry_delay * (2 ** (retry_count - 1))
                print(
                    f"API error (code: {e.code}): {e.message}. Retrying in {wait_time} seconds (attempt {retry_count}/{max_retries})...")
                time.sleep(wait_time)

    return all_embeddings


def load_text_embeddings(df, collection, batch_size=500):

    # Generate ids
    df["id"] = df.index.astype(str)
    hashed_sources = df["source"].apply(
        lambda x: hashlib.sha256(x.encode()).hexdigest()[:16])
    df["id"] = hashed_sources + "-" + df["id"]

    # metadata = {
    #     "book": df["book"].tolist()[0]
    # }
    # if metadata["book"] in book_mappings:
    #     book_mapping = book_mappings[metadata["book"]]
    #     metadata["author"] = book_mapping["author"]
    #     metadata["year"] = book_mapping["year"]

    # Process data in batches
    total_inserted = 0
    for i in range(0, df.shape[0], batch_size):
        # Create a copy of the batch and reset the index
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
        print(f"Inserted {total_inserted} items...")

    print(
        f"Finished inserting {total_inserted} items into collection '{collection.name}'")


def chunk(method="char-split"):
    print("chunk()")

    # Make dataset folders
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Get the list of text file
    text_files = glob.glob(os.path.join(INPUT_FOLDER, "*.txt"))
    print("Number of files to process:", len(text_files))

    # Process
    for text_file in text_files:
        print("Processing file:", text_file)
        filename = os.path.basename(text_file)
        source_name = os.path.splitext(filename)[0]

        with open(text_file) as f:
            input_text = f.read()

        text_chunks = None
        if method == "char-split":
            chunk_size = 350
            chunk_overlap = 20
            # Init the splitter
            text_splitter = CharacterTextSplitter(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap, separator='', strip_whitespace=False)

            # Perform the splitting
            text_chunks = text_splitter.create_documents([input_text])
            text_chunks = [doc.page_content for doc in text_chunks]
            print("Number of chunks:", len(text_chunks))

        elif method == "recursive-split":
            chunk_size = 350
            # Init the splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size)

            # Perform the splitting
            text_chunks = text_splitter.create_documents([input_text])
            text_chunks = [doc.page_content for doc in text_chunks]
            print("Number of chunks:", len(text_chunks))

        elif method == "semantic-split":
            # Init the splitter
            text_splitter = SemanticChunker(
                embedding_function=generate_text_embeddings)
            # Perform the splitting
            text_chunks = text_splitter.create_documents([input_text])

            text_chunks = [doc.page_content for doc in text_chunks]
            print("Number of chunks:", len(text_chunks))

        if text_chunks is not None:
            # Save the chunks
            data_df = pd.DataFrame(text_chunks, columns=["chunk"])
            data_df["source"] = source_name
            print("Shape:", data_df.shape)
            print(data_df.head())

            jsonl_filename = os.path.join(
                OUTPUT_FOLDER, f"chunks-{method}-{source_name}.jsonl")
            with open(jsonl_filename, "w") as json_file:
                json_file.write(data_df.to_json(orient='records', lines=True))


def embed(method="char-split"):
    print("embed()")

    # Get the list of chunk files
    jsonl_files = glob.glob(os.path.join(
        OUTPUT_FOLDER, f"chunks-{method}-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    # Process
    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        print("Shape:", data_df.shape)
        print(data_df.head())

        chunks = data_df["chunk"].values
        chunks = chunks.tolist()
        if method == "semantic-split":
            embeddings = generate_text_embeddings(
                chunks, EMBEDDING_DIMENSION, batch_size=15)
        else:
            embeddings = generate_text_embeddings(
                chunks, EMBEDDING_DIMENSION, batch_size=100)
        data_df["embedding"] = embeddings

        time.sleep(5)

        # Save
        print("Shape:", data_df.shape)
        print(data_df.head())

        jsonl_filename = jsonl_file.replace("chunks-", "embeddings-")
        with open(jsonl_filename, "w") as json_file:
            json_file.write(data_df.to_json(orient='records', lines=True))


def load(method="char-split"):
    print("load()")

    # Clear Cache
    chromadb.api.client.SharedSystemClient.clear_system_cache()

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = f"{method}-collection"
    print("Creating collection:", collection_name)

    try:
        # Clear out any existing items in the collection
        client.delete_collection(name=collection_name)
        print(f"Deleted existing collection '{collection_name}'")
    except Exception:
        print(f"Collection '{collection_name}' did not exist. Creating new.")

    collection = client.create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"})
    print(f"Created new empty collection '{collection_name}'")
    print("Collection:", collection)

    # Get the list of embedding files
    jsonl_files = glob.glob(os.path.join(
        OUTPUT_FOLDER, f"embeddings-{method}-*.jsonl"))
    print("Number of files to process:", len(jsonl_files))

    # Process
    for jsonl_file in jsonl_files:
        print("Processing file:", jsonl_file)

        data_df = pd.read_json(jsonl_file, lines=True)
        print("Shape:", data_df.shape)
        print(data_df.head())

        # Load data
        load_text_embeddings(data_df, collection)


def query(method="char-split"):
    print("query()")

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)

    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = f"{method}-collection"

    # Ask user for question
    query = input("Enter your FitAI question: ") or "Summarize the main findings."
    print(f"\nQuery: {query}")

    # Generate embedding for the question
    query_embedding = generate_query_embedding(query)

    # Get the collection
    collection = client.get_collection(name=collection_name)

    # Run semantic similarity search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5  # top 5 similar chunks
    )
    print("\n\nResults:", results)

    # # 1: Query based on embedding value
    # results = collection.query(
    # 	query_embeddings=[query_embedding],
    # 	n_results=10
    # )
    # print("Query:", query)
    # print("\n\nResults:", results)

    # # 2: Query based on embedding value + metadata filter
    # results = collection.query(
    # 	query_embeddings=[query_embedding],
    # 	n_results=10,
    # 	where={"book":"The Complete Book of Cheese"}
    # )
    # print("Query:", query)
    # print("\n\nResults:", results)

    # # 3: Query based on embedding value + lexical search filter
    # search_string = "Italian"
    # results = collection.query(
    # 	query_embeddings=[query_embedding],
    # 	n_results=10,
    # 	where_document={"$contains": search_string}
    # )
    # print("Query:", query)
    # print("\n\nResults:", results)

    # 4: Query based on embedding value + lexical search filter
    # search_string = "Italian"
    # results = collection.query(
    #     query_embeddings=[query_embedding],
    #     n_results=10,
    #     where={"book": "The Complete Book of Cheese"},
    #     where_document={"$contains": search_string}
    # )
    # print("Query:", query)
    # print("\n\nResults:", results)


def chat(method="char-split"):
    print("chat()")

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = f"{method}-collection"

    query = input("Ask FitAI: ") or "Summarize this document."
    query_embedding = generate_query_embedding(query)
    print("Query:", query)
    print("Embedding values:", query_embedding)
    # Get the collection
    collection = client.get_collection(name=collection_name)

    # Query based on embedding value
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=10
    )
    print("\n\nResults:", results)

    print(len(results["documents"][0]))

    context_chunks = "\n\n---\n".join(results["documents"][0])

    INPUT_PROMPT = f"""
    System: {SYSTEM_INSTRUCTION}

    User question:
    {query}

    Context from retrieved text:
    {context_chunks}
    """

    print("INPUT_PROMPT: ", INPUT_PROMPT)
    response = llm_client.models.generate_content(
        model=GENERATIVE_MODEL, contents=INPUT_PROMPT
    )
    generated_text = response.text

    print("\nFitAI Response:\n", getattr(response, "text", str(response)))


def get(method="char-split"):
    print("get()")

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = f"{method}-collection"

    # Get the collection
    collection = client.get_collection(name=collection_name)

    # Get documents with filters
    results = collection.get(
        where={"book": "The Complete Book of Cheese"},
        limit=10
    )
    print("\n\nResults:", results)


def agent(method="char-split"):
    print("agent()")

    # Connect to chroma DB
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    # Get a collection object from an existing collection, by name. If it doesn't exist, create it.
    collection_name = f"{method}-collection"
    # Get the collection
    collection = client.get_collection(name=collection_name)

    # User prompt
    user_prompt_content = Content(
        role="user",
        parts=[
            Part(text="Describe where cheese making is important in Pavlos's book?"),
        ],
    )

    # Step 1: Prompt LLM to find the tool(s) to execute to find the relevant chunks in vector db
    print("user_prompt_content: ", user_prompt_content)
    response = llm_client.models.generate_content(
        model=GENERATIVE_MODEL,
        contents=user_prompt_content,
        config=types.GenerateContentConfig(
            temperature=0,
            tools=[agent_tools.cheese_expert_tool],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="any"
                )
            )
        )
    )
    print("LLM Response:", response)

    # Step 2: Execute the function and send chunks back to LLM to answer get the final response
    function_calls = [part.function_call for part in response.candidates[0].content.parts if part.function_call]
    print("Function calls:", function_calls)
    function_responses = agent_tools.execute_function_calls(
        function_calls, collection, embed_func=generate_query_embedding)
    if len(function_responses) == 0:
        print("Function calls did not result in any responses...")
    else:
        # Call LLM with retrieved responses
        response = llm_client.models.generate_content(
            model=GENERATIVE_MODEL,
            contents=[
                user_prompt_content,  # User prompt
                response.candidates[0].content,  # Function call response
                Content(
                    parts=function_responses
                ),
            ],
            config=types.GenerateContentConfig(
                tools=[agent_tools.cheese_expert_tool]
            )
        )
        print("LLM Response:", response)


def main(args=None):
    print("CLI Arguments:", args)

    if args.chunk:
        chunk(method=args.chunk_type)

    if args.embed:
        embed(method=args.chunk_type)

    if args.load:
        load(method=args.chunk_type)

    if args.query:
        query(method=args.chunk_type)

    if args.chat:
        chat(method=args.chunk_type)

    if args.get:
        get(method=args.chunk_type)

    if args.agent:
        agent(method=args.chunk_type)


if __name__ == "__main__":
    # Generate the inputs arguments parser
    # if you type into the terminal '--help', it will provide the description
    parser = argparse.ArgumentParser(description="CLI")

    parser.add_argument(
        "--chunk",
        action="store_true",
        help="Chunk text",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Generate embeddings",
    )
    parser.add_argument(
        "--load",
        action="store_true",
        help="Load embeddings to vector db",
    )
    parser.add_argument(
        "--query",
        action="store_true",
        help="Query vector db",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Chat with LLM",
    )
    parser.add_argument(
        "--get",
        action="store_true",
        help="Get documents from vector db",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="Chat with LLM Agent",
    )
    parser.add_argument("--chunk_type", default="char-split",
                        help="char-split | recursive-split | semantic-split")

    args = parser.parse_args()

    main(args)
