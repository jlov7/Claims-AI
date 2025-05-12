from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import status, Request
from fastapi.responses import ORJSONResponse
from contextlib import asynccontextmanager

from backend.core.config import get_settings  # Import get_settings

# Get settings at the module level
settings = get_settings()

from backend.api.v1 import (
    query_router,
    summarise_router,
    draft_router,
    precedent_router,
    speech_router,
    redteam_router,
    document_router,
)

logger = logging.getLogger(__name__)
# Basic config for logging, will be refined in startup
logging.basicConfig(level=settings.LOG_LEVEL.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Application startup (lifespan)...")

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
    logger.info(f"LM Studio API Base: {settings.PHI4_API_BASE}")
    logger.info(f"ChromaDB Host: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")

    yield
    # Shutdown logic (if any) can go here
    logger.info("Application shutdown (lifespan)...")


app = FastAPI(
    title="Claims-AI API",
    description="API for Claims-AI document processing, Q&A, and strategy note generation.",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# Add CORS middleware at module level
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
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


@app.get("/health", summary="Check API Health", tags=["General"])
async def health_check():
    # settings is already available at module level
    logger.info("Health check endpoint called.")
    try:
        if settings.PHI4_API_BASE:
            logger.info(f"LM Studio API base configured: {settings.PHI4_API_BASE}")
        else:
            logger.warning("LM Studio API base not configured in settings.")
        logger.info("Core application settings seem accessible.")
    except Exception as e:
        logger.error(
            f"Health check: Core component initialization issue: {e}", exc_info=True
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
