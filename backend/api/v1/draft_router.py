from fastapi import APIRouter
import logging

# from backend.models import DraftStrategyNoteRequest # Original import
# from backend.services.drafting_service import DraftingService, get_drafting_service # Original import

logger = logging.getLogger(__name__)
router = APIRouter()  # Define an empty router

"""
IMPORTANT: Drafting functionality has been moved to LangServe

The direct REST API endpoints that were previously defined in this file have been migrated
to the LangServe application (backend/services/langserve_app/app.py).

LangServe provides a more flexible and traceable interface for drafting strategy notes.
Please use the LangServe endpoints instead of these direct APIs:

- For strategy note drafting: /api/langserve/draft_strategy_note_runnable/invoke

The original endpoint definitions are kept below as comments for reference:

# @router.post(
#     "/draft",
#     summary="Draft a Claim Strategy Note as a DOCX file",
#     tags=["Drafting"],
#     response_description="A DOCX file containing the drafted Claim Strategy Note.",
# )
# async def draft_strategy_note_endpoint(
#     request: DraftStrategyNoteRequest = Body(...),
#     drafting_service: DraftingService = Depends(get_drafting_service),
# ):
#     ...
"""
