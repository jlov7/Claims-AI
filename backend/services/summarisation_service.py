import logging
import os
import builtins  # For module-level open alias
import re  # Import re for regex operations
import json
import asyncio  # Added for asyncio.to_thread
from typing import Optional, Dict, Any

from fastapi import HTTPException

from core.config import Settings, get_settings
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, FilePath, validator

logger = logging.getLogger(__name__)

# Keep module-level open alias for tests if they rely on patching builtins.open
_sync_open = builtins.open


class SummarisationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_client = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
        )
        logger.info(
            f"SummarisationService initialized with ChatOllama client using model: {settings.OLLAMA_MODEL_NAME} at base_url: {settings.OLLAMA_BASE_URL}"
        )

    async def get_content_from_id(self, document_id: str) -> str:
        """Async: Get the document content by its ID."""
        if "/" in document_id or ".." in document_id:
            logger.error(f"Invalid document_id format: {document_id}")
            raise HTTPException(status_code=400, detail="Invalid document ID format.")

        base_id = document_id
        original_extension = ""
        for ext in [".pdf", ".docx", ".txt", ".tiff", ".tif"]:
            if base_id.lower().endswith(ext):
                original_extension = ext
                base_id = base_id[: -len(ext)]
                logger.info(
                    f"Stripped original extension {ext}, base_id now: {base_id}"
                )
                break

        paths_to_try = []
        docker_base_path = "/app/data/processed_text"
        paths_to_try.append(os.path.join(docker_base_path, f"{document_id}.json"))
        if original_extension:
            paths_to_try.append(os.path.join(docker_base_path, f"{base_id}.json"))
        if not document_id.endswith(".json"):
            paths_to_try.append(os.path.join(docker_base_path, f"{document_id}.json"))
        paths_to_try.append(os.path.join(docker_base_path, document_id))

        try:
            from pathlib import Path

            project_root = Path(__file__).resolve().parent.parent.parent
            local_base_path = project_root / "data" / "processed_text"
            paths_to_try.append(str(local_base_path / f"{document_id}.json"))
            if original_extension:
                paths_to_try.append(str(local_base_path / f"{base_id}.json"))
            if not document_id.endswith(".json"):
                paths_to_try.append(str(local_base_path / f"{document_id}.json"))
            paths_to_try.append(str(local_base_path / document_id))
            logger.info(f"Will try local development paths as well: {project_root}")
        except Exception as e:
            logger.warning(f"Could not construct local paths: {e}")

        logger.info(
            f"Will try to read document from the following paths: {paths_to_try}"
        )

        errors = []

        def _read_file_sync(file_path_sync):
            # This synchronous function will be run in a thread
            file_content_str: Optional[str] = None
            is_json = file_path_sync.lower().endswith(".json")

            with _sync_open(file_path_sync, "r", encoding="utf-8") as f_sync:
                logger.info(f"Successfully opened file: {file_path_sync}")
                if is_json:
                    try:
                        data = json.load(f_sync)
                        content_found_in_json = False
                        for key in [
                            "text",
                            "content",
                            "extracted_text",
                            "document_text",
                        ]:
                            if key in data and isinstance(data[key], str):
                                file_content_str = data[key]
                                logger.info(
                                    f"Found content under key: '{key}' in JSON file {file_path_sync}"
                                )
                                content_found_in_json = True
                                break
                        if not content_found_in_json:
                            error_detail = f"JSON file {file_path_sync} for document_id: {document_id} has no usable text content under expected keys."
                            logger.error(f"Critical: {error_detail}")
                            raise HTTPException(status_code=500, detail=error_detail)
                    except json.JSONDecodeError as jde_sync:
                        error_detail = f"File {file_path_sync} for document_id: {document_id} is not valid JSON."
                        logger.error(f"Critical: {error_detail} - {jde_sync}")
                        raise HTTPException(status_code=500, detail=error_detail)
                else:  # Assumed to be a plain text file if not .json
                    file_content_str = f_sync.read()
                    if not file_content_str:
                        error_detail = f"Plain text file {file_path_sync} for document_id: {document_id} is empty."
                        logger.error(f"Critical: {error_detail}")
                        raise HTTPException(status_code=500, detail=error_detail)
                    logger.info(
                        f"Successfully read plain text content from {file_path_sync} for document_id: {document_id}"
                    )

            if file_content_str is not None:
                return file_content_str
            else:
                # This case should ideally not be reached if logic above is correct
                error_detail = f"Failed to extract content from {file_path_sync} for document_id: {document_id} after processing."
                logger.error(f"Critical: {error_detail}")
                raise HTTPException(status_code=500, detail=error_detail)

        for file_path in paths_to_try:
            try:
                content_from_file = await asyncio.to_thread(_read_file_sync, file_path)
                return content_from_file  # Return as soon as content is found
            except FileNotFoundError:
                logger.info(f"File not found: {file_path}")
                errors.append(f"File not found: {file_path}")
            except (
                HTTPException
            ) as http_exc:  # Catch HTTPException raised from _read_file_sync
                raise http_exc  # Re-raise it to be caught by the caller
            except Exception as e:
                logger.warning(f"Unexpected error reading file {file_path}: {e}")
                errors.append(f"Unexpected error reading {file_path}: {str(e)}")

        error_msg = f"Could not read document by ID: {document_id}. Tried paths: {paths_to_try}. Errors: {errors}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=404,
            detail=f"Document content not found for ID: {document_id}. Searched paths: {paths_to_try}",
        )

    async def summarise_text(
        self, text_content: str, document_id: Optional[str] = None
    ) -> str:
        if not text_content.strip():
            logger.warning("Received empty text for summarisation.")
            raise HTTPException(status_code=400, detail="Cannot summarise empty text.")

        template = """You are an AI assistant that specializes in summarizing documents.

Write a concise professional summary (4‑8 bullet points).  
DO NOT include any sentence like "Here is the summary" – output ONLY the
bullet list.

Text to summarise:
{text_content}
"""
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm_client | StrOutputParser()

        try:
            logger.info(
                f"Requesting summary from LLM for document_id: {document_id if document_id else 'direct content'}. Content length: {len(text_content)}"
            )
            raw = await chain.ainvoke({"text_content": text_content})
            cleaned = re.sub(
                r"^(Summary:|Here(?: is|\'s) a summary:)\s*", "", raw, flags=re.I
            )
            if not cleaned.lstrip().startswith(("•", "-", "*")):
                cleaned = "• " + cleaned
            logger.info(
                f"Successfully generated summary for document_id: {document_id if document_id else 'direct content'}"
            )
            return cleaned
        except Exception as e:
            logger.error(
                f"Error during LLM call for summarisation (doc_id: {document_id if document_id else 'direct content'}): {type(e).__name__} - {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Failed to generate summary due to LLM error."
            )


def get_summarisation_service() -> SummarisationService:
    # This could be enhanced with caching or dependency injection framework if needed
    settings = get_settings()
    return SummarisationService(settings=settings)
