import pytest
from backend.models import SourceDocument
from httpx import AsyncClient
from pydantic import BaseModel

# client fixture is from conftest.py


# V1 Models for expected response structure from LangServe (matching langserve_app/app.py)
# These represent the structure of the JSON output from the /langserve/query/invoke endpoint.
class V1SourceDocument(BaseModel):
    document_id: str
    chunk_id: str
    file_name: str
    chunk_content: str
    score: float | None = None


class V1RAGQueryResponse(BaseModel):
    answer: str
    sources: list[V1SourceDocument]
    confidence_score: int | None = None
    self_heal_attempts: int | None = 0


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_invoke_success_high_confidence(client: AsyncClient, mocker):
    mock_answer = "This is a confident test answer."
    # Service returns V2 SourceDocument, ensure test mock aligns or adapt assertion
    mock_sources_v2 = [
        SourceDocument(
            document_id="doc1",
            chunk_id="c1",
            chunk_content="Content1",
            filename="file1.txt",
            score=0.9,
        )
    ]
    mock_final_confidence = 5

    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources_v2, mock_final_confidence, 0),
    )

    response = await client.post(
        "/langserve/query/invoke", json={"input": {"query": "A good query?"}}
    )
    assert response.status_code == 200
    data = response.json()
    assert "output" in data
    output = data["output"]
    assert output["answer"] == mock_answer
    assert len(output["sources"]) == 1
    assert output["sources"][0]["document_id"] == "doc1"
    assert output["confidence_score"] == mock_final_confidence


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_invoke_success_low_confidence(client: AsyncClient, mocker):
    mock_answer = "This is a low confidence test answer."
    mock_sources_v2 = [
        SourceDocument(
            document_id="doc2",
            chunk_id="c2",
            chunk_content="Content2",
            filename="file2.txt",
            score=0.7,
        )
    ]
    mock_final_confidence = 2

    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources_v2, mock_final_confidence, 0),
    )

    response = await client.post(
        "/langserve/query/invoke", json={"input": {"query": "A tricky query?"}}
    )
    assert response.status_code == 200
    data = response.json()
    assert "output" in data
    output = data["output"]
    assert output["answer"] == mock_answer
    assert len(output["sources"]) == 1
    assert output["confidence_score"] == mock_final_confidence


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_invoke_empty_query(client: AsyncClient, mocker):
    # RAGQueryLangServeRequest (V1) has query: str, so an empty string is valid for the model.
    # The underlying service or logic in rag_query_logic should handle it.
    mock_answer = "Please provide a valid query."
    mock_sources_v2 = []
    mock_final_confidence = 1  # Example, service might define this

    # Mock what the service returns for an empty query
    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources_v2, mock_final_confidence, 0),
    )

    response_empty_query = await client.post(
        "/langserve/query/invoke", json={"input": {"query": ""}}
    )
    # Behavior depends on how rag_query_logic and RAGService handle empty string
    # Assuming it now processes and returns a specific response rather than HTTP 400 from router
    assert response_empty_query.status_code == 200
    data_empty = response_empty_query.json()["output"]
    assert data_empty["answer"] == mock_answer
    # Or if it raises an HTTPException(400) from within rag_query_logic:
    # assert response_empty_query.status_code == 400
    # assert "Query cannot be empty" in response_empty_query.json()["detail"]

    response_whitespace_query = await client.post(
        "/langserve/query/invoke", json={"input": {"query": "   "}}
    )
    assert response_whitespace_query.status_code == 200  # Similar assumption
    data_whitespace = response_whitespace_query.json()["output"]
    assert data_whitespace["answer"] == mock_answer


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_invoke_missing_query_field(client: AsyncClient):
    response = await client.post(
        "/langserve/query/invoke", json={"input": {}}
    )  # Missing 'query'
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    # LangServe's V1 Pydantic validation error structure for FastAPI might differ
    # It usually returns a list of errors. Example: err["msg"] == "field required", err["loc"] includes "query"
    assert isinstance(error_detail, list)
    found_query_error = False
    for err in error_detail:
        if err.get("type") == "value_error.missing" and "query" in err.get("loc", []):
            found_query_error = True
            break
    # Fallback for older Pydantic v1 style or different error shape
    if not found_query_error:
        for err in error_detail:
            if (
                "query" in err.get("loc", [])
                and "field required" in err.get("msg", "").lower()
            ):
                found_query_error = True
                break
    assert (
        found_query_error
    ), f"Query field missing error not found in detail: {error_detail}"


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_invoke_internal_service_error(client: AsyncClient, mocker):
    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        side_effect=Exception("Major service malfunction"),
    )

    response = await client.post(
        "/langserve/query/invoke",
        json={"input": {"query": "Query causing internal error"}},
    )
    # LangServe wraps exceptions. It might return 500 with a generic FastAPI error,
    # or a specific structure if the error is caught and re-raised as HTTPException in the runnable logic.
    # The rag_query_logic in app.py catches Exception and raises HTTPException(500, detail=str(e))
    assert response.status_code == 500
    data = response.json()
    assert "Major service malfunction" in data["detail"]
