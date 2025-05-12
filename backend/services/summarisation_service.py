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
            model=settings.PHI4_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        logger.info("SummarisationService initialized with LLM client.")

    def _get_content_from_id(self, document_id: str) -> str:
        # Assuming document_id is a filename in data/processed_text/
        # These files are expected to be JSON containing the extracted text, e.g. {"text": "..."}
        # Base path is relative to the WORKSPACE ROOT where data/ is.
        # The backend service has ./data mounted to /app/data in Docker if WORKDIR is /app
        # Or if data is mounted at /app/data and CWD is /app then path is data/processed_text
        # Let's assume a path relative to the data mount in the container.
        # The docker-compose.yml mounts ./data:/app/data
        # So, the path inside the container would be /app/data/processed_text/<document_id>

        # For security, ensure document_id is just a filename and not a path traversal attempt.
        if "/" in document_id or ".." in document_id:
            logger.error(f"Invalid document_id format: {document_id}")
            raise HTTPException(status_code=400, detail="Invalid document ID format.")

        file_path = os.path.join("/app/data/processed_text", document_id)
        logger.info(f"Attempting to read document for summarisation from: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Assuming the file is a JSON object with a "text" key holding the content
                # This matches the output of a potential `extract_text.py` script.
                data = json.load(f)
                content = data.get("text")
                if content is None:
                    logger.error(f"'text' key not found in JSON file: {file_path}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Could not extract text from document ID: {document_id}",
                    )
                logger.info(
                    f"Successfully read content from {file_path} for document_id: {document_id}"
                )
                return content
        except FileNotFoundError:
            logger.error(f"Document file not found: {file_path}")
            raise HTTPException(
                status_code=404, detail=f"Document not found for ID: {document_id}"
            )
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from file: {file_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading document format for ID: {document_id}",
            )
        except Exception as e:
            logger.error(
                f"Error reading document by ID {document_id} from {file_path}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Could not read document by ID: {document_id}"
            )

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
