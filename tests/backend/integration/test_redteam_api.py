import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from typing import Optional

from backend.models import RedTeamPrompt, SourceDocument
from backend.core.config import get_settings

settings = get_settings()

import backend.services.redteam_service  # Import for singleton reset and patch.object

# Test Data - Mocked Prompts as Python objects
MOCK_PROMPTS_LIST = [
    RedTeamPrompt(
        id="RT001",
        category="Instruction Override",
        text="Test prompt 1",
        expected_behavior="Behave normally",
    ),
    RedTeamPrompt(
        id="RT002",
        category="Role Play",
        text="Test prompt 2",
        expected_behavior="Also behave normally",
    ),
]


@pytest.fixture
def mock_rag_service_for_redteam(monkeypatch):
    mock_rag = AsyncMock()

    async def mock_query_rag(
        query: str,
        current_document_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        if "fail_rag" in query:
            raise HTTPException(status_code=500, detail="RAG service error simulation")
        return (
            "Mocked RAG answer for: " + query,
            [SourceDocument(chunk_content="mock source", document_id="s1")],
            0.9,
            1,
        )

    mock_rag.query_rag = AsyncMock(side_effect=mock_query_rag)
    monkeypatch.setattr(
        "backend.services.redteam_service.get_rag_service", lambda: mock_rag
    )
    return mock_rag


@pytest.mark.integration
@pytest.mark.api
async def test_run_red_team_success(client: AsyncClient, mock_rag_service_for_redteam):
    backend.services.redteam_service._redteam_service_instance = (
        None  # Reset singleton before test
    )
    try:
        mock_rag_responses = {
            "Test prompt 1": (
                "Mocked RAG answer for prompt 1",
                [
                    SourceDocument(
                        document_id="s1",
                        chunk_id="c1",
                        chunk_content="src1",
                        file_name="f1.txt",
                    )
                ],  # metadata is optional
                4.5,
            ),
            "Test prompt 2": ("Mocked RAG answer for prompt 2", [], 3.0),
        }

        with patch(
            "backend.services.redteam_service.RedTeamService._load_prompts",
            return_value=MOCK_PROMPTS_LIST,
        ) as mock_load_prompts, patch(
            "backend.services.rag_service.RAGService.query_rag", new_callable=AsyncMock
        ) as mock_query_rag:

            async def side_effect_query_rag(query: str, *args, **kwargs):
                # Return 4 values now, adding a dummy for self_heal_attempts
                rag_answer, sources, confidence = mock_rag_responses.get(
                    query, ("Default mock answer", [], 2.0)
                )
                return (
                    rag_answer,
                    sources,
                    confidence,
                    0,
                )  # Added 0 for self_heal_attempts

            mock_query_rag.side_effect = side_effect_query_rag

            response = await client.post("/api/v1/redteam/run")

            assert response.status_code == 200
            result_data = response.json()
            assert "results" in result_data
            assert "summary_stats" in result_data

            assert len(result_data["results"]) == len(MOCK_PROMPTS_LIST)
            assert result_data["summary_stats"]["prompts_run"] == len(MOCK_PROMPTS_LIST)
            assert result_data["summary_stats"]["successful_executions"] == len(
                MOCK_PROMPTS_LIST
            )

            assert mock_query_rag.call_count == len(MOCK_PROMPTS_LIST)
            # Verify that each prompt text was actually queried
            called_queries = {call.args[0] for call in mock_query_rag.call_args_list}
            for p_data in MOCK_PROMPTS_LIST:
                assert (
                    p_data.text in called_queries
                ), f"Prompt text '{p_data.text}' not found in called queries: {called_queries}"

            attempt1 = next(
                att for att in result_data["results"] if att["prompt_id"] == "RT001"
            )
            assert attempt1["response_text"] == "Mocked RAG answer for prompt 1"
            assert attempt1["rag_confidence"] == 4.5
            assert len(attempt1["rag_sources"]) == 1
            assert attempt1["rag_sources"][0]["document_id"] == "s1"
            assert attempt1["rag_sources"][0]["chunk_content"] == "src1"
    finally:
        backend.services.redteam_service._redteam_service_instance = (
            None  # Ensure cleanup
        )


@pytest.mark.asyncio
@pytest.mark.api
async def test_run_red_team_no_prompts_loaded(client: AsyncClient):
    backend.services.redteam_service._redteam_service_instance = None  # Reset singleton
    try:
        with patch(
            "backend.services.redteam_service.RedTeamService._load_prompts",
            return_value=[],
        ) as mock_load_prompts:
            response = await client.get(f"{settings.API_V1_STR}/redteam/run")

            assert response.status_code == 200
            result_data = response.json()
            assert len(result_data["results"]) == 0
            assert result_data["summary_stats"]["prompts_run"] == 0
            assert "No prompts were loaded." in result_data["summary_stats"].get(
                "notes", ""
            )
    finally:
        backend.services.redteam_service._redteam_service_instance = (
            None  # Ensure cleanup
        )


@pytest.mark.asyncio
@pytest.mark.api
async def test_run_red_team_rag_service_error(client: AsyncClient):
    backend.services.redteam_service._redteam_service_instance = None  # Reset singleton
    try:
        with patch(
            "backend.services.redteam_service.RedTeamService._load_prompts",
            return_value=[MOCK_PROMPTS_LIST[0]],
        ) as mock_load_prompts, patch(
            "backend.services.rag_service.RAGService.query_rag",
            new_callable=AsyncMock,
            side_effect=Exception("RAG service blew up"),
        ) as mock_query_rag:
            response = await client.get(f"{settings.API_V1_STR}/redteam/run")

            assert response.status_code == 200
            result_data = response.json()
            assert len(result_data["results"]) == 1
            attempt = result_data["results"][0]
            assert attempt["prompt_id"] == MOCK_PROMPTS_LIST[0].id
            assert "Error during RAG execution." in attempt["response_text"]
            assert (
                "Failed to get response from RAG system: RAG service blew up"
                in attempt["evaluation_notes"]
            )
            assert result_data["summary_stats"]["prompts_run"] == 1
            assert result_data["summary_stats"]["successful_executions"] == 0
            assert result_data["summary_stats"]["failed_executions"] == 1
    finally:
        backend.services.redteam_service._redteam_service_instance = (
            None  # Ensure cleanup
        )


@pytest.mark.asyncio
@pytest.mark.api
async def test_run_red_team_prompts_file_init_error(client: AsyncClient):
    original_init = backend.services.redteam_service.RedTeamService.__init__

    def faulty_init_for_test(*args, **kwargs):
        raise HTTPException(
            status_code=500,
            detail="Test: Critical failure loading prompts file in __init__",
        )

    backend.services.redteam_service._redteam_service_instance = None

    with patch.object(
        backend.services.redteam_service.RedTeamService,
        "__init__",
        side_effect=faulty_init_for_test,
    ) as mock_init:
        try:
            response = await client.get(f"{settings.API_V1_STR}/redteam/run")
            assert response.status_code == 500
            assert (
                "Test: Critical failure loading prompts file in __init__"
                in response.json()["detail"]
            )
            assert mock_init.called
        finally:
            backend.services.redteam_service.RedTeamService.__init__ = original_init
            backend.services.redteam_service._redteam_service_instance = None
