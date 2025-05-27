from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from pathlib import Path

from .model_loader import (
    get_model,
    get_model_version,
    predict_reserve,
    load_model,
    settings as model_settings,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reserve Predictor API",
    description="API for predicting claim reserve amounts.",
    version="0.1.0",
)

# CORS middleware configuration
origins = [
    "*",  # Allow all origins for now, restrict in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    # Define the expected request body for prediction
    # Based on sample_data/settlements.csv
    feature1: float
    feature2: float  # Assuming feature2 from CSV is also float, despite integer values in sample
    feature3: float  # Assuming feature3 from CSV is also float
    injury_type: str


class PredictionResponse(BaseModel):
    prediction: float
    model_version: str


@app.on_event("startup")
async def startup_event():
    logger.info("Reserve Predictor Microservice starting up...")
    logger.info(f"Attempting to load model from path: {model_settings.model_path}")
    model = load_model()  # Attempt to load the model at startup
    if model is None:
        logger.warning(
            "Model could not be loaded at startup (or dummy creation failed). Predictions might fail or use a dummy if one was successfully created in a previous attempt."
        )
    else:
        logger.info(
            f"Model loaded successfully at startup. Version: {get_model_version()}"
        )


@app.post("/predict", response_model=PredictionResponse)
async def predict_reserve_endpoint(request: PredictionRequest):
    """
    Predicts the reserve amount for a claim based on input features.
    Uses the loaded CatBoost model.
    """
    logger.info(f"Received prediction request: {request.dict()}")

    model = get_model()
    if model is None:
        logger.error(
            "Prediction failed: Model is not loaded and dummy model could not be established."
        )
        raise HTTPException(
            status_code=503,
            detail="Model not available. Please ensure it is loaded or a dummy can be created.",
        )

    try:
        # Convert Pydantic model to dict for the predict_reserve function
        features_dict = request.dict()

        prediction_value = predict_reserve(features_dict)
        current_model_version = get_model_version()

        logger.info(
            f"Prediction successful: {prediction_value}, Model Version: {current_model_version}"
        )
        return PredictionResponse(
            prediction=prediction_value, model_version=current_model_version
        )

    except ValueError as ve:
        # Specifically catch ValueError from predict_reserve if model is not loaded or features are bad
        logger.error(f"Prediction error (ValueError): {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        # Catch RuntimeError from predict_reserve for other prediction failures
        logger.error(f"Prediction error (RuntimeError): {re}")
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        logger.exception(
            "An unexpected error occurred during prediction."
        )  # Logs full stack trace
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    model_loaded_status = get_model() is not None
    current_model_version = "N/A"
    if model_loaded_status:
        current_model_version = get_model_version()

    return {
        "status": "ok",
        "model_loaded": model_loaded_status,
        "model_version": current_model_version,
        "configured_model_path": str(
            model_settings.model_path.resolve()
            if model_settings.model_path.is_absolute()
            else (Path.cwd() / model_settings.model_path).resolve()
        ),  # Show resolved path
    }


if __name__ == "__main__":
    import uvicorn

    # Port 8001 to avoid conflict with main app (usually 8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)

# To run this app locally (for testing, assuming uvicorn is installed):
# Ensure you are in the `backend/services/reserve_predictor` directory.
# Command: uvicorn app.main:app --reload --port 8001
#
# Or, if in the project root:
# Command: uvicorn backend.services.reserve_predictor.app.main:app --reload --port 8001
#
# A Dockerfile will be added later for containerized execution.
