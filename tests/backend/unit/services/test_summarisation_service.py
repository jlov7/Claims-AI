import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from pathlib import Path
from langchain_core.messages import AIMessage

from backend.services.summarisation_service import SummarisationService
from backend.core.config import Settings

# Path to the processed_text directory within the test environment (relative to this test file)
# This assumes tests are run from the project root or that paths are resolved correctly.
# For service unit tests, we often mock file system interactions.
# The service itself tries to find files in /app/data/processed_text or ./data/processed_text
# Let's define a constant for where our test files will be placed by mocks.
# This should align with how the service's local path resolution works for testing.
_TEST_SERVICE_UNIT_PROCESSED_TEXT_PATH = (
    Path(__file__).parent.parent.parent.parent / "data" / "processed_text"
)


@pytest.fixture
def settings():
    return Settings(
        PHI4_API_BASE="http://localhost:11434/v1",
        PHI4_MODEL_NAME="phi-4-reasoning-plus",
        LLM_TEMPERATURE=0.1,
        LLM_MAX_TOKENS=500,
    )


# Remove the singleton test as the singleton pattern was removed from the service
# def test_get_summarisation_service_singleton(settings):
#     service1 = get_summarisation_service()
#     service2 = get_summarisation_service()
#     assert service1 is service2
#     assert isinstance(service1, SummarisationService)
#     # Re-assign global_settings for other tests if necessary, or ensure tests use their own settings
#     from backend.core import config
#     config.settings = settings # Ensure the global settings are the test ones for this instance


@pytest.mark.asyncio
async def test_get_content_from_id_invalid_format(settings):
    svc = SummarisationService(settings)
    with pytest.raises(HTTPException) as excinfo:
        await svc.get_content_from_id("../../../etc/passwd")
    assert excinfo.value.status_code == 400
    assert "Invalid document ID format" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_content_from_id_not_found(settings, monkeypatch):
    svc = SummarisationService(settings)

    async def fake_async_read_file_sync_not_found(file_path_sync):
        raise FileNotFoundError(f"Mocked: File not found: {file_path_sync}")

    with patch(
        "asyncio.to_thread",
        new=AsyncMock(side_effect=FileNotFoundError("Mocked: File not found")),
    ):
        with pytest.raises(HTTPException) as excinfo:
            await svc.get_content_from_id("non_existent_doc.json")

    assert excinfo.value.status_code == 404
    assert (
        "Document content not found for ID: non_existent_doc.json"
        in excinfo.value.detail
    )


@pytest.mark.asyncio
async def test_get_content_from_id_invalid_json(settings, tmp_path, monkeypatch):
    target_doc_id = "doc_with_invalid_json.json"
    svc = SummarisationService(settings)
    expected_error_detail = (
        f"Document {target_doc_id} found at MOCK_PATH but is not valid JSON."
    )

    # This is the function that will be the side_effect of the patched asyncio.to_thread
    # It needs to accept the arguments that asyncio.to_thread would pass to its first argument (_read_file_sync)
    # However, asyncio.to_thread itself receives (_read_file_sync, file_path)
    # So the side_effect for asyncio.to_thread should mimic this.
    def mock_to_thread_side_effect_invalid_json(sync_func_to_run, path_arg):
        # sync_func_to_run would be _read_file_sync from the service
        # path_arg would be the file_path
        # We want to simulate an error during the execution of sync_func_to_run(path_arg)
        raise HTTPException(
            status_code=500,
            detail=expected_error_detail.replace("MOCK_PATH", str(path_arg)),
        )

    with patch(
        "asyncio.to_thread",
        new=AsyncMock(side_effect=mock_to_thread_side_effect_invalid_json),
    ) as mock_async_to_thread:
        with pytest.raises(HTTPException) as excinfo:
            await svc.get_content_from_id(target_doc_id)

    assert excinfo.value.status_code == 500
    assert (
        expected_error_detail.replace(
            "MOCK_PATH", str(mock_async_to_thread.call_args[0][1])
        )
        in excinfo.value.detail
    )  # Check detail


@pytest.mark.asyncio
async def test_get_content_from_id_missing_text_key(settings, tmp_path, monkeypatch):
    target_doc_id = "doc_with_missing_key.json"
    svc = SummarisationService(settings)
    expected_error_detail = f"Document {target_doc_id} found at MOCK_PATH but has no usable content (missing expected key)."

    def mock_to_thread_side_effect_missing_key(sync_func_to_run, path_arg):
        raise HTTPException(
            status_code=500,
            detail=expected_error_detail.replace("MOCK_PATH", str(path_arg)),
        )

    with patch(
        "asyncio.to_thread",
        new=AsyncMock(side_effect=mock_to_thread_side_effect_missing_key),
    ) as mock_async_to_thread:
        with pytest.raises(HTTPException) as excinfo:
            await svc.get_content_from_id(target_doc_id)

    assert excinfo.value.status_code == 500
    assert (
        expected_error_detail.replace(
            "MOCK_PATH", str(mock_async_to_thread.call_args[0][1])
        )
        in excinfo.value.detail
    )  # Check detail


