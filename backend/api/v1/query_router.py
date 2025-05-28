from fastapi import APIRouter
import logging

# from backend.models import RAGQueryRequest, RAGQueryResponse # Original import
# from backend.services.rag_service import RAGService, get_rag_service # Original import

logger = logging.getLogger(__name__)
router = APIRouter()  # Define an empty router

"""
IMPORTANT: RAG Query functionality has been moved to LangServe

The direct REST API endpoints that were previously defined in this file have been migrated
to the LangServe application (backend/services/langserve_app/app.py).

LangServe provides a more flexible and traceable interface for querying the RAG system.
Please use the LangServe endpoints instead of these direct APIs:

- For RAG queries: /api/langserve/rag_query_runnable/invoke
- For collection-specific queries: /api/langserve/rag_collection_query_runnable/invoke

The original endpoint definitions are kept below as comments for reference:

# @router.post(
#     "/ask",
#     response_model=RAGQueryResponse,
#     summary="Ask a question to the RAG system",
#     tags=["Query"],
# )
# async def rag_ask_endpoint(
#     request: RAGQueryRequest, rag_service: RAGService = Depends(get_rag_service)
# ) -> RAGQueryResponse:
#     ...
"""

# Keep router instance for now, might be imported elsewhere, will be cleaned by ruff if unused.
