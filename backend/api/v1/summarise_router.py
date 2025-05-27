from fastapi import APIRouter
import logging

# from backend.models import SummariseRequest, SummariseResponse # Original import
# from backend.services.summarisation_service import get_summarisation_service # Original import

logger = logging.getLogger(__name__)
router = APIRouter()  # Define an empty router

"""
# All @router.post definitions from the original file should be commented out here.
# For example:
# @router.post(
#     "/summarise",
#     response_model=SummariseResponse,
#     summary="Summarise a document by ID or content",
#     tags=["Summarisation"],
# )
# async def summarise_endpoint(raw_body: dict = Body(...)):
#     ...
"""
