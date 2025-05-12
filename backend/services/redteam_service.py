import yaml
import logging
import importlib.resources as pkg
from typing import List, Optional

from backend.core.config import get_settings, Settings
from backend.models import (
    RedTeamPrompt,
    RedTeamAttempt,
    RedTeamRunResult,
    SourceDocument,
)
from backend.services.rag_service import RAGService, get_rag_service
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Configuration                                                              #
# --------------------------------------------------------------------------- #
# We resolve the prompts YAML via importlib.resources so it works the same
# in the source tree AND inside the Docker image.

PROMPTS_YAML = pkg.files("backend.security").joinpath("redteam_prompts.yml")

from backend.core.config import settings  # wherever you keep env‑driven config

# Ensure the LM‑Studio URL is taken from env or falls back to a sane default.
PHI4_API_BASE = settings.PHI4_API_BASE or "http://host.docker.internal:1234/v1"

# Default model name. Override via env PHI4_MODEL_NAME if you like.
PHI4_MODEL_NAME = getattr(settings, "PHI4_MODEL_NAME", None) or "phi-4-reasoning-plus"


class RedTeamService:
    def __init__(self, settings_instance: Settings, rag_service: RAGService):
        self.settings = settings_instance
        self.rag_service = rag_service
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> List[RedTeamPrompt]:
        """Loads red team prompts from the YAML file."""
        if not PROMPTS_YAML.exists():
            logger.error(f"Red team prompts file not found: {PROMPTS_YAML}")
            raise HTTPException(
                status_code=500,
                detail=f"Red team prompts file not found: {PROMPTS_YAML}",
            )

        try:
            with PROMPTS_YAML.open("r", encoding="utf-8") as f:
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
                    f"No valid prompts loaded from {PROMPTS_YAML}. The 'prompts' list might be empty or all entries malformed."
                )

            return loaded_prompts
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {PROMPTS_YAML}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error parsing red team prompts file: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error loading prompts from {PROMPTS_YAML}: {e}")
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

                # Use the injected RAGService to process the prompt
                (
                    rag_response_text,
                    rag_sources,
                    rag_confidence,
                ) = await self.rag_service.query_rag(
                    query=prompt_item.text,
                    # Assuming red team prompts don't need specific user_id or session_id
                    # If they do, these would need to be passed or handled appropriately
                    user_id="red_team_user",
                    session_id=f"red_team_session_{prompt_item.id}",
                )

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
