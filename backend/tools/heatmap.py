import logging
from typing import List, Dict, Union, Optional
import numpy as np

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from core.config import get_settings

# Assuming a similar document loading mechanism to SummarisationService
# This might need to be refactored into a shared DocumentService later
# from backend.services.summarisation_service import SummarisationService

logger = logging.getLogger(__name__)
settings = get_settings()


# Helper function to calculate cosine similarity using NumPy
def cosine_similarity_numpy(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculates cosine similarity between two numpy vectors."""
    if not isinstance(vec1, np.ndarray) or not isinstance(vec2, np.ndarray):
        logger.error(f"Inputs must be numpy arrays. Got {type(vec1)=}, {type(vec2)=}")
        return 0.0
    if vec1.shape != vec2.shape:
        logger.error(
            f"Input vectors must have the same shape. Got {vec1.shape=}, {vec2.shape=}"
        )
        return 0.0

    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)

    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0  # Or handle as an error, depending on requirements

    return dot_product / (norm_vec1 * norm_vec2)


@tool
async def smart_skim_tool(
    document_id: str,
    query: str,
    top_n: int = 5,
    chunk_size: int = 1000,  # Characters per chunk (simulating a page)
    chunk_overlap: int = 200,  # Overlap between chunks
) -> List[Dict[str, Union[int, float, str]]]:
    """
    Scores document chunks (pages) based on embedding similarity to a query
    and returns the top N most relevant chunks.
    """
    logger.info(
        f"Smart-Skim tool invoked for document_id: '{document_id}', query: '{query[:50]}...'"
    )

    try:
        # 1. Fetch document content
        # Adapting from SummarisationService._get_content_from_id
        # TODO: Refactor document loading into a shared service if not already planned.
        # For now, let's instantiate SummarisationService to use its method.
        # This is not ideal for a tool, but works as a starting point.
        summarisation_service = SummarisationService()  # Requires settings
        # The _get_content_from_id is protected, let's make a conceptual call here.
        # In a real scenario, this would be a public method or a separate service.

        # Simplified document fetching for now, assuming direct path construction
        # This part needs to be robust based on how document_id translates to a file path
        # For example, if document_id is just a filename like "mydoc.txt"
        raw_file_path = settings.RAW_DATA_DIR / document_id
        processed_file_path = settings.PROCESSED_TEXT_DIR / document_id
        json_file_path_raw = settings.RAW_DATA_DIR / f"{document_id}.json"
        json_file_path_processed = settings.PROCESSED_TEXT_DIR / f"{document_id}.json"

        content: Optional[str] = None

        # Try loading based on common patterns. This is a simplified version
        # of _get_content_from_id's logic.
        potential_paths = [
            raw_file_path,
            processed_file_path,
            json_file_path_raw,
            json_file_path_processed,
        ]

        document_text: Optional[str] = None
        found_path = None

        for path_obj in potential_paths:
            try:
                if path_obj.exists():
                    # SummarisationService._get_content_from_id has more complex logic for JSON
                    # For simplicity, we assume text files or simple JSON with a "text" field.
                    if path_obj.suffix == ".json":
                        import json

                        with open(path_obj, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            document_text = data.get(
                                "text"
                            )  # Assuming a common structure
                    else:  # Assume .txt or other plain text
                        with open(path_obj, "r", encoding="utf-8") as f:
                            document_text = f.read()

                    if document_text:
                        found_path = path_obj
                        logger.info(f"Successfully loaded content from {found_path}")
                        break
            except Exception as e:
                logger.warning(f"Could not read or parse {path_obj}: {e}")
                continue

        if not document_text:
            logger.error(
                f"Document not found or content is empty for document_id: {document_id}"
            )
            return [{"error": f"Document not found or empty: {document_id}"}]

    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {e}")
        return [{"error": f"Failed to fetch document {document_id}: {str(e)}"}]

    # 2. Split content into pages/chunks
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_text(document_text)
        if not chunks:
            logger.warning(
                f"Document {document_id} resulted in no text chunks after splitting."
            )
            return []
        logger.info(f"Document {document_id} split into {len(chunks)} chunks.")
    except Exception as e:
        logger.error(f"Error splitting document {document_id}: {e}")
        return [{"error": f"Failed to split document {document_id}: {str(e)}"}]

    # 3. Initialize Embeddings
    try:
        embeddings_model = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            openai_api_base=settings.openai_api_base,
            model=settings.embedding_model_name,
        )
    except Exception as e:
        logger.error(f"Failed to initialize embeddings model: {e}")
        return [{"error": f"Failed to initialize embeddings model: {str(e)}"}]

    # 4. Generate embeddings
    try:
        query_embedding_list = await embeddings_model.aembed_query(query)
        query_embedding = np.array(query_embedding_list)

        chunk_embeddings_list = await embeddings_model.aembed_documents(chunks)
        chunk_embeddings = [np.array(emb) for emb in chunk_embeddings_list]

        if (
            query_embedding.size == 0
            or not chunk_embeddings
            or all(ce.size == 0 for ce in chunk_embeddings)
        ):
            logger.error("Failed to generate valid embeddings for query or chunks.")
            return [{"error": "Failed to generate embeddings."}]

    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return [{"error": f"Failed to generate embeddings: {str(e)}"}]

    # 5. Calculate cosine similarity
    page_scores: List[Dict[str, Union[int, float, str]]] = []
    for i, chunk_emb in enumerate(chunk_embeddings):
        if chunk_emb.size == 0:
            score = 0.0
            logger.warning(f"Empty embedding for chunk {i} of document {document_id}")
        else:
            try:
                score = cosine_similarity_numpy(query_embedding, chunk_emb)
            except Exception as e:
                logger.error(f"Error calculating similarity for chunk {i}: {e}")
                score = 0.0  # Default score on error

        page_scores.append(
            {
                "page_number": i + 1,  # 1-indexed page/chunk number
                "score": float(score),
                "preview": (
                    chunks[i][:200] + "..." if len(chunks[i]) > 200 else chunks[i]
                ),  # Preview of the chunk
            }
        )

    # 6. Sort by score and return top N
    sorted_pages = sorted(page_scores, key=lambda x: x["score"], reverse=True)

    logger.info(
        f"Successfully processed Smart-Skim for {document_id}. Top score: {sorted_pages[0]['score'] if sorted_pages else 'N/A'}"
    )
    return sorted_pages[:top_n]


if __name__ == "__main__":
    # Example Usage (requires Ollama or OpenAI API compatible server running)
    import os
    from dotenv import load_dotenv

    # Create dummy files and directories for testing
    def setup_dummy_files():
        # Load .env from project root for settings
        # Assumes .env is in the workspace root if this script is run directly
        # For testing, it's better to configure settings directly or use a test-specific .env
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        dotenv_path = os.path.join(project_root, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path=dotenv_path, override=True)
            print(f"Loaded .env from {dotenv_path}")
        else:
            print(
                f".env file not found at {dotenv_path}. Ensure OPENAI_API_KEY and OPENAI_API_BASE are set for embeddings."
            )
            # Fallback for critical env vars if .env is not found/loaded
            if not os.getenv("OPENAI_API_BASE"):
                os.environ["OPENAI_API_BASE"] = (
                    "http://localhost:11434/v1"  # Default for Ollama
                )
            if not os.getenv("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = "ollama"  # Common placeholder for Ollama

        # Ensure settings are reloaded with env vars
        global settings
        settings = get_settings(
            reload=True
        )  # Add reload capability to get_settings if needed or re-instantiate

        # Access settings after reload
        print(f"Using RAW_DATA_DIR: {settings.RAW_DATA_DIR}")
        print(f"Using PROCESSED_TEXT_DIR: {settings.PROCESSED_TEXT_DIR}")

        os.makedirs(settings.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_TEXT_DIR, exist_ok=True)

        # Create a dummy text file
        dummy_text_content = """
        The quick brown fox jumps over the lazy dog. This is the first page of an example document.
        It contains some common words and phrases. We can use this for testing the smart skim tool.
        The smart skim tool should help identify relevant sections based on a query.
        
        This is the second page. It talks about different things. For example, artificial intelligence.
        AI is a rapidly growing field with many applications. LangChain and LangGraph are useful tools.
        We are building a system for claims processing.
        
        Page three contains details about data privacy and security. It's important to handle data carefully.
        Anonymization and encryption are key techniques. The Smart-Skim tool will process text.
        
        The final page, page four, discusses future plans and development.
        We aim to improve accuracy and efficiency. More tools will be added.
        The project uses Mistral models via Ollama.
        """
        with open(settings.RAW_DATA_DIR / "test_doc.txt", "w", encoding="utf-8") as f:
            f.write(dummy_text_content)

        # Create a dummy JSON file
        dummy_json_content = {
            "text": "This is a JSON document. It has some text content about cats and dogs. The smart skim tool might be queried about pets.",
            "metadata": {"source": "dummy_json_generator"},
        }
        with open(
            settings.PROCESSED_TEXT_DIR / "test_json_doc.json", "w", encoding="utf-8"
        ) as f:
            import json

            json.dump(dummy_json_content, f, indent=2)

    async def main():
        setup_dummy_files()

        # Test with the text document
        print("\n--- Testing with test_doc.txt ---")
        doc_id_txt = "test_doc.txt"
        query1 = "artificial intelligence and claims processing"
        results1 = await smart_skim_tool(document_id=doc_id_txt, query=query1, top_n=2)
        print(f"Results for query '{query1}':")
        for res in results1:
            print(
                f"  Page: {res.get('page_number')}, Score: {res.get('score'):.4f}, Preview: '{res.get('preview')}'"
            )

        query2 = "data privacy"
        results2 = await smart_skim_tool(document_id=doc_id_txt, query=query2, top_n=1)
        print(f"\nResults for query '{query2}':")
        for res in results2:
            print(
                f"  Page: {res.get('page_number')}, Score: {res.get('score'):.4f}, Preview: '{res.get('preview')}'"
            )

        # Test with the JSON document
        print("\n--- Testing with test_json_doc.json ---")
        doc_id_json = "test_json_doc.json"
        query3 = "pets like cats and dogs"
        results3 = await smart_skim_tool(document_id=doc_id_json, query=query3, top_n=1)
        print(f"Results for query '{query3}':")
        for res in results3:
            print(
                f"  Page: {res.get('page_number')}, Score: {res.get('score'):.4f}, Preview: '{res.get('preview')}'"
            )

        # Test document not found
        print("\n--- Testing document not found ---")
        results_not_found = await smart_skim_tool(
            document_id="non_existent_doc.txt", query="anything"
        )
        print(f"Results for non_existent_doc.txt: {results_not_found}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    )
    # asyncio.run(main()) # This will be commented out as it's for local testing by the developer.
    # print("To test, uncomment asyncio.run(main()) and run this file directly.")
    # print("Ensure Ollama is running and serving an embedding model (e.g., `ollama pull nomic-embed-text` and then ensure your .env points OPENAI_API_BASE to ollama and uses a model name like 'nomic-embed-text').")
