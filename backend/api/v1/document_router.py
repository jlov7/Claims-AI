from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List

# Corrected import paths assuming 'backend' is a recognizable top-level package or on PYTHONPATH
from backend.services.document_service import document_service, DocumentService
from backend.models import BatchUploadResponse, UploadResponseItem
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    doc_service: DocumentService = Depends(
        lambda: document_service
    ),  # Use service instance
):
    logger.info(
        f"Received {len(files)} files for upload and processing. First file: {files[0].filename if files else 'N/A'}"
    )
    """
    Receives one or more documents, saves them, triggers OCR processing,
    and returns a batch response with the status of each file.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided in the request.",
        )

    allowed_content_types = [
        "application/pdf",
        "image/tiff",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    for (
        file_upload
    ) in files:  # Renamed variable to avoid conflict with File from fastapi
        if file_upload.content_type not in allowed_content_types:
            logger.warning(
                f"Rejected file {file_upload.filename} with unsupported content type: {file_upload.content_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_upload.content_type} for {file_upload.filename} is not supported. Supported types: PDF, TIFF, DOCX.",
            )

    try:
        logger.info(f"Received {len(files)} files for upload and processing.")
        response = await doc_service.save_and_process_documents(files)
        return response
    except FileNotFoundError as fnf_error:
        logger.error(
            f"Processing error due to missing critical file: {fnf_error}", exc_info=True
        )
        # This specific error should ideally be caught by a global exception handler if it implies config issues
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"A critical server file (like the OCR script) is missing. Cannot process documents. Details: {str(fnf_error)}",
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during document upload processing: {e}",
            exc_info=True,
        )
        # Construct a BatchUploadResponse to inform client about the failure mode
        error_results = [
            UploadResponseItem(
                filename=f.filename,
                success=False,
                message="Unexpected server error during processing.",
                error_details=str(e),
            )
            for f in files
        ]
        # Note: FastAPI will return this with a 200 OK status unless an HTTPException is raised.
        # For a more RESTful approach, consider raising an HTTPException here or using a global exception handler
        # to convert such error responses to 500s.
        return BatchUploadResponse(overall_status="Failed", results=error_results)
