import pytest
from backend.services.speech_service import SpeechService
from backend.services.speech_service import settings as speech_settings


@pytest.fixture(autouse=True)
def dummy_uuid(monkeypatch):
    class DummyUUID:
        hex = "fixeduuid"

    monkeypatch.setattr("backend.services.speech_service.uuid", DummyUUID)


@pytest.fixture
def service(monkeypatch):
    # Reset singleton so patched get_minio_service is used
    from backend.services.speech_service import SpeechService

    SpeechService._instance = None

    # Stub AsyncClient
    class DummyResponse:
        def __init__(self, content=b"data", status_code=200):
            self.content = content
            self.status_code = status_code

        def raise_for_status(self):
            pass

    class DummyClient:
        def __init__(self, *args, **kwargs):
            # Accept any init arguments (e.g., timeout)
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, data):
            return DummyResponse()

    monkeypatch.setattr(
        "backend.services.speech_service.httpx.AsyncClient", DummyClient
    )

    # Stub MinioService.upload_file
    class DummyMinio:
        def upload_file(self, bucket_name, object_name, data, content_type):
            return f"http://url/{bucket_name}/{object_name}"

    monkeypatch.setattr(
        "backend.services.speech_service.get_minio_service", lambda: DummyMinio()
    )
    return SpeechService()


def test_singleton():
    s1 = SpeechService()
    s2 = SpeechService()
    assert s1 is s2


@pytest.mark.asyncio
async def test_generate_and_store_speech_success(service):
    svc = service
    url, filename = await svc.generate_and_store_speech("text", None, None)
    assert url == f"http://url/{speech_settings.MINIO_SPEECH_BUCKET}/{filename}"
    assert filename.endswith(".mp3")


@pytest.mark.asyncio
async def test_generate_and_store_speech_no_audio(service, monkeypatch):
    # Stub post to return empty content
    class DummyResponseEmpty:
        content = b""
        status_code = 200

        def raise_for_status(self):
            pass

    class DummyClientEmpty:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, data):
            return DummyResponseEmpty()

    monkeypatch.setattr(
        "backend.services.speech_service.httpx.AsyncClient", DummyClientEmpty
    )
    svc = service
    with pytest.raises(Exception):
        await svc.generate_and_store_speech("text", None, None)
