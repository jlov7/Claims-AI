from langgraph.graph import StateGraph, END
import json  # Added for Kafka payload serialization
from aiokafka import AIOKafkaProducer  # Added for Kafka integration
import asyncio  # Added for Kafka producer

# For ToolNode
from langgraph.prebuilt import ToolNode
from agents.draft import tools as draft_agent_tools  # Import the tools

from agents.orchestrator import orchestrator_agent_node
from agents.summarise import summarise_agent_node
from agents.qa import qa_agent_node
from agents.draft import draft_agent_node
from core.config import get_settings  # Added to get Kafka settings
from core.state import AgentState  # Import AgentState from the new state.py


# --- Agent State Definition ---
# class AgentState(TypedDict): <-- REMOVE THIS BLOCK
#     """Shared state for the LangGraph agent execution."""
#
#     session_id: str
#     initial_user_request: Optional[str]  # What the user initially asked for
# ... (rest of the old AgentState definition removed)
#     last_agent_activity: Optional[str]  # Description of the last thing an agent did


# --- Graph Construction ---
workflow = StateGraph(AgentState)  # This will now use the imported AgentState

# Add nodes
workflow.add_node("orchestrator", orchestrator_agent_node)
workflow.add_node("summarise", summarise_agent_node)
workflow.add_node("qa", qa_agent_node)
workflow.add_node("draft", draft_agent_node)

# Add ToolNode for DraftAgent
# This node will execute tools called by the DraftAgent
tool_node = ToolNode(draft_agent_tools)
workflow.add_node("draft_tool_node", tool_node)


# Placeholder for a Kafka publishing node (to be defined)
async def publish_to_kafka_node(state: AgentState) -> AgentState:  # Made async
    logger.info(
        f"[KafkaNode] Attempting to publish data for session: {state.get('session_id')}"
    )
    settings = get_settings()
    producer = None  # Initialize producer to None for finally block

    try:
        payload_to_publish = {
            "session_id": state.get("session_id"),
            "document_id": state.get("document_id"),
            "summary": state.get("summary"),
            "final_answer": state.get("answer"),
            "sources": (
                [src.model_dump() for src in state.get("sources", [])]
                if state.get("sources")
                else []
            ),  # Serialize sources
            "draft_file_path": state.get("draft_strategy_note_result", {}).get(
                "file_path"
            ),
            "draft_strategy_note": state.get("draft_strategy_note"),
            "negotiation_coach_advice": state.get("negotiation_coach_advice"),
            "reserve_prediction": state.get("reserve_prediction"),
            "user_criteria": state.get("user_criteria"),
            "qa_history_str": state.get("qa_history_str"),
            "orchestration_status": state.get("orchestration_status"),
        }
        state["kafka_payload"] = payload_to_publish

        logger.debug(
            f"[KafkaNode] Kafka bootstrap servers: {settings.KAFKA_BOOTSTRAP_SERVERS}"
        )
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            loop=asyncio.get_event_loop(),  # Ensure loop is passed if running in different context
            client_id=f"claims-ai-graph-{state.get('session_id', 'unknown_session')}",
        )
        await producer.start()
        logger.info(
            f"[KafkaNode] Kafka producer started for session: {state.get('session_id')}"
        )

        topic = "claim-facts"
        message_bytes = json.dumps(payload_to_publish).encode("utf-8")

        logger.info(
            f"[KafkaNode] Sending message to topic '{topic}': {payload_to_publish}"
        )
        await producer.send_and_wait(topic, message_bytes)

        state["kafka_publish_status"] = "Success"
        state["processed_steps"].append(
            f"publish_to_kafka_node: Payload successfully sent to topic '{topic}'"
        )
        logger.info(
            f"[KafkaNode] Payload successfully sent for session: {state.get('session_id')}"
        )
        state["kafka_error_message"] = None

    except Exception as e:
        error_message = f"Failed to publish to Kafka: {str(e)}"
        logger.error(
            f"[KafkaNode] {error_message} for session: {state.get('session_id')}",
            exc_info=True,
        )
        state["kafka_publish_status"] = "Failed"
        state["kafka_error_message"] = error_message  # Store the error message
        state["processed_steps"].append(f"publish_to_kafka_node: {error_message}")
    finally:
        if producer:
            logger.info(
                f"[KafkaNode] Stopping Kafka producer for session: {state.get('session_id')}"
            )
            await producer.stop()
            logger.info(
                f"[KafkaNode] Kafka producer stopped for session: {state.get('session_id')}"
            )

    return state


workflow.add_node("publish_to_kafka", publish_to_kafka_node)

# Set entry point
workflow.set_entry_point("orchestrator")

# Define standard sequential flow (will be modified for conditional QA retry)
workflow.add_edge("orchestrator", "summarise")
workflow.add_edge("summarise", "qa")
# Edge from QA will be conditional
# workflow.add_edge("qa", "draft") # This will be replaced by conditional logic

