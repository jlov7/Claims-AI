from fastapi import APIRouter, HTTPException, Body
import logging

from backend.models import SummariseRequest, SummariseResponse
from backend.services.summarisation_service import (
    get_summarisation_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/summarise",
    response_model=SummariseResponse,
    summary="Summarise a document by ID or content",
    tags=["Summarisation"],
)
async def summarise_endpoint(raw_body: dict = Body(...)):
    """
    Accepts either a `document_id` (referring to a processed file name, e.g., `my_doc.pdf.json`)
    or direct `content` string.

    - If `document_id` is provided, the service attempts to read the content from
      `data/processed_text/{document_id}`.
    - If `content` is provided, that text is used directly.

    Generates a summary of the document content using the Phi-4 model.
    Returns the summary, and if applicable, the original document ID and a preview of the content.
    """
    payload_data = (
        raw_body.get("summarise_request")
        if isinstance(raw_body.get("summarise_request"), dict)
        else raw_body
    )
    try:
        summarise_request = SummariseRequest(**payload_data)
    except ValueError as e:
        logger.error(f"Validation error in summarise_request: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(
        f"Received request for /summarise. Doc ID: {summarise_request.document_id}, Content provided: {bool(summarise_request.content)}"
    )

    # Fetch the summarisation service at runtime to allow overrides
    summarisation_service = get_summarisation_service()

    original_content_preview = None
    text_to_summarise = ""

    try:
        if summarise_request.content:
            text_to_summarise = summarise_request.content
            original_content_preview = (
                (text_to_summarise[:200] + "...")
                if len(text_to_summarise) > 200
                else text_to_summarise
            )
            logger.info(
                f"Summarising direct content. Preview: {original_content_preview}"
            )
        elif summarise_request.document_id:
            # Log the document_id to help with debugging
            logger.info(
                f"Attempting to retrieve content for document_id: '{summarise_request.document_id}'"
            )

            try:
                # _get_content_from_id will raise HTTPException on failure
                text_to_summarise = summarisation_service._get_content_from_id(
                    summarise_request.document_id
                )
                original_content_preview = (
                    (text_to_summarise[:200] + "...")
                    if len(text_to_summarise) > 200
                    else text_to_summarise
                )
                logger.info(
                    f"Successfully retrieved content for document_id: {summarise_request.document_id}. Preview: {original_content_preview[:50]}..."
                )
            except HTTPException as doc_exc:
                # Re-raise with more context
                logger.error(f"Error retrieving document content: {doc_exc.detail}")
                raise HTTPException(
                    status_code=doc_exc.status_code,
                    detail=f"Error retrieving document content: {doc_exc.detail}",
                )
        else:
            # As a safeguard, though model validator ensures one is present
            logger.error("Neither document_id nor content provided in request")
            raise HTTPException(
                status_code=400,
                detail="Request must include 'document_id' or 'content'.",
            )

        if not text_to_summarise or not text_to_summarise.strip():
            logger.error("Content to summarise is empty or whitespace")
            raise HTTPException(
                status_code=400, detail="Content to summarise is empty or whitespace."
            )

        try:
            summary = summarisation_service.summarise_text(
                text_to_summarise, summarise_request.document_id
            )

            logger.info(f"Successfully generated summary of length {len(summary)}")

            return SummariseResponse(
                summary=summary,
                original_document_id=summarise_request.document_id,
                original_content_preview=original_content_preview,
            )
        except HTTPException as summary_exc:
            # Re-raise with more context
            logger.error(f"Error generating summary: {summary_exc.detail}")
            raise HTTPException(
                status_code=summary_exc.status_code,
                detail=f"Error generating summary: {summary_exc.detail}",
            )

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (e.g., from _get_content_from_id or validator)
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in /summarise endpoint: {e}", exc_info=True)
        # Provide a more detailed error message
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
