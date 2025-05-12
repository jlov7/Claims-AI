from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path  # Import Path
import os  # Import os
import logging
import sys  # Add this import
from typing import Optional, List  # Ensure Union is imported
from dotenv import load_dotenv

# Determine the project root directory
# Assuming config.py is in backend/core/, so ../../ gives the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

# Load .env into OS environment without overriding existing OS vars
load_dotenv(dotenv_path=str(DOTENV_PATH), override=False)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Docker & Service Ports
    BACKEND_PORT: int = 8000

    # FastAPI
    PROJECT_NAME: str = "Claims-AI MVP"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "DEBUG"

    # CORS Settings
    RAW_CORS_ORIGINS: str = "http://localhost:5173"  # Comma-separated string from .env
    BACKEND_CORS_ORIGINS: List[str] = []  # Will be populated by validator

    # LM Studio (Phi-4)
    PHI4_API_BASE: str = "http://host.docker.internal:1234/v1"
    PHI4_MODEL_NAME: str = (
        "phi-4-reasoning-plus"  # Ensure this matches your LM Studio model
    )
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048  # Max tokens for Phi-4-plus, adjust if needed

    # ChromaDB
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int
    CHROMA_COLLECTION_NAME: str = "claims_collection"
    CHROMA_PRECEDENTS_COLLECTION_NAME: str = "claims_precedents"
    CHROMA_USER: Optional[str] = None  # Added for optional auth
    CHROMA_PASSWORD: Optional[str] = None  # Added for optional auth
    EMBEDDING_MODEL_NAME: str = (
        "text-embedding-3-small"  # For OpenAI, or local equivalent
    )
    RAG_NUM_SOURCES: int = 3  # Number of source chunks to retrieve

    # Phase 4: Innovation - Confidence & Self-Healing
    CONFIDENCE_THRESHOLD_SELF_HEAL: int = (
        3  # Score below which self-healing is triggered
    )
    SELF_HEAL_MAX_ATTEMPTS: int = 1  # Max attempts for self-healing

    # Minio
    MINIO_URL: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_RAW_BUCKET: str = "raw-documents"
    MINIO_PROCESSED_TEXT_BUCKET: str = "processed-text"
    MINIO_EMBEDDINGS_BUCKET: str = "embeddings"
    MINIO_OUTPUTS_BUCKET: str = "outputs"  # For general outputs like strategy notes
    MINIO_SPEECH_BUCKET: str = "speech-audio"  # For MP3s from TTS

    # Coqui TTS Configuration
    COQUI_TTS_URL: str = (
        "http://tts:5002"  # Service name for Docker, localhost for local script
    )

    # PostgreSQL
    POSTGRES_USER: str = "claims_user"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: (
        str  # Automatically constructed if other PG vars are set, or set directly
    )

    # Phase 4: Innovation Layer
    # P4.A: Nearest Precedent Finder
    CHROMA_PRECEDENTS_COLLECTION_NAME: str = "claims_precedents"
    # P4.B: Confidence Meter
    CONFIDENCE_THRESHOLD_SELF_HEAL: int = 3
    SELF_HEAL_MAX_ATTEMPTS: int = 1  # Number of re-prompts if confidence is low
    # P4.D: Red Team
    REDTEAM_PROMPTS_FILE: str = "backend/security/redteam_prompts.yml"

    model_config = SettingsConfigDict(
        extra="ignore"  # Allow extra fields from OS environment
    )

    @classmethod
    def customise_sources(
        cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Load .env first, then let environment variables override those values
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @field_validator("CHROMA_PORT", mode="before")
    def clean_chroma_port(cls, value):
        if isinstance(value, str):
            cleaned_value = value.split("#")[0].strip()
            print(
                f"DEBUG: Validating CHROMA_PORT. Original: '{value}', Cleaned: '{cleaned_value}'"
            )
            try:
                return int(cleaned_value)
            except ValueError as e:
                print(
                    f"DEBUG: Error converting cleaned CHROMA_PORT '{cleaned_value}' to int: {e}"
                )
                raise ValueError(
                    f"Invalid CHROMA_PORT: '{value}'. Cleaned to '{cleaned_value}' but still not a valid int."
                ) from e
        print(
            f"DEBUG: CHROMA_PORT is not a string: '{value}' (type: {type(value)}). Passing through."
        )
        return value

    @model_validator(mode="after")
    def assemble_cors_origins(
        cls, values: "Settings"
    ) -> "Settings":  # Use Self for type hint if Python 3.11+
        raw_origins = values.RAW_CORS_ORIGINS  # Direct attribute access
        if isinstance(raw_origins, str):
            values.BACKEND_CORS_ORIGINS = [
                origin.strip() for origin in raw_origins.split(",") if origin.strip()
            ]
        elif (
            not values.BACKEND_CORS_ORIGINS
        ):  # If not set by raw and not already populated
            values.BACKEND_CORS_ORIGINS = ["http://localhost:5173"]  # Default
        return values

    def model_post_init(self, __context):
        # This method is called after the model is initialized and validated.
        # For raw inspection *before* validation, it's trickier with Pydantic v2 BaseSettings.
        # However, we can inspect what os.getenv would provide for CHROMA_PORT here
        # to see if it matches the error.
        raw_chroma_port_from_os = os.getenv("CHROMA_PORT")
        print(
            f"DEBUG: Raw CHROMA_PORT from os.getenv just before/during Settings init: '{raw_chroma_port_from_os}'"
        )
        # Note: This runs *after* Pydantic has already tried to parse and potentially failed.
        # A more involved way would be to customize the Pydantic settings source.


def get_settings() -> Settings:
    settings = Settings()

    # --- Pytest specific overrides ---
    # Check if running under pytest. This is a common heuristic.
    is_pytest_run = any("pytest" in arg for arg in sys.argv)
    if is_pytest_run:
        print(
            "DEBUG: Pytest environment detected. Overriding CHROMA_HOST to 'localhost' and CHROMA_PORT to 8008."
        )
        settings.CHROMA_HOST = "localhost"
        settings.CHROMA_PORT = 8008  # Explicitly set for pytest
        settings.PHI4_API_BASE = (
            "http://localhost:1234/v1"  # Added this line for pytest
        )
    # --- End Pytest specific overrides ---

    # Example of how to construct DATABASE_URL if not explicitly set in .env
    # This is often handled by libraries like SQLAlchemy, but good to be aware
    if not settings.DATABASE_URL and all(
        [
            settings.POSTGRES_USER,
            settings.POSTGRES_PASSWORD,
            settings.POSTGRES_HOST,
            settings.POSTGRES_PORT,
            settings.POSTGRES_DB,
        ]
    ):
        settings.DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

    # You might want to add a check here if DATABASE_URL is still None and raise an error
    # or provide a default for local development if appropriate.
    return settings


settings = get_settings()  # Create the global instance for other modules to import

# You might want to add a check here if DATABASE_URL is still None and raise an error
# or provide a default for local development if appropriate.

# For local testing convenience if MinIO is not running or accessible
# For example, when running pytest, you might want to disable MinIO interactions
# if not os.getenv("CI"): # Example: Disable in CI if not configured
#     MINIO_URL: Optional[str] = None

# Optional: Add a logging statement to confirm settings are loaded
# import logging
# logging.basicConfig(level=settings.LOG_LEVEL.upper())
# logging.getLogger(__name__).info(f"Settings loaded: Project '{settings.PROJECT_NAME}', Environment: '{settings.ENVIRONMENT}'") # Assuming ENVIRONMENT is added
# logging.getLogger(__name__).debug(f"Full settings: {settings.model_dump_json(indent=2)}")
