from typing import TypedDict, Optional, List, Dict, Any
# from backend.models import SourceDocument  # For type hinting sources from QAAgent
from models import SourceDocument  # For type hinting sources from QAAgent


# --- Main Agent State Definition (for the primary workflow) ---
class AgentState(TypedDict):
    """Shared state for the main LangGraph agent execution."""

    session_id: str
    initial_user_request: Optional[str]  # What the user initially asked for
    document_id: Optional[str]  # Primary document being processed
    collection_name: Optional[str]  # For RAG, if scoped to a collection
    text_content_override: Optional[
        str
    ]  # If text is provided directly, bypassing doc_id lookup

    # Orchestrator outputs
    processed_steps: List[str]  # Log of agents/steps executed
    orchestration_status: Optional[
        str
    ]  # e.g., "Processing", "Blocked", "Failed", "Completed"

    # SummariseAgent outputs
    summary: Optional[str]
    # summary_output_key: Optional[str] # Decided against dynamic keys for simplicity in graph state

    # QAAgent outputs
    query: Optional[str]  # The question being asked
    answer: Optional[str]
    sources: Optional[List[SourceDocument]]  # List of V2 SourceDocument models
    confidence_score: Optional[int]
    rag_self_heal_attempts: int
    qa_retry_attempts: int  # Specific counter for QA retry loop, initialized to 0

    # DraftAgent outputs
    key_document_ids: Optional[List[str]]  # Curated list of doc IDs for drafting
    qa_history_str: Optional[
        str
    ]  # String representation of Q&A history for drafting context
    user_criteria: Optional[str]  # Specific user criteria for the draft
    output_filename: Optional[str]  # Suggested filename for the draft
    draft_strategy_note_result: Optional[
        Dict[str, Any]
    ]  # Contains file_path, file_name, message or error
    # draft_output_key: Optional[str] # Decided against dynamic keys for simplicity
    negotiation_coach_advice: Optional[str]  # Explicit field for negotiation tip

    # Kafka output (placeholder for now)
    kafka_payload: Optional[Dict[str, Any]]  # Data to be published to Kafka
    kafka_publish_status: Optional[str]  # "Pending", "Success", "Failed"
    kafka_error_message: Optional[str]  # Added to store kafka error

    # General error/status fields
    agent_error: Optional[str]  # Last error message from an agent
    last_agent_activity: Optional[str]  # Description of the last thing an agent did


# --- Draft Agent State Definition (for the drafting sub-workflow) ---
# This state is specific to the draft_agent_node and its internal LangGraph workflow,
# managed by DraftingService.
class DraftAgentState(TypedDict):
    """State for the draft agent's internal LangGraph workflow."""

    # Inputs required by the draft agent
    session_id: str  # For logging and context
    summary: Optional[str]
    qa_pairs: Optional[
        List[Dict[str, str]]
    ]  # List of Q&A dicts { "question": "...", "answer": "..."}
    user_query: Optional[
        str
    ]  # The most recent or relevant user query that led to drafting
    document_ids: Optional[List[str]]  # List of document IDs used for summary/QA
    initial_user_request: Optional[str]  # Original request if available

    # Conversation history for the draft agent's LLM
    messages: List[
        Dict[str, Any]
    ]  # List of messages (Human, AI, Tool) in LangChain format

    # Internal state for the draft agent if it becomes more complex (e.g., multi-step)
    # current_draft_content: Optional[str]

    # Output from the draft agent node
    draft_strategy_note: Optional[str]  # The drafted strategy note content
    draft_error: Optional[str]  # Any error during the drafting process itself