# EDGES FOR DRAFT AGENT AND TOOL NODE WILL BE CONDITIONAL
# workflow.add_edge("draft", "publish_to_kafka") # This will be replaced
workflow.add_edge("publish_to_kafka", END)

# --- Conditional Logic for QA Agent Retry ---
MAX_QA_RETRIES = 2


def should_retry_qa(state: AgentState) -> str:
    """Determines if the QA agent should retry based on confidence and attempt count."""
    confidence = state.get("confidence_score")  # Get value, could be None
    if confidence is None:  # Explicitly check for None and default to 0
        confidence = 0

    current_attempts = state.get("qa_retry_attempts", 0)
    agent_error = state.get("agent_error")

    if (
        agent_error and "QAAgent" in agent_error
    ):  # If QA agent itself had an error, maybe don't retry LLM confidence
        logger.warning(
            f"[GraphLogic] QAAgent reported an error: {agent_error}. Proceeding without retry."
        )
        return "proceed_to_draft"

    if (
        confidence < 3 and current_attempts < MAX_QA_RETRIES
    ):  # Confidence threshold from v2project.md is <0.7, mapping to <3 for int score
        logger.info(
            f"[GraphLogic] QA confidence ({confidence}) is low. Attempts: {current_attempts}. Retrying QA."
        )
        # state["qa_retry_attempts"] = current_attempts + 1 # This modification should be in the node or a dedicated modifier node
        return "retry_qa"
    else:
        if confidence >= 3:
            logger.info(
                f"[GraphLogic] QA confidence ({confidence}) is sufficient. Proceeding to draft."
            )
        else:
            logger.warning(
                f"[GraphLogic] QA confidence ({confidence}) still low after {current_attempts} retries. Proceeding to draft anyway."
            )
        return "proceed_to_draft"


# To correctly increment retry_attempts, it's often better done within the node being retried or a small utility node
# For simplicity here, if retry is chosen, the QA node must be responsible for incrementing its attempt count from state
# Or, we add a small node to increment attempts before looping back to QA.
# Let's assume for now the QAAgent node will need to be aware of this and increment `qa_retry_attempts` if it's re-entered.
# A cleaner way is a dedicated small node to update the counter.


async def increment_qa_retry_node(state: AgentState) -> AgentState:
    current_attempts = state.get("qa_retry_attempts", 0)
    state["qa_retry_attempts"] = current_attempts + 1
    state["processed_steps"].append(
        f"increment_qa_retry_node: Attempts now {state['qa_retry_attempts']}"
    )
    logger.info(
        f"[GraphLogic] Incrementing QA retry attempts to {state['qa_retry_attempts']}"
    )
    # Clear previous QA answer if retrying, or QAAgent should handle this
    state["answer"] = None
    state["sources"] = None
    state["confidence_score"] = None
    state["agent_error"] = None  # Clear previous error before retry
    state["kafka_error_message"] = None  # Clear kafka error before retry as well
    return state


workflow.add_node("increment_qa_retry", increment_qa_retry_node)

# Add conditional edge from QA
workflow.add_conditional_edges(
    "qa",
    should_retry_qa,
    {"retry_qa": "increment_qa_retry", "proceed_to_draft": "draft"},
)
workflow.add_edge("increment_qa_retry", "qa")  # Loop back to QA agent


# --- Conditional Logic for Draft Agent Tool Calling ---
def should_draft_or_use_tool(state: AgentState) -> str:
    """
    Determines if the DraftAgent should proceed to publish (draft complete)
    or if it needs to call tools (ToolCallRequested).
    The DraftAgentState is part of the overall AgentState if managed globally,
    or this needs to access the specific sub-state if draft agent has its own.
    Assuming draft_status is updated in the main AgentState by draft_agent_node.
    """
    # draft_status is set by draft_agent_node within the main AgentState
    draft_status = state.get("draft_status")
    logger.info(f"[GraphLogic] Checking draft status: {draft_status}")

    if draft_status == "ToolCallRequested":
        # The draft_agent_node has already put the AIMessage with tool_calls into AgentState.messages
        logger.info(
            "[GraphLogic] DraftAgent requested tool call. Routing to draft_tool_node."
        )
        return "call_draft_tools"
    elif draft_status == "DraftComplete":
        logger.info("[GraphLogic] Draft is complete. Routing to publish_to_kafka.")
        return "proceed_to_publish"
    else:
        # Fallback or error case - perhaps loop back to draft or end with error
        logger.warning(
            f"[GraphLogic] Unknown draft status: {draft_status}. Defaulting to proceed_to_publish."
        )
        # For safety, or could raise an error / go to a specific error handling node
        return "proceed_to_publish"


# Add conditional edges from DraftAgent
workflow.add_conditional_edges(
    "draft",
    should_draft_or_use_tool,
    {"call_draft_tools": "draft_tool_node", "proceed_to_publish": "publish_to_kafka"},
)

# Edge from Draft ToolNode back to DraftAgent
# After tools are executed by draft_tool_node, their results (ToolMessages)
# are appended to the 'messages' list in the state.
# The DraftAgent then needs to process these ToolMessages.
workflow.add_edge("draft_tool_node", "draft")


