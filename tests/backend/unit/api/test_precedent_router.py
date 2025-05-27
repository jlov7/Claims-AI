import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
)
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import PrecedentResultItem

client = TestClient(app)


class DummyPrecedentService:
    def find_precedents(self, claim_summary, top_k):
        # Return a dummy list of precedent items
        return [
            PrecedentResultItem(
                claim_id="PREC001",
                summary="Dummy summary",
                outcome="Dummy outcome",
                keywords="kw1,kw2",
                distance=0.123,
            )
        ]


@pytest.fixture(autouse=True)
def override_precedent_service():
    # Override FastAPI dependency for precedent service
    from backend.main import app
    import backend.services.precedent_service as ps

    dummy = DummyPrecedentService()
    # Map the original dependency function to return our dummy service
    app.dependency_overrides[ps.get_precedent_service] = lambda: dummy
    yield
    # Clean up override after tests
    app.dependency_overrides.pop(ps.get_precedent_service, None)


def test_precedent_success():
    payload = {"claim_summary": "Test summary", "top_k": 1}
    # Wrap payload under parameter name as the endpoint expects
    response = client.post("/api/v1/precedents", json={"query_request": payload})
    assert response.status_code == 200
    data = response.json()
    assert "precedents" in data
    assert isinstance(data["precedents"], list)
    first = data["precedents"][0]
    assert first["claim_id"] == "PREC001"
    assert first["summary"] == "Dummy summary"


def test_precedent_error():
    # Use FastAPI dependency overrides to simulate service failure
    from backend.main import app
    import backend.services.precedent_service as ps

    class ErrorService:
        def find_precedents(self, claim_summary, top_k):
            raise Exception("Service failure")

    # Override the precedent service dependency
    app.dependency_overrides[ps.get_precedent_service] = lambda: ErrorService()
    payload = {"claim_summary": "Test summary", "top_k": 1}
    # Wrap payload under parameter name as the endpoint expects
    response = client.post("/api/v1/precedents", json={"query_request": payload})
    # Clean up override
    app.dependency_overrides.pop(ps.get_precedent_service, None)
    assert response.status_code == 500
    assert response.json().get("detail") == "Failed to find precedents."
