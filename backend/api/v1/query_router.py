from fastapi import APIRouter, HTTPException, Depends
import logging

from backend.models import RAGQueryRequest, RAGQueryResponse  # Removed AskRequest
from backend.services.rag_service import RAGService, get_rag_service

logger = logging.getLogger(__name__)
# settings object is now directly imported, no need to call get_settings()

router = APIRouter()


@router.post(
    "/ask",
    response_model=RAGQueryResponse,
    summary="Ask a question to the RAG system",
    tags=["Query"],
)  # Changed tag to Query from RAG
async def rag_ask_endpoint(
    request: RAGQueryRequest, rag_service: RAGService = Depends(get_rag_service)
) -> RAGQueryResponse:  # Changed request type to RAGQueryRequest
    """
    Receives a query, uses the RAGService to find relevant documents,
    generate an answer, and return the answer along with source documents and a confidence score.
    """
    logger.info(f"/ask endpoint called with query: '{request.query}'")
    if not request.query or not request.query.strip():
        logger.warning("Query is empty or whitespace.")
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        (
            answer,
            sources,
            confidence_score,
            self_heal_attempts,
        ) = await rag_service.query_rag(request.query)
        logger.info(
            f"Successfully processed query. Answer: '{answer[:50]}...', Sources: {len(sources)}, Confidence: {confidence_score}"
        )
        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            confidence_score=confidence_score,
            self_heal_attempts=self_heal_attempts,
        )
    except Exception as e:
        logger.error(
            f"Error in /ask endpoint for query '{request.query}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"An internal error occurred: {str(e)}"
        )
