import pytest
from fastapi.testclient import TestClient
import backend.api.v1.speech_router as speech_router
from backend.main import app

client = TestClient(app)


class DummySpeechService:
    async def generate_and_store_speech(self, text, speaker_id=None, language_id=None):
        return "http://example.com/audio.mp3", "audio.mp3"


@pytest.fixture(autouse=True)
def override_speech_service(monkeypatch):
    dummy = DummySpeechService()
    monkeypatch.setattr(speech_router, "get_speech_service", lambda: dummy)


def test_speech_success():
    response = client.post("/api/v1/speech", json={"text": "Hello world"})
    assert response.status_code == 200
    data = response.json()
    assert data.get("audio_url", "").endswith(".mp3")
    assert data.get("filename") == "audio.mp3"
    assert "message" in data


def test_speech_empty_text():
    response = client.post("/api/v1/speech", json={"text": "   "})
    assert response.status_code == 400
    detail = response.json().get("detail", "").lower()
    assert "text cannot be empty" in detail


def test_speech_service_error(monkeypatch):
    class ErrorService:
        async def generate_and_store_speech(
            self, text, speaker_id=None, language_id=None
        ):
            raise Exception("TTS failure")

    monkeypatch.setattr(speech_router, "get_speech_service", lambda: ErrorService())
    response = client.post("/api/v1/speech", json={"text": "Hello again"})
    assert response.status_code == 500
    detail = response.json().get("detail", "").lower()
    assert "unexpected error occurred during speech generation" in detail
