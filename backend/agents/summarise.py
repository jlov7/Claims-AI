import logging
from typing import Dict, Any, Optional

from services.summarisation_service import (
    get_summarisation_service,
    SummarisationService,
)
from core.state import AgentState

logger = logging.getLogger(__name__)


# Placeholder for the Smart-Skim tool interaction
# This tool is expected to be defined in tools/heatmap.py later
# and might refine what content is passed to the summarisation service.
def _invoke_smart_skim_tool(
    document_id: str, session_id: Optional[str] = None
) -> Optional[str]:
    """
    Placeholder for Smart-Skim tool.
    In the future, this tool would identify key sections of a document.
    For now, it might return None or the full content path if no skimming is done.
    """
    logger.info(
        f"[SummariseAgent] Smart-Skim tool invoked for doc_id: {document_id} (placeholder)"
    )
    # When implemented, this could return specific text sections or a modified document reference.
    # For now, returning None signifies that the agent should use the default content retrieval.
    return None


async def summarise_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the SummariseAgent.
    This agent takes a document ID or text content from the state,
    optionally uses a Smart-Skim tool (placeholder), generates a summary,
    and updates the state with this summary.
    """
    logger.info("[SummariseAgent] Node execution started.")

    session_id = state.get("session_id")
    if not session_id:
        logger.error("[SummariseAgent] session_id missing from state.")
        # Or raise an error, or return state with an error message
        state["agent_error"] = "SummariseAgent: session_id missing"
        return state

    # For managing more complex state if needed, though LangGraph handles state dict directly
    # session_memory = SessionMemory(session_id)

    document_id = state.get("document_id")
    text_content_override = state.get(
        "text_content_override"
    )  # e.g., from a previous agent or direct input
    summary_output_key = state.get(
        "summary_output_key", "summary"
    )  # Where to put the summary in state

    if not document_id and not text_content_override:
        logger.warning(
            "[SummariseAgent] No document_id or text_content_override in state. Cannot summarise."
        )
        state["agent_error"] = "SummariseAgent: No document or content to summarise."
        state[summary_output_key] = (
            "Error: No document or content provided for summarisation."
        )
        return state

    text_to_summarise = None
    summarisation_service: SummarisationService = get_summarisation_service()

    # Placeholder for Smart-Skim tool logic
    # skimmed_content_reference = _invoke_smart_skim_tool(document_id, session_id)
    # if skimmed_content_reference: ... use it ...

    if text_content_override:
        logger.info("[SummariseAgent] Using text_content_override for summarisation.")
        text_to_summarise = text_content_override
        # If content is directly provided, document_id might be for reference only
    elif document_id:
        logger.info(
            f"[SummariseAgent] Using document_id: {document_id} for summarisation."
        )
        try:
            # The service's _get_content_from_id handles resolving the actual content.
            # This method is internal; ideally, a public interface would be used if available.
            text_to_summarise = summarisation_service._get_content_from_id(document_id)
        except Exception as e:
            logger.error(
                f"[SummariseAgent] Error retrieving content for doc_id {document_id}: {e}"
            )
            state["agent_error"] = (
                f"SummariseAgent: Error retrieving document {document_id}."
            )
            state[summary_output_key] = (
                f"Error: Could not retrieve document {document_id} for summarisation."
            )
            return state

    if not text_to_summarise or not text_to_summarise.strip():
        logger.warning("[SummariseAgent] Content to summarise is empty or whitespace.")
        state["agent_error"] = "SummariseAgent: Content to summarise is empty."
        state[summary_output_key] = (
            "Error: Content for summarisation is empty or whitespace."
        )
        return state

    try:
        logger.info(
            f"[SummariseAgent] Generating summary for document_id: {document_id if document_id else 'N/A (direct content)'}"
        )
        # The service method returns the summary string directly.
        # Note: summarise_text is synchronous as per previous fixes.
        summary_text = summarisation_service.summarise_text(
            text_content=text_to_summarise,
            document_id=document_id,  # Pass for context/logging if service uses it
        )
        state[summary_output_key] = summary_text
        state["last_agent_activity"] = "SummariseAgent: Success"
        if "agent_error" in state:  # Clear previous error if successful now
            del state["agent_error"]
        logger.info("[SummariseAgent] Summary generated successfully.")
    except Exception as e:
        logger.error(f"[SummariseAgent] Error during summarisation: {e}")
        state["agent_error"] = (
            f"SummariseAgent: Error during summary generation: {str(e)}"
        )
        state[summary_output_key] = (
            f"Error: Failed to generate summary. Details: {str(e)}"
        )

    return state


# Example of how this might be used in a LangGraph (conceptual)
# from langgraph.graph import StateGraph, END
# class AgentState(TypedDict):
#     session_id: str
#     document_id: Optional[str]
#     text_content_override: Optional[str]
#     summary: Optional[str]
#     summary_output_key: Optional[str] # Allows dynamic output key for summary
#     agent_error: Optional[str]
#     last_agent_activity: Optional[str]

# if __name__ == '__main__':
#     # This is a conceptual test, not a runnable example without a graph setup
#     async def run_test():
#         initial_state = {
#             "session_id": "agent_test_session_001",
#             "document_id": "test_doc.txt", # Needs SummarisationService to be able to resolve this
#             "summary_output_key": "document_summary"
#         }
#         # Mocking SummarisationService for standalone test
#         class MockSummarisationService:
#             def _get_content_from_id(self, doc_id):
#                 if doc_id == "test_doc.txt":
#                     return "This is a long test document about summarisation agents and their exciting lives in a digital world."
#                 raise FileNotFoundError(f"Mock: Doc {doc_id} not found")
#             def summarise_text(self, text_content, document_id=None):
#                 return f"Mocked summary: {text_content[:30]}..."

#         original_get_service = summarisation_service_module.get_summarisation_service
#         summarisation_service_module.get_summarisation_service = lambda: MockSummarisationService()

#         updated_state = await summarise_agent_node(initial_state.copy())
#         print(f"State after summarisation: {updated_state}")
#         assert updated_state.get("document_summary") is not None
#         assert "Mocked summary" in updated_state.get("document_summary")

#         error_state = await summarise_agent_node({"session_id": "s2"}) # No doc_id or content
#         print(f"State after error: {error_state}")
#         assert error_state.get("agent_error") is not None

#         # Restore original service getter
#         summarisation_service_module.get_summarisation_service = original_get_service

#     import asyncio
#     asyncio.run(run_test())
