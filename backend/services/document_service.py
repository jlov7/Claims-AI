import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List
from fastapi import UploadFile
from ..models import UploadResponseItem, BatchUploadResponse
import logging

logger = logging.getLogger(__name__)

# Define base path for the application, assuming this service is in backend/services
# Adjust if your project structure is different or if running in Docker with different workdir
APP_BASE_DIR = (
    Path(__file__).resolve().parent.parent.parent
)  # Should point to Claims-AI root
RAW_UPLOAD_DIR = APP_BASE_DIR / "data" / "temp_raw_uploads"
PROCESSED_TEXT_DIR = APP_BASE_DIR / "data" / "processed_text"
OCR_SCRIPT_PATH = APP_BASE_DIR / "scripts" / "extract_text.py"


class DocumentService:
    def __init__(self):
        RAW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_TEXT_DIR.mkdir(parents=True, exist_ok=True)

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
                        results[
                            i
                        ].error_details = f"OCR script error: {process.stderr[:200] if process.stderr else 'Unknown processing error'}"
                batch_overall_status = "Completed with errors"
            else:
                logger.info("OCR script completed successfully.")
                # Ingest each processed document into the RAG vector store
                try:
                    from backend.services.document_loader import (
                        get_document_loader_service,
                    )
                    from backend.services.rag_service import get_rag_service

                    loader = get_document_loader_service()
                    rag_service = get_rag_service()
                    for saved_path in saved_file_paths:
                        doc_id = saved_path.name  # filename used as document ID
                        content = loader.load_document_content_by_id(doc_id)
                        if content:
                            rag_service.collection.add(
                                documents=[content],
                                metadatas=[{"document_id": doc_id}],
                                ids=[doc_id],
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
                    results[
                        i
                    ].message = "File saved, but processing could not be initiated."
                    results[i].error_details = str(fnf_error)

        except Exception as e:
            logger.error(f"Error during OCR processing: {e}", exc_info=True)
            batch_overall_status = "Failed"
            for i in range(len(results)):
                if results[i].success:
                    results[i].success = False
                    results[
                        i
                    ].message = "File saved, but processing failed unexpectedly."
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

        if not results:  # Should have been caught by "if not saved_file_paths" earlier, but as a safeguard
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


document_service = DocumentService()
