from typing import Dict, Any, List
import logging
import json  # Added for schema serialization
import uuid  # Add for generating tool call IDs

# LangChain and LangGraph imports
from langchain_core.tools import BaseTool, tool, Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)  # Added BaseMessage
# from langchain_community.chat_models import ChatOllama  # Deprecated import
from langchain_ollama import ChatOllama  # Updated import

# from langchain_experimental.chat_models.ollama_functions import OllamaFunctions # Removed experimental
from langchain_core.pydantic_v1 import BaseModel, Field as V1Field # For tool input schema
from langchain_core.output_parsers.openai_tools import PydanticToolsParser

# from backend.core.config import get_settings
from core.config import get_settings

settings = get_settings()  # Initialize settings at module level after import

# from backend.core.state import (
from core.state import (
    AgentState,  # Main state
    DraftAgentState,  # Specific state for this agent if needed, or use fields in AgentState
)
# from backend.agents.base import AgentState, BaseAgentNode # Removed this problematic import
from tools.negotiation import get_negotiation_tip # Corrected path assuming tools is at the same level as agents
# from backend.tools.reserve_predictor_client import (
from tools.reserve_predictor_client import (
    get_reserve_prediction  # Corrected path, removed non-existent import
)
# from backend.tools.heatmap import smart_skim_tool  # Added import for smart_skim_tool
from tools.heatmap import smart_skim_tool # Corrected path

# Placeholder for a more sophisticated file naming/saving mechanism

logger = logging.getLogger(__name__)

# Define the tools the DraftAgent can use
tools: List[BaseTool] = [get_negotiation_tip, get_reserve_prediction, smart_skim_tool]

# Initialize the LLM for the DraftAgent
# Assuming Mistral 7B Instruct is running via Ollama
# For tool calling with Ollama, we might need specific prompting or model versions.
llm = ChatOllama(
    model=settings.OLLAMA_MODEL_NAME,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=settings.LLM_TEMPERATURE,
    format="json",
)  # Ensure format="json" is present
# llm = OllamaFunctions(model=settings.OLLAMA_MODEL_NAME, temperature=settings.LLM_TEMPERATURE, format="json") # Removed experimental

# The direct .bind_tools() might not be fully supported by ChatOllama in this version for automatic tool invocation.
# We will rely on prompt engineering and JSON mode for tool calling.
# So, llm_with_tools will just be the llm, and the prompt needs to guide JSON output for tools.
llm_with_tools = llm  # Revert this line

# Tool Executor
# The ToolExecutor is responsible for taking a ToolInvocation (name, args) and running the actual tool.
# tool_executor = ToolExecutor(tools)

# Remove old helper functions that were replaced by proper tools or agent logic
# async def _invoke_reserve_predictor_tool(...) -> Dict[str, Any]: ...
# async def _invoke_negotiation_coach_tool(...) -> Dict[str, Any]: ...
# async def _call_reserve_predictor(...) -> Optional[float]: ...


# --- Helper Function to Format Tools for Prompt ---
def format_tools_for_prompt(tools_list: List[BaseTool]) -> str:
    """
    Formats a list of tools into a string description suitable for an LLM prompt.
    """
    tool_descriptions = []
    for t in tools_list:
        tool_desc = (
            f"Tool Name: {t.name}\\n"
            f"Tool Description: {t.description}\\n"
            f"Tool Arguments (JSON Schema): {json.dumps(t.args, indent=2) if hasattr(t, 'args') and t.args else '{}'}"
        )
        tool_descriptions.append(tool_desc)
    return "\\n\\n---\\n\\n".join(tool_descriptions)


# --- Tool Definitions ---
# These tools will be made available to the DraftAgent
# Note: The actual functions are imported from their respective modules.
# The @tool decorator here, or rather instantiating Tool objects, makes them LangChain-compatible tools.

# @PydanticTool <--- No, we instantiate Tool objects directly for more control or use function references
# If get_negotiation_tip and get_reserve_prediction are already decorated with @tool in their own files,
# they might not need to be re-wrapped if they are directly usable as BaseTool instances.
# For clarity and to ensure they are LangChain BaseTool instances:
negotiation_tool = Tool(
    name="get_negotiation_tip",
    func=get_negotiation_tip,  # Direct function reference
    description="Provides negotiation tips based on claimant solicitor and injury type. Use this to get advice on how to approach settlement discussions.",
    # args_schema should be automatically inferred if get_negotiation_tip uses Pydantic models or has type hints
)

