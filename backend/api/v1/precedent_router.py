import logging

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List

from models import (
    PrecedentQueryRequest,
    PrecedentResponse,
    HealthCheckResponse,
)
from services.precedent_service import PrecedentService, get_precedent_service
from core.config import get_settings, Settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings_instance = get_settings() # Get settings at module level if needed globally


@router.post(
    "/precedents",
    response_model=PrecedentResponse,
    summary="Find the k nearest precedents",
    description="Accepts a claim summary and returns the top-k most similar precedents from the database.",
)
async def find_nearest_precedents(
    query_request: PrecedentQueryRequest = Body(..., embed=True),
    precedent_service: PrecedentService = Depends(get_precedent_service),
):
    """
    Finds the k nearest precedents to a given claim summary.
    The claim summary is embedded, and ChromaDB is queried for the most similar precedent embeddings.
    """
    try:
        results = precedent_service.find_precedents(
            claim_summary=query_request.claim_summary, top_k=query_request.top_k
        )
        return PrecedentResponse(precedents=results)
    except Exception as e:
        logger.exception(
            f"Error finding precedents for summary '{query_request.claim_summary[:50]}...': {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to find precedents.")


# Health check endpoint for the precedent service (optional, good for diagnostics)
@router.get(
    "/precedents/health",
    response_model=HealthCheckResponse,
    tags=["Precedents", "Health"],
)
async def precedent_service_health(settings: Settings = Depends(get_settings)):
    # Basic check: Can we connect to ChromaDB?
    # More sophisticated checks could be added here (e.g., collection exists, has items)
    # For now, relies on ChromaDB client initialization in PrecedentService
    try:
        # Attempt to create a service instance, which might try to connect to Chroma
        # This is a lightweight way to check if Chroma settings are present
        # A more direct check would be to use precedent_service.check_chroma_connection() if implemented
        # For now, we assume if settings are okay, service can be spun up.
        logger.info(
            f"Attempting health check for precedent service with Chroma host: {settings.CHROMA_HOST}"
        )
        # Note: We don't actually call a precedent_service method that hits Chroma here
        # to keep the health check light. The actual connection is tested on service use.
        # If CHROMA_HOST is not set, get_precedent_service would raise an error during its setup.
        # This check primarily ensures the route is responsive and config *could* be loaded.

        # To truly check Chroma, you'd inject PrecedentService and call a method:
        # precedent_service: PrecedentService = Depends(get_precedent_service)
        # await precedent_service.ping_chroma() # (A hypothetical method)

        return HealthCheckResponse(
            status="ok",
            detail="Precedent service is running. Chroma connectivity tested upon use.",
        )
    except Exception as e:
        logger.error(f"Precedent service health check failed: {e}", exc_info=True)
        return HealthCheckResponse(
            status="error", detail=f"Precedent service potential issue: {str(e)}"
        )


# Ensure this is the *only* definition for /precedents POST
# The old find_nearest_precedents_api should be removed if this new one is active.
