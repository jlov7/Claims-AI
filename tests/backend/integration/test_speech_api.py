import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import uuid

# Adjust the import path based on your project structure
# This assumes your tests are run from the root of the project or tests/backend/integration
from backend.core.config import get_settings

settings = get_settings()


# Test Client fixture from conftest.py should be available if running via pytest
# If not, or for standalone running, you might define it here:
# @pytest.fixture(scope="module")
# def client():
#     with TestClient(app) as c:
#         yield c


@pytest.mark.integration
@pytest.mark.api
async def test_generate_speech_success(
    client: AsyncClient,
    # mock_tts_service, # REMOVED
    # mock_minio_service_speech, # REMOVED
):  # client fixture from conftest.py
    test_text = "Hello, this is a test for speech generation."
    mock_audio_data = b"mock_mp3_audio_data"
    mock_filename = f"{uuid.uuid4().hex}.mp3"
    mock_audio_url = (
        f"http://localhost:9000/{settings.MINIO_SPEECH_BUCKET}/{mock_filename}"
    )

    # Mock the SpeechService methods
    # Path to SpeechService instance used by the router might vary based on DI
    # Assuming SpeechService is instantiated and its methods are called
    with patch(
        "backend.services.speech_service.SpeechService.generate_and_store_speech",
        new_callable=AsyncMock,
    ) as mock_generate_store:
        mock_generate_store.return_value = (mock_audio_url, mock_filename)

        response = await client.post(
            f"{settings.API_V1_STR}/speech",
            json={"text": test_text, "speaker_id": "p225", "language_id": "en"},
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["audio_url"] == mock_audio_url
        assert json_response["filename"] == mock_filename
        assert json_response["message"] == "Speech generated and stored successfully."
        mock_generate_store.assert_called_once_with(
            text=test_text, speaker_id="p225", language_id="en"
        )


@pytest.mark.api
@pytest.mark.asyncio
async def test_generate_speech_empty_text(client: AsyncClient):
    response = await client.post(f"{settings.API_V1_STR}/speech", json={"text": "  "})
    assert response.status_code == 400
    assert response.json()["detail"] == "Text cannot be empty."


@pytest.mark.api
@pytest.mark.asyncio
async def test_generate_speech_tts_unavailable(client: AsyncClient):
    test_text = "Test TTS unavailable."
    from fastapi import HTTPException

    with patch(
        "backend.services.speech_service.SpeechService.generate_and_store_speech",
        new_callable=AsyncMock,
    ) as mock_generate_store:
        mock_generate_store.side_effect = HTTPException(
            status_code=503, detail="TTS service unavailable"
        )

        response = await client.post(
            f"{settings.API_V1_STR}/speech", json={"text": test_text}
        )
        assert response.status_code == 503
        assert "TTS service unavailable" in response.json()["detail"]


@pytest.mark.api
@pytest.mark.asyncio
async def test_generate_speech_minio_error(client: AsyncClient):
    test_text = "Test Minio error."
    from fastapi import HTTPException

    with patch(
        "backend.services.speech_service.SpeechService.generate_and_store_speech",
        new_callable=AsyncMock,
    ) as mock_generate_store:
        mock_generate_store.side_effect = HTTPException(
            status_code=500, detail="Failed to store speech audio"
        )

        response = await client.post(
            f"{settings.API_V1_STR}/speech", json={"text": test_text}
        )
        assert response.status_code == 500
        assert "Failed to store speech audio" in response.json()["detail"]


# To run these tests, ensure pytest and necessary plugins (like pytest-asyncio) are installed.
# Command: pytest tests/backend/integration/test_speech_api.py -m api
