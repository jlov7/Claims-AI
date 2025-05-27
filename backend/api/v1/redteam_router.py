import logging
from fastapi import APIRouter, HTTPException, Depends

from models import RedTeamRunResult
from services.redteam_service import get_redteam_service
from services.redteam_service import RedTeamService # Explicit import for type hint

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/redteam/run",
    response_model=RedTeamRunResult,
    summary="Run Red Team Evaluation",
    tags=["Red Teaming"],
    description="Executes a predefined set of adversarial prompts against the RAG system and returns the results.",
)
async def run_red_team_tests() -> RedTeamRunResult:
    """
    Triggers a red team evaluation run.

    The service will load prompts from the configured YAML file, execute each against the RAG system,
    and return a structured result including the original prompt, the RAG system's response,
    any retrieved sources, confidence scores, and basic summary statistics.
    """
    try:
        logger.info("Received request to run red team evaluation.")
        # Fetch the redteam service at runtime to allow overrides
        redteam_service = get_redteam_service()
        result = await redteam_service.run_red_team_evaluation()
        logger.info(
            f"Red team evaluation completed. Prompts run: {result.summary_stats.get('prompts_run', 0)}"
        )
        return result
    except HTTPException as e:
        # Re-raise HTTPExceptions (e.g., file not found for prompts)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during red team evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during red team evaluation: {str(e)}",
        )

@router.post("/run", response_model=RedTeamRunResult)
async def run_red_team_evaluation(
    redteam_service: RedTeamService = Depends(get_redteam_service),
) -> RedTeamRunResult:
    result = await redteam_service.run_evaluation()
    return result
