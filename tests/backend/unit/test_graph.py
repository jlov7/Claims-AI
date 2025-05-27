import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch
import json

from langgraph.graph import StateGraph, END

from backend.core.graph import (
    AgentState,  # This is the main AgentState for the graph being tested
    increment_qa_retry_node,
    error_guard,
    qa_router_with_error_check,
)
from backend.models import SourceDocument

DEFAULT_SESSION_ID = "test_session_001"
DEFAULT_DOCUMENT_ID = "test_doc.pdf"
DEFAULT_QUERY = "What is the meaning of life?"


# get_initial_state uses the main AgentState for the graph
def get_initial_state(
    session_id: str = DEFAULT_SESSION_ID,
    document_id: Optional[str] = DEFAULT_DOCUMENT_ID,
    initial_user_request: Optional[str] = "Test request",
    query: Optional[str] = DEFAULT_QUERY,
    text_content_override: Optional[str] = None,
    collection_name: Optional[str] = None,
    summary: Optional[str] = None,
    answer: Optional[str] = None,
    sources: Optional[List[SourceDocument]] = None,
    confidence_score: Optional[int] = None,
    draft_strategy_note_result: Optional[Dict[str, Any]] = None,
    kafka_publish_status: Optional[str] = None,
    agent_error: Optional[str] = None,
    kafka_error_message: Optional[str] = None,
) -> AgentState:
    return AgentState(
        session_id=session_id,
        initial_user_request=initial_user_request,
        document_id=document_id,
        collection_name=collection_name,
        text_content_override=text_content_override,
        processed_steps=[],
        orchestration_status=None,
        summary=summary,
        query=query,
        answer=answer,
        sources=sources,
        confidence_score=confidence_score,
        rag_self_heal_attempts=0,
        qa_retry_attempts=0,
        key_document_ids=None,
        qa_history_str=None,
        user_criteria=None,
        output_filename=None,
        draft_strategy_note_result=draft_strategy_note_result,
        kafka_payload=None,
        kafka_publish_status=kafka_publish_status,
        agent_error=agent_error,
        last_agent_activity=None,
        kafka_error_message=kafka_error_message,
    )