reserve_predictor_tool = Tool(
    name="get_reserve_prediction",
    func=get_reserve_prediction,  # Direct function reference
    description="Predicts the likely reserve amount for a claim based on various claim features. Use this to get an estimated financial reserve.",
    # args_schema should be automatically inferred
)

smart_skim_tool_instance = Tool(
    name="smart_skim_document_chunks",
    func=smart_skim_tool,  # Direct function reference
    description="Scores document chunks (pages) based on embedding similarity to a query and returns the top N most relevant chunks. Use this to find key sections in a document related to a specific topic before drafting, if the initial summary and Q&A are insufficient. Requires a document_id and a query string.",
    # args_schema should be automatically inferred from smart_skim_tool type hints
)

tools = [negotiation_tool, reserve_predictor_tool, smart_skim_tool_instance]

# --- LLM and Prompt Setup ---
# llm = ChatOllama(model=settings.OLLAMA_MODEL_NAME, temperature=settings.LLM_TEMPERATURE)
# tool_executor = ToolExecutor(tools=tools)

# Format tools for the prompt
formatted_tool_descriptions = format_tools_for_prompt(tools)

# --- System Prompt for the Draft Agent ---
system_prompt_content = """\
You are a helpful assistant for drafting strategy notes for insurance claims.
Your goal is to create a comprehensive draft strategy note based on the provided context,
summary, and Q&A pairs.

You have access to the following tools:
{tool_descriptions}

If you need to use a tool to gather more information or perform an action before drafting the note,
you MUST respond ONLY with a single JSON object with two keys: 'tool_name' and 'tool_args'.
The 'tool_name' must be one of the tool names listed above.
The 'tool_args' must be a JSON object containing the arguments for that tool, matching the schema provided.

Example of a tool call:
{{
  "tool_name": "get_reserve_prediction",
  "tool_args": {{"claim_features": {{"injury_type": "whiplash", "complexity": "low"}}}}
}}

If you have sufficient information from the context, summary, and Q&A, or after receiving tool results,
proceed to draft the strategy note. The strategy note should be well-structured and cover all
relevant aspects of the claim.
"""

# Updated prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(
            content=system_prompt_content.format(
                tool_descriptions=formatted_tool_descriptions
            )
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