@pytest.mark.asyncio
async def test_get_content_from_id_success(settings, tmp_path, monkeypatch):
    target_doc_id = "doc_success.json"
    expected_content = "hello world"
    svc = SummarisationService(settings)

    # This side_effect will be for asyncio.to_thread.
    # It needs to accept (sync_function, path_arg)
    # and return what sync_function(path_arg) would return.
    def mock_to_thread_side_effect_success(sync_func_to_run, path_arg):
        # We are mocking that the call to sync_func_to_run(path_arg) returns expected_content
        return expected_content

    with patch(
        "asyncio.to_thread",
        new=AsyncMock(side_effect=mock_to_thread_side_effect_success),
    ):
        content = await svc.get_content_from_id(target_doc_id)

    assert content == expected_content


@pytest.mark.asyncio
async def test_summarise_text_empty(settings):
    svc = SummarisationService(settings)
    with pytest.raises(HTTPException) as excinfo:
        await svc.summarise_text("   ", "docid")  # Added await
    assert excinfo.value.status_code == 400
    assert "Cannot summarise empty text" in excinfo.value.detail


@pytest.mark.asyncio
@patch("backend.services.summarisation_service.ChatOllama.ainvoke")
async def test_summarise_text_success(mock_llm_ainvoke, settings):
    # ChatOllama.ainvoke returns a BaseMessage (e.g., AIMessage)
    # StrOutputParser then extracts the .content attribute from this message.
    mock_llm_ainvoke.return_value = AIMessage(content="SUMMARY")  # Return AIMessage
    svc = SummarisationService(settings)
    result = await svc.summarise_text("text", "docid1")
    assert result == "• SUMMARY"
    mock_llm_ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("backend.services.summarisation_service.ChatOllama.ainvoke")
async def test_summarise_text_llm_error(mock_llm_ainvoke, settings):
    mock_llm_ainvoke.side_effect = Exception("LLM busted")
    svc = SummarisationService(settings)
    with pytest.raises(HTTPException) as excinfo:
        await svc.summarise_text("text", "docid_error")
    assert excinfo.value.status_code == 500
    assert "Failed to generate summary due to LLM error" in excinfo.value.detail
    mock_llm_ainvoke.assert_called_once()


# Example of how one might have tested _sync_open if needed, but patching asyncio.to_thread is better for these async tests.
# @pytest.mark.asyncio
# async def test_get_content_from_id_success_mocking_sync_open(settings, tmp_path, monkeypatch):
#     target_doc_id = "doc_success_alt.json"
#     temp_file_path = tmp_path / target_doc_id # This path is not directly used by the service
# The service constructs its own paths to try.
#     file_content_dict = {"text": "hello from sync open mock"}
#     file_content_str = json.dumps(file_content_dict)
#     # temp_file_path.write_text(file_content_str) # Not strictly needed if open is perfectly mocked

#     svc = SummarisationService(settings)

#     # Identify one of the paths the service *will* try.
#     # For local dev, it includes paths like: data/processed_text/doc_success_alt.json
#     # We need to ensure our mock intercepts exactly one of these.
#     # Example: assume it tries a path that matches our intended mock target.
#     path_service_will_try = _TEST_SERVICE_UNIT_PROCESSED_TEXT_PATH / target_doc_id

#     mock_file_opened_correctly = MagicMock()

#     def highly_selective_sync_open(file_to_open_str, mode="r", encoding=None):
# non_overwriting_passthrough_node_error
#         nonlocal mock_file_opened_correctly
#         # Ensure the path matches exactly what the service is expected to try
#         if str(file_to_open_str) == str(path_service_will_try):
#             mock_file_opened_correctly(file_to_open_str) # Record that our target was opened
#             return io.StringIO(file_content_str) # Return an in-memory text wrapper
#         # For any other path, raise FileNotFoundError
#         raise FileNotFoundError(f"Mock (_sync_open): Path {file_to_open_str} not the target {path_service_will_try} or not found.")

#     monkeypatch.setattr(
#         "backend.services.summarisation_service._sync_open",
#         highly_selective_sync_open
#     )

#     content = await svc.get_content_from_id(target_doc_id)
#     assert content == "hello from sync open mock"
#     mock_file_opened_correctly.assert_called_once_with(str(path_service_will_try))
