from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List
import os

# Corrected import paths assuming 'backend' is a recognizable top-level package or on PYTHONPATH
from services.document_service import (
    DocumentService,
    get_document_service,
    RAW_UPLOAD_DIR,
    PROCESSED_TEXT_DIR,
)
from models import BatchUploadResponse, UploadResponseItem
from core.config import get_settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    doc_service: DocumentService = Depends(get_document_service),
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


@router.get("/list")
async def list_documents():
    """
    List all processed documents available in the system.
    """
    try:
        # Path to the processed text directory
        processed_dir = PROCESSED_TEXT_DIR

        # Ensure the directory exists
        if not processed_dir.exists():
            logger.warning(
                f"Processed documents directory does not exist: {processed_dir}"
            )
            return {"documents": []}

        # Get a list of all files in the directory
        documents = []
        for file_path in processed_dir.glob("*.json"):
            # Get the original file name (without .json extension)
            original_name = file_path.stem

            # Add document info to the list
            documents.append(
                {
                    "id": file_path.name,  # Include the .json extension for the ID
                    "filename": original_name,
                    "path": str(file_path),
                    "size": os.path.getsize(file_path),
                    "ingested": True,  # Assume all documents in the processed directory are ingested
                }
            )

        # We removed the RAW_DOCS_PATH lookup since it's not defined in settings

        logger.info(f"Found {len(documents)} documents")
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.post("/reingest", status_code=status.HTTP_200_OK)
async def reingest_documents(
    collection_name: str = None,
    skip_test_docs: bool = True,
    reset_collection: bool = False,
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    Re-ingest all processed documents into the ChromaDB collection.
    This is useful if ChromaDB was reset or documents are missing from the collection.

    Args:
        collection_name: Optional name of the ChromaDB collection to use.
                        If not provided, uses the default from settings.
        skip_test_docs: If True, will skip test documents that don't represent real insurance data.
                       Default is True.
        reset_collection: If True, will reset the collection before reingesting documents.
                        Default is False.
    """
    try:
        logger.info(
            f"Starting re-ingestion of all documents into ChromaDB{' (collection: ' + collection_name + ')' if collection_name else ''}, skip_test_docs={skip_test_docs}, reset_collection={reset_collection}"
        )

        # If requested, reset the collection first
        if reset_collection:
            from services.rag_service import get_rag_service

            rag_service = get_rag_service()
            reset_result = await rag_service.reset_collection(collection_name)

            if reset_result.get("status") == "error":
                logger.error(
                    f"Failed to reset collection: {reset_result.get('message')}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reset collection: {reset_result.get('message')}",
                )
            logger.info(f"Successfully reset collection: {reset_result}")

        # Now proceed with re-ingestion
        result = await doc_service.reingest_all_documents(
            collection_name=collection_name, skip_test_docs=skip_test_docs
        )

        if result.get("status") == "failed":
            logger.error(f"Re-ingestion failed: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to re-ingest documents: {result.get('error')}",
            )

        logger.info(f"Re-ingestion completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error during re-ingestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-ingest documents: {str(e)}",
        )
