import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import BatchUploadResponse, UploadResponseItem
from backend.services.document_service import document_service

client = TestClient(app)


class DummyDocumentService:
    async def save_and_process_documents(self, files):
        # Return a fixed successful response
        return BatchUploadResponse(
            overall_status="Completed",
            results=[
                UploadResponseItem(filename="dummy.txt", success=True, message="ok")
            ],
        )


@pytest.fixture(autouse=True)
def override_document_service(monkeypatch):
    # Stub out actual document processing
    dummy = DummyDocumentService()
    monkeypatch.setattr(
        document_service, "save_and_process_documents", dummy.save_and_process_documents
    )


def test_upload_success():
    # Simulate uploading a valid PDF file
    files = [("files", ("test.pdf", b"dummy content", "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "Completed"
    assert isinstance(data["results"], list)
    assert data["results"][0]["filename"] == "dummy.txt"


def test_upload_unsupported_content_type():
    # Simulate uploading an unsupported file type
    files = [("files", ("image.jpg", b"data", "image/jpeg"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "not supported" in detail.lower()
