import pytest
import pytest_asyncio
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from fastapi import UploadFile
from backend.services.document_service import (
    DocumentService,
    RAW_UPLOAD_DIR,
    PROCESSED_TEXT_DIR,
    OCR_SCRIPT_PATH,
    APP_BASE_DIR,
)

# Ensure APP_BASE_DIR is correctly defined for test context if it's used for resolving paths
# This might need adjustment based on how tests are run and how DocumentService resolves it.
# For now, assume DocumentService's APP_BASE_DIR is robust enough.


@pytest_asyncio.fixture
async def document_service(request):
    with patch.object(
        Path, "mkdir", autospec=True
    ) as mock_mkdir_fixture_level, patch.object(
        Path, "exists", autospec=True
    ) as mock_exists_fixture_level, patch.object(
        Path, "is_file", autospec=True
    ) as mock_is_file_fixture_level:
        service = DocumentService()

        mock_exists_fixture_level.return_value = True
        mock_is_file_fixture_level.return_value = True

        path_related_mocks = {
            "mkdir": mock_mkdir_fixture_level,
            "exists": mock_exists_fixture_level,
            "is_file": mock_is_file_fixture_level,
        }

        if request.node.get_closest_marker("reset_path_mocks_for_test"):
            mock_mkdir_fixture_level.reset_mock()
            mock_exists_fixture_level.reset_mock()
            mock_is_file_fixture_level.reset_mock()
            mock_exists_fixture_level.return_value = True
            mock_is_file_fixture_level.return_value = True

        yield service, path_related_mocks


