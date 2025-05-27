import logging
from typing import List, Optional, Tuple
import chromadb
from chromadb.utils.embedding_functions.chroma_langchain_embedding_function import (
    create_langchain_embedding,
)
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama
import base64
import re  # For confidence score parsing

from core.config import get_settings
from models import SourceDocument
from core.rag_pipeline import create_rag_pipeline  # Correct import
from langchain_core.prompts import ChatPromptTemplate  # For confidence score
from langchain_core.output_parsers import StrOutputParser  # For confidence score

logger = logging.getLogger(__name__)

# Global RAGService instance to enable singleton-like behavior if desired via get_rag_service
_rag_service_instance: Optional["RAGService"] = None

class RAGService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance

    def __init__(self, settings_instance=get_settings()):
        if hasattr(self, "_initialized") and self._initialized:
            return
        logger.info("Initializing RAGService...")
        self.settings = settings_instance

        self.llm_client = ChatOllama(
            base_url=self.settings.OLLAMA_BASE_URL,
            model=self.settings.OLLAMA_MODEL_NAME,
            temperature=self.settings.LLM_TEMPERATURE,
        )
        logger.info(
            f"ChatOllama client initialized for RAGService with model: {self.settings.OLLAMA_MODEL_NAME} at base_url: {self.settings.OLLAMA_BASE_URL}"
        )

        self.rag_pipeline = create_rag_pipeline(self.llm_client)
        logger.info("Core RAG pipeline created and initialized.")

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

            self.chroma_client = chromadb.HttpClient(
                host=self.settings.CHROMA_HOST,
                port=self.settings.CHROMA_PORT,
                headers=headers,
            )
            logger.info(
                f"Attempting to connect to ChromaDB at {self.settings.CHROMA_HOST}:{self.settings.CHROMA_PORT}"
            )
            self.chroma_client.heartbeat()
            logger.info("Successfully connected to ChromaDB.")

            self.embedding_function = OllamaEmbeddings(
                base_url=self.settings.OLLAMA_BASE_URL,
                model=self.settings.EMBEDDING_MODEL_NAME,
            )
            logger.info(
                f"Using OllamaEmbeddings with model: {self.settings.EMBEDDING_MODEL_NAME} at base_url: {self.settings.OLLAMA_BASE_URL}"
            )

            # Wrap the LangChain embedding function with ChromaDB's adapter
            chroma_compatible_embedding_function = create_langchain_embedding(
                self.embedding_function
            )

            self.collection = self.chroma_client.get_or_create_collection(
                name=self.settings.CHROMA_COLLECTION_NAME,
                embedding_function=chroma_compatible_embedding_function,
            )
            logger.info(
                f"Successfully got or created ChromaDB collection: {self.settings.CHROMA_COLLECTION_NAME}"
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize ChromaDB client or collection: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"RAGService failed to initialize ChromaDB: {e}")

        self._initialized = True
        logger.info("RAGService initialized.")

    # _format_context, _format_context_enhanced, and _post_process_answer methods are removed.
    # Their logic is now in backend.core.rag_pipeline.py

    async def query_rag(
        self, user_query: str
    ) -> Tuple[str, List[SourceDocument], Optional[int], int]:
        logger.info(f"RAG query received: {user_query}")
        if not user_query:
            logger.warning("Empty query received.")
            return "Please provide a query.", [], 3, 0

        source_documents: List[SourceDocument] = []
        num_retrieved_chunks = 0

        try:
            logger.debug(
                f"Querying ChromaDB collection '{self.collection.name}' for query: '{user_query}'"
            )

            collection_info = self.collection.get()  # type: ignore
            collection_count = (
                len(collection_info.get("ids", [])) if collection_info else 0
            )
            logger.info(
                f"Collection '{self.collection.name}' has {collection_count} documents"
            )

            current_collection_to_query = self.collection
            if collection_count == 0:
                logger.warning(
                    f"Collection '{self.collection.name}' is empty! Attempting to query alternative collection"
                )
                try:
                    alt_collection_name = (
                        "claims_documents_mvp"
                        if self.collection.name == "claims_collection"
                        else "claims_collection"
                    )
                    logger.info(f"Trying alternative collection: {alt_collection_name}")
                    alt_collection = self.chroma_client.get_collection(
                        name=alt_collection_name,
                        embedding_function=self.embedding_function,
                    )
                    if alt_collection.count() > 0:  # type: ignore
                        current_collection_to_query = alt_collection
                        logger.info(
                            f"Switched to alternative collection: {alt_collection_name} for this query."
                        )
                    else:
                        logger.warning(
                            f"Alternative collection '{alt_collection_name}' is also empty or not found."
                        )
                except Exception as alt_e:
                    logger.error(
                        f"Error trying to access alternative collection: {alt_e}"
                    )

            if current_collection_to_query.count() > 0:  # type: ignore
                results = current_collection_to_query.query(
                    query_texts=[user_query],
                    n_results=self.settings.RAG_NUM_SOURCES,
                    include=["documents", "metadatas", "distances"],
                )
                num_retrieved_chunks = len(results.get("ids", [[]])[0])
                logger.info(f"Retrieved {num_retrieved_chunks} chunks from ChromaDB.")

                if results and results.get("documents") and results.get("metadatas"):
                    docs = results["documents"][0]
                    metadatas = results["metadatas"][0]
                    for i, doc_content in enumerate(docs):
                        metadata = metadatas[i]
                        source_documents.append(
                            SourceDocument(
                                document_id=metadata.get("document_id", "unknown"),
                                chunk_id=metadata.get("chunk_id", f"chunk_{i}"),
                                file_name=metadata.get("file_name", "unknown_file"),
                                chunk_content=doc_content,
                                score=(
                                    results["distances"][0][i]
                                    if results.get("distances")
                                    else None
                                ),
                            )
                        )
            else:
                logger.warning(
                    f"Collection '{current_collection_to_query.name}' is empty. No documents to retrieve."
                )

            pipeline_input = {"query": user_query, "documents": source_documents}
            pipeline_result = await self.rag_pipeline.ainvoke(pipeline_input)

            llm_answer = pipeline_result.get(
                "answer", "Failed to get answer from pipeline."
            )
            context_for_confidence = pipeline_result.get(
                "formatted_context", "No context was generated by the pipeline."
            )

            confidence_score = await self._get_confidence_score(
                user_query, context_for_confidence, llm_answer
            )
            logger.info(f"RAG Confidence Score: {confidence_score}")

            return llm_answer, source_documents, confidence_score, num_retrieved_chunks

        except Exception as e:
            logger.error(f"Error during RAG query: {e}", exc_info=True)
            return (
                f"An error occurred while processing your query: {str(e)}",
                source_documents,
                1,
                num_retrieved_chunks,
            )

    async def _get_confidence_score(self, query: str, context: str, answer: str) -> int:
        """Generates a confidence score for the RAG answer."""
        if (
            not answer
            or "I was unable to find a relevant answer" in answer
            or "No relevant documents found" in answer
            or "Failed to get answer" in answer
        ):
            return 1

        if (
            not context
            or "No relevant documents found" in context
            or "No context was generated" in context
        ):
            if (
                "I don't know" in answer.lower()
                or "unable to determine" in answer.lower()
            ):
                return 1
            return 2

        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a confidence scoring AI. Evaluate the provided query, context, and answer. "
                    "Rate the answer's confidence on a scale of 1 to 5, where 1 is very low (likely incorrect or irrelevant) "
                    "and 5 is very high (correct and well-supported by the context). "
                    "Consider if the answer directly addresses the query and is well-supported by the provided context. "
                    "A short, direct answer can be highly confident if accurate. "
                    "An answer that states information is not in the context should be rated based on whether that assessment is correct.",
                ),
                (
                    "human",
                    "Query: {query}\n\nContext: {context}\n\nAnswer: {answer}\n\nConfidence Score (1-5):",
                ),
            ]
        )

        confidence_chain = prompt_template | self.llm_client | StrOutputParser()

        try:
            response_str = await confidence_chain.ainvoke(
                {"query": query, "context": context, "answer": answer}
            )
            match = re.search(r"\d", response_str)
            if match:
                score = int(match.group(0))
                return max(1, min(5, score))
            else:
                logger.warning(
                    f"Could not extract a numeric confidence score from LLM response: '{response_str}'"
                )
                return 3
        except Exception as e:
            logger.error(f"Error getting confidence score: {e}", exc_info=True)
            return 3

    async def query_collection(
        self, collection_name: str, query: str
    ) -> Tuple[str, List[SourceDocument], Optional[int], int]:
        logger.info(
            f"Querying collection '{collection_name}' directly for query: '{query}'"
        )
        num_retrieved_chunks = 0
        source_documents: List[SourceDocument] = []
        try:
            target_collection = self.chroma_client.get_collection(
                name=collection_name, embedding_function=self.embedding_function
            )
            if target_collection.count() == 0:  # type: ignore
                return f"Collection '{collection_name}' is empty.", [], 3, 0

            results = target_collection.query(
                query_texts=[query],
                n_results=self.settings.RAG_NUM_SOURCES,
                include=["documents", "metadatas", "distances"],
            )
            num_retrieved_chunks = len(results.get("ids", [[]])[0])

            if results and results.get("documents") and results.get("metadatas"):
                docs = results["documents"][0]
                metadatas = results["metadatas"][0]
                for i, doc_content in enumerate(docs):
                    metadata = metadatas[i]
                    source_documents.append(
                        SourceDocument(
                            document_id=metadata.get("document_id", "unknown"),
                            chunk_id=metadata.get("chunk_id", f"chunk_{i}"),
                            file_name=metadata.get("file_name", "unknown_file"),
                            chunk_content=doc_content,
                            score=(
                                results["distances"][0][i]
                                if results.get("distances")
                                else None
                            ),
                        )
                    )

            if source_documents:
                pipeline_input = {"query": query, "documents": source_documents}
                pipeline_result = await self.rag_pipeline.ainvoke(pipeline_input)
                llm_answer = pipeline_result.get(
                    "answer", "Failed to get answer from pipeline."
                )
                return llm_answer, source_documents, 3, num_retrieved_chunks
            else:
                return "No relevant documents found in the collection.", [], 3, 0

        except Exception as e:
            logger.error(
                f"Error querying collection '{collection_name}': {e}", exc_info=True
            )
            return f"Error querying collection '{collection_name}': {str(e)}", [], 1, 0

    async def reset_collection(self, collection_name: str = None) -> dict:
        """Resets (deletes and recreates) a ChromaDB collection."""
        target_collection_name = collection_name or self.settings.CHROMA_COLLECTION_NAME
        logger.info(f"Resetting collection: {target_collection_name}")
        try:
            self.chroma_client.delete_collection(name=target_collection_name)
            logger.info(f"Collection '{target_collection_name}' deleted.")
        except Exception as e:
            logger.warning(
                f"Could not delete collection '{target_collection_name}' (it might not exist): {e}"
            )

        try:
            # Re-assign to self.collection only if it's the main collection being reset
            recreated_collection = self.chroma_client.get_or_create_collection(
                name=target_collection_name, embedding_function=self.embedding_function
            )
            if target_collection_name == self.settings.CHROMA_COLLECTION_NAME:
                self.collection = recreated_collection
            logger.info(
                f"Collection '{target_collection_name}' (re)created and assigned."
            )
            return {
                "status": "success",
                "message": f"Collection '{target_collection_name}' reset.",
            }
        except Exception as e:
            logger.error(
                f"Failed to recreate collection '{target_collection_name}': {e}",
                exc_info=True,
            )
            return {
                "status": "error",
                "message": f"Failed to recreate collection '{target_collection_name}'.",
            }


def get_rag_service() -> RAGService:
    return RAGService()
