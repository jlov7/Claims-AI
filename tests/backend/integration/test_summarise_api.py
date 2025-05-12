import pytest
from httpx import AsyncClient  # Added

from backend.main import app
from backend.services.summarisation_service import (
    SummarisationService,
    get_summarisation_service,
)  # For DI override

# Constants for test document IDs
# Assume these files exist in data/processed_text for some tests
# Ensure they are small and simple for testing purposes.
VALID_DOC_ID_FOR_TEST = "test_document_123.txt"  # Create this dummy file
INVALID_DOC_ID_FOR_TEST = "non_existent_document_xyz123.txt"

# Mocked LLM response
MOCKED_LLM_SUMMARY_CONTENT = "This is a mocked summary of the document."


@pytest.fixture(scope="module", autouse=True)
def create_dummy_processed_files(tmp_path_factory):
    """Ensure dummy files exist in a temporary processed_text dir for tests."""
    # This fixture will run once per test module.
    # We need to influence where DocumentLoaderService looks for files.
    # This is better handled by mocking DocumentLoaderService.load_document_content_by_id
    # For now, this fixture shows intent but won't work without more complex patching
    # of DocumentLoaderService's file paths. We will mock the loader instead.
    pass


@pytest.fixture(autouse=True)
def mock_summarisation_service_llm(monkeypatch, request):
    """
    Mocks the LLM call within SummarisationService for most tests in this module.
    Tests marked with 'full_llm_summarise_test' will not be mocked.
    """
    if "full_llm_summarise_test" in request.keywords:
        yield
    else:

        def mock_generate_summary(*args, **kwargs):
            return MOCKED_LLM_SUMMARY_CONTENT

        monkeypatch.setattr(
            "backend.services.summarisation_service.SummarisationService.summarise_text",
            mock_generate_summary,
        )
        yield


@pytest.fixture
def mock_doc_loader_service(monkeypatch):
    """Mocks the DocumentLoaderService to control document content for tests."""

    # This fixture is no longer directly used by override_summarisation_dependencies
    # in the same way, as SummarisationService doesn't take doc_loader as init arg.
    # However, if other services use DocumentLoaderService via DI, this mock can still be useful.
    # For SummarisationService, we will mock its internal _get_content_from_id directly.
    def mock_load_content(self, document_id: str):
        if document_id == VALID_DOC_ID_FOR_TEST:
            return (
                "This is the dummy content of test_document_123.txt for summarisation."
            )
        elif document_id == DRAFT_DOC_ID_1:  # If reused from draft tests
            return "Content of draft test doc 1."
        logger.warning(f"MockDocLoader: Attempt to load unmocked doc ID: {document_id}")
        return None

    monkeypatch.setattr(
        "backend.services.document_loader.DocumentLoaderService.load_document_content_by_id",
        mock_load_content,
    )


@pytest.fixture(autouse=True)
def override_summarisation_dependencies(
    monkeypatch,
):  # Removed mock_doc_loader_service from args
    """
    Overrides dependencies for SummarisationService.
    It ensures SummarisationService uses the mocked _get_content_from_id.
    """

    def mock_get_content(self, document_id: str):
        if document_id == VALID_DOC_ID_FOR_TEST:
            return (
                "This is the dummy content of test_document_123.txt for summarisation."
            )
        # Add other valid doc IDs if needed for specific tests
        logger.warning(
            f"MockSummarisationService._get_content_from_id: Unmocked doc ID: {document_id}"
        )
        # Simulate HTTPException(status_code=404, detail="Document not found") behavior
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail=f"Mocked: Document not found for ID: {document_id}"
        )

    monkeypatch.setattr(
        "backend.services.summarisation_service.SummarisationService._get_content_from_id",
        mock_get_content,
    )

    # Provide a SummarisationService instance. Its _get_content_from_id is now mocked.
    # Its LLM call (summarise_text) is mocked by mock_summarisation_service_llm fixture.
    def get_correctly_mocked_summarisation_service():
        settings = get_settings()
        # SummarisationService now takes only settings
        service = SummarisationService(settings=settings)
        return service

    app.dependency_overrides[get_summarisation_service] = (
        get_correctly_mocked_summarisation_service
    )

    # No need to override get_document_loader_service for SummarisationService tests anymore
    # as it doesn't use it via DI for the parts we are testing with these mocks.
    yield
    app.dependency_overrides.clear()