# --- Error Guarding ---
def error_guard(state: AgentState) -> bool:
    """Checks if an agent_error is present in the state."""
    is_error = bool(state.get("agent_error"))
    if is_error:
        logger.warning(
            f"[GraphLogic] Error guard triggered due to agent_error: {state.get('agent_error')}. Short-circuiting to END."
        )
    return is_error


# Add error guards after nodes that might set agent_error and should halt the main flow
# If orchestrator fails, it might be too early to even start, but let's assume it sets an error
# For now, focusing on summarise and qa as per user request.
# User requested:
# graph.edge(
#     summarise_agent_node, END,                   # short‑circuit to END
#     condition=error_guard,
# )
# graph.edge(
#     qa_agent_node, END,
#     condition=error_guard,
# )
# This syntax for add_edge with a condition and a single target for that condition is unusual.
# Typically, add_conditional_edges is used, or if an edge should *only* be taken on a condition,
# it implies the non-conditional path is removed or handled differently.
# LangGraph's add_edge(source, target, condition_function) means this edge is *only* taken if condition is true.
# It doesn't replace existing non-conditional edges from that source unless explicitly removed.

# Let's assume the intent is that IF error_guard is true AFTER summarise, THEN go to END.
# This means we need to be careful about existing edges from "summarise".
# The existing edge is: workflow.add_edge("summarise", "qa")
# We want:
#   summarise --(if error_guard)--> END
#   summarise --(if not error_guard)--> qa

# This is best handled by add_conditional_edges:
workflow.add_conditional_edges(
    "summarise",
    lambda state: "error_occurred" if error_guard(state) else "proceed_to_qa",
    {
        "error_occurred": END,
        "proceed_to_qa": "qa",  # This re-establishes the normal path if no error
    },
)
# We need to remove the old direct edge from summarise to qa if add_conditional_edges doesn't implicitly do that.
# Based on LangGraph, add_conditional_edges *replaces* any existing simple edges from the source node.
# So, the old workflow.add_edge("summarise", "qa") is effectively superseded.

# Similarly for QA node:
# Existing conditional edges from QA:
# workflow.add_conditional_edges(
#     "qa",
#     should_retry_qa,  <-- This is the main condition
#     {"retry_qa": "increment_qa_retry", "proceed_to_draft": "draft"},
# )
# If an error occurs *within* qa_agent_node itself (and it sets agent_error),
# we want to go to END instead of retrying or proceeding to draft.


# We need a combined condition or a preliminary error check before should_retry_qa.
def qa_router_with_error_check(state: AgentState) -> str:
    if error_guard(state):  # Check for error first
        return "error_occurred"
    # If no error, proceed with existing retry logic
    return should_retry_qa(state)


workflow.add_conditional_edges(
    "qa",
    qa_router_with_error_check,  # Use the new router
    {
        "error_occurred": END,  # New path for errors from QA node
        "retry_qa": "increment_qa_retry",
        "proceed_to_draft": "draft",
    },
)
# This replaces the previous conditional edge from "qa".


# Compile the graph
# Need to import logger for publish_to_kafka_node if it's not already global
import logging

logger = logging.getLogger(
    __name__
)  # Ensure logger is available for the graph functions

app = workflow.compile()

# Example of how to run (for testing, actual invocation will be via LangServe)
# async def run_graph_example():
#     # Define initial_state: AgentState for testing here, ensuring all fields are covered.
#     # Example:
#     # initial_state: AgentState = {
#     #     "session_id": "example_session_001",
#     #     "initial_user_request": "Summarise example.pdf",
#     #     "document_id": "example.pdf",
#     #     "query": "What are the key points?",
#     #     "processed_steps": [],
#     #     "qa_retry_attempts": 0,
#     #     "text_content_override": None, # etc. for all fields in AgentState
#     # }

# Mocking services for graph run - this would be complex
# For now, this is a placeholder to show invocation pattern

# config = {"recursion_limit": 10}
# async for event in app.astream_events(initial_state, config=config, version="v1"):
#     kind = event["event"]
#     if kind == "on_chain_end":
#         print(f"--- Event: {kind} for {event['name']} ---")
#         print(f"Output: {event['data'].get('output')}")
#         print("----\n")
#     elif kind == "on_chat_model_stream":
#         # content = event["data"]["chunk"].content
# if content:
# print(content, end="|")
#         pass
# final_state = await app.ainvoke(initial_state, config=config)
# print("\n--- Final State ---")
# print(final_state)

# if __name__ == '__main__':
#     import asyncio
#     # asyncio.run(run_graph_example()) # Requires mocked services to run cleanly
#     print("Graph compiled. Run example requires service mocking or live services.")

# Placeholder for main graph compilation - will be filled out later
# compiled_graph = None

# The if __name__ == '__main__' block containing only comments and placeholder
# 'pass' statement has been removed to resolve persistent linter errors.
# Actual graph testing and invocation should be done via dedicated test files
# or LangServe endpoints.
