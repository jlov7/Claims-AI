import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
)
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import backend.api.v1.draft_router as draft_router
from backend.main import app

client = TestClient(app)


class DummyDraftingService:
    def __init__(self, temp_file: Path):
        self.temp_file = temp_file

    def _build_llm_context(self, request):
        # Return dummy context regardless of input
        return "dummy context"

    def generate_strategy_note_text(self, context: str) -> str:
        # Return dummy text for DOCX creation
        return "dummy text content"

    def create_docx_from_text(self, text: str, filename_suggestion: str) -> Path:
        # Create a dummy DOCX file at the specified path
        self.temp_file.write_bytes(b"DUMMY DOCX CONTENT")
        return self.temp_file


@pytest.fixture(autouse=True)
def override_drafting_service(tmp_path):
    # Setup a dummy DOCX file path and dummy service
    dummy_file = tmp_path / "test.docx"
    dummy_service = DummyDraftingService(dummy_file)
    # Override the dependency used in the draft_router endpoint
    app.dependency_overrides[draft_router.get_drafting_service] = lambda: dummy_service
    yield
    # Clean up overrides after test
    app.dependency_overrides.pop(draft_router.get_drafting_service, None)


def test_draft_success():
    # Send a valid drafting request
    payload = {"claimSummary": "Test claim summary", "outputFilename": "test.docx"}
    response = client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    # Check headers for DOCX content type and filename
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    content_disposition = response.headers.get("content-disposition", "")
    assert 'filename="test.docx"' in content_disposition
    # Ensure response body contains our dummy content
    assert response.content == b"DUMMY DOCX CONTENT"


def test_draft_validation_no_context():
    # Missing context fields (no claimSummary, documentIds, qaHistory, additionalCriteria)
    payload = {"outputFilename": "test.docx"}
    response = client.post("/api/v1/draft", json=payload)
    assert response.status_code == 422
