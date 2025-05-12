import logging
from fastapi import APIRouter, HTTPException

from ...services.speech_service import get_speech_service
from ...models import SpeechRequest, SpeechResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/speech", response_model=SpeechResponse, tags=["Speech"])
async def generate_speech_endpoint(request: SpeechRequest):
    """
    Generates speech from text using Coqui TTS, stores it in Minio, and returns the audio URL.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        logger.info(
            f"Received speech generation request for text: {request.text[:50]}..."
        )
        # Fetch the speech service at runtime to allow overrides
        speech_service = get_speech_service()
        audio_url, filename = await speech_service.generate_and_store_speech(
            text=request.text,
            speaker_id=request.speaker_id,
            language_id=request.language_id,
        )
        return SpeechResponse(
            audio_url=audio_url,
            filename=filename,
            message="Speech generated and stored successfully.",
        )
    except HTTPException as e:
        # Re-raise HTTPExceptions thrown by the service (e.g., TTS unavailable, Minio error)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in speech endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during speech generation: {str(e)}",
        )
