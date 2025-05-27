import pytest
from httpx import AsyncClient
from backend.main import app

from backend.services.summarisation_service import (
    get_summarisation_service,
)
from backend.services.document_loader import get_document_loader_service
from backend.core.config import get_settings
import logging
from fastapi import Depends

logger = logging.getLogger(__name__)

VALID_DOC_ID_FOR_TEST = "test_document_123.txt"
INVALID_DOC_ID_FOR_TEST = "non_existent_document_xyz123.txt"
MOCKED_LLM_SUMMARY_CONTENT = "This is a mocked summary of the document."

# V1 Models for LangServe payload/response structure (matching langserve_app/app.py)
# These are for mental model and structuring test assertions, not direct instantiation here usually.


@pytest.fixture
def mock_document_loader(monkeypatch):
    from unittest.mock import Mock  # Import Mock
    from backend.services.document_loader import (
        DocumentLoaderService,
    )  # Import DocumentLoaderService

    loader = Mock(spec=DocumentLoaderService)
    loader.load_document_content_by_id.return_value = "dummy text"
    monkeypatch.setattr(
        "backend.services.summarisation_service.get_document_loader_service",  # Target the getter function
        lambda settings: loader,  # The getter should return the loader instance
    )


# The above change replaces a previous, more complex mock_document_loader that might have been causing issues.
# This also implies that SummarisationService correctly uses get_document_loader_service(settings=self.settings)
# in its __init__ to get the loader.


@pytest.fixture(autouse=True)
def mock_summarisation_service_llm(monkeypatch, request):
    if "full_llm_summarise_test" in request.keywords:
        yield
    else:

        async def mock_generate_summary(*args, **kwargs):
            return MOCKED_LLM_SUMMARY_CONTENT

        monkeypatch.setattr(
            "backend.services.summarisation_service.SummarisationService.summarise_text",
            mock_generate_summary,
        )
        yield