@pytest.mark.asyncio
async def test_document_service_init(document_service):
    service, path_mocks = document_service
    assert path_mocks["mkdir"].call_count >= 2
    path_mocks["mkdir"].assert_any_call(RAW_UPLOAD_DIR, parents=True, exist_ok=True)
    path_mocks["mkdir"].assert_any_call(PROCESSED_TEXT_DIR, parents=True, exist_ok=True)


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_happy_path(document_service):
    service, path_mocks = document_service
    mock_path_mkdir = path_mocks["mkdir"]
    mock_path_exists = path_mocks["exists"]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test_document.pdf"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("11111111-1111-1111-1111-111111111111")
    file_id_uuid_val = uuid.UUID("22222222-2222-2222-2222-222222222222")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj") as mock_copyfileobj, patch(
        "shutil.rmtree"
    ) as mock_rmtree, patch(
        "shutil.which", return_value="/usr/bin/python3"
    ) as mock_which, patch("subprocess.run") as mock_subprocess_run, patch(
        "uuid.uuid4", side_effect=[batch_uuid_val, file_id_uuid_val]
    ):
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_process_result.stdout = "OCR successful"
        mock_process_result.stderr = ""
        mock_subprocess_run.return_value = mock_process_result

        response = await service.save_and_process_documents([mock_file])

        assert response.overall_status == "Completed"
        assert len(response.results) == 1
        assert response.results[0].filename == "test_document.pdf"
        assert response.results[0].success is True
        assert "File processed successfully." in response.results[0].message

        mock_path_mkdir.assert_any_call(
            expected_batch_dir_path, parents=True, exist_ok=True
        )

        mock_open.assert_called_once_with(
            expected_batch_dir_path / "test_document.pdf", "wb+"
        )
        mock_copyfileobj.assert_called_once()
        mock_file.file.close.assert_called_once()

        mock_subprocess_run.assert_called_once_with(
            [
                "/usr/bin/python3",
                str(OCR_SCRIPT_PATH),
                "--src",
                str(expected_batch_dir_path),
                "--out",
                str(PROCESSED_TEXT_DIR),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=APP_BASE_DIR,
        )
        mock_rmtree.assert_called_once_with(expected_batch_dir_path)
        mock_path_exists.assert_any_call(expected_batch_dir_path)


@pytest.mark.asyncio
async def test_save_and_process_documents_empty_file_list(document_service):
    service, _ = document_service
    response = await service.save_and_process_documents([])
    assert response.overall_status == "Failed"
    assert len(response.results) == 1
    assert response.results[0].filename == "N/A"
    assert "No files were processed." in response.results[0].message


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_save_failure(document_service):
    service, path_mocks = document_service
    mock_path_mkdir = path_mocks["mkdir"]
    mock_path_exists = path_mocks["exists"]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "fail_save.txt"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("33333333-3333-3333-3333-333333333333")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch(
        "shutil.copyfileobj", side_effect=IOError("Disk full")
    ) as mock_copyfileobj, patch("shutil.rmtree") as mock_rmtree, patch(
        "uuid.uuid4", return_value=batch_uuid_val
    ):
        response = await service.save_and_process_documents([mock_file])

        assert response.overall_status == "Completed with errors"
        assert len(response.results) == 1
        assert response.results[0].filename == "fail_save.txt"
        assert response.results[0].success is False
        assert "Failed to save file: Disk full" in response.results[0].message

        mock_path_mkdir.assert_any_call(
            expected_batch_dir_path, parents=True, exist_ok=True
        )

        mock_open.assert_called_once_with(
            expected_batch_dir_path / "fail_save.txt", "wb+"
        )
        mock_copyfileobj.assert_called_once()
        mock_file.file.close.assert_called_once()
        mock_rmtree.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_ocr_script_not_found(document_service):
    service, path_mocks = document_service

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "ocr_fail.pdf"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("44444444-4444-4444-4444-444444444444")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    mock_ocr_script_path_instance = MagicMock(spec=Path)
    mock_ocr_script_path_instance.is_file.return_value = False
    mock_ocr_script_path_instance.__str__ = MagicMock(return_value=str(OCR_SCRIPT_PATH))

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj") as mock_copyfileobj, patch(
        "shutil.rmtree"
    ) as mock_rmtree, patch("shutil.which", return_value="/usr/bin/python3"), patch(
        "backend.services.document_service.OCR_SCRIPT_PATH",
        mock_ocr_script_path_instance,
    ), patch("uuid.uuid4", return_value=batch_uuid_val):
        response = await service.save_and_process_documents([mock_file])

        assert response.overall_status == "Failed"
        assert len(response.results) == 1
        assert response.results[0].filename == "ocr_fail.pdf"
        assert response.results[0].success is False
        assert (
            "File saved, but processing could not be initiated."
            in response.results[0].message
        )
        assert (
            f"OCR script not found at {str(OCR_SCRIPT_PATH)}"
            in response.results[0].error_details
        )

        mock_copyfileobj.assert_called_once()
        mock_ocr_script_path_instance.is_file.assert_called_once()
        mock_rmtree.assert_called_once_with(expected_batch_dir_path)


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_ocr_script_failure(document_service):
    service, path_mocks = document_service

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "ocr_script_fails.pdf"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("55555555-5555-5555-5555-555555555555")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj") as mock_copyfileobj, patch(
        "shutil.rmtree"
    ) as mock_rmtree, patch("shutil.which", return_value="/usr/bin/python3"), patch(
        "subprocess.run"
    ) as mock_subprocess_run, patch("uuid.uuid4", return_value=batch_uuid_val):
        mock_process_result = MagicMock()
        mock_process_result.returncode = 1
        mock_process_result.stdout = ""
        mock_process_result.stderr = "OCR engine error"
        mock_subprocess_run.return_value = mock_process_result

        response = await service.save_and_process_documents([mock_file])

        assert response.overall_status == "Failed"
        assert len(response.results) == 1
        assert response.results[0].filename == "ocr_script_fails.pdf"
        assert response.results[0].success is False
        assert "File saved, but processing failed." in response.results[0].message
        assert "OCR script error: OCR engine error" in response.results[0].error_details

        mock_subprocess_run.assert_called_once()
        mock_rmtree.assert_called_once_with(expected_batch_dir_path)


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_filename_sanitization(document_service):
    service, path_mocks = document_service

    mock_file_problematic_name = MagicMock(spec=UploadFile)
    mock_file_problematic_name.filename = "file with spaces &*^%.docx"
    mock_file_problematic_name.file = MagicMock()

    mock_file_empty_name = MagicMock(spec=UploadFile)
    mock_file_empty_name.filename = ""
    mock_file_empty_name.file = MagicMock()

    uuid_for_batch = uuid.UUID("66666666-6666-6666-6666-666666666666")
    uuid_for_problematic_file_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    uuid_for_empty_filename_file_id = uuid.UUID("77777777-7777-7777-7777-777777777777")

    expected_batch_dir_path = RAW_UPLOAD_DIR / str(uuid_for_batch)
    expected_sanitized_name1 = "file_with_spaces_____.docx"
    expected_name_for_empty_file = f"{str(uuid_for_empty_filename_file_id)}_upload"

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj") as mock_copyfileobj, patch(
        "shutil.rmtree"
    ) as mock_rmtree, patch("shutil.which", return_value="/usr/bin/python3"), patch(
        "subprocess.run"
    ) as mock_subprocess_run, patch(
        "uuid.uuid4",
        side_effect=[
            uuid_for_batch,
            uuid_for_problematic_file_id,
            uuid_for_empty_filename_file_id,
        ],
    ):
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_process_result.stdout = "OCR successful"
        mock_process_result.stderr = ""
        mock_subprocess_run.return_value = mock_process_result

        files_to_process = [mock_file_problematic_name, mock_file_empty_name]
        response = await service.save_and_process_documents(files_to_process)

        assert response.overall_status == "Completed"
        assert len(response.results) == 2

        assert response.results[0].filename == "file with spaces &*^%.docx"
        assert response.results[0].success is True

        assert response.results[1].filename == ""
        assert response.results[1].success is True

        assert mock_copyfileobj.call_count == 2

        mock_open.assert_any_call(
            expected_batch_dir_path / expected_sanitized_name1, "wb+"
        )
        mock_open.assert_any_call(
            expected_batch_dir_path / expected_name_for_empty_file, "wb+"
        )

        mock_subprocess_run.assert_called_once()
        mock_rmtree.assert_called_once_with(expected_batch_dir_path)


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_cleanup_failure_in_finally_block(document_service):
    service, path_mocks = document_service
    mock_path_mkdir = path_mocks["mkdir"]
    mock_path_exists = path_mocks["exists"]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test_cleanup_fail.pdf"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("88888888-8888-8888-8888-888888888888")
    file_id_val = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    def mock_exists_side_effect_func(self_path_instance):
        if self_path_instance == expected_batch_dir_path:
            return True
        return False

    mock_path_exists.side_effect = mock_exists_side_effect_func
    mock_path_mkdir.return_value = None
    path_mocks["is_file"].return_value = True

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj") as mock_copyfileobj, patch(
        "shutil.rmtree", side_effect=OSError("Cleanup failed")
    ) as mock_rmtree, patch("shutil.which", return_value="/usr/bin/python3"), patch(
        "subprocess.run"
    ) as mock_subprocess_run, patch(
        "uuid.uuid4", side_effect=[batch_uuid_val, file_id_val]
    ), patch("backend.services.document_service.logger") as mock_logger:
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_subprocess_run.return_value = mock_process_result

        response = await service.save_and_process_documents([mock_file])

        assert response.overall_status == "Completed"
        assert len(response.results) == 1
        assert response.results[0].filename == "test_cleanup_fail.pdf"
        assert response.results[0].success is True
        assert "File processed successfully." in response.results[0].message

        mock_path_exists.assert_any_call(expected_batch_dir_path)
        mock_rmtree.assert_called_once_with(expected_batch_dir_path)
        mock_logger.error.assert_any_call(
            f"Error cleaning up temporary batch directory {expected_batch_dir_path}: Cleanup failed"
        )


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_python_executable_fallback(document_service):
    service, path_mocks = document_service
    mock_path_mkdir = path_mocks["mkdir"]
    mock_path_exists = path_mocks["exists"]
    mock_path_is_file = path_mocks["is_file"]

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test_python_fallback.pdf"
    mock_file.file = MagicMock()

    batch_uuid_val = uuid.UUID("99999999-9999-9999-9999-999999999999")
    file_id_val = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid_val)

    mock_path_exists.return_value = True
    mock_path_is_file.return_value = True
    mock_path_mkdir.return_value = None

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch("shutil.copyfileobj"), patch("shutil.rmtree"), patch(
        "shutil.which", side_effect=[None, None]
    ) as mock_which, patch("subprocess.run") as mock_subprocess_run, patch(
        "uuid.uuid4", side_effect=[batch_uuid_val, file_id_val]
    ):
        mock_process_result = MagicMock()
        mock_process_result.returncode = 0
        mock_subprocess_run.return_value = mock_process_result

        await service.save_and_process_documents([mock_file])

        mock_which.assert_has_calls([call("python"), call("python3")], any_order=False)
        assert mock_which.call_count == 2

        expected_python_executable_in_sut = "/usr/local/bin/python"

        mock_subprocess_run.assert_called_once_with(
            [
                expected_python_executable_in_sut,
                str(OCR_SCRIPT_PATH),
                "--src",
                str(expected_batch_dir_path),
                "--out",
                str(PROCESSED_TEXT_DIR),
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=APP_BASE_DIR,
        )


@pytest.mark.asyncio
@pytest.mark.reset_path_mocks_for_test
async def test_save_and_process_documents_multiple_files_mixed_results(
    document_service,
):
    service, path_mocks = document_service
    mock_path_mkdir = path_mocks["mkdir"]
    mock_path_exists = path_mocks["exists"]
    mock_path_is_file = path_mocks["is_file"]

    mock_file_ok = MagicMock(spec=UploadFile, filename="success.pdf", file=MagicMock())
    mock_file_save_fail = MagicMock(
        spec=UploadFile, filename="save_fail.txt", file=MagicMock()
    )
    mock_file_ocr_fail = MagicMock(
        spec=UploadFile, filename="ocr_fail.docx", file=MagicMock()
    )

    batch_uuid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    file_id_1_uuid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    file_id_2_uuid = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    file_id_3_uuid = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

    expected_batch_dir_path = RAW_UPLOAD_DIR / str(batch_uuid)

    def copyfileobj_side_effect(src, dest_file_object):
        if src == mock_file_save_fail.file:
            raise IOError("Simulated save error for save_fail.txt")
        return None

    mock_path_exists.return_value = True
    mock_path_is_file.return_value = True
    mock_path_mkdir.return_value = None

    with patch(
        "backend.services.document_service.open", new_callable=MagicMock
    ) as mock_open, patch(
        "shutil.copyfileobj", side_effect=copyfileobj_side_effect
    ) as mock_copyfileobj, patch("shutil.rmtree") as mock_rmtree, patch(
        "shutil.which", return_value="/usr/bin/python3"
    ), patch("subprocess.run") as mock_subprocess_run, patch(
        "uuid.uuid4",
        side_effect=[batch_uuid, file_id_1_uuid, file_id_2_uuid, file_id_3_uuid],
    ):
        mock_ocr_fail_result = MagicMock()
        mock_ocr_fail_result.returncode = 1
        mock_ocr_fail_result.stdout = ""
        mock_ocr_fail_result.stderr = "General OCR error"
        mock_subprocess_run.return_value = mock_ocr_fail_result

        files = [mock_file_ok, mock_file_save_fail, mock_file_ocr_fail]
        response = await service.save_and_process_documents(files)

        assert response.overall_status == "Failed"
        assert len(response.results) == 3

        results_map = {r.filename: r for r in response.results}

        res_ok_then_ocr_fail = results_map["success.pdf"]
        assert res_ok_then_ocr_fail.success is False
        assert "File saved, but processing failed." in res_ok_then_ocr_fail.message
        assert "General OCR error" in res_ok_then_ocr_fail.error_details

        res_save_fail = results_map["save_fail.txt"]
        assert res_save_fail.success is False
        assert (
            "Failed to save file: Simulated save error for save_fail.txt"
            in res_save_fail.message
        )

        res_ocr_fail_doc = results_map["ocr_fail.docx"]
        assert res_ocr_fail_doc.success is False
        assert "File saved, but processing failed." in res_ocr_fail_doc.message
        assert "General OCR error" in res_ocr_fail_doc.error_details

        assert mock_copyfileobj.call_count == 3

        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert args[0][3] == str(expected_batch_dir_path)

        mock_rmtree.assert_called_once_with(expected_batch_dir_path)

        mock_file_ok.file.close.assert_called_once()
        mock_file_save_fail.file.close.assert_called_once()
        mock_file_ocr_fail.file.close.assert_called_once()
