from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path  # Import Path
import os  # Import os
import logging
import sys  # Add this import
from typing import Optional, List  # Ensure Union is imported
from dotenv import load_dotenv
from functools import lru_cache  # Import lru_cache

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
    PROJECT_VERSION: str = "0.1.0"  # Added
    PROJECT_DESCRIPTION: str = (
        "API for Claims-AI agentic workflows, document processing, Q&A, and strategy note generation."  # Added
    )
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "DEBUG"

    # CORS Settings
    RAW_CORS_ORIGINS: str = "http://localhost:5173"  # Comma-separated string from .env
    BACKEND_CORS_ORIGINS: List[str] = []  # Will be populated by validator

    # Ollama
    OLLAMA_BASE_URL: str = (
        "http://host.docker.internal:11434"  # Default for Dockerized services to reach host Ollama
    )
    OLLAMA_MODEL_NAME: str = "mistral:7b-instruct"  # Default generation model
    LLM_TEMPERATURE: float = (
        0.1  # Already present, ensure it's used (was defined twice, consolidating)
    )
    LLM_MAX_TOKENS: int = (
        2048  # Already present, ensure it's used (was defined twice, consolidating)
    )

    # ChromaDB
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int
    CHROMA_COLLECTION_NAME: str = (
        "claims_collection"  # Changed to claims_collection to match frontend expectations
    )
    CHROMA_PRECEDENTS_COLLECTION_NAME: str = "claims_precedents"
    CHROMA_USER: Optional[str] = None  # Added for optional auth
    CHROMA_PASSWORD: Optional[str] = None  # Added for optional auth
    EMBEDDING_MODEL_NAME: str = (
        "nomic-embed-text:latest"  # Default embedding model, ensure :latest matches ollama list output if intended
    )
    RAG_NUM_SOURCES: int = 3  # Number of source chunks to retrieve

    # Phase 4: Innovation - Confidence & Self-Healing
    CONFIDENCE_THRESHOLD_SELF_HEAL: int = (
        3  # Score below which self-healing is triggered
    )
    SELF_HEAL_MAX_ATTEMPTS: int = (
        2  # Increased from 1 to allow more self-healing attempts
    )

    # Minio
    MINIO_URL: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_RAW_BUCKET: str = "raw-documents"
    MINIO_PROCESSED_BUCKET: str = "processed-text"
    MINIO_TEMP_UPLOAD_BUCKET: str = "temp-raw-uploads"
    MINIO_EMBEDDINGS_BUCKET: str = "embeddings"
    MINIO_OUTPUTS_BUCKET: str = "outputs"  # For general outputs like strategy notes
    MINIO_SPEECH_BUCKET: str = "speech-audio"  # For MP3s from TTS

    # Coqui TTS Configuration
    COQUI_TTS_URL: str = (
        "http://tts:5002"  # Service name for Docker, localhost for local script
    )

    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS"
    )
    KAFKA_CONSUMER_GROUP: str = Field(
        default="claims_ai_consumer_group", env="KAFKA_CONSUMER_GROUP"
    )
    KAFKA_RAW_TOPIC: str = Field(default="raw-claims-input", env="KAFKA_RAW_TOPIC")

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

    # Reserve Predictor Microservice
    RESERVE_PREDICTOR_URL: str = Field(
        default="http://localhost:8001/predict",
        env="RESERVE_PREDICTOR_URL",
        description="URL for the Reserve Predictor microservice's predict endpoint.",
    )

    # Minio / S3
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")

    # LangServe specific settings
    LANGSERVE_ENABLE_FEEDBACK: bool = Field(
        default=False, env="LANGSERVE_ENABLE_FEEDBACK"
    )
    LANGSERVE_ENABLE_PUBLIC_TRACE: bool = Field(
        default=False, env="LANGSERVE_ENABLE_PUBLIC_TRACE"
    )

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
            # First, remove comments. Then, strip whitespace. Finally, strip potential surrounding quotes.
            cleaned_value = value.split("#")[0].strip().strip("'\"")
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

    @model_validator(mode="before")
    @classmethod
    def assemble_database_url(cls, values: dict) -> dict:
        """Construct DATABASE_URL from components if not explicitly provided."""
        if values.get("DATABASE_URL"):
            return values  # If DATABASE_URL is already set, do nothing

        db_user = values.get("POSTGRES_USER")
        db_password = values.get("POSTGRES_PASSWORD")
        db_host = values.get("POSTGRES_HOST")
        db_port = values.get("POSTGRES_PORT")
        db_name = values.get("POSTGRES_DB")

        if all([db_user, db_password, db_host, db_port, db_name]):
            values["DATABASE_URL"] = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )
            logger.debug(f"Constructed DATABASE_URL: {values['DATABASE_URL']}")
        # If components are missing and DATABASE_URL isn't set, validation will fail later for DATABASE_URL if it's a required field without a default.
        # If DATABASE_URL is Optional, it will remain None.
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


