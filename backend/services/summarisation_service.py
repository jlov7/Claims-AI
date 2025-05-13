import logging
import os
import builtins  # For module-level open alias
import re  # Import re for regex operations

# Module-level open alias for tests
open = builtins.open
import json  # For reading processed JSON files
from fastapi import HTTPException

from backend.core.config import Settings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class SummarisationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_client = ChatOpenAI(
            openai_api_base=settings.PHI4_API_BASE,
            openai_api_key="lm-studio",  # Required by Langchain, not used by LM Studio
            model="llama-3.2-3b-instruct",  # Explicitly use Llama model instead of settings.PHI4_MODEL_NAME
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        logger.info(
            "SummarisationService initialized with LLM client using model: llama-3.2-3b-instruct"
        )

    def _get_content_from_id(self, document_id: str) -> str:
        """
        Get the document content by its ID. This method handles various file naming scenarios:
        - Direct document_id (e.g., 'document123')
        - Document with extension (e.g., 'document.pdf')
        - Document with processed extension (e.g., 'document.pdf.json')
        """
        # For security, ensure document_id is just a filename and not a path traversal attempt
        if "/" in document_id or ".." in document_id:
            logger.error(f"Invalid document_id format: {document_id}")
            raise HTTPException(status_code=400, detail="Invalid document ID format.")

        # Clean up the document_id to ensure consistent handling
        base_id = document_id

        # Handle common document extensions - strip .pdf, .docx, etc. if present
        # but we'll keep track of the original extension for potential fallbacks
        original_extension = ""
        for ext in [".pdf", ".docx", ".txt", ".tiff", ".tif"]:
            if base_id.lower().endswith(ext):
                original_extension = ext
                base_id = base_id[: -len(ext)]
                logger.info(
                    f"Stripped original extension {ext}, base_id now: {base_id}"
                )
                break

        # Possible file paths to try (in order of preference)
        paths_to_try = []

        # Docker environment paths
        docker_base_path = "/app/data/processed_text"
        # Try exact ID with .json
        paths_to_try.append(os.path.join(docker_base_path, f"{document_id}.json"))
        # Try without original extension but with .json
        if original_extension:
            paths_to_try.append(os.path.join(docker_base_path, f"{base_id}.json"))
        # Try with .json on direct ID
        if not document_id.endswith(".json"):
            paths_to_try.append(os.path.join(docker_base_path, f"{document_id}.json"))
        # Try exact ID (in case it already has .json)
        paths_to_try.append(os.path.join(docker_base_path, document_id))

        # Local development paths
        try:
            from pathlib import Path

            project_root = Path(__file__).resolve().parent.parent.parent
            local_base_path = project_root / "data" / "processed_text"

            # Mirror the same patterns for local paths
            paths_to_try.append(str(local_base_path / f"{document_id}.json"))
            if original_extension:
                paths_to_try.append(str(local_base_path / f"{base_id}.json"))
            if not document_id.endswith(".json"):
                paths_to_try.append(str(local_base_path / f"{document_id}.json"))
            paths_to_try.append(str(local_base_path / document_id))

            logger.info(f"Will try local development paths as well: {project_root}")
        except Exception as e:
            logger.warning(f"Could not construct local paths: {e}")

        # Log all paths we'll try
        logger.info(
            f"Will try to read document from the following paths: {paths_to_try}"
        )

        # Try each path in order
        errors = []
        for file_path in paths_to_try:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    logger.info(f"Successfully opened file: {file_path}")
                    try:
                        data = json.load(f)
                        # Try different keys that might contain the content
                        content = None
                        for key in [
                            "text",
                            "content",
                            "extracted_text",
                            "document_text",
                        ]:
                            if key in data:
                                content = data[key]
                                logger.info(f"Found content under key: {key}")
                                break

                        if content:
                            logger.info(
                                f"Successfully read content from {file_path} for document_id: {document_id}"
                            )
                            return content
                        else:
                            logger.warning(
                                f"No recognized content key found in JSON file: {file_path}"
                            )
                            errors.append(f"No recognized content key in {file_path}")
                    except json.JSONDecodeError:
                        logger.warning(f"File is not valid JSON: {file_path}")
                        errors.append(f"JSON decode error in {file_path}")
            except FileNotFoundError:
                logger.info(f"File not found: {file_path}")
                errors.append(f"File not found: {file_path}")
            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                errors.append(f"Error reading {file_path}: {str(e)}")

        # If we reach here, all paths failed
        error_msg = f"Could not read document by ID: {document_id}. Tried paths: {paths_to_try}. Errors: {errors}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    def summarise_text(self, text_content: str, document_id: str = None) -> str:
        if not text_content.strip():
            logger.warning("Received empty text for summarisation.")
            raise HTTPException(status_code=400, detail="Cannot summarise empty text.")

        # Create a typical summarisation prompt
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
            raw = chain.invoke({"text_content": text_content})

            # delete common lead‑ins
            cleaned = re.sub(
                r"^(Summary:|Here(?: is|\'s) a summary:)\s*", "", raw, flags=re.I
            )

            # ensure bullet list starts with "•"
            if not cleaned.lstrip().startswith(("•", "-", "*")):
                cleaned = "• " + cleaned

            logger.info(
                f"Successfully generated summary for document_id: {document_id if document_id else 'direct content'}"
            )
            return cleaned
        except Exception as e:
            logger.error(
                f"LLM summarisation call failed for {document_id if document_id else 'direct content'}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail="Failed to generate summary due to LLM error."
            )


_summarisation_service_instance = None


def get_summarisation_service() -> SummarisationService:
    """
    Factory for SummarisationService singleton. Initializes the service using global settings.
    """
    global _summarisation_service_instance
    if _summarisation_service_instance is None:
        from backend.core.config import settings as global_settings

        _summarisation_service_instance = SummarisationService(global_settings)
    return _summarisation_service_instance
