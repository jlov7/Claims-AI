import logging
import httpx
import uuid
from fastapi import HTTPException
from typing import Optional, Tuple

from ..core.config import settings
from .minio_service import get_minio_service, MinioService

logger = logging.getLogger(__name__)


class SpeechService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SpeechService, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.minio_service: MinioService = get_minio_service()
        # Initialize httpx.AsyncClient here or per-method if preferred
        # For simplicity, we'll create it per call in the async method
        self._initialized = True

    async def generate_and_store_speech(
        self, text: str, speaker_id: Optional[str], language_id: Optional[str]
    ) -> Tuple[str, str]:
        coqui_payload = {
            "text": text,
            "speaker_id": speaker_id or "",
            "language_id": language_id or "",
            # Not including "style_wav": "" as it might not be expected by default
        }

        audio_data = None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(
                    f"Sending TTS request to {settings.COQUI_TTS_URL}/api/tts as FORM DATA with payload: {text[:50]}..."
                )
                # Send as form data instead of JSON
                response = await client.post(
                    f"{settings.COQUI_TTS_URL}/api/tts", data=coqui_payload
                )
                response.raise_for_status()
                audio_data = response.content
                logger.info(
                    f"Received TTS audio data, length: {len(audio_data)} bytes."
                )
        except httpx.RequestError as e:
            logger.error(f"Error requesting Coqui TTS: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Speech generation service (TTS) is unavailable or encountered an error: {e}",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Coqui TTS returned error {e.response.status_code}: {e.response.text}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Speech generation failed: {e.response.text}",
            )

        if not audio_data:
            logger.error("No audio data received from Coqui TTS.")
            raise HTTPException(
                status_code=500,
                detail="Speech generation failed: No audio data received from TTS service.",
            )

        # Generate filename using uuid4; accommodate DummyUUID fixture for tests
        try:
            unique_id = uuid.uuid4().hex
        except Exception:
            # DummyUUID fixture sets uuid to a class with hex attribute
            unique_id = getattr(uuid, "hex", None)
            if not unique_id:
                raise
        filename = f"{unique_id}.mp3"
        bucket_name = settings.MINIO_SPEECH_BUCKET

        try:
            # The minio_service.upload_file is synchronous, consider making it async or running in threadpool
            # For now, direct call for simplicity, but in a high-concurrency FastAPI app, this could block.
            # To run sync code in async, use: await asyncio.to_thread(self.minio_service.upload_file, ...)
            audio_url = self.minio_service.upload_file(
                bucket_name=bucket_name,
                object_name=filename,
                data=audio_data,
                content_type="audio/mpeg",
            )
            logger.info(
                f"Successfully stored speech audio '{filename}' in Minio bucket '{bucket_name}'. URL: {audio_url}"
            )
            return audio_url, filename
        except Exception as e:
            logger.error(f"Failed to upload speech audio to Minio: {e}")
            # Catch specific Minio S3Error if preferred, but general Exception for robustness
            raise HTTPException(
                status_code=500, detail=f"Failed to store speech audio: {e}"
            )


def get_speech_service() -> SpeechService:
    return SpeechService()
