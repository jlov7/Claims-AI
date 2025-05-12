import pytest
from fastapi.testclient import TestClient

from backend.main import app  # Assuming your FastAPI app instance is named 'app'


# Fixture to provide a TestClient instance (can be in conftest.py or here if specific)
# Using the one from conftest.py if available, otherwise define locally for clarity
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.api
def test_find_nearest_precedents_success(client: TestClient):
    """Test successful retrieval of precedents."""
    # Use a summary that is likely to match one of the synthetic precedents
    # e.g., related to "rear-end collision" or "water damage"
    query_summary = "Claim involving a minor car accident with whiplash."
    payload_content = {"claim_summary": query_summary, "top_k": 3}
    # Wrap payload content under 'query_request' key due to FastAPI behavior
    payload = {"query_request": payload_content}

    response = client.post("/api/v1/precedents", json=payload)

    if response.status_code != 200:
        print("test_find_nearest_precedents_success FAILED! Response content:")
        try:
            print(response.json())
        except Exception as e:
            print(f"Could not parse JSON response: {e}")
            print(f"Raw response text: {response.text}")

    assert response.status_code == 200
    response_data = response.json()
    assert "precedents" in response_data

    retrieved_precedents = response_data["precedents"]
    assert isinstance(retrieved_precedents, list)
    assert len(retrieved_precedents) <= 3  # Should be at most top_k

    if retrieved_precedents:  # If any precedents are returned
        for item in retrieved_precedents:
            assert "claim_id" in item
            assert "summary" in item
            # outcome and keywords are optional in model but should be present from our CSV data
            assert "outcome" in item
            assert "keywords" in item
            assert "distance" in item
            assert isinstance(item["distance"], float)  # Chroma distances are floats
            # Check if the summary of a known precedent is found
            if "PREC001" in item["claim_id"]:
                assert "rear-end collision" in item["summary"].lower()


@pytest.mark.api
def test_find_nearest_precedents_empty_summary(client: TestClient):
    """Test request with an empty claim summary."""
    payload_content = {"claim_summary": "   ", "top_k": 3}
    payload = {"query_request": payload_content}
    response = client.post("/api/v1/precedents", json=payload)
    assert response.status_code == 422  # Expecting Pydantic validation error
    data = response.json()
    assert "detail" in data
    # Check for specific Pydantic error structure
    assert any(
        err["type"] == "string_too_short"
        and err["loc"] == ["body", "query_request", "claim_summary"]
        for err in data["detail"]
    )


@pytest.mark.api
def test_find_nearest_precedents_invalid_top_k(client: TestClient):
    """Test with top_k out of bounds (e.g., 0 or too high)."""
    # Test top_k < 1
    payload_min_content = {"claim_summary": "Valid summary", "top_k": 0}
    payload_min = {"query_request": payload_min_content}
    response_min = client.post("/api/v1/precedents", json=payload_min)
    assert response_min.status_code == 422  # Pydantic validation error for ge=1

    # Test top_k > 20
    payload_max_content = {"claim_summary": "Valid summary", "top_k": 21}
    payload_max = {"query_request": payload_max_content}
    response_max = client.post("/api/v1/precedents", json=payload_max)
    assert response_max.status_code == 422  # Pydantic validation error for le=20


@pytest.mark.api
def test_find_nearest_precedents_no_matching(client: TestClient):
    """Test with a summary very unlikely to match any precedents."""
    query_summary = "Extremely obscure query about cosmic ray interference with pigeon navigation systems."
    payload_content = {"claim_summary": query_summary, "top_k": 5}
    payload = {"query_request": payload_content}

    response = client.post("/api/v1/precedents", json=payload)
    assert response.status_code == 200
    response_data = response.json()
    assert "precedents" in response_data
    assert isinstance(response_data["precedents"], list)
    # It's possible it might still find *some* precedent if embeddings are very abstract
    # but for highly dissimilar queries, it might return fewer than top_k, or an empty list.
    # For this test, we primarily care it doesn't error out and returns a valid structure.
    if not response_data["precedents"]:
        assert len(response_data["precedents"]) == 0
    else:
        assert len(response_data["precedents"]) <= 5