@lru_cache()  # Keep the decorator for non-test runs
def get_settings() -> Settings:
    # --- Pytest specific detection ---
    # It's important this check happens *before* any potential return from cache
    # or early exit, to ensure test overrides are always considered.
    is_pytest_run = any("pytest" in arg for arg in sys.argv)

    if is_pytest_run:
        # For pytest runs, we want to ensure we ALWAYS re-evaluate settings
        # to pick up monkeypatches and avoid stale cache from other tests/sessions.
        # Temporarily 'uncache' or bypass for this call if possible,
        # or create a fresh instance and apply overrides.
        # The simplest way given lru_cache is to clear it if we know it's a test call
        # *before* creating/returning the settings object for this call.
        # However, get_settings.cache_clear() here would affect subsequent non-test calls
        # if the test runner imports this module multiple times or in complex ways.

        # Create a fresh settings object for tests and apply overrides directly.
        # This bypasses the cache for test runs more cleanly.
        print(
            "DEBUG: Pytest environment detected in get_settings(). Creating fresh Settings object."
        )
        settings_obj = Settings()  # Create a new instance

        # Apply pytest-specific overrides
        print(
            "DEBUG: Pytest environment detected. Overriding CHROMA_HOST to 'localhost' and CHROMA_PORT to 8008."
        )
        settings_obj.CHROMA_HOST = "localhost"
        settings_obj.CHROMA_PORT = 8008
        # settings_obj.OLLAMA_API_BASE = "http://localhost:11434/v1" # This field no longer exists and should not be set
        settings_obj.OLLAMA_MODEL_NAME = (
            "mistral:7b-instruct"  # Explicitly set for tests, though it matches default
        )
        settings_obj.EMBEDDING_MODEL_NAME = (
            "nomic-embed-text"  # Test-specific override (no :latest)
        )

        # Ensure LangSmith is off for tests
        os.environ["LANGCHAIN_API_KEY"] = ""
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

        # Construct DATABASE_URL for tests if components are available and URL isn't set
        if not settings_obj.DATABASE_URL and all(
            [
                settings_obj.POSTGRES_USER,
                settings_obj.POSTGRES_PASSWORD,
                settings_obj.POSTGRES_HOST,
                settings_obj.POSTGRES_PORT,
                settings_obj.POSTGRES_DB,
            ]
        ):
            settings_obj.DATABASE_URL = f"postgresql://{settings_obj.POSTGRES_USER}:{settings_obj.POSTGRES_PASSWORD}@{settings_obj.POSTGRES_HOST}:{settings_obj.POSTGRES_PORT}/{settings_obj.POSTGRES_DB}"
            logger.debug(
                f"Constructed DATABASE_URL for tests: {settings_obj.DATABASE_URL}"
            )

        return settings_obj

    # For non-pytest runs, proceed as before (relying on lru_cache at the decorator level)
    # The @lru_cache decorator will handle caching for non-test calls.
    # logger.debug("Loading settings...")
    return Settings()


settings = get_settings()

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
