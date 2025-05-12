from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import FileResponse
import logging
import os

from backend.models import DraftStrategyNoteRequest
from backend.services.drafting_service import DraftingService, get_drafting_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/draft",
    # No response_model if returning FileResponse directly,
    # but good to document what kind of file and typical headers.
    summary="Draft a Claim Strategy Note as a DOCX file",
    tags=["Drafting"],
    response_description="A DOCX file containing the drafted Claim Strategy Note.",
)
async def draft_strategy_note_endpoint(
    request: DraftStrategyNoteRequest = Body(...),
    drafting_service: DraftingService = Depends(get_drafting_service),
):
    """
    Accepts various context inputs (claim summary, document IDs, Q&A history, criteria)
    and a desired output filename for the DOCX.

    1.  Builds a comprehensive context string from the provided inputs.
    2.  Uses Phi-4 LLM to generate the text content of a claim strategy note.
    3.  Formats the generated text into a DOCX document using `python-docx`.
    4.  Saves the DOCX to a server-side location (`data/outputs/strategy_notes/`).
    5.  Returns the generated DOCX file as a downloadable attachment.
    """
    try:
        # Log the received output_filename for easier debugging if needed
        logger.info(
            f"Received request for /draft. Output filename suggestion: {request.output_filename}"
        )

        context = drafting_service._build_llm_context(request)
        if not context:  # Should be caught by Pydantic, but double-check
            raise HTTPException(
                status_code=400,
                detail="Insufficient context for drafting. Please provide relevant information.",
            )

        note_text_content = drafting_service.generate_strategy_note_text(context)
        if not note_text_content:
            # This case should ideally be handled within generate_strategy_note_text by raising an error
            logger.error("LLM generated empty content for strategy note.")
            raise HTTPException(status_code=500, detail="LLM generated empty content.")

        # Call create_docx_from_text with keyword arguments
        docx_file_path = drafting_service.create_docx_from_text(
            text=note_text_content, filename_suggestion=request.output_filename
        )

        if not os.path.exists(docx_file_path):
            logger.error(
                f"Drafted DOCX file not found at expected path: {docx_file_path}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to save or locate the drafted DOCX file.",
            )

        logger.info(
            f"Successfully drafted strategy note. Path: {docx_file_path}, Filename: {request.output_filename}"
        )
        return FileResponse(
            path=str(docx_file_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=docx_file_path.name,  # Use the actual name of the created file for download
        )
    except ValueError as ve:  # Catch specific ValueErrors, e.g. from _build_llm_context
        logger.warning(f"ValueError in /draft endpoint: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (e.g., from LLM call or DOCX creation/saving)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in /draft endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while drafting the strategy note: {str(e)}",
        )