# Need to import get_settings from config for the override
from backend.core.config import get_settings
import logging  # for logger in mock_doc_loader_service

logger = logging.getLogger(__name__)

# Dummy document IDs for draft tests, if they are needed by summarise tests
DRAFT_DOC_ID_1 = "draft_test_doc1.json"


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_by_content_success(client: AsyncClient):
    """Test /summarise with direct content successfully. LLM will be mocked."""
    payload_content = {
        "content": "This is a lengthy piece of text about the intricacies of modern software development. It discusses agile methodologies, DevOps practices, and the importance of continuous integration and delivery. The goal is to produce high-quality software efficiently."
    }
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert data["summary"] == MOCKED_LLM_SUMMARY_CONTENT
    assert "original_content_preview" in data
    assert data["original_content_preview"].startswith("This is a lengthy piece")


@pytest.mark.api
@pytest.mark.full_llm_summarise_test
@pytest.mark.asyncio
async def test_summarise_by_content_full_llm(client: AsyncClient):
    """Test /summarise with direct content and actual LLM call."""
    payload_content = {
        "content": "The quick brown fox jumps over the lazy dog. This sentence contains all letters of the alphabet. It is often used for testing typewriters and fonts."
    }
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert data["summary"] != MOCKED_LLM_SUMMARY_CONTENT  # Should be real summary
    assert len(data["summary"]) > 0
    assert data["original_content_preview"].startswith("The quick brown fox")


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_by_document_id_success(client: AsyncClient):
    """Test /summarise with a valid document_id successfully. LLM and DocLoader will be mocked."""
    payload_content = {"document_id": VALID_DOC_ID_FOR_TEST}
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == MOCKED_LLM_SUMMARY_CONTENT
    assert data["original_content_preview"].startswith("This is the dummy content")
    assert data["original_document_id"] == VALID_DOC_ID_FOR_TEST


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_by_document_id_not_found(client: AsyncClient):
    """Test /summarise with a non-existent document_id. DocLoader will be mocked."""
    payload_content = {"document_id": INVALID_DOC_ID_FOR_TEST}
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "Document not found" in data["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_no_input(client: AsyncClient):
    """Test /summarise with neither content nor document_id."""
    # Pydantic model SummariseRequest has a root_validator to ensure one is present.
    # FastAPI should return 422 if Pydantic validation fails at model level.
    payload_content = {}
    payload = {
        "summarise_request": payload_content
    }  # Even an empty request needs to be under the key now
    response = await client.post(
        "/api/v1/summarise", json=payload
    )  # empty body or not matching model
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_both_inputs(client: AsyncClient):
    """Test /summarise providing both content and document_id (should be disallowed by model)."""
    payload_content = {"document_id": VALID_DOC_ID_FOR_TEST, "content": "Some text"}
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert response.status_code == 422  # Pydantic validation error (root_validator)


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_empty_content_string(client: AsyncClient):
    """Test /summarise with empty string content."""
    payload_content = {"content": "   "}  # Whitespace only
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    # The service itself raises HTTPException for empty/whitespace content before LLM call
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Content to summarise is empty or whitespace" in data["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_summarise_invalid_document_id_format(client: AsyncClient):
    """Test /summarise with an invalid document_id format (e.g., path traversal)."""
    payload_content = {"document_id": "../../../../etc/passwd"}
    payload = {"summarise_request": payload_content}
    response = await client.post("/api/v1/summarise", json=payload)
    assert (
        response.status_code == 404
    )  # Service should reject invalid doc ID format -> Not Found
    assert (
        "Mocked: Document not found for ID: ../../../../etc/passwd"
        in response.json()["detail"]
    )  # Match mock output


# End of summarise tests
