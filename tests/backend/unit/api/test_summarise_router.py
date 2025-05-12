import pytest
from fastapi.testclient import TestClient
import backend.api.v1.summarise_router as summarise_router
from backend.main import app

client = TestClient(app)


class DummySummarisationService:
    def _get_content_from_id(self, doc_id):
        return "dummy text"

    def summarise_text(self, text, doc_id=None):
        return "dummy summary"


@pytest.fixture(autouse=True)
def override_summarisation_service(monkeypatch):
    dummy = DummySummarisationService()
    monkeypatch.setattr(summarise_router, "get_summarisation_service", lambda: dummy)


def test_summarise_by_content_success():
    payload = {"content": "Some text to summarise"}
    response = client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "dummy summary"
    assert data.get("original_document_id") is None


def test_summarise_by_document_id_success():
    payload = {"document_id": "doc123"}
    response = client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "dummy summary"
    assert data["original_document_id"] == "doc123"


def test_summarise_empty_content_error():
    payload = {"content": "   "}
    response = client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 400
    detail = response.json().get("detail", "").lower()
    assert "content to summarise is empty" in detail


def test_summarise_validation_missing_fields():
    response = client.post("/api/v1/summarise", json={})
    assert response.status_code == 422


def test_summarise_validation_both_fields():
    payload = {"content": "text", "document_id": "doc123"}
    response = client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 422
