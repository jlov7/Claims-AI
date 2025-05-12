import pytest
from backend.models import SourceDocument
from httpx import AsyncClient

# client fixture is from conftest.py


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_endpoint_success_high_confidence(client: AsyncClient, mocker):
    # Mock RAGService.query_rag to simulate a final high confidence score
    mock_answer = "This is a confident test answer."
    mock_sources = [
        SourceDocument(
            document_id="doc1",
            chunk_id="c1",
            chunk_content="Content1",
            filename="file1.txt",
            score=0.9,
        )
    ]
    mock_final_confidence = (
        5  # Simulate a high confidence score after any internal logic
    )

    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources, mock_final_confidence, 0),
    )

    response = await client.post("/api/v1/ask", json={"query": "A good query?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == mock_answer
    assert len(data["sources"]) == 1
    assert data["confidence_score"] == mock_final_confidence
    assert 1 <= data["confidence_score"] <= 5


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_endpoint_success_low_confidence(client: AsyncClient, mocker):
    # Mock RAGService.query_rag to simulate a final low confidence score
    mock_answer = "This is a low confidence test answer, perhaps after failed healing."
    mock_sources = [
        SourceDocument(
            document_id="doc2",
            chunk_id="c2",
            chunk_content="Content2",
            filename="file2.txt",
            score=0.7,
        )
    ]
    mock_final_confidence = 2  # Simulate a low confidence score

    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources, mock_final_confidence, 0),
    )

    response = await client.post("/api/v1/ask", json={"query": "A tricky query?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == mock_answer
    assert len(data["sources"]) == 1
    assert data["confidence_score"] == mock_final_confidence
    assert 1 <= data["confidence_score"] <= 5


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_endpoint_empty_query_service_handled(client: AsyncClient, mocker):
    """Test the /api/v1/ask endpoint with an empty query string."""
    # Service's query_rag now handles empty query directly and returns a default confidence
    # The router also has a check, but this tests the service-level handling via mocking.
    mock_answer = "Please provide a query."
    mock_sources = []
    mock_confidence = 3  # Default confidence for empty query from service
    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        return_value=(mock_answer, mock_sources, mock_confidence, 0),
    )

    response = await client.post("/api/v1/ask", json={"query": ""})
    # The router's HTTPException for empty query might fire first if not carefully mocked.
    # For this test, we assume the request passes the router's initial validation (e.g. by mocking it or ensuring query_rag is called)
    # However, the current router logic raises HTTPException for empty string *before* calling the service.
    # So this test as written will hit the router's 400, not the service's direct return.
    # To properly test the service's handling, one would call the service method directly in a unit test.
    # For this integration test, we'll test the router's behavior.
    # Let's adjust this test to reflect the router's immediate handling of empty string.
    # No mocking needed if we test the router's direct validation.

    # Re-evaluating test: The router /api/v1/ask has:
    # if not request.query or not request.query.strip():
    #     raise HTTPException(status_code=400, detail="Query cannot be empty.")
    # So, this will return 400, not 200 with the service's default.

    response_empty_query = await client.post("/api/v1/ask", json={"query": ""})
    assert response_empty_query.status_code == 400
    assert response_empty_query.json()["detail"] == "Query cannot be empty."

    response_whitespace_query = await client.post("/api/v1/ask", json={"query": "   "})
    assert response_whitespace_query.status_code == 400
    assert response_whitespace_query.json()["detail"] == "Query cannot be empty."


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_endpoint_missing_query_field(client: AsyncClient):
    """Test sending a request without the 'query' field."""
    response = await client.post("/api/v1/ask", json={})
    assert response.status_code == 422  # Unprocessable Entity for missing field
    # Detail structure can vary, check for presence of "query" in error
    error_detail = response.json()["detail"]
    found_query_error = False
    for err in error_detail:
        if err["type"] == "missing" and "query" in err["loc"]:
            found_query_error = True
            break
    assert found_query_error


@pytest.mark.api
@pytest.mark.integration
@pytest.mark.asyncio
async def test_ask_endpoint_internal_service_error(client: AsyncClient, mocker):
    mocker.patch(
        "backend.services.rag_service.RAGService.query_rag",
        side_effect=Exception("Major service malfunction"),
    )

    response = await client.post(
        "/api/v1/ask", json={"query": "Query causing internal error"}
    )
    assert response.status_code == 500
    data = response.json()
    assert "An internal error occurred" in data["detail"]
    # The confidence score is not applicable here as the request fails before normal response generation.


# Note: Testing the "hybrid search" (keyword aspect) deterministically is hard without:
# 1. Highly controlled data in ChromaDB where specific keywords guarantee document retrieval.
# 2. Mocking ChromaDB calls to verify the `where_document` filter is constructed correctly.
# For this integration test, we rely on the fact that the filter is added and hope
# that general queries will implicitly test its presence, though not its specific impact.
