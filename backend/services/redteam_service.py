import logging
import yaml
import importlib.resources as pkg
from typing import List, Optional
from pathlib import Path

from core.config import get_settings, Settings
from models import (
    RedTeamPrompt,
    RedTeamAttempt,
    RedTeamRunResult,
    SourceDocument,
)
from services.rag_service import RAGService, get_rag_service
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Configuration                                                              #
# --------------------------------------------------------------------------- #
# We resolve the prompts YAML via importlib.resources so it works the same
# in the source tree AND inside the Docker image.

# PROMPTS_YAML = pkg.files("security").joinpath("redteam_prompts.yml") # Moved into _load_prompts

# from backend.core.config import settings  # REMOVED - Unused and incorrect import

# REMOVED - These module-level variables were unused and relied on the removed global settings object.
# # Ensure the Ollama URL is taken from env or falls back to a sane default.
# OLLAMA_API_BASE_LOCAL = (
#     settings.OLLAMA_API_BASE or "http://host.docker.internal:11434/v1"
# )
#
# # Default model name. Override via env OLLAMA_MODEL_NAME if you like.
# OLLAMA_MODEL_NAME_LOCAL = settings.OLLAMA_MODEL_NAME or "mistral:7b-instruct"


class RedTeamService:
    def __init__(self, settings_instance: Settings, rag_service: RAGService):
        self.settings = settings_instance
        self.rag_service = rag_service
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> List[RedTeamPrompt]:
        """Loads red team prompts from the YAML file."""
        # Define PROMPTS_YAML here so it's resolved at call time
        prompts_yaml_path = pkg.files("security").joinpath("redteam_prompts.yml")

        if not prompts_yaml_path.exists():
            logger.error(f"Red team prompts file not found: {prompts_yaml_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Red team prompts file not found: {prompts_yaml_path}",
            )

        try:
            with prompts_yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            loaded_prompts = []
            for p_data in data.get("prompts", []):
                # Basic validation
                if not all(
                    key in p_data
                    for key in ["id", "category", "text", "expected_behavior"]
                ):
                    logger.warning(
                        f"Skipping malformed prompt: {p_data.get('id', 'N/A')}"
                    )
                    continue
                loaded_prompts.append(RedTeamPrompt(**p_data))

            if not loaded_prompts:
                logger.warning(
                    f"No valid prompts loaded from {prompts_yaml_path}. The 'prompts' list might be empty or all entries malformed."
                )

            return loaded_prompts
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {prompts_yaml_path}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error parsing red team prompts file: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error loading prompts from {prompts_yaml_path}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error loading red team prompts: {e}",
            )

    async def run_red_team_evaluation(self) -> RedTeamRunResult:
        if not self.prompts:
            logger.warning("No red team prompts loaded. Skipping evaluation.")
            return RedTeamRunResult(
                results=[],
                summary_stats={
                    "prompts_run": 0,
                    "categories_tested": 0,
                    "notes": "No prompts were loaded.",
                },
            )

        attempts: List[RedTeamAttempt] = []
        categories_tested = set()

        for prompt_item in self.prompts:
            categories_tested.add(prompt_item.category)
            response_text = ""
            rag_sources: Optional[List[SourceDocument]] = None
            rag_confidence: Optional[float] = None
            evaluation_notes_suffix = f"Expected behavior: {prompt_item.expected_behavior}. Manual review pending for detailed evaluation."
            current_evaluation_notes = evaluation_notes_suffix  # Default

            try:
                logger.info(
                    f"Running red team prompt ID: {prompt_item.id}, Category: {prompt_item.category} via RAGService"
                )

                # Call RAGService with only the prompt text (positional argument)
                (
                    rag_response_text,
                    rag_sources,
                    rag_confidence,
                    _,
                ) = await self.rag_service.query_rag(prompt_item.text)

                # Normalize rag_sources to SourceDocument instances
                if rag_sources is not None:
                    normalized_sources: List[SourceDocument] = []
                    for src in rag_sources:
                        if isinstance(src, SourceDocument):
                            normalized_sources.append(src)
                        elif isinstance(src, dict):
                            normalized_sources.append(SourceDocument(**src))
                        else:
                            normalized_sources.append(SourceDocument(chunk_content=src))
                    rag_sources = normalized_sources

                attempt = RedTeamAttempt(
                    prompt_id=prompt_item.id,
                    prompt_text=prompt_item.text,
                    category=prompt_item.category,
                    response_text=rag_response_text,
                    rag_sources=rag_sources,
                    rag_confidence=rag_confidence,
                    evaluation_notes=current_evaluation_notes,
                )
                attempts.append(attempt)
            except Exception as e:
                logger.error(
                    f"Error processing red team prompt ID {prompt_item.id} via RAGService: {e}",
                    exc_info=True,
                )
                response_text = (
                    "<system_error>Error during RAG execution.</system_error>"
                )
                current_evaluation_notes = f"Failed to get response from RAG system: {str(e)}. {evaluation_notes_suffix}"
                attempt = RedTeamAttempt(
                    prompt_id=prompt_item.id,
                    prompt_text=prompt_item.text,
                    category=prompt_item.category,
                    response_text=response_text,  # Use the error message
                    rag_sources=None,
                    rag_confidence=None,
                    evaluation_notes=current_evaluation_notes,
                )
                attempts.append(attempt)

        summary_stats = {
            "prompts_run": len(self.prompts),
            "categories_tested": len(categories_tested),
            "unique_categories": list(categories_tested),
            "successful_executions": sum(
                1
                for att in attempts
                if "Error during RAG execution." not in att.response_text
            ),
            "failed_executions": sum(
                1
                for att in attempts
                if "Error during RAG execution." in att.response_text
            ),
        }

        return RedTeamRunResult(results=attempts, summary_stats=summary_stats)


_redteam_service_instance = None


def get_redteam_service() -> RedTeamService:
    """
    Factory for RedTeamService singleton. Initializes the service using real settings and RAGService.
    """
    global _redteam_service_instance
    if _redteam_service_instance is None:
        logger.info("Initializing RedTeamService singleton")
        # Load dependencies manually
        settings_instance = get_settings()
        rag_service = get_rag_service()
        _redteam_service_instance = RedTeamService(settings_instance, rag_service)
    return _redteam_service_instance
