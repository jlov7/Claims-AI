from typing import Dict, Any
import logging

from services.rag_service import get_rag_service, RAGService
from core.state import AgentState  # Assuming AgentState is in core.state

logger = logging.getLogger(__name__)


async def qa_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph node for the QAAgent.
    This agent takes a query from the state, uses the RAGService to find an answer
    with sources and confidence, and updates the state.
    """
    logger.info("[QAAgent] Node execution started.")

    session_id = state.get("session_id")
    if not session_id:
        logger.error("[QAAgent] session_id missing from state.")
        state["agent_error"] = "QAAgent: session_id missing"
        return state

    query = state.get("query")
    if not query or not query.strip():
        logger.warning("[QAAgent] No query provided in state or query is empty.")
        state["agent_error"] = "QAAgent: No query provided or query is empty."
        state["answer"] = "Error: Please provide a question."
        state["sources"] = []
        state["confidence_score"] = 0
        return state

    # Optional: if QA should be scoped to a specific collection or document_id from state
    collection_name = state.get("collection_name")  # e.g., default RAG collection
    # document_id_context = state.get("document_id_context") # For future use if RAG can be scoped to a single doc

    rag_service: RAGService = get_rag_service()

    try:
        logger.info(f"[QAAgent] Performing RAG query: '{query}'")
        if collection_name:
            logger.info(f"[QAAgent] Using collection: {collection_name}")
            answer, sources, confidence, attempts = await rag_service.query_collection(
                collection_name=collection_name, query=query
            )
        else:
            # Default to general RAG query if no specific collection is given
            answer, sources, confidence, attempts = await rag_service.query_rag(query)

        state["answer"] = answer
        # The sources from RAGService are V2SourceDocumentInternal.
        # LangServe routes convert them to V1SourceDocument for output.
        # Here, we store the V2 model directly in the internal agent state.
        state["sources"] = sources
        state["confidence_score"] = confidence
        state["rag_self_heal_attempts"] = attempts
        state["last_agent_activity"] = "QAAgent: Success"
        if "agent_error" in state:  # Clear previous error
            del state["agent_error"]
        logger.info(
            f"[QAAgent] RAG query successful. Answer: {answer[:50]}... Confidence: {confidence}"
        )

    except Exception as e:
        logger.error(f"[QAAgent] Error during RAG query: {e}")
        state["agent_error"] = f"QAAgent: Error during RAG query: {str(e)}"
        state["answer"] = f"Error: Could not answer question. Details: {str(e)}"
        state["sources"] = []
        state["confidence_score"] = 0
        state["rag_self_heal_attempts"] = state.get(
            "rag_self_heal_attempts", 0
        )  # Preserve if already set

    return state


# Example of how this might be used in a LangGraph (conceptual)
# from langgraph.graph import StateGraph, END
# from typing import TypedDict

# class AgentState(TypedDict):
#     session_id: str
#     query: Optional[str]
#     collection_name: Optional[str]
#     answer: Optional[str]
#     sources: Optional[List[SourceDocument]]
#     confidence_score: Optional[int]
#     rag_self_heal_attempts: Optional[int]
#     agent_error: Optional[str]
#     last_agent_activity: Optional[str]

# if __name__ == '__main__':
#     # Conceptual test
#     async def run_test():
#         initial_state = {
#             "session_id": "qa_agent_test_001",
#             "query": "What is the meaning of life?",
#             "collection_name": "general_knowledge" # Assuming RAGService can handle this
#         }

#         # Mocking RAGService for standalone test
#         class MockRAGService:
#             async def query_collection(self, collection_name, query):
#                 return f"Mock answer for '{query}' in {collection_name}", [], 5, 0
#             async def query_rag(self, query):
#                 return f"Mock general answer for '{query}'", [], 4, 0

#         import backend.agents.qa as qa_module # to patch the right get_rag_service
#         original_get_service = qa_module.get_rag_service
#         qa_module.get_rag_service = lambda: MockRAGService()

#         updated_state = await qa_agent_node(initial_state.copy())
#         print(f"State after QA: {updated_state}")
#         assert "Mock answer for" in updated_state.get("answer", "")

#         error_state = await qa_agent_node({"session_id": "s2"}) # No query
#         print(f"State after error (no query): {error_state}")
#         assert error_state.get("agent_error") is not None

#         # Restore
#         qa_module.get_rag_service = original_get_service

#     import asyncio
#     asyncio.run(run_test())
