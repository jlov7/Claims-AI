import pytest
from httpx import AsyncClient
import io
from docx import Document
from pathlib import Path  # For tmp_path

from backend.main import app
from backend.services.drafting_service import get_drafting_service, DraftingService

# client fixture is from conftest.py

DRAFT_DOC_ID_1 = "draft_test_doc1.json"
DRAFT_DOC_ID_2 = "draft_test_doc2.json"

# Mocked LLM response for most tests
MOCKED_LLM_DRAFT_CONTENT = "Mocked LLM draft content. This is a test."


@pytest.fixture(autouse=True)
def mock_drafting_service_llm(monkeypatch, request):
    """
    Mocks the LLM call within DraftingService for most tests in this module.
    Tests marked with 'full_llm_test' will not be mocked.
    """
    if "full_llm_test" in request.keywords:
        yield  # Do not mock, proceed with the actual service
    else:

        def mock_generate_text(*args, **kwargs):
            return MOCKED_LLM_DRAFT_CONTENT

        # Path to the method to be mocked
        monkeypatch.setattr(
            "backend.services.drafting_service.DraftingService.generate_strategy_note_text",
            mock_generate_text,
        )
        yield  # Test runs with the mock


# This fixture will be auto-used by tests in this file if they depend on temp_drafting_service
# No, we need to explicitly override the dependency in the app for the test client


