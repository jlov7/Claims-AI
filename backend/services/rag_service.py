import logging
from typing import List, Optional, Tuple
import chromadb
from chromadb.utils import embedding_functions
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import re
import base64  # Added for Basic Auth

from backend.core.config import get_settings
from backend.models import SourceDocument

# Configure logging
logger = logging.getLogger(__name__)
# settings: Settings = get_settings() # This line can be removed as settings is imported directly

# For Langchain LCEL debugging (optional)
# langchain.debug = True


class RAGService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance

    def __init__(self, settings_instance=get_settings()):
        # Prevent re-initialization
        if hasattr(self, "_initialized") and self._initialized:
            return
        logger.info("Initializing RAGService...")
        self.settings = settings_instance
        logger.info(
            f"Initializing RAGService with LM Studio URL: {self.settings.PHI4_API_BASE}"
        )
        logger.info(
            f"Embedding Model: {self.settings.EMBEDDING_MODEL_NAME}, LLM Model: {self.settings.PHI4_MODEL_NAME}"
        )

        # This specific OpenAIEmbeddings client might be redundant if
        # ChromaDB's collection handles embeddings via its assigned embedding_function.
        # For now, keeping it to ensure no other part relies on it, but review for removal if unused.
        # self.embeddings_client = OpenAIEmbeddings(
        #     openai_api_base=self.settings.PHI4_API_BASE,
        #     openai_api_key="lm-studio",
        #     model=self.settings.EMBEDDING_MODEL_NAME,
        #     chunk_size=1
        # )
        # logger.info("OpenAIEmbeddings client (self.embeddings_client) initialized.")

        self.llm_client = ChatOpenAI(
            openai_api_base=self.settings.PHI4_API_BASE,
            openai_api_key="lm-studio",  # Required by Langchain, but not used by LM Studio
            model="llama-3.2-3b-instruct",  # Explicitly use Llama model
            temperature=0.1,  # Much lower temperature to force direct answers
        )
        logger.info("ChatOpenAI client initialized with model: llama-3.2-3b-instruct")

        try:
            headers = {}
            if self.settings.CHROMA_USER and self.settings.CHROMA_PASSWORD:
                credentials = (
                    f"{self.settings.CHROMA_USER}:{self.settings.CHROMA_PASSWORD}"
                )
                encoded_credentials = base64.b64encode(
                    credentials.encode("utf-8")
                ).decode("utf-8")
                headers["Authorization"] = f"Basic {encoded_credentials}"

            # Updated HttpClient initialization
            self.chroma_client = chromadb.HttpClient(
                host=self.settings.CHROMA_HOST,
                port=self.settings.CHROMA_PORT,
                headers=headers,  # Pass headers here
                # settings=chromadb.config.Settings( # This part is removed/modified
                #     chroma_client_auth_provider="chromadb.auth.basic.BasicAuthClientProvider",
                #     chroma_client_auth_credentials=f"{self.settings.CHROMA_USER}:{self.settings.CHROMA_PASSWORD}"
                # )
            )
            logger.info(
                f"Attempting to connect to ChromaDB at {self.settings.CHROMA_HOST}:{self.settings.CHROMA_PORT}"
            )
            self.chroma_client.heartbeat()  # Check connection
            logger.info("Successfully connected to ChromaDB.")

            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_base=self.settings.PHI4_API_BASE,  # Use the same base for embeddings if served by LM Studio
                api_key="dummy_key",  # OpenAI API key, not strictly needed for LM Studio if not charging
                model_name=self.settings.EMBEDDING_MODEL_NAME,
            )
            logger.info(f"Using embedding model: {self.settings.EMBEDDING_MODEL_NAME}")

            self.collection = self.chroma_client.get_or_create_collection(
                name=self.settings.CHROMA_COLLECTION_NAME,
                embedding_function=self.embedding_function,
                # metadata={"hnsw:space": "cosine"} # Default is l2, cosine is often preferred
            )
            logger.info(
                f"Successfully got or created ChromaDB collection: {self.settings.CHROMA_COLLECTION_NAME}"
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize ChromaDB client or collection: {e}",
                exc_info=True,
            )
            # Depending on the desired behavior, you might want to raise the exception
            # or handle it in a way that the service can still operate in a degraded mode (if applicable)
            raise RuntimeError(f"RAGService failed to initialize ChromaDB: {e}")

        self._initialized = True
        logger.info("RAGService initialized.")

    def _format_context(self, documents: List[str]) -> str:
        return "\n\n".join(doc for doc in documents if doc)

    async def query_rag(
        self, user_query: str
    ) -> Tuple[str, List[SourceDocument], Optional[int], int]:
        logger.info(f"RAG query received: {user_query}")
        if not user_query:
            logger.warning("Empty query received.")
            return (
                "Please provide a query.",
                [],
                3,
                0,
            )  # Default confidence for empty query

        try:
            # 1. Generate query embedding
            # query_embedding = self.embedding_function([user_query])[0] # Chroma's EF handles this if passed in query

            # 2. Query ChromaDB for relevant chunks
            logger.debug(
                f"Querying ChromaDB collection '{self.collection.name}' for query: '{user_query}'"
            )
            # Hybrid search: semantic + keyword filter
            results = self.collection.query(
                query_texts=[user_query],
                n_results=self.settings.RAG_NUM_SOURCES,
                include=["metadatas", "documents", "distances"],
            )
            logger.debug(f"ChromaDB results: {results}")

            sources: List[SourceDocument] = []
            context_str = ""
            if (
                not results
                or not results.get("documents")
                or not results["documents"][0]
                or len(results["documents"][0]) == 0
            ):
                logger.info("No relevant documents found in ChromaDB for the query.")

                # Always return the SAME tuple shape the frontend expects:
                #   text:str, sources:list[dict], confidence:int, attempts:int
                placeholder_content = "Unfortunately, I couldn't find specific text passages that answer your question directly. Would you like to try rephrasing your question or exploring a different topic?"
                empty_source = {
                    "file_name": "placeholder_document.txt",
                    "chunk_content": placeholder_content,
                    "page_content": placeholder_content,  # Added for frontend compatibility
                    "chunk_id": "placeholder_chunk",
                    "score": 0.5,
                }

                return (
                    "I don't have enough specific information from your documents to answer this question confidently. Try rephrasing or asking about a topic covered in your documents.",
                    [empty_source],  # still a list, but with placeholder
                    2,  # low confidence
                    0,  # no self‑healing attempts
                )

            for i, doc_content in enumerate(results["documents"][0]):
                meta = (
                    results["metadatas"][0][i]
                    if results.get("metadatas")
                    and results["metadatas"][0]
                    and i < len(results["metadatas"][0])
                    else {}
                )
                dist = (
                    results["distances"][0][i]
                    if results.get("distances")
                    and results["distances"][0]
                    and i < len(results["distances"][0])
                    else None
                )

                # Ensure this matches the SourceDocument model fields
                source_doc = SourceDocument(
                    document_id=meta.get("document_id", "unknown_id"),
                    chunk_id=meta.get("chunk_id", "unknown_chunk"),
                    chunk_content=doc_content,  # Corrected field name
                    file_name=meta.get("filename", "unknown_file"),
                    score=round(dist, 2) if dist is not None else 0.0,
                )

                # Create a dictionary representation that includes both chunk_content and page_content
                source_dict = source_doc.model_dump()
                source_dict["page_content"] = (
                    doc_content  # Add page_content for frontend compatibility
                )
                sources.append(
                    SourceDocument(**source_dict)
                )  # Create a new SourceDocument with both fields

                context_str += f"Source {i+1} (Document: {source_doc.file_name}, Chunk: {source_doc.chunk_id}):\n{doc_content}\n\n"
            logger.info(f"Retrieved {len(sources)} sources from ChromaDB.")

            if not sources:
                logger.info(
                    "No relevant documents found in ChromaDB for the query after processing."
                )
                placeholder_content = "Unfortunately, I couldn't find specific text passages that answer your question directly. Would you like to try rephrasing your question or exploring a different topic?"
                empty_source = {
                    "file_name": "placeholder_document.txt",
                    "chunk_content": placeholder_content,
                    "page_content": placeholder_content,  # Added for frontend compatibility
                    "chunk_id": "placeholder_chunk",
                    "score": 0.5,
                }

                return (
                    "I don't have enough specific information from your documents to answer this question confidently. Try rephrasing or asking about a topic covered in your documents.",
                    [empty_source],
                    2,
                    0,
                )

            # 3. Construct prompt with context
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    (
                        "user",
                        "Query: {query}\n\nContext:\n{context}\n\nAnswer the query using ONLY information from the context above. If the answer is not in the context, say 'I don't know based on the provided documents.'",
                    ),
                ]
            )

            chain = prompt_template | self.llm_client | StrOutputParser()

            # 4. Generate answer using LLM
            logger.debug("Sending prompt to LLM for answer generation.")
            answer = await chain.ainvoke({"context": context_str, "query": user_query})
            logger.info(f"LLM generated answer: {answer}")

            # 5. Generate confidence score for the first answer
            confidence_score = await self._get_confidence_score(
                user_query, context_str, answer
            )
            logger.info(f"Initial confidence score: {confidence_score}")

            # 6. Self-healing mechanism
            current_attempt = 0
            while (
                confidence_score < self.settings.CONFIDENCE_THRESHOLD_SELF_HEAL
                and current_attempt < self.settings.SELF_HEAL_MAX_ATTEMPTS
            ):
                current_attempt += 1
                logger.info(
                    f"Confidence score {confidence_score} is below threshold {self.settings.CONFIDENCE_THRESHOLD_SELF_HEAL}. Attempting self-heal #{current_attempt}."
                )

                # Construct re-prompt for self-healing
                re_prompt_template = ChatPromptTemplate.from_messages(
                    [
                        (
                            "user",
                            "Query: {query}\n\nContext:\n{context}\n\nPrevious answer: {previous_answer}\n\nPlease revise the previous answer using ONLY information from the context above.",
                        ),
                    ]
                )

                revision_chain = (
                    re_prompt_template | self.llm_client | StrOutputParser()
                )
                logger.debug(
                    "Sending prompt to LLM for answer revision (self-healing)."
                )
                revised_answer = await revision_chain.ainvoke(
                    {
                        "query": user_query,
                        "context": context_str,
                        "previous_answer": answer,  # Pass the previous low-confidence answer
                    }
                )
                logger.info(
                    f"LLM generated revised answer (self-heal attempt #{current_attempt}): {revised_answer}"
                )
                answer = revised_answer  # Update answer with the revised one

                # Recalculate confidence for the revised answer
                confidence_score = await self._get_confidence_score(
                    user_query, context_str, answer
                )
                logger.info(
                    f"Confidence score after self-heal attempt #{current_attempt}: {confidence_score}"
                )

            logger.info(
                f"Final answer: '{answer[:100]}...', Sources: {len(sources)}, Confidence: {confidence_score}"
            )
            return answer, sources, confidence_score, current_attempt

        except Exception as e:
            logger.error(
                f"Error processing RAG query '{user_query}': {e}", exc_info=True
            )
            # Fallback response in case of unexpected errors
            return (
                "I encountered an error trying to answer your question.",
                [],
                1,
                0,
            )  # Lowest confidence on error

    # Helper method for confidence scoring to avoid repetition
    async def _get_confidence_score(self, query: str, context: str, answer: str) -> int:
        confidence_prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "user",
                    "Rate confidence from 1-5: {answer} (based on context: {context}). Return ONLY a number.",
                ),
            ]
        )
        confidence_chain = (
            confidence_prompt_template | self.llm_client | StrOutputParser()
        )
        logger.debug("Sending prompt to LLM for confidence scoring.")
        confidence_score_str = await confidence_chain.ainvoke(
            {"query": query, "context": context, "answer": answer}
        )
        logger.info(f"LLM generated confidence score string: '{confidence_score_str}'")

        parsed_score = 3  # Default confidence score
        try:
            match = re.search(r"\d+", confidence_score_str)
            if match:
                score = int(match.group(0))
                if 1 <= score <= 5:
                    parsed_score = score
                else:
                    logger.warning(
                        f"Confidence score '{score}' out of range (1-5). Defaulting to 3."
                    )
            else:
                logger.warning(
                    f"Could not parse confidence score from LLM response: '{confidence_score_str}'. Defaulting to 3."
                )
        except ValueError:
            logger.warning(
                f"Could not parse confidence score from LLM response: '{confidence_score_str}'. Defaulting to 3."
            )
        except Exception as e:
            logger.error(
                f"Error parsing confidence score: {e}. Defaulting to 3.", exc_info=True
            )
        return parsed_score


# Dependency for FastAPI
# settings is imported globally from backend.core.config
_rag_service_instance = None


def get_rag_service() -> RAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        # Use get_settings() to ensure a fully initialized settings object is used.
        current_settings = get_settings()
        _rag_service_instance = RAGService(settings_instance=current_settings)
    return _rag_service_instance


# Removed incomplete SummarisationService to fix linter error
# class SummarisationService:
#     # ... existing code ...
#     # ... additional methods ...
#     # ...
