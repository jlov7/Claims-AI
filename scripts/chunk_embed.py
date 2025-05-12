import argparse
import os
import json
import chromadb  # For ChromaDB client
from langchain_text_splitters import RecursiveCharacterTextSplitter  # Updated import

# from langchain_openai import OpenAIEmbeddings # No longer used directly
from dotenv import load_dotenv
import openai  # For direct client usage

# --- Refined HTTP Request Debugging ---
# Configure basicConfig to capture DEBUG from all loggers.
# This should make httpx and openai library log more details, hopefully including request bodies.
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# Explicitly set openai and httpx loggers to DEBUG just in case they don't inherit
# or if basicConfig was called by another library first with a higher level.
# logging.getLogger("openai").setLevel(logging.DEBUG)
# logging.getLogger("httpx").setLevel(logging.DEBUG)
# --- End Refined HTTP Request Debugging ---

# Load environment variables from .env file
# Ensure this path is correct, pointing to the .env file in the project root
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if not os.path.exists(dotenv_path):
    print(
        f"Warning: .env file not found at {dotenv_path}. Using default or system environment variables."
    )
load_dotenv(dotenv_path=dotenv_path, override=True)

# ChromaDB connection details (from .env)
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")  # Default to service name
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")  # Chroma server port inside Docker
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "claims_documents_mvp")

# Embedding model details (from .env)
# For local LM Studio, use the IP/port of your LM Studio server
OPENAI_API_BASE = os.getenv("PHI4_API_BASE", "http://host.docker.internal:1234/v1")
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME", "nomic-embed-text"
)  # Or your chosen model ID
OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY", "lm-studio"
)  # Dummy key for local LM Studio


class CustomLMStudioEmbeddings:
    """A custom embedding class that uses the openai client directly."""

    def __init__(self, api_base, api_key, model_name):
        self.client = openai.OpenAI(
            base_url=api_base,
            api_key=api_key,
        )
        self.model_name = model_name
        print(
            f"CustomLMStudioEmbeddings initialized: API_Base='{api_base}', Model='{model_name}'"
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts or not isinstance(texts, list):
            # print("Warning: embed_documents received empty or invalid input.")
            return []  # Return empty list if input is invalid

        response = self.client.embeddings.create(input=texts, model=self.model_name)
        embeddings = [item.embedding for item in response.data]
        # print(f"DEBUG: Custom embed_documents received {len(texts)} texts, returned {len(embeddings)} embeddings.")
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        if not text or not isinstance(text, str):
            raise ValueError("Input 'text' must be a non-empty string.")

        response = self.client.embeddings.create(
            input=[text],  # API expects a list, even for a single query
            model=self.model_name,
        )
        # print(f"DEBUG: Custom embed_query received '{text}', returned 1 embedding.")
        return response.data[0].embedding


def get_embedding_function():
    """Initializes and returns a custom embedding object compatible with LM Studio."""

    # Direct OpenAI client approach was successful, so we build upon that.
    print("--- Initializing CustomLMStudioEmbeddings ---")
    try:
        embedding_function = CustomLMStudioEmbeddings(
            api_base=OPENAI_API_BASE,
            api_key=OPENAI_API_KEY,
            model_name=EMBEDDING_MODEL_NAME,
        )
        # Test the custom embedding function
        test_query_embedding = embedding_function.embed_query(
            "Test query for custom embedder"
        )
        if not test_query_embedding or not isinstance(test_query_embedding[0], float):
            raise ValueError(
                "Custom embed_query test failed to return valid embedding."
            )

        test_docs_embeddings = embedding_function.embed_documents(
            ["Doc 1 for custom embedder", "Doc 2 for custom embedder"]
        )
        if (
            not test_docs_embeddings
            or len(test_docs_embeddings) != 2
            or not isinstance(test_docs_embeddings[0][0], float)
        ):
            raise ValueError(
                "Custom embed_documents test failed to return valid embeddings."
            )

        print("CustomLMStudioEmbeddings initialized and tested successfully.")
        return embedding_function

    except Exception as e:
        print(f"Error initializing CustomLMStudioEmbeddings: {e}")
        print(f"Model='{EMBEDDING_MODEL_NAME}', API_Base='{OPENAI_API_BASE}'")
        print(
            "Ensure LM Studio is running, serving an OpenAI-compatible embedding model, and environment variables are correct."
        )
        return None


def get_chromadb_client():
    """Initializes and returns a ChromaDB client."""
    try:
        # print(f"DEBUG: Attempting to connect to ChromaDB with CHROMA_HOST='{CHROMA_HOST}' and CHROMA_PORT='{CHROMA_PORT}'")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))
        # Check heartbeat to confirm connection
        client.heartbeat()  # This will raise an exception if connection fails
        print(f"Successfully connected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
        return client
    except Exception as e:
        print(f"Error connecting to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT} - {e}")
        print(
            "Ensure ChromaDB container is running and CHROMA_HOST/CHROMA_PORT are correct in .env."
        )
        return None


def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    """Chunks text using Langchain's RecursiveCharacterTextSplitter."""
    if not text or not text.strip():
        print("Warning: Attempted to chunk empty or whitespace-only text.")
        return []
    try:
        # It's good practice to use a tokenizer for more accurate chunking based on tokens
        # rather than just character length, especially if the embedding model has token limits.
        # However, RecursiveCharacterTextSplitter with char length is a good start.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,  # Max characters per chunk
            chunk_overlap=chunk_overlap,  # Characters to overlap between chunks
            length_function=len,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],  # Common separators, tried in order
        )
        chunks = text_splitter.split_text(text)
        if not chunks:
            print(
                "Warning: Text splitting resulted in no chunks. Original text might be too short or splitter misconfigured. Returning original text as one chunk."
            )
            return [text]  # Fallback to return the whole text as one chunk
        print(
            f"Split text into {len(chunks)} chunks (target size {chunk_size}, overlap {chunk_overlap})."
        )
        return chunks
    except Exception as e:
        print(f"Error during text chunking: {e}")
        return [text]  # Fallback: return original text as a single chunk on error