@pytest.fixture(autouse=True)
def override_drafting_service_dependency(temp_drafting_service: DraftingService):
    """Overrides the get_drafting_service dependency for all tests in this module."""
    app.dependency_overrides[get_drafting_service] = lambda: temp_drafting_service
    yield
    app.dependency_overrides.clear()  # Clear overrides after tests in this module run


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_strategy_note_success_with_summary(client: AsyncClient):
    """Test /draft with a claim_summary, expecting a DOCX file."""
    payload = {
        "claim_summary": "The claimant experienced a minor fender bender. Seeking compensation for bumper damage.",
        "output_filename": "test_summary_note.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "test_summary_note.docx" in response.headers["content-disposition"]

    # Check if the content is a valid DOCX and non-empty
    assert len(response.content) > 0
    try:
        docx_file = io.BytesIO(response.content)
        doc = Document(docx_file)
        assert len(doc.paragraphs) > 0  # Basic check that it has some content
    except Exception as e:
        pytest.fail(f"Failed to parse returned DOCX file: {e}")


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_strategy_note_with_document_ids(client: AsyncClient):
    """Test /draft with document_ids."""
    payload = {
        "document_ids": [DRAFT_DOC_ID_1, DRAFT_DOC_ID_2],
        "additional_criteria": "Focus on policy coverage discrepancies.",
        "output_filename": "test_docs_note.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "test_docs_note.docx" in response.headers["content-disposition"]
    assert len(response.content) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_strategy_note_with_qa_history(client: AsyncClient):
    """Test /draft with qa_history."""
    payload = {
        "qa_history": [
            {"question": "What was the date of incident?", "answer": "2023-01-15"},
            {"question": "Was a police report filed?", "answer": "Yes, report #12345"},
        ],
        "output_filename": "test_qa_note.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "test_qa_note.docx" in response.headers["content-disposition"]
    assert len(response.content) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_strategy_note_all_inputs(client: AsyncClient):
    """Test /draft with all possible input types."""
    payload = {
        "claim_summary": "Complex multi-vehicle incident with disputed liability.",
        "document_ids": [DRAFT_DOC_ID_1],
        "qa_history": [
            {
                "question": "Any injuries reported?",
                "answer": "Minor whiplash by one party.",
            }
        ],
        "additional_criteria": "Draft a conservative initial assessment. Highlight areas needing further investigation.",
        "output_filename": "test_all_inputs_note.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "test_all_inputs_note.docx" in response.headers["content-disposition"]
    assert len(response.content) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_validation_no_substantive_input(client: AsyncClient):
    """Test /draft request validation: no substantive context provided."""
    payload = {
        "output_filename": "test_no_substantive_input.docx"
    }  # Only output_filename
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 422  # Pydantic validation from the model
    data = response.json()
    assert "detail" in data
    # Example: "At least one of 'claim_summary', 'document_ids', 'qa_history', or 'additional_criteria' must be provided"


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_with_non_existent_document_id(client: AsyncClient):
    """Test /draft with a non-existent document_id among valid ones."""
    # The service is designed to skip non-existent doc_ids and proceed if other context exists.
    payload = {
        "claim_summary": "Summary for a case with one missing document.",
        "document_ids": [DRAFT_DOC_ID_1, "non_existent_doc_xyz.json", DRAFT_DOC_ID_2],
        "output_filename": "test_missing_doc_note.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "test_missing_doc_note.docx" in response.headers["content-disposition"]
    assert len(response.content) > 0
    # Further validation could involve checking if the content of DRAFT_DOC_ID_1 and DRAFT_DOC_ID_2 influenced the output.


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_filename_sanitization(client: AsyncClient):
    """Test that output_filename is sanitized."""
    payload = {
        "claim_summary": "Test filename sanitization.",
        "output_filename": "../invalid/path/chars*?.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    expected_sanitized_filename = "chars.docx"  # Updated expected filename
    assert (
        f'filename="{expected_sanitized_filename}"'
        in response.headers["content-disposition"]
    )


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_simple_summary(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test /draft with a simple claim summary. LLM will be mocked."""
    payload = {"claim_summary": "Minor fender bender, no injuries."}
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "content-disposition" in response.headers
    # Check if the file was actually written by the mocked service
    # The filename will be based on the default from the model or sanitized suggestion
    # For this test, we expect a default name if none is provided.
    # We can list files in the temp_drafting_service.output_dir
    written_files = list(Path(temp_drafting_service.output_dir).glob("*.docx"))
    assert len(written_files) == 1
    # Further check content if needed, but it will be the mocked content.


@pytest.mark.api
@pytest.mark.full_llm_test
@pytest.mark.asyncio
async def test_draft_with_actual_llm_call(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """
    Test /draft ensuring a real LLM call is made.
    This test will be slower.
    """
    payload = {
        "claim_summary": "A complex claim involving multiple parties and significant property damage. Need a detailed strategy.",
        "output_filename": "real_llm_draft_complex.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert (
        'filename="real_llm_draft_complex.docx"'
        in response.headers["content-disposition"]
    )

    file_path = Path(temp_drafting_service.output_dir) / "real_llm_draft_complex.docx"
    assert file_path.exists()
    # Here, you might add checks for the actual content if there's a predictable element,
    # or just verify it's not the MOCKED_LLM_DRAFT_CONTENT.
    # For now, existence and non-mocked content (by implication of not being mocked) is enough.


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_with_document_ids(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test /draft with document IDs. LLM will be mocked."""
    # Create dummy files that the DocumentLoaderService can "find"
    # The DocumentLoaderService itself might need mocking if it hits external resources
    # For now, assuming it can run and find placeholder files or is also mocked appropriately.
    # This test focuses on the DraftingService's interaction with doc IDs.

    # For this test to pass without actual files, DocumentLoaderService.load_document_content_by_id
    # would also need to be mocked in this test setup.
    # Let's assume for now the DI for DocumentLoaderService in DraftingService handles this,
    # or we add another mock here specific to DocumentLoaderService.
    # For simplicity, let's focus on the drafting LLM mock first.
    # If DocumentLoaderService also makes external calls or needs specific file setup,
    # it should be mocked similarly.

    payload = {
        "document_ids": [DRAFT_DOC_ID_1, DRAFT_DOC_ID_2],
        "additional_criteria": "Focus on liability.",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    written_files = list(Path(temp_drafting_service.output_dir).glob("*.docx"))
    assert len(written_files) >= 1  # Filename might be default


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_with_qa_history(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test /draft with Q&A history. LLM will be mocked."""
    payload = {
        "qa_history": [
            {
                "question": "What was the primary damage?",
                "answer": "Rear bumper crushed.",
            },
            {
                "question": "Any injuries reported?",
                "answer": "Claimant reported whiplash.",
            },
        ],
        "output_filename": "draft_with_qa.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert 'filename="draft_with_qa.docx"' in response.headers["content-disposition"]
    file_path = Path(temp_drafting_service.output_dir) / "draft_with_qa.docx"
    assert file_path.exists()


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_all_inputs(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test /draft with all possible inputs. LLM will be mocked."""
    payload = {
        "claim_summary": "Comprehensive test case.",
        "document_ids": [DRAFT_DOC_ID_1],
        "qa_history": [{"question": "Q1", "answer": "A1"}],
        "additional_criteria": "Be thorough.",
        "output_filename": "draft_all_inputs.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200
    assert 'filename="draft_all_inputs.docx"' in response.headers["content-disposition"]
    file_path = Path(temp_drafting_service.output_dir) / "draft_all_inputs.docx"
    assert file_path.exists()


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_output_file_actually_written(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test that the DOCX file is actually written to the temp_drafting_service's output directory."""
    filename = "test_output_written.docx"
    payload = {
        "claim_summary": "Content for written file test.",
        "output_filename": filename,
    }

    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200

    expected_file_path = Path(temp_drafting_service.output_dir) / filename
    assert expected_file_path.exists(), f"File {expected_file_path} was not written."
    assert expected_file_path.is_file()
    # Optionally, check file size or try to parse it as a DOCX if robust testing is needed
    # For now, existence is the key check.


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_long_filename_truncation(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test that very long filenames are truncated correctly. LLM will be mocked."""
    long_base = "a" * 300
    payload = {
        "claim_summary": "Test long filename.",
        "output_filename": f"{long_base}.docx",
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert response.status_code == 200

    # Max length in service is 250. Extension is .docx (5 chars)
    # So, base name max length is 245.
    expected_truncated_base = long_base[:245]
    expected_filename = f"{expected_truncated_base}.docx"
    assert f'filename="{expected_filename}"' in response.headers["content-disposition"]

    file_path = Path(temp_drafting_service.output_dir) / expected_filename
    assert file_path.exists()


@pytest.mark.api
@pytest.mark.asyncio
async def test_draft_filename_becomes_empty_after_sanitize(
    client: AsyncClient, temp_drafting_service: DraftingService
):
    """Test that a filename which sanitizes to empty (or just .docx) gets a default UUID name."""
    payload = {
        "claim_summary": "Test with a filename that should be sanitized to default.",
        "output_filename": "///.docx",  # This should sanitize to an empty base name
    }
    response = await client.post("/api/v1/draft", json=payload)
    assert (
        response.status_code == 200
    ), f"Expected 200 OK, got {response.status_code}. Response: {response.text}"

    # 1. Check content-disposition header
    content_disposition = response.headers.get("content-disposition", "")
    assert (
        "filename=" in content_disposition
    ), f"'filename=' not in content-disposition: {content_disposition}"

    import re

    match = re.search(
        r"filename\*?=(?:UTF-8\'\')?([^;]+)", content_disposition, re.IGNORECASE
    )
    assert (
        match is not None
    ), f"Could not parse filename from content-disposition: {content_disposition}"

    actual_filename_in_header = match.group(1).strip('" ')
    print(
        f"DEBUG: Filename from header for ///.docx: {actual_filename_in_header}"
    )  # Debug print

    assert actual_filename_in_header.startswith(
        "strategy_note_"
    ), f"Filename in header '{actual_filename_in_header}' does not start with 'strategy_note_'"
    assert actual_filename_in_header.endswith(
        ".docx"
    ), f"Filename in header '{actual_filename_in_header}' does not end with '.docx'"

    uuid_part = actual_filename_in_header[len("strategy_note_") : -len(".docx")]
    assert len(uuid_part) == 8, f"UUID part '{uuid_part}' is not 8 characters long"
    assert all(
        c in "0123456789abcdef" for c in uuid_part.lower()
    ), f"UUID part '{uuid_part}' is not a valid hex string"

    # 2. Check file written on disk by the service (which uses temp_drafting_service.output_dir)
    expected_filename_on_disk = (
        actual_filename_in_header  # Filename on disk should match header
    )
    file_path_on_disk = (
        Path(temp_drafting_service.output_dir) / expected_filename_on_disk
    )

    assert file_path_on_disk.exists(), f"Expected file '{file_path_on_disk}' not found in temp output dir: {temp_drafting_service.output_dir}. Contents: {list(Path(temp_drafting_service.output_dir).glob('*'))}"
    assert file_path_on_disk.is_file()
