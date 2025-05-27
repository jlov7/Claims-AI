from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


async def orchestrator_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for the OrchestratorAgent.
    This agent is responsible for setting initial goals, preparing the state,
    and potentially deciding the sequence of other agents or delegating tasks.
    For now, it will ensure essential IDs are present and log the start of orchestration.
    """
    logger.info("[OrchestratorAgent] Node execution started.")

    session_id = state.get("session_id")
    if not session_id:
        # In a real scenario, session_id should be guaranteed by the graph entry point
        # or the LangServe endpoint that invokes the graph.
        logger.error(
            "[OrchestratorAgent] CRITICAL: session_id missing at orchestration start."
        )
        state["agent_error"] = (
            "OrchestratorAgent: session_id is missing. Cannot proceed."
        )
        state["orchestration_status"] = "Failed: Missing session_id"
        # This might be a point to halt the graph (e.g. by routing to END if an error state is set)
        return state

    initial_user_request = state.get(
        "initial_user_request", "No specific request provided."
    )
    document_id = state.get("document_id")  # Main document to process

    logger.info(f"[OrchestratorAgent] Orchestrating for session_id: {session_id}")
    logger.info(f"[OrchestratorAgent] Initial user request: {initial_user_request}")
    logger.info(f"[OrchestratorAgent] Target document_id: {document_id}")

    # Initialize or validate required state fields
    if "processed_steps" not in state:
        state["processed_steps"] = []

    state["processed_steps"].append("OrchestratorAgent: Initialized")
    state["orchestration_status"] = "Processing"
    state["last_agent_activity"] = "OrchestratorAgent: Ready"
    if "agent_error" in state:  # Clear any prior unrelated error
        del state["agent_error"]

    # Future logic for this agent could involve:
    # 1. Decomposing user_request into a plan (e.g., list of agent calls).
    # 2. Setting up specific input parameters for the first agent in the sequence.
    # 3. Routing: Deciding which agent/tool to call next based on the current state.
    #    For example, if a document_id is provided, the next step is likely summarization or Q&A setup.
    #    If only a general query is provided, it might go straight to a general RAG agent.

    if (
        not document_id
        and "query" not in state
        and "text_content_override" not in state
    ):
        logger.warning(
            "[OrchestratorAgent] No document_id, query, or content provided. Limited operations possible."
        )
        state["orchestration_status"] = "Blocked: Insufficient input for processing."
        # Depending on the graph, this might lead to an error state or a request for more input.

    logger.info(
        f"[OrchestratorAgent] State prepared for next step: {state.get('orchestration_status')}"
    )
    return state


# Example of how this might be used in a LangGraph (conceptual)
# if __name__ == '__main__':
#     async def run_test():
#         initial_state_no_session = {}
#         updated_state = await orchestrator_agent_node(initial_state_no_session.copy())
#         print(f"State after orchestration (no session_id): {updated_state}")
#         assert "OrchestratorAgent: session_id is missing" in updated_state.get("agent_error", "")

#         initial_state_with_session = {
#             "session_id": "orch_test_session_001",
#             "initial_user_request": "Summarise and analyse the attached document for key risks.",
#             "document_id": "claim_form_abc.pdf"
#         }
#         updated_state = await orchestrator_agent_node(initial_state_with_session.copy())
#         print(f"State after orchestration (with session_id): {updated_state}")
#         assert updated_state.get("orchestration_status") == "Processing"
#         assert "OrchestratorAgent: Initialized" in updated_state.get("processed_steps", [])

#         initial_state_no_doc = {
#             "session_id": "orch_test_session_002",
#             "initial_user_request": "Answer my question.",
#             # No document_id or query yet
#         }
#         updated_state = await orchestrator_agent_node(initial_state_no_doc.copy())
#         print(f"State after orchestration (no doc/query): {updated_state}")
#         assert updated_state.get("orchestration_status") == "Blocked: Insufficient input for processing."

#     import asyncio
#     asyncio.run(run_test())