@pytest.fixture(autouse=True)
def override_summarisation_dependencies(monkeypatch):
    from fastapi import HTTPException  # For mocking service behavior
    from backend.services.summarisation_service import (
        SummarisationService as RealSummarisationService,
    )
    from backend.services.document_loader import DocumentLoaderService

    class MockSummarisationService(RealSummarisationService):
        def __init__(
            self, settings_param, document_loader_param
        ):  # Match real signature
            super().__init__(
                settings_param
            )  # Pass only settings_param to parent if it only expects that
            print(
                f"DEBUG: MockSummarisationService INSTANCE CREATED: {self}"
            )  # ADDED DEBUG
            self.mock_llm_failure = False  # Flag to simulate LLM errors
            self.mock_doc_storage = {
                VALID_DOC_ID_FOR_TEST: "This is the mock content for the valid document.",
                # Add other specific mock documents if needed by other tests
            }

        async def get_content_from_id(
            self, document_id: str
        ) -> str:  # RENAMED from _get_content_from_id
            logger.info(
                f"MockSummarisationService.get_content_from_id CALLED with: {document_id}"  # Added CALLED for clarity
            )
            if document_id in self.mock_doc_storage:
                return self.mock_doc_storage[document_id]

            logger.error(
                f"MockSummarisationService: Simulating 404 for unmocked document_id: {document_id}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Mocked: Document not found for ID: {document_id}",
            )

        async def summarise_text(
            self, text_content: str, document_id: str = "direct content"
        ) -> str:  # Made async
            logger.info(
                f"MockSummarisationService.summarise_text called for doc: {document_id}, content len: {len(text_content)}"
            )
            if self.mock_llm_failure:
                logger.error("MockSummarisationService: Simulating LLM failure.")
                raise HTTPException(status_code=500, detail="Mocked LLM failure.")

            if "fail_summary" in text_content.lower():
                logger.error(
                    "MockSummarisationService: Simulating LLM failure based on content trigger."
                )
                raise HTTPException(
                    status_code=500, detail="Mocked LLM failure due to content trigger."
                )

            return f"Mock summary for: {text_content[:50]}..."

    # Factory function for the mock service
    def get_mock_summarisation_service(
        settings=Depends(get_settings),  # Keep Depends for signature compatibility
        doc_loader: DocumentLoaderService = Depends(get_document_loader_service),
    ):
        # Create a real DocumentLoaderService instance if needed by the mock, or mock it too
        # For now, assuming default doc_loader is fine or also overridden if necessary
        return MockSummarisationService(
            settings_param=settings, document_loader_param=doc_loader
        )

    app.dependency_overrides[get_summarisation_service] = get_mock_summarisation_service
    yield
    app.dependency_overrides.clear()


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_by_content_success(client: AsyncClient):
    payload = {"input": {"content": "A long text for summarisation."}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert response.status_code == 200
    data = response.json()["output"]
    assert data["summary"] == MOCKED_LLM_SUMMARY_CONTENT
    assert data["original_content_preview"].startswith("A long text")


@pytest.mark.api
@pytest.mark.full_llm_summarise_test  # This will use the real LLM
@pytest.mark.asyncio
async def test_summarise_invoke_by_content_full_llm(client: AsyncClient):
    payload = {"input": {"content": "The quick brown fox. A very short text."}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert response.status_code == 200
    data = response.json()["output"]
    assert data["summary"] != MOCKED_LLM_SUMMARY_CONTENT
    assert len(data["summary"]) > 0
    assert data["original_content_preview"].startswith("The quick brown fox")


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_by_document_id_success(client: AsyncClient):
    payload = {"input": {"document_id": VALID_DOC_ID_FOR_TEST}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert response.status_code == 200
    data = response.json()["output"]
    assert data["summary"] == MOCKED_LLM_SUMMARY_CONTENT
    assert data["original_content_preview"].startswith(
        "This is a test document for integration tests.\nIt needs to exist for test_summarise_invoke_by_document_id_success."
    )
    assert data["original_document_id"] == VALID_DOC_ID_FOR_TEST


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_by_document_id_not_found(client: AsyncClient):
    payload = {"input": {"document_id": INVALID_DOC_ID_FOR_TEST}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert (
        response.status_code == 404
    )  # Real service's get_content_from_id raises 404 if mock isn't hit
    data = response.json()
    assert (
        f"Document content not found for ID: {INVALID_DOC_ID_FOR_TEST}"  # MODIFIED to check for real service message start
        in data["detail"]
    )
    assert (
        "Searched paths: " in data["detail"]
    )  # MODIFIED to check for real service message part


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_no_input(client: AsyncClient):
    payload = {"input": {}}  # Neither content nor document_id
    response = await client.post("/langserve/summarise/invoke", json=payload)
    # summarise_logic in app.py raises 400 if neither is provided.
    assert response.status_code == 400
    data = response.json()
    assert "Either 'document_id' or 'content' must be provided." in data["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_both_inputs_content_priority(client: AsyncClient):
    # The V1 model allows both. The summarise_logic prioritizes content.
    content_text = "This is explicit content."
    payload = {"input": {"document_id": VALID_DOC_ID_FOR_TEST, "content": content_text}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert response.status_code == 200
    data = response.json()["output"]
    assert data["summary"] == MOCKED_LLM_SUMMARY_CONTENT
    assert data["original_content_preview"].startswith(
        "This is explicit content"
    )  # Content was used
    assert (
        data.get("original_document_id") is None
    )  # document_id from request might not be passed if content is used


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_empty_content_string(client: AsyncClient):
    payload = {"input": {"content": "   "}}  # Whitespace only
    response = await client.post("/langserve/summarise/invoke", json=payload)
    # summarise_logic in app.py raises 400 for empty/whitespace content.
    assert response.status_code == 400
    data = response.json()
    assert "Content for summarisation is empty." in data["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invoke_invalid_document_id_format(client: AsyncClient):
    # This test the mock of _get_content_from_id, which simulates a 404 for this.
    doc_id = "../../../../etc/passwd"
    payload = {"input": {"document_id": doc_id}}
    response = await client.post("/langserve/summarise/invoke", json=payload)
    assert (
        response.status_code == 400
    )  # MODIFIED (real service raises 400 for invalid format)
    assert "Invalid document ID format." in response.json()["detail"]  # MODIFIED
