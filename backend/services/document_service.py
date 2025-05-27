import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List
from fastapi import UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from models import UploadResponseItem, BatchUploadResponse
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from core.config import get_settings, Settings
from .minio_service import MinioService, get_minio_service

logger = logging.getLogger(__name__)

# Define base path for the application, assuming this service is in backend/services
# Adjust if your project structure is different or if running in Docker with different workdir
APP_BASE_DIR = (
    Path(__file__).resolve().parent.parent
)  # Should point to /app, which is the WORKDIR
RAW_UPLOAD_DIR = APP_BASE_DIR / "data" / "temp_raw_uploads"
PROCESSED_TEXT_DIR = APP_BASE_DIR / "data" / "processed_text"
OCR_SCRIPT_PATH = APP_BASE_DIR / "scripts" / "extract_text.py"


class DocumentService:
    def __init__(self):
        RAW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    async def reingest_all_documents(
        self, collection_name: str = None, skip_test_docs: bool = True
    ):
        """
        Re-ingest all processed text documents into the ChromaDB collection.
        This is useful if ChromaDB was reset or documents are missing from the collection.

        Args:
            collection_name: Optional name of the ChromaDB collection to use.
                            If not provided, uses the default from settings.
            skip_test_docs: If True, will skip test documents that don't represent real insurance data.

        Returns:
            dict: Summary of the operation with counts of success and failures.
        """
        logger.info("Starting re-ingestion of all processed documents into ChromaDB")

        try:
            from services.document_loader import get_document_loader_service
            from services.rag_service import get_rag_service
            from core.config import get_settings

            settings = get_settings()
            loader = get_document_loader_service()
            rag_service = get_rag_service()

            # Check if RAG service is properly initialized
            if not hasattr(rag_service, "collection") or rag_service.collection is None:
                error_msg = "RAG service collection is not initialized"
                logger.error(error_msg)
                return {"status": "failed", "error": error_msg}

            # Use the specified collection or default to the one in RAG service
            if collection_name:
                try:
                    # Get or create the specified collection
                    collection = rag_service.chroma_client.get_or_create_collection(
                        name=collection_name,
                        embedding_function=rag_service.embedding_function,
                    )
                    logger.info(
                        f"Using specified ChromaDB collection: {collection_name}"
                    )
                except Exception as e:
                    error_msg = f"Failed to access specified collection '{collection_name}': {str(e)}"
                    logger.error(error_msg)
                    return {"status": "failed", "error": error_msg}
            else:
                collection = rag_service.collection
                collection_name = getattr(collection, "name", "unknown")
                logger.info(f"Using default ChromaDB collection: {collection_name}")

            # Get all files in the processed text directory
            processed_files = list(PROCESSED_TEXT_DIR.glob("*.json"))
            logger.info(
                f"Found {len(processed_files)} files in processed text directory"
            )

            # Prioritize user-uploaded documents
            uploads_dir = (
                RAW_UPLOAD_DIR.parent
            )  # Get the parent directory of temp_raw_uploads
            user_uploaded_docs = []

            # Look for user uploaded documents first
            for file_path in processed_files:
                # Check if there's a corresponding file in the raw uploads directory
                original_name = file_path.stem
                # If it's a recently uploaded document, prioritize it
                if (
                    uploads_dir / original_name
                ).exists() or "upload" in original_name.lower():
                    user_uploaded_docs.append(file_path)
                    logger.info(f"Found user-uploaded document: {file_path.name}")

            # Filter out test documents if requested
            if skip_test_docs:
                # Define patterns for test documents to skip
                test_patterns = [
                    "draft_test_doc",
                    "sample",
                    "summarisation_test",
                    "test_",
                    "example_",
                    "dummy_",
                    "mock_",
                    "lorem",
                    "ipsum",
                ]

                # Filter the non-user-uploaded documents
                other_docs = [
                    f
                    for f in processed_files
                    if f not in user_uploaded_docs
                    and not any(pattern in f.name.lower() for pattern in test_patterns)
                ]

                logger.info(
                    f"Identified {len(user_uploaded_docs)} user-uploaded documents and {len(other_docs)} other valid documents"
                )

                # Combine the lists, with user uploads first
                processed_files = user_uploaded_docs + other_docs

                logger.info(f"Total documents to ingest: {len(processed_files)}")

            # Statistics
            success_count = 0
            failure_count = 0
            skipped_count = 0
            ingested_docs = []

            # Process each file
            for file_path in processed_files:
                doc_id = file_path.name
                logger.info(f"Processing document: {doc_id}")

                try:
                    content = loader.load_document_content_by_id(doc_id)
                    if not content:
                        logger.warning(
                            f"No content extracted for document {doc_id}, skipping"
                        )
                        skipped_count += 1
                        continue

                    # Split content into chunks
                    chunks = content.split("\n---\n")
                    chunk_count = 0

                    # Add each chunk to ChromaDB
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue

                        chunk_id = f"{doc_id}_chunk_{i}"

                        try:
                            # Check if this chunk already exists by ID
                            existing = collection.get(ids=[chunk_id])
                            if (
                                existing
                                and existing.get("ids")
                                and len(existing["ids"]) > 0
                            ):
                                logger.info(
                                    f"Chunk {chunk_id} already exists in collection {collection_name}, skipping"
                                )
                                continue

                            # Add the chunk to ChromaDB with improved metadata
                            collection.add(
                                documents=[chunk],
                                metadatas=[
                                    {
                                        "document_id": doc_id,
                                        "chunk_id": chunk_id,
                                        "filename": doc_id,
                                        "is_user_uploaded": file_path
                                        in user_uploaded_docs,
                                    }
                                ],
                                ids=[chunk_id],
                            )
                            chunk_count += 1
                            logger.info(
                                f"Successfully added chunk {i+1}/{len(chunks)} for document {doc_id} to collection {collection_name}"
                            )
                        except Exception as chunk_error:
                            logger.error(
                                f"Failed to add chunk {i+1}/{len(chunks)} for document {doc_id} to collection {collection_name}: {chunk_error}"
                            )

                    if chunk_count > 0:
                        success_count += 1
                        ingested_docs.append(doc_id)
                    else:
                        logger.warning(
                            f"No chunks were added for document {doc_id} to collection {collection_name}"
                        )
                        skipped_count += 1

                except Exception as e:
                    logger.error(
                        f"Error processing document {doc_id}: {e}", exc_info=True
                    )
                    failure_count += 1

            logger.info(
                f"Re-ingestion to collection {collection_name} complete. Success: {success_count}, Failed: {failure_count}, Skipped: {skipped_count}"
            )
            return {
                "status": "completed",
                "collection_name": collection_name,
                "total_documents": len(processed_files),
                "successful": success_count,
                "failed": failure_count,
                "skipped": skipped_count,
                "ingested_documents": ingested_docs,
                "user_uploaded_count": len(user_uploaded_docs),
            }

        except Exception as e:
            error_msg = f"Failed to re-ingest documents: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "failed", "error": error_msg}

    async def save_and_process_documents(
        self, files: List[UploadFile]
    ) -> BatchUploadResponse:
        results: List[UploadResponseItem] = []
        batch_overall_status = "Completed"
        uploaded_count = 0
        ingested_count = 0

        temp_batch_dir = RAW_UPLOAD_DIR / str(uuid.uuid4())
        temp_batch_dir.mkdir(parents=True, exist_ok=True)

        saved_file_paths: List[Path] = []

        for file in files:
            file_id = str(uuid.uuid4())
            # Corrected sanitization line
            sanitized_filename = "".join(
                c if c.isalnum() or c in (".", "-", "_") else "_" for c in file.filename
            )
            if not sanitized_filename:
                sanitized_filename = f"{file_id}_upload"

            # Create document_id that will be consistent and returned to frontend
            document_id = sanitized_filename
            file_location = temp_batch_dir / sanitized_filename

            try:
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
                saved_file_paths.append(file_location)
                results.append(
                    UploadResponseItem(
                        filename=file.filename,
                        message="Successfully saved. Awaiting processing.",
                        success=True,
                        document_id=document_id,  # Always set document_id
                    )
                )
                uploaded_count += 1
            except Exception as e:
                logger.error(f"Error saving file {file.filename}: {e}")
                results.append(
                    UploadResponseItem(
                        filename=file.filename,
                        message=f"Failed to save file: {str(e)}",
                        success=False,
                        error_details=str(e),
                    )
                )
                batch_overall_status = "Completed with errors"
            finally:
                if hasattr(file, "file") and file.file:
                    file.file.close()

        if not saved_file_paths:
            if not results:
                return BatchUploadResponse(
                    overall_status="Failed",
                    results=[
                        UploadResponseItem(
                            filename="N/A",
                            message="No files were processed.",
                            success=False,
                        )
                    ],
                    uploaded=0,
                    ingested=0,
                    errors=["No files were processed"],
                )
            return BatchUploadResponse(
                overall_status=batch_overall_status,
                results=results,
                uploaded=uploaded_count,
                ingested=ingested_count,
                errors=["Some files failed to save"],
            )

        try:
            logger.info(f"Running OCR script for files in: {temp_batch_dir}")
            python_executable = (
                shutil.which("python")
                or shutil.which("python3")
                or "/usr/local/bin/python"
            )

            if not OCR_SCRIPT_PATH.is_file():
                logger.error(f"OCR script not found at {OCR_SCRIPT_PATH}")
                raise FileNotFoundError(f"OCR script not found at {OCR_SCRIPT_PATH}")

            process = subprocess.run(
                [
                    python_executable,
                    str(OCR_SCRIPT_PATH),
                    "--src",
                    str(temp_batch_dir),
                    "--out",
                    str(PROCESSED_TEXT_DIR),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=APP_BASE_DIR,
            )

            logger.info(f"OCR Script STDOUT: {process.stdout}")
            if process.stderr:
                logger.error(f"OCR Script STDERR: {process.stderr}")

            if process.returncode != 0:
                logger.error(
                    f"OCR script failed with return code {process.returncode}."
                )
                for i, item in enumerate(results):
                    # Check if the item corresponds to a file that was attempted in this batch
                    is_part_of_batch = any(
                        saved_file.name == item.filename
                        or (
                            len(item.filename) > 30
                            and saved_file.name.startswith(item.filename[:30])
                        )
                        for saved_file in saved_file_paths
                    )
                    if is_part_of_batch and results[i].success:
                        results[i].success = False
                        results[i].message = "File saved, but processing failed."
                        results[i].error_details = (
                            f"OCR script error: {process.stderr[:200] if process.stderr else 'Unknown processing error'}"
                        )
                batch_overall_status = "Completed with errors"
            else:
                logger.info("OCR script completed successfully.")
                # Ingest each processed document into the RAG vector store
                try:
                    from services.document_loader import (
                        get_document_loader_service,
                    )
                    from services.rag_service import get_rag_service

                    loader = get_document_loader_service()
                    rag_service = get_rag_service()
                    for saved_path in saved_file_paths:
                        doc_id = saved_path.name  # filename used as document ID
                        content = loader.load_document_content_by_id(doc_id)
                        if content:
                            # Fix: Check if collection is initialized
                            if (
                                not hasattr(rag_service, "collection")
                                or rag_service.collection is None
                            ):
                                logger.error("RAG service collection not initialized")
                                continue

                            # Get collection name for logging
                            collection_name = getattr(
                                rag_service.collection, "name", "unknown"
                            )
                            logger.info(
                                f"Adding document {doc_id} to ChromaDB collection: {collection_name}"
                            )

                            # Split content into chunks for better retrieval
                            chunks = content.split("\n---\n")

                            # Add each chunk with metadata
                            for i, chunk in enumerate(chunks):
                                if not chunk.strip():
                                    continue

                                chunk_id = f"{doc_id}_chunk_{i}"

                                try:
                                    rag_service.collection.add(
                                        documents=[chunk],
                                        metadatas=[
                                            {
                                                "document_id": doc_id,
                                                "chunk_id": chunk_id,
                                                "filename": doc_id,
                                            }
                                        ],
                                        ids=[chunk_id],
                                    )
                                    logger.info(
                                        f"Successfully added chunk {i+1}/{len(chunks)} for document {doc_id}"
                                    )
                                except Exception as chunk_error:
                                    logger.error(
                                        f"Failed to add chunk {i+1}/{len(chunks)} for document {doc_id}: {chunk_error}"
                                    )

                            ingested_count += 1  # Increment ingested count for each successful ingestion
                except Exception as e:
                    logger.error(
                        f"Failed to ingest documents into RAG store: {e}", exc_info=True
                    )

                for i, item in enumerate(results):
                    is_part_of_batch = any(
                        saved_file.name == item.filename
                        or (
                            len(item.filename) > 30
                            and saved_file.name.startswith(item.filename[:30])
                        )
                        for saved_file in saved_file_paths
                    )
                    if is_part_of_batch and results[i].success:
                        results[i].message = "File processed successfully."
                        results[i].ingested = True  # Mark as ingested
                        # Ensure document_id is set (in case it wasn't already)
                        if not results[i].document_id:
                            # Find the corresponding saved file
                            for saved_file in saved_file_paths:
                                if saved_file.name == item.filename or (
                                    len(item.filename) > 30
                                    and saved_file.name.startswith(item.filename[:30])
                                ):
                                    results[i].document_id = saved_file.name
                                    break

        except FileNotFoundError as fnf_error:
            logger.error(f"FileNotFoundError during OCR processing: {fnf_error}")
            batch_overall_status = "Failed"
            for i in range(len(results)):
                if results[i].success:
                    results[i].success = False
                    results[i].message = (
                        "File saved, but processing could not be initiated."
                    )
                    results[i].error_details = str(fnf_error)

        except Exception as e:
            logger.error(f"Error during OCR processing: {e}", exc_info=True)
            batch_overall_status = "Failed"
            for i in range(len(results)):
                if results[i].success:
                    results[i].success = False
                    results[i].message = (
                        "File saved, but processing failed unexpectedly."
                    )
                    results[i].error_details = f"Processing error: {str(e)[:200]}"

        finally:
            if temp_batch_dir.exists():
                try:
                    shutil.rmtree(temp_batch_dir)
                    logger.info(
                        f"Successfully cleaned up temporary batch directory: {temp_batch_dir}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error cleaning up temporary batch directory {temp_batch_dir}: {e}"
                    )

        if (
            not results
        ):  # Should have been caught by "if not saved_file_paths" earlier, but as a safeguard
            return BatchUploadResponse(
                overall_status="Failed",
                results=[
                    UploadResponseItem(
                        filename="N/A",
                        message="No files were provided or processed.",
                        success=False,
                    )
                ],
            )

        if all(r.success for r in results):
            batch_overall_status = "Completed"
        elif any(r.success for r in results):
            batch_overall_status = "Completed with errors"
        else:  # All must have failed if we have results and none are True
            batch_overall_status = "Failed"

        return BatchUploadResponse(
            overall_status=batch_overall_status,
            results=results,
            uploaded=uploaded_count,
            ingested=ingested_count,
            errors=(
                ["Some files failed to process"]
                if batch_overall_status != "Completed"
                else []
            ),
        )


# document_service = DocumentService() # Removed direct instantiation

_document_service_instance = None

def get_document_service() -> DocumentService:
    """
    Factory function to get a singleton instance of DocumentService.
    """
    global _document_service_instance
    if _document_service_instance is None:
        _document_service_instance = DocumentService()
    return _document_service_instance