def process_json_file(file_path, collection, embedding_func):
    """Loads a JSON file, chunks its content, generates embeddings, and stores in ChromaDB."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        content = data.get("content")
        original_filename = data.get("original_filename", os.path.basename(file_path))

        if not content:
            print(f"No 'content' found in {original_filename}. Skipping.")
            return

        text_chunks = chunk_text(content)

        if not text_chunks:
            print(f"No text chunks generated for {original_filename}. Skipping.")
            return

        print(
            f"Generating embeddings for {len(text_chunks)} chunks from {original_filename}..."
        )
        try:
            chunk_embeddings = embedding_func.embed_documents(text_chunks)
            print(f"Successfully generated {len(chunk_embeddings)} embeddings.")
        except Exception as e:
            print(
                f"Error generating embeddings for {original_filename}: {e}. Skipping this file."
            )
            return

        if not chunk_embeddings or len(chunk_embeddings) != len(text_chunks):
            print(
                f"Embedding generation failed or returned unexpected number of embeddings for {original_filename}. Skipping."
            )
            return

        documents_to_store = text_chunks
        metadatas_to_store = []
        ids_to_store = []

        for i, chunk_content in enumerate(text_chunks):
            chunk_id = f"{data.get('sha256_hash', original_filename)}_chunk_{i}"  # Use hash for more robust ID
            metadatas_to_store.append(
                {
                    "original_filename": original_filename,
                    "chunk_index": i,
                    "document_sha256_hash": data.get("sha256_hash"),
                    "document_source_extension": data.get("source_file_extension"),
                    "document_file_size_bytes": data.get("file_size_bytes"),
                }
            )
            ids_to_store.append(chunk_id)

        collection.add(
            embeddings=chunk_embeddings,
            documents=documents_to_store,
            metadatas=metadatas_to_store,
            ids=ids_to_store,
        )
        print(
            f"Successfully stored {len(documents_to_store)} chunks for {original_filename} in ChromaDB collection '{collection.name}'."
        )

    except FileNotFoundError:
        print(f"Error: File not found {file_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred processing {file_path}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Chunk text from processed JSON files, generate embeddings, and store in ChromaDB."
    )
    parser.add_argument(
        "--in",
        dest="input_dir",
        required=True,
        help="Input directory containing processed JSON files from the OCR script.",
    )
    parser.add_argument(
        "--collection",
        default=CHROMA_COLLECTION_NAME,
        help=f"Name of the ChromaDB collection (default: {CHROMA_COLLECTION_NAME}).",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    collection_name = args.collection

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory '{input_dir}' not found.")
        return

    chroma_client = get_chromadb_client()
    embedding_func = get_embedding_function()

    if not chroma_client or not embedding_func:
        print(
            "CRITICAL Error: ChromaDB client or embedding function could not be initialized. Exiting."
        )
        return

    try:
        # Get or create the collection. Langchain embedding functions are usually not passed here directly.
        # The embedding model is implicitly defined by the vectors you add, or by collection metadata if supported.
        # For chromadb versions around 0.4.x, you might pass an EmbeddingFunction object.
        # For 0.5.x client, `sentence_transformers.SentenceTransformer` or `openai.OpenAIEmbeddings` from chromadb.utils.embedding_functions
        # For now, let's assume the collection will accept embeddings directly without pre-defining function at collection level here.
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            # metadata={"hnsw:space": "cosine"} # Default is L2, cosine often better for semantic
        )
        print(f"Using ChromaDB collection: '{collection.name}'")
    except Exception as e:
        print(f"Error getting or creating ChromaDB collection '{collection_name}': {e}")
        return

    print(f"Starting chunking and embedding process for files in '{input_dir}'...")

    processed_files_count = 0
    for item in os.listdir(input_dir):
        if item.endswith(".json"):
            file_path = os.path.join(input_dir, item)
            print(f"--- Processing JSON file: {item} ---")
            process_json_file(file_path, collection, embedding_func)
            processed_files_count += 1
        else:
            print(f"Skipping non-JSON file: {item}")

    if processed_files_count == 0:
        print(f"No JSON files found in '{input_dir}'. Nothing to process.")

    print("Chunking and embedding process completed.")


if __name__ == "__main__":
    main()