# --- Helper function for message serialization ---
def serialise_messages_for_state(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Serialises a list of LangChain BaseMessage objects to a list of dicts for state."""
    serialised_messages = []
    for msg in messages:
        msg_data = {"type": msg.type, "content": msg.content}
        if isinstance(msg, AIMessage) and msg.tool_calls:
            msg_data["tool_calls"] = [
                {
                    "name": tc["name"],
                    "args": tc["args"],
                    "id": tc["id"],
                }
                for tc in msg.tool_calls
            ]
        serialised_messages.append(msg_data)
    return serialised_messages


# --- End Helper function ---


# --- Draft Agent Node ---
async def draft_agent_node(state: DraftAgentState) -> Dict[str, Any]:
    logger.info(f"[DraftAgent] Node called for session: {state.get('session_id')}")
    logger.debug(f"[DraftAgent] Full incoming state: {state}")

    current_messages_serializable = state.get("messages", [])

    # Deserialize messages from state to LangChain BaseMessage objects
    # This is crucial for the LLM chain
    messages: List[BaseMessage] = []
    for msg_data in current_messages_serializable:
        if msg_data.get("type") == "human":
            messages.append(HumanMessage(content=msg_data.get("content", "")))
        elif msg_data.get("type") == "ai":
            # Reconstruct AIMessage, including tool_calls if present
            tool_calls = msg_data.get("tool_calls")
            if tool_calls:  # Ensure tool_calls is not None before passing
                messages.append(
                    AIMessage(
                        content=msg_data.get("content", ""), tool_calls=tool_calls
                    )
                )
            else:
                messages.append(AIMessage(content=msg_data.get("content", "")))
        elif msg_data.get("type") == "tool":
            messages.append(
                ToolMessage(
                    content=msg_data.get("content", ""),
                    tool_call_id=msg_data.get("tool_call_id", ""),
                )
            )
        elif (
            msg_data.get("type") == "system"
        ):  # Should ideally be set once in the graph
            messages.append(SystemMessage(content=msg_data.get("content", "")))
        # Add other types if necessary

    # If messages list is empty or only contains system messages, construct initial context
    # This logic might need refinement based on how the graph is started.
    # The expectation is that the graph starts with some human message/initial context.
    is_first_meaningful_call = not any(
        isinstance(m, (HumanMessage, AIMessage)) for m in messages
    )

    initial_context_parts = []
    if is_first_meaningful_call:
        logger.info(
            "[DraftAgent] First meaningful call or history empty, constructing initial context."
        )
        if state.get("initial_user_request"):
            initial_context_parts.append(
                f"The initial request was: {state.get('initial_user_request')}"
            )

        context_str = state.get("summary", "No summary available.")
        if state.get("text_content_override"):
            context_str = state.get("text_content_override")
        initial_context_parts.append(
            f"Here is the available context/summary:\\\\n{context_str}"
        )

        qa_pairs = state.get("qa_pairs")
        if qa_pairs:
            qa_str = "\\\\n".join(
                [f"Q: {qa['question']}\\\\nA: {qa['answer']}" for qa in qa_pairs]
            )
            initial_context_parts.append(
                f"Here are some relevant Q&A pairs:\\\\n{qa_str}"
            )
        else:
            initial_context_parts.append("No Q&A pairs were generated or provided.")

        initial_context_parts.append(
            "Based on all the above, please draft the strategy note. If you need to use a tool first, please do so."
        )

        # Prepend this initial context as a HumanMessage if not already present
        # This ensures the LLM has the task description
        if not messages or not isinstance(
            messages[0], SystemMessage
        ):  # Avoid adding if system prompt is first
            messages.insert(
                0, HumanMessage(content="\\\\n\\\\n".join(initial_context_parts))
            )
        elif len(messages) > 0 and isinstance(
            messages[0], SystemMessage
        ):  # Insert after system prompt
            messages.insert(
                1, HumanMessage(content="\\\\n\\\\n".join(initial_context_parts))
            )

    logger.debug(f"[DraftAgent] Messages for LLM: {messages}")

    # Invoke the LLM with the prepared messages
    # The prompt is already part of the llm_with_tools chain construction (prompt | llm_with_tools)
    # However, llm_with_tools expects a dict with "messages" key
    # The system prompt is already part of the `prompt` object.

    chain_with_prompt = (
        prompt | llm_with_tools
    )  # This ensures the system prompt is used correctly
    ai_response: AIMessage = await chain_with_prompt.ainvoke({"messages": messages})

    logger.debug(f"[DraftAgent] LLM raw response object: {ai_response}")
    logger.debug(f"[DraftAgent] LLM raw response content: {ai_response.content}")
    if hasattr(ai_response, "tool_calls") and ai_response.tool_calls:
        logger.debug(
            f"[DraftAgent] LLM response tool_calls (native): {ai_response.tool_calls}"
        )

    # Manually parse tool calls from content if not already populated by LangChain/Ollama
    # This is a common workaround for models that output JSON for tools but don't populate tool_calls directly.
    if (
        not ai_response.tool_calls
        and isinstance(ai_response.content, str)
        and ai_response.content.strip()
    ):
        logger.info(
            "[DraftAgent] ai_response.tool_calls is empty, attempting to parse from content."
        )
        parsed_tool_calls = []
        content_str = ai_response.content.strip()

        # Heuristic: Mistral (and other models via Ollama) might wrap JSON in ```json ... ``` or just ``` ... ```
        # or just output raw JSON, possibly with surrounding text.
        if content_str.startswith("```json"):
            content_str = content_str[len("```json") :]
        elif content_str.startswith("```"):
            content_str = content_str[len("```") :]
        if content_str.endswith("```"):
            content_str = content_str[: -len("```")]
        content_str = content_str.strip()

        # Try to find the outermost JSON object or array
        json_start_index = -1
        json_end_index = -1

        if content_str.startswith("{") and content_str.endswith(
            "}"
        ):  # It's likely a single JSON object
            json_start_index = 0
            json_end_index = len(content_str) - 1
        elif content_str.startswith("[") and content_str.endswith(
            "]"
        ):  # It's likely a JSON array (of tool calls)
            json_start_index = 0
            json_end_index = len(content_str) - 1
        else:  # Fallback: find first '{' and last '}'
            json_start_index = content_str.find("{")
            json_end_index = content_str.rfind("}")

        if (
            json_start_index != -1
            and json_end_index != -1
            and json_end_index > json_start_index
        ):
            json_str = content_str[json_start_index : json_end_index + 1]
            logger.debug(f"[DraftAgent] Extracted potential JSON string: {json_str}")
            try:
                tool_call_data = json.loads(json_str)

                # Based on the prompt, we expect a single dict: {"tool_name": "...", "tool_args": {...}}
                if (
                    isinstance(tool_call_data, dict)
                    and "tool_name" in tool_call_data
                    and "tool_args" in tool_call_data
                ):
                    tool_call_id = str(uuid.uuid4())
                    parsed_tool_calls.append(
                        {
                            "name": tool_call_data["tool_name"],
                            "args": tool_call_data["tool_args"],
                            "id": tool_call_id,
                        }
                    )
                    # If the model outputs a list of tool calls, adjust here. For now, single obj.
                elif isinstance(
                    tool_call_data, list
                ):  # Handle if model outputs a list of tool calls
                    for tc_item in tool_call_data:
                        if (
                            isinstance(tc_item, dict)
                            and "tool_name" in tc_item
                            and "tool_args" in tc_item
                        ):
                            tool_call_id = str(uuid.uuid4())
                            parsed_tool_calls.append(
                                {
                                    "name": tc_item["tool_name"],
                                    "args": tc_item["tool_args"],
                                    "id": tool_call_id,
                                }
                            )
                        else:
                            logger.warning(
                                f"[DraftAgent] Item in list is not a valid tool call structure: {tc_item}"
                            )

                if parsed_tool_calls:
                    # ai_response.tool_calls is mutable if it's a Pydantic model field
                    if hasattr(ai_response, "tool_calls"):
                        ai_response.tool_calls = parsed_tool_calls
                        # Also update .additional_kwargs if that's where LangChain might look for it
                        # with OllamaFunctions or similar wrappers. Usually .tool_calls is sufficient.
                        if (
                            not hasattr(ai_response, "additional_kwargs")
                            or ai_response.additional_kwargs is None
                        ):
                            ai_response.additional_kwargs = {}  # Initialize if None
                        ai_response.additional_kwargs["tool_calls"] = (
                            parsed_tool_calls  # Some models/wrappers use this
                        )
                        logger.info(
                            f"[DraftAgent] Manually parsed and assigned tool_calls: {ai_response.tool_calls}"
                        )
                    else:  # Should not happen with AIMessage
                        logger.error(
                            "[DraftAgent] ai_response object does not have tool_calls attribute to assign to."
                        )
                else:
                    logger.info(
                        f"[DraftAgent] Parsed JSON but did not conform to expected tool call structure: {json_str}"
                    )

            except json.JSONDecodeError as e:
                logger.warning(
                    f"[DraftAgent] Could not parse JSON from LLM content fragment \\'{json_str}\\'. Error: {e}. Full content: {ai_response.content}"
                )
            except Exception as e:
                logger.error(
                    f"[DraftAgent] Unexpected error during manual tool call parsing from content \\'{json_str}\\': {e}"
                )
        else:
            logger.info(
                f"[DraftAgent] No clear JSON object/array found in content for tool call parsing: {content_str}"
            )
    elif ai_response.tool_calls:
        logger.info(
            f"[DraftAgent] Tool calls were natively populated: {ai_response.tool_calls}"
        )
    else:
        logger.info(
            "[DraftAgent] No tool_calls natively and no content to parse for manual tool calls."
        )

    # Append the AI's response to our serializable list
    new_ai_message_serializable = {
        "type": "ai",
        "content": str(ai_response.content),
    }  # Ensure content is string
    # Ensure tool_calls are serializable (they should be List[Dict] from Pydantic model)
    if hasattr(ai_response, "tool_calls") and ai_response.tool_calls:
        # Make sure tool_calls are in the correct serializable format if they came from AIMessage.tool_calls
        serializable_tool_calls = []
        for tc in ai_response.tool_calls:
            if isinstance(tc, dict):  # Already a dict (e.g. from manual parsing)
                serializable_tool_calls.append(tc)
            # Add handling if tc is an object that needs to be dict()-ed, though AIMessage.tool_calls should be dicts
            # Example: elif hasattr(tc, 'dict'): serializable_tool_calls.append(tc.dict())
        if serializable_tool_calls:
            new_ai_message_serializable["tool_calls"] = serializable_tool_calls

    updated_messages_serializable = current_messages_serializable + [
        new_ai_message_serializable
    ]
    output_state: Dict[str, Any] = {"messages": updated_messages_serializable}

    # Check ai_response.tool_calls again as it might have been populated by manual parsing
    if (
        hasattr(ai_response, "tool_calls")
        and ai_response.tool_calls
        and len(ai_response.tool_calls) > 0
    ):
        logger.info(
            f"[DraftAgent] LLM requested tool calls (after potential manual parse): {ai_response.tool_calls}"
        )
        output_state["draft_status"] = "ToolCallRequested"
        # The graph's ToolNode will execute these and add ToolMessages
    else:
        logger.info(
            "[DraftAgent] No tool calls from LLM. Treating response as final draft."
        )
        final_draft = ai_response.content
        output_state["draft_strategy_note"] = final_draft
        output_state["draft_status"] = "DraftComplete"  # Or "Drafted" as before

        # Placeholder for saving the draft (e.g., to Minio)
        # This logic should be added here or in a subsequent dedicated node
        session_id = state.get("session_id", "unknown_session")
        document_id = state.get("document_id", "unknown_document")
        try:
            # from backend.services.minio_service import MinioService # Import locally if not top-level
            # minio_service = MinioService()
            # file_name = f"draft_strategy_note_{session_id}_{document_id}.txt"
            # await minio_service.upload_text_to_minio(final_draft, file_name, settings.MINIO_BUCKET_STRATEGY_NOTES)
            logger.info(
                f"Draft strategy note for session {session_id}, doc {document_id} would be saved here."
            )
        except Exception as e:
            logger.error(
                f"Error saving draft strategy note for session {session_id}: {e}"
            )
            # Decide if this error should change the draft_status

    logger.info(
        f"[DraftAgent] Node returning state with draft_status: {output_state.get('draft_status')}"
    )
    return output_state


# Example usage (for local testing if needed, typically run via LangGraph)
# async def main():
#     test_state = AgentState(
#         session_id="test_session_123",
#         initial_user_request="Claim for RTA, whiplash, claimant solicitor is 'Speedy Claims Ltd'.",
#         summary="The claimant, John Doe, was involved in a rear-end collision on 2023-01-15. Reported whiplash injury. Vehicle damage minor. Claimant represented by Speedy Claims Ltd.",
#         qa_pairs=[
#             {"question": "What is the main injury?", "answer": "Whiplash"},
#             {"question": "Who is the claimant's solicitor?", "answer": "Speedy Claims Ltd"}
#         ],
#         document_id="doc123",
#         collection_name="claims_docs",
#         processed_steps=["summarised", "qa_generated"],
#         orchestration_status="Drafting",
#         draft_strategy_note=None, # Ensure this is None or not present initially
#         draft_status=None,
#         # Add other fields as per AgentState definition
#         text_content_override=None,
#         claim_context_summary=None, # Assuming this is covered by 'summary'
#         final_response=None,
#         user_feedback=None,
#         review_needed=False,
#         reviewed_draft=None,
#         negotiation_advice=None, # This will be populated by the tool if called
#         reserve_prediction=None, # This will be populated by the tool if called
#         red_team_critique=None,
#         final_strategy_note=None
#     )
#     result = await draft_agent_node(test_state)
#     print("--- Draft Strategy Note ---")
#     print(result.get("draft_strategy_note"))
#     print("--- Status ---")
#     print(result.get("draft_status"))

# if __name__ == "__main__":
#     asyncio.run(main())
