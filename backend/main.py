import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import status, Request
from fastapi.responses import ORJSONResponse
from contextlib import asynccontextmanager

from core.config import get_settings  # Import get_settings
# from core.kafka_client import KafkaClientManager # Assuming kafka_client is in core # REMOVED - Unused and module not found

# Get settings at the module level
settings = get_settings()

from api.v1 import (
    query_router,
    summarise_router,
    draft_router,
    precedent_router,
    speech_router,
    redteam_router,
    document_router,
    # langserve_event_router, # Added for langserve events --- Temporarily commented out
)

# Import the function that now returns a FastAPI sub-app instance
from services.langserve_app.app import add_all_langserve_routes
# Remove imports for add_routes and RunnablePassthrough from langserve/langchain_core if they were added for the previous strategy
# from langserve import add_routes 
# from langchain_core.runnables import RunnablePassthrough

logger = logging.getLogger(__name__)
# Basic config for logging, will be refined in startup
logging.basicConfig(level=settings.LOG_LEVEL.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application startup (lifespan)...")
    logger.info(
        f"Settings loaded via get_settings(): Project Name - {settings.PROJECT_NAME}, Log Level - {settings.LOG_LEVEL} (effective: {logging.getLogger().getEffectiveLevel()})"
    )
    logger.info(
        f"Ollama API Base: {settings.OLLAMA_BASE_URL}"
    )  # Changed from OLLAMA_API_BASE
    logger.info(f"Ollama Model Name: {settings.OLLAMA_MODEL_NAME}")
    logger.info(f"Embedding Model Name: {settings.EMBEDDING_MODEL_NAME}")
    logger.info(f"Chroma Host: {settings.CHROMA_HOST}")

    log_level_to_set = settings.LOG_LEVEL.upper()
    # Ensure root and uvicorn loggers are set correctly
    logging.getLogger().setLevel(log_level_to_set)
    logging.getLogger("uvicorn.access").setLevel(log_level_to_set)
    logging.getLogger("uvicorn.error").setLevel(log_level_to_set)
    logging.getLogger("uvicorn").setLevel(log_level_to_set)

    # Re-apply basicConfig to ensure handlers are set up with the potentially new level for the current process
    logging.basicConfig(
        level=log_level_to_set, force=True
    )  # force=True to override existing basicConfig

    logger.info(
        f"Settings loaded via get_settings(): Project Name - {settings.PROJECT_NAME}, Log Level - {settings.LOG_LEVEL} (effective: {log_level_to_set})"
    )
    logger.info(f"Ollama API Base: {settings.OLLAMA_BASE_URL}")
    logger.info(f"Ollama Model Name: {settings.OLLAMA_MODEL_NAME}")
    logger.info(f"Chroma Host: {settings.CHROMA_HOST}")

    yield
    # Shutdown logic (if any) can go here
    logger.info("Application shutdown (lifespan)...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    lifespan=lifespan,
    default_response_class=ORJSONResponse,  # Use ORJSONResponse for better performance
)

# Get the LangServe sub-application
langserve_sub_app = add_all_langserve_routes()
# Mount the LangServe sub-application at /langserve
app.mount("/langserve", langserve_sub_app, name="langserve_mounted_app")

# Add CORS middleware at module level
app.add_middleware(
    CORSMiddleware,
    # Allow all localhost ports for dev/demo
    allow_origins=[
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers at module level
app.include_router(query_router.router, prefix=settings.API_V1_STR, tags=["RAG"])
app.include_router(
    summarise_router.router, prefix=settings.API_V1_STR, tags=["Summarisation"]
)
app.include_router(draft_router.router, prefix=settings.API_V1_STR, tags=["Drafting"])
app.include_router(
    precedent_router.router, prefix=settings.API_V1_STR, tags=["Precedents"]
)
app.include_router(speech_router.router, prefix=settings.API_V1_STR, tags=["Speech"])
app.include_router(
    redteam_router.router, prefix=settings.API_V1_STR, tags=["Red Teaming"]
)
app.include_router(
    document_router.router,
    prefix=f"{settings.API_V1_STR}/documents",
    tags=["Documents"],
)

# app.include_router(langserve_event_router.router, prefix=settings.API_V1_STR, tags=["LangServe Events"]) # Temporarily commented out


@app.get("/health", summary="Check API Health", tags=["General"])
async def health_check():
    logger.info("Health check endpoint called.")
    core_components_ok = True
    details = {"core_services": "OK", "ollama_connection": "Unknown"}

    try:
        # Check if settings are loaded (minimal check for core service viability)
        if (
            not settings.PROJECT_NAME
        ):  # Basic check that settings object is somewhat populated
            raise ValueError("Settings not loaded properly.")

        # Check Ollama connection status
        if settings.OLLAMA_BASE_URL:  # Changed from OLLAMA_API_BASE
            logger.info(
                f"Ollama API base configured: {settings.OLLAMA_BASE_URL}"
            )  # Changed
            # Consider adding a more active check here if feasible, e.g., a lightweight ping or model list
            # For now, just checking if the URL is configured is a basic step.
            details["ollama_connection"] = (
                f"Configured ({settings.OLLAMA_BASE_URL})"  # Changed
            )
        else:
            details["ollama_connection"] = "Not Configured"
            core_components_ok = (
                False  # If Ollama isn't configured, consider it a core issue
            )

    except Exception as e:
        logger.error(
            f"Health check: Core component initialization issue: {e}", exc_info=True
        )
        details["core_services"] = f"Error: {str(e)}"
        core_components_ok = False

    if core_components_ok:
        logger.info("Core application settings seem accessible.")
        return {
            "status": "Ok",
            "message": "API is healthy. Check component-specific logs for detailed status.",
        }
    else:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: Core components might be down - {details['core_services']}",
        )


@app.get("/api/v1/health", summary="Check API Health (v1)", tags=["General"])
async def health_check_v1():
    # Reuse the same logic as /health
    logger.info("Health check v1 endpoint called.")
    try:
        if settings.OLLAMA_BASE_URL:
            logger.info(f"Ollama API base configured: {settings.OLLAMA_BASE_URL}")
        else:
            logger.warning("Ollama API base not configured in settings.")
        logger.info("Core application settings seem accessible.")
    except Exception as e:
        logger.error(
            f"Health check v1: Core component initialization issue: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: Core components might be down - {str(e)}",
        )
    return {
        "status": "Ok",
        "message": "API is healthy. Check component-specific logs for detailed status.",
    }


@app.get("/", summary="Root endpoint", tags=["General"])
async def read_root():
    logger.info("Root endpoint called.")
    return {"message": "Welcome to Claims-AI API. Visit /docs for API documentation."}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Log the full Pydantic validation error and return it to the caller.
    This guarantees we can always see why a 422 happened.
    Ensures that context in errors is JSON serializable.
    """
    # Process errors to ensure serializability
    serializable_errors = []
    for error in exc.errors():
        new_error = error.copy()  # Start with a copy
        if "ctx" in new_error and new_error["ctx"] is not None:
            # Ensure 'ctx' itself is a dict, if it exists
            if isinstance(new_error["ctx"], dict):
                new_ctx = {}
                for key, value in new_error["ctx"].items():
                    if isinstance(
                        value, ValueError
                    ):  # Or any other non-serializable type
                        new_ctx[key] = str(value)
                    else:
                        new_ctx[key] = value
                new_error["ctx"] = new_ctx
            else:  # if ctx is not a dict but some other non-serializable type
                new_error["ctx"] = str(new_error["ctx"])

        serializable_errors.append(new_error)

    logger.error(
        "422 Validation error on %s – %s",
        request.url.path,
        serializable_errors,  # Log the processed errors
        exc_info=False,  # exc_info=True would log the original exception again
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": serializable_errors},  # Use processed errors
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
