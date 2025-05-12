import logging
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions  # For OpenAIEmbeddingFunction

from backend.core.config import Settings, get_settings
from backend.models import PrecedentResultItem

logger = logging.getLogger(__name__)


class PrecedentService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PrecedentService, cls).__new__(cls)
        return cls._instance

    def __init__(self, settings_instance: Optional[Settings] = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        logger.info("Initializing PrecedentService...")
        if settings_instance:
            self.settings = settings_instance
        else:
            # This path might be taken if directly instantiated outside FastAPI's DI
            logger.warning(
                "PrecedentService initialized without explicit settings. Loading globally."
            )
            self.settings = get_settings()  # Relies on global settings

        try:
            self.chroma_client = chromadb.HttpClient(
                host=self.settings.CHROMA_HOST, port=self.settings.CHROMA_PORT
            )
            self.chroma_client.heartbeat()
            logger.info(
                f"PrecedentService connected to ChromaDB at {self.settings.CHROMA_HOST}:{self.settings.CHROMA_PORT}"
            )
        except Exception as e:
            logger.error(
                f"PrecedentService failed to connect to ChromaDB: {e}", exc_info=True
            )
            # Allow service to initialize but it won't be functional for Chroma operations
            self.chroma_client = None

        # Initialize embedding function (ensure API base ends with /v1)
        phi4_api_base = self.settings.PHI4_API_BASE
        if not phi4_api_base.endswith("/v1"):
            phi4_api_base = phi4_api_base.rstrip("/") + "/v1"

        try:
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_base=phi4_api_base,
                model_name=self.settings.EMBEDDING_MODEL_NAME,
                api_key="sk-dummykey",  # Dummy key for local LM Studio
            )
            logger.info(
                f"PrecedentService initialized OpenAIEmbeddingFunction with API base: {phi4_api_base} and model: {self.settings.EMBEDDING_MODEL_NAME}"
            )
        except Exception as e:
            logger.error(
                f"PrecedentService failed to initialize embedding function: {e}",
                exc_info=True,
            )
            self.embedding_function = None

        self.precedents_collection_name = (
            self.settings.CHROMA_PRECEDENTS_COLLECTION_NAME
        )
        self._initialized = True

    def _get_precedents_collection(self):
        if not self.chroma_client:
            logger.error("ChromaDB client not available in PrecedentService.")
            raise ConnectionError("ChromaDB client not available.")
        if not self.embedding_function:
            logger.error("Embedding function not available in PrecedentService.")
            raise ValueError("Embedding function not initialized.")
        try:
            collection = self.chroma_client.get_collection(
                name=self.precedents_collection_name,
                embedding_function=self.embedding_function,  # Pass EF here if needed by get_collection
            )
            logger.info(
                f"Successfully retrieved precedent collection: {self.precedents_collection_name}"
            )
            return collection
        except (
            Exception
        ) as e:  # Broad exception for now, ChromaDB can raise various things here
            # Fallback to get_or_create if simple get fails (e.g. if collection exists but EF not set initially)
            logger.warning(
                f"Could not get collection '{self.precedents_collection_name}' directly, trying get_or_create. Error: {e}"
            )
            try:
                collection = self.chroma_client.get_or_create_collection(
                    name=self.precedents_collection_name,
                    embedding_function=self.embedding_function,
                )
                logger.info(
                    f"Successfully got or created precedent collection: {self.precedents_collection_name}"
                )
                return collection
            except Exception as e_create:
                logger.error(
                    f"Failed to get or create precedent collection '{self.precedents_collection_name}': {e_create}",
                    exc_info=True,
                )
                raise ConnectionError(
                    f"Could not access precedent collection '{self.precedents_collection_name}'."
                )

    def find_precedents(
        self, claim_summary: str, top_k: int
    ) -> List[PrecedentResultItem]:
        """
        Finds top_k nearest precedents for a given claim summary.
        """
        logger.info(
            f"PrecedentService received find_precedents call with summary: '{claim_summary[:100]}...', top_k: {top_k}"
        )

        if not self.chroma_client or not self.embedding_function:
            logger.error(
                "PrecedentService not properly initialized (Chroma client or embedding function missing)."
            )
            return []

        try:
            query_embedding = self.embedding_function([claim_summary])[0]
        except Exception as e:
            logger.error(
                f"Failed to generate embedding for query summary: {e}", exc_info=True
            )
            return []  # Or raise an exception that can be caught by the API layer

        try:
            collection = self._get_precedents_collection()
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=[
                    "metadatas",
                    "documents",
                    "distances",
                ],  # documents = original summaries
            )
        except Exception as e:
            logger.error(
                f"Failed to query precedent collection '{self.precedents_collection_name}': {e}",
                exc_info=True,
            )
            return []  # Or raise

        retrieved_precedents: List[PrecedentResultItem] = []
        if results and results.get("ids") and results.get("ids")[0]:
            for i in range(len(results["ids"][0])):
                meta = (
                    results["metadatas"][0][i]
                    if results["metadatas"] and results["metadatas"][0]
                    else {}
                )
                # The 'document' from Chroma query is the original summary we embedded
                doc_summary = (
                    results["documents"][0][i]
                    if results["documents"] and results["documents"][0]
                    else meta.get("original_summary", "Summary not found")
                )
                distance = (
                    results["distances"][0][i]
                    if results["distances"] and results["distances"][0]
                    else None
                )

                item = PrecedentResultItem(
                    claim_id=meta.get(
                        "claim_id", results["ids"][0][i]
                    ),  # Fallback to Chroma ID if claim_id not in meta
                    summary=doc_summary,
                    outcome=meta.get("outcome"),
                    keywords=meta.get("keywords"),
                    distance=distance,
                )
                retrieved_precedents.append(item)
            logger.info(
                f"Retrieved {len(retrieved_precedents)} precedents from ChromaDB."
            )
        else:
            logger.info("No precedents found for the given query summary.")

        return retrieved_precedents


# Singleton factory
_precedent_service_instance = None


def get_precedent_service(
    settings_instance: Optional[Settings] = None,
) -> PrecedentService:
    global _precedent_service_instance
    if _precedent_service_instance is None:
        if settings_instance:
            _precedent_service_instance = PrecedentService(
                settings_instance=settings_instance
            )
        else:
            _precedent_service_instance = PrecedentService(
                settings_instance=get_settings()
            )
    return _precedent_service_instance