@pytest.mark.asyncio
class TestLangGraphFlow:
    @pytest.fixture(autouse=True)
    def mock_agent_nodes_and_compile_graph(self, mocker):
        # Base behavior for mocked nodes
        async def base_mock_node_behavior(
            state: AgentState, node_name_for_log: str
        ) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append(f"{node_name_for_log}: mocked_execution")
            if node_name_for_log == "qa":
                state["confidence_score"] = state.get("confidence_score", 4)
            return state

        # Specific async side_effect functions for each mock object
        async def orchestrator_se_func(state: AgentState):
            return await base_mock_node_behavior(state, "orchestrator")

        async def summarise_se_func(state: AgentState):
            return await base_mock_node_behavior(state, "summarise")

        async def qa_se_func(state: AgentState):
            return await base_mock_node_behavior(state, "qa")

        async def draft_se_func(state: AgentState):
            return await base_mock_node_behavior(state, "draft")

        async def kafka_se_func(state: AgentState):
            return await base_mock_node_behavior(state, "publish_to_kafka")

        # AsyncMock objects that tests can manipulate
        self.mock_orchestrator_obj = AsyncMock(side_effect=orchestrator_se_func)
        self.mock_summarise_obj = AsyncMock(side_effect=summarise_se_func)
        self.mock_qa_obj = AsyncMock(side_effect=qa_se_func)
        self.mock_draft_obj = AsyncMock(side_effect=draft_se_func)
        self.mock_kafka_obj = AsyncMock(side_effect=kafka_se_func)

        # Wrapper functions for LangGraph nodes that await the AsyncMock objects
        async def orchestrator_node(state: AgentState) -> AgentState:
            return await self.mock_orchestrator_obj(state)

        async def summarise_node(state: AgentState) -> AgentState:
            return await self.mock_summarise_obj(state)

        async def qa_node(state: AgentState) -> AgentState:
            return await self.mock_qa_obj(state)

        async def draft_node(state: AgentState) -> AgentState:
            return await self.mock_draft_obj(state)

        async def kafka_node(state: AgentState) -> AgentState:
            return await self.mock_kafka_obj(state)

        self.real_increment_qa_retry_node = increment_qa_retry_node

        test_workflow = StateGraph(AgentState)  # Using the main AgentState
        test_workflow.add_node("orchestrator", orchestrator_node)
        test_workflow.add_node("summarise", summarise_node)
        test_workflow.add_node("qa", qa_node)
        test_workflow.add_node("draft", draft_node)
        test_workflow.add_node("publish_to_kafka", kafka_node)
        test_workflow.add_node("increment_qa_retry", self.real_increment_qa_retry_node)

        test_workflow.set_entry_point("orchestrator")
        test_workflow.add_edge("orchestrator", "summarise")

        # Add error guard for summarise node (mirroring backend/core/graph.py)
        test_workflow.add_conditional_edges(
            "summarise",
            lambda state: "error_occurred" if error_guard(state) else "proceed_to_qa",
            {"error_occurred": END, "proceed_to_qa": "qa"},
        )

        # Add error guard and retry logic for qa node (mirroring backend/core/graph.py)
        # Note: qa_router_with_error_check itself calls should_retry_qa if no error
        test_workflow.add_conditional_edges(
            "qa",
            qa_router_with_error_check,  # This includes the error guard
            {
                "error_occurred": END,
                "retry_qa": "increment_qa_retry",
                "proceed_to_draft": "draft",
            },
        )
        test_workflow.add_edge("increment_qa_retry", "qa")

        # Assuming draft and publish_to_kafka do not have intermediate error guards for this test setup
        # or their error handling is implicit (e.g. an exception would halt the graph)
        # The user's fix focused on summarise and qa error guards.
        # The original test_graph.py also had: test_workflow.add_edge("summarise", "qa") which is now replaced.
        # And the original: test_workflow.add_conditional_edges("qa", should_retry_qa, ...)

        test_workflow.add_edge(
            "draft", "publish_to_kafka"
        )  # This can remain if no error guard for draft
        test_workflow.add_edge("publish_to_kafka", END)

        self.compiled_graph_app_for_test = test_workflow.compile()
        yield

    async def test_straight_through_success_flow(self):
        initial_state = get_initial_state()

        async def qa_success_behavior(state: AgentState) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append("qa: mocked_execution_success")
            state["answer"] = "This is a good answer."
            state["confidence_score"] = 4
            state["sources"] = [
                SourceDocument(
                    document_id="doc1",
                    chunk_content="content1",
                    page_number=1,
                    score=0.9,
                )
            ]
            return state

        self.mock_qa_obj.side_effect = qa_success_behavior

        async def draft_success_behavior(state: AgentState) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append("draft: mocked_execution_success")
            state["draft_strategy_note_result"] = {
                "file_path": "/path/to/draft.docx",
                "file_name": "draft.docx",
            }
            return state

        self.mock_draft_obj.side_effect = draft_success_behavior

        async def kafka_success_behavior(state: AgentState) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append(
                "publish_to_kafka: mocked_execution_success"
            )
            state["kafka_publish_status"] = "Success"
            return state

        self.mock_kafka_obj.side_effect = kafka_success_behavior

        config = {"recursion_limit": 10}
        final_state = await self.compiled_graph_app_for_test.ainvoke(
            initial_state, config=config
        )
        assert "orchestrator: mocked_execution" in final_state["processed_steps"]
        assert "summarise: mocked_execution" in final_state["processed_steps"]
        assert "qa: mocked_execution_success" in final_state["processed_steps"]
        assert "draft: mocked_execution_success" in final_state["processed_steps"]
        assert (
            "publish_to_kafka: mocked_execution_success"
            in final_state["processed_steps"]
        )
        assert final_state["kafka_publish_status"] == "Success"
        assert final_state["answer"] == "This is a good answer."
        assert final_state["draft_strategy_note_result"]["file_name"] == "draft.docx"
        assert final_state["qa_retry_attempts"] == 0

    async def test_qa_retry_once_then_success(self):
        initial_state = get_initial_state()
        qa_call_count = 0

        async def qa_retry_behavior(state: AgentState) -> AgentState:
            nonlocal qa_call_count
            qa_call_count += 1
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append(
                f"qa: mocked_execution_attempt_{qa_call_count}"
            )
            if qa_call_count == 1:
                state["answer"] = "Uncertain answer."
                state["confidence_score"] = 1
                state["sources"] = []
                state["kafka_error_message"] = None
                state["agent_error"] = None
            else:
                state["answer"] = "Confident answer after retry."
                state["confidence_score"] = 4
                state["sources"] = [
                    SourceDocument(
                        document_id="doc1",
                        chunk_content="content1",
                        page_number=1,
                        score=0.9,
                    )
                ]
            return state

        self.mock_qa_obj.side_effect = qa_retry_behavior
        config = {"recursion_limit": 10}
        final_state = await self.compiled_graph_app_for_test.ainvoke(
            initial_state, config=config
        )
        assert "qa: mocked_execution_attempt_1" in final_state["processed_steps"]
        assert (
            "increment_qa_retry_node: Attempts now 1" in final_state["processed_steps"]
        )
        assert "qa: mocked_execution_attempt_2" in final_state["processed_steps"]
        assert final_state["answer"] == "Confident answer after retry."
        assert final_state["confidence_score"] == 4
        assert final_state["qa_retry_attempts"] == 1
        assert "draft: mocked_execution" in final_state["processed_steps"]
        assert "publish_to_kafka: mocked_execution" in final_state["processed_steps"]

    async def test_orchestrator_blocks_on_missing_input(self):
        initial_state_no_session = get_initial_state(session_id=None)

        async def orchestrator_specific_error_behavior(state: AgentState) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append("orchestrator: attempt_execution")
            if not state.get("session_id"):
                state["agent_error"] = "OrchestratorError: session_id is missing"
                state["orchestration_status"] = "Failed_Precondition"
            else:
                state["processed_steps"].append(
                    "orchestrator: mocked_execution_success"
                )
            return state

        self.mock_orchestrator_obj.side_effect = orchestrator_specific_error_behavior

        async def non_overwriting_passthrough(
            state: AgentState, node_name: str
        ) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append(
                f"{node_name}: mocked_passthrough_after_orchestrator_error"
            )
            return state

        # Assign async side_effect functions
        async def summarise_nop_se(state: AgentState):
            return await non_overwriting_passthrough(state, "summarise")

        async def qa_nop_se(state: AgentState):
            return await non_overwriting_passthrough(state, "qa")

        async def draft_nop_se(state: AgentState):
            return await non_overwriting_passthrough(state, "draft")

        async def kafka_nop_se(state: AgentState):
            return await non_overwriting_passthrough(state, "publish_to_kafka")

        self.mock_summarise_obj.side_effect = summarise_nop_se
        self.mock_qa_obj.side_effect = qa_nop_se
        self.mock_draft_obj.side_effect = draft_nop_se
        self.mock_kafka_obj.side_effect = kafka_nop_se

        config = {"recursion_limit": 10}
        final_state = await self.compiled_graph_app_for_test.ainvoke(
            initial_state_no_session, config=config
        )
        assert "orchestrator: attempt_execution" in final_state["processed_steps"]
        assert (
            final_state.get("agent_error") == "OrchestratorError: session_id is missing"
        )
        assert (
            "summarise: mocked_passthrough_after_orchestrator_error"
            in final_state["processed_steps"]
        )

    async def test_node_error_handling(self):
        initial_state = get_initial_state()

        async def summarise_error_behavior(state: AgentState) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append("summarise: mocked_error_execution")
            state["agent_error"] = "SummariseAgentError: Could not process document"
            return state

        self.mock_summarise_obj.side_effect = summarise_error_behavior

        async def passthrough_after_error(
            state: AgentState, node_name: str
        ) -> AgentState:
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            if not state.get("agent_error"):
                state["agent_error"] = (
                    f"{node_name} called after summarise error, this shouldn't happen if error halts processing at summarise."
                )
            state["processed_steps"].append(
                f"{node_name}: mocked_execution_after_summarise_error"
            )
            return state

        async def qa_passthrough_se(state: AgentState):
            return await passthrough_after_error(state, "qa")

        self.mock_qa_obj.side_effect = qa_passthrough_se

        config = {"recursion_limit": 10}
        final_state = await self.compiled_graph_app_for_test.ainvoke(
            initial_state, config=config
        )
        assert "summarise: mocked_error_execution" in final_state["processed_steps"]
        assert (
            final_state.get("agent_error")
            == "SummariseAgentError: Could not process document"
        )
        assert (
            "qa: mocked_execution_after_summarise_error"
            not in final_state["processed_steps"]
        )
        assert "draft: mocked_execution" not in final_state["processed_steps"]
        assert (
            "publish_to_kafka: mocked_execution" not in final_state["processed_steps"]
        )

    # Test for when QA returns low confidence twice, then Kafka fails
    async def test_qa_retry_kafka_fails(self):
        initial_state = get_initial_state()
        qa_call_count = 0

        async def qa_retry_behavior(state: AgentState) -> AgentState:
            nonlocal qa_call_count
            qa_call_count += 1
            if "processed_steps" not in state or state["processed_steps"] is None:
                state["processed_steps"] = []
            state["processed_steps"].append(
                f"qa: mocked_execution_attempt_{qa_call_count}"
            )
            if qa_call_count == 1:
                state["answer"] = "Uncertain answer."
                state["confidence_score"] = 1
                state["sources"] = []
                state["kafka_error_message"] = None
                state["agent_error"] = None
            else:
                state["answer"] = "Confident answer after retry."
                state["confidence_score"] = 4
                state["sources"] = [
                    SourceDocument(
                        document_id="doc1",
                        chunk_content="content1",
                        page_number=1,
                        score=0.9,
                    )
                ]
            return state

        self.mock_qa_obj.side_effect = qa_retry_behavior
        config = {"recursion_limit": 10}
        final_state = await self.compiled_graph_app_for_test.ainvoke(
            initial_state, config=config
        )
        assert "qa: mocked_execution_attempt_1" in final_state["processed_steps"]
        assert (
            "increment_qa_retry_node: Attempts now 1" in final_state["processed_steps"]
        )
        assert "qa: mocked_execution_attempt_2" in final_state["processed_steps"]
        assert final_state["answer"] == "Confident answer after retry."
        assert final_state["confidence_score"] == 4
        assert final_state["qa_retry_attempts"] == 1
        assert "draft: mocked_execution" in final_state["processed_steps"]
        assert "publish_to_kafka: mocked_execution" in final_state["processed_steps"]

    async def test_kafka_payload_fields(self):
        """
        Test that the Kafka payload includes all required fields when the workflow completes.
        """
        # Prepare a state with all relevant fields
        initial_state = get_initial_state(
            summary="Summary text",
            answer="Final answer",
            draft_strategy_note_result={
                "file_path": "/path/to/draft.docx",
                "file_name": "draft.docx",
            },
        )
        # Add extra fields to state
        initial_state["draft_strategy_note"] = "This is the actual draft content."
        initial_state["negotiation_coach_advice"] = "Negotiate assertively."
        initial_state["reserve_prediction"] = 12345.67
        initial_state["user_criteria"] = "Conservative approach"
        initial_state["qa_history_str"] = "Q: What? A: That."

        # Patch the Kafka producer to capture the payload
        with patch(
            "backend.core.graph.AIOKafkaProducer", autospec=True
        ) as mock_producer_cls:
            mock_producer = AsyncMock()
            mock_producer_cls.return_value = mock_producer
            # Simulate send_and_wait as a coroutine
            mock_producer.send_and_wait = AsyncMock()
            # Import the real publish_to_kafka_node
            from backend.core.graph import publish_to_kafka_node

            # Run the node
            result_state = await publish_to_kafka_node(initial_state)
            # Check that send_and_wait was called
            assert (
                mock_producer.send_and_wait.called
            ), "Kafka send_and_wait was not called!"
            # Get the payload sent
            args, kwargs = mock_producer.send_and_wait.call_args
            topic = args[0]
            message_bytes = args[1]
            assert topic == "claim-facts"
            payload = json.loads(message_bytes.decode("utf-8"))
            # Check all required fields
            assert payload["draft_strategy_note"] == "This is the actual draft content."
            assert payload["reserve_prediction"] == 12345.67
            assert payload["negotiation_coach_advice"] == "Negotiate assertively."
            assert payload["user_criteria"] == "Conservative approach"
            assert payload["qa_history_str"] == "Q: What? A: That."
            assert payload["draft_file_path"] == "/path/to/draft.docx"
            assert payload["summary"] == "Summary text"
            assert payload["final_answer"] == "Final answer"
            # Optionally check for other fields
            assert payload["session_id"] == initial_state["session_id"]
            assert payload["document_id"] == initial_state["document_id"]
