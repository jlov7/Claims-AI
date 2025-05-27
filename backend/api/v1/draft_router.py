from fastapi import APIRouter
import logging

# from backend.models import DraftStrategyNoteRequest # Original import
# from backend.services.drafting_service import DraftingService, get_drafting_service # Original import

logger = logging.getLogger(__name__)
router = APIRouter()  # Define an empty router

"""
# All @router.post definitions from the original file should be commented out here.
# For example:
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
