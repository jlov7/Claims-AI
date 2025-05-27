import csv
import os
import chromadb
from dotenv import load_dotenv
import logging
from langchain.embeddings import OpenAIEmbeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def load_env_vars():
    """Load environment variables from .env file."""
    load_dotenv(override=True)  # Ensure .env overrides shell variables
    required_vars = [
        "CHROMA_HOST",
        "CHROMA_PORT",
        "CHROMA_PRECEDENTS_COLLECTION_NAME",
        "OLLAMA_API_BASE",
        "EMBEDDING_MODEL_NAME",
        "OPENAI_API_KEY",
    ]
    env_vars = {var: os.getenv(var) for var in required_vars}
    for var, value in env_vars.items():
        if not value:
            logging.error(f"Missing required environment variable: {var}")
            raise ValueError(f"Missing required environment variable: {var}")
    # Ensure OLLAMA_API_BASE ends with /v1 if it doesn't already, for OpenAIEmbeddings
    if not env_vars["OLLAMA_API_BASE"].endswith("/v1"):
        env_vars["OLLAMA_API_BASE"] = env_vars["OLLAMA_API_BASE"].rstrip("/") + "/v1"
        logging.info(f"Adjusted OLLAMA_API_BASE to: {env_vars['OLLAMA_API_BASE']}")
    return env_vars


def get_chroma_client(host, port):
    """Initialize and return ChromaDB client."""
    try:
        logging.info(
            f"Attempting to use CHROMA_HOST: '{host}', CHROMA_PORT: '{port}' (type: {type(port)})"
        )
        client = chromadb.HttpClient(host=host, port=port)
        client.heartbeat()  # Check connection
        logging.info(f"Successfully connected to ChromaDB at {host}:{port}")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to ChromaDB: {e}")
        raise


def get_embedding_function(api_base: str, model_name: str, api_key: str):
    """Initializes and returns an OpenAI-compatible embedding function."""
    try:
        # For LangChain >0.1.0, use OpenAIEmbeddings directly
        # The api_key can be a dummy string if the local server doesn't require it,
        # or it might be used to select among multiple models.
        embeddings = OpenAIEmbeddings(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
        )
        logging.info(
            f"Initialized OpenAIEmbeddings with model '{model_name}' and base URL '{api_base}'"
        )
        return embeddings
    except Exception as e:
        logging.error(f"Failed to initialize embedding function: {e}")
        raise


def process_precedents(csv_filepath, collection_name, chroma_client, embed_func):
    """Read precedents from CSV, generate embeddings, and store in ChromaDB."""
    try:
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=embed_func,  # Assign embedding function at collection creation/retrieval
        )
        logging.info(f"Using ChromaDB collection: {collection_name}")
    except Exception as e:
        logging.error(f"Failed to get or create collection '{collection_name}': {e}")
        raise

    documents = []
    metadatas = []
    ids = []
    count = 0

    try:
        with open(csv_filepath, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                claim_id = row.get("ClaimID")
                summary = row.get("Summary")
                outcome = row.get("Outcome")
                keywords = row.get("Keywords")

                if not claim_id or not summary:
                    logging.warning(
                        f"Skipping row due to missing ClaimID or Summary: {row}"
                    )
                    continue

                documents.append(summary)  # Text to be embedded
                metadatas.append(
                    {
                        "claim_id": claim_id,
                        "outcome": outcome,
                        "keywords": keywords,
                        "original_summary": summary,  # Store original summary in metadata too
                    }
                )
                ids.append(claim_id)  # Use ClaimID as the unique ID for ChromaDB entry
                count += 1
                logging.debug(f"Prepared precedent ID: {claim_id} for embedding.")

        if not documents:
            logging.info("No valid documents found in CSV to process.")
            return 0

        # Add to ChromaDB. The embedding function assigned to the collection will be used.
        # ChromaDB client handles batching if documents list is large.
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logging.info(
            f"Successfully processed and added {count} precedents to collection '{collection_name}'."
        )
        return count
    except FileNotFoundError:
        logging.error(f"Precedent CSV file not found at: {csv_filepath}")
        raise
    except Exception as e:
        logging.error(f"Error processing precedents CSV or adding to ChromaDB: {e}")
        raise


def main():
    logging.info("Starting precedent embedding script...")
    try:
        env_vars = load_env_vars()

        chroma_client = get_chroma_client(
            env_vars["CHROMA_HOST"], env_vars["CHROMA_PORT"]
        )

        # The embedding function is now associated with the collection, not passed to add() directly
        # For OpenAIEmbeddingFunction, it's better to instantiate it once and pass it to the collection.
        # However, chromadb's client API for OpenAIEmbeddingFunction wants it passed during collection creation/get.
        # So we will pass the embedding function class and its parameters to get_or_create_collection
        # through the embedding_function parameter.
        # Let's define the embedding function for the collection

        # For chromadb versions 0.4.22+, embedding_functions.OpenAIEmbeddingFunction is the way
        ef = get_embedding_function(
            env_vars["OLLAMA_API_BASE"],
            env_vars["EMBEDDING_MODEL_NAME"],
            env_vars["OPENAI_API_KEY"],  # Pass the api_key
        )

        csv_filepath = "data/precedents/precedents.csv"
        collection_name = env_vars["CHROMA_PRECEDENTS_COLLECTION_NAME"]

        num_processed = process_precedents(
            csv_filepath, collection_name, chroma_client, ef
        )
        logging.info(
            f"Precedent embedding script finished. Processed {num_processed} precedents."
        )

    except ValueError as ve:
        logging.error(f"Configuration error: {ve}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main()
