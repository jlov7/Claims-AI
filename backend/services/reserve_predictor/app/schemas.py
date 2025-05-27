from pydantic import BaseModel, Field

# Pydantic models for request and response validation


class PredictionRequest(BaseModel):
    # Define the expected input features for the model.
    # These should match the columns in `sample_data/settlements.csv`
    # that the CatBoost model was trained on.

    feature1: float = Field(..., example=10.0, description="Numerical feature 1.")
    feature2: float = Field(..., example=20.0, description="Numerical feature 2.")
    feature3: float = Field(..., example=30.0, description="Numerical feature 3.")
    injury_type: str = Field(
        ...,
        example="WHIPLASH",
        description="Type of injury (e.g., WHIPLASH, BACK_PAIN, FRACTURE, SOFT_TISSUE).",
    )

    # features: Dict[str, Any] = Field(..., example={"feature1": 1.0, "feature2": "value", "feature3": 0}, description="Key-value pairs of features for prediction.")

    # It's generally better to define explicit fields for type checking and OpenAPI documentation.
    # For example, if your model takes 'age' and 'claim_type':
    # age: int
    # claim_type: str
    # ... and so on for all features used by the model.
    # For now, using a generic Dict to get started quickly.
    # TODO: Update this with actual feature names and types from settlements.csv

    class Config:
        json_schema_extra = {
            "example": {
                "feature1": 15.5,
                "feature2": 25.0,
                "feature3": 35.2,
                "injury_type": "FRACTURE",
            }
        }


class PredictionResponse(BaseModel):
    prediction: float = Field(
        ..., example=75000.50, description="The predicted reserve amount."
    )
    model_version: str = Field(
        ...,
        example="0.1.0_catboost",
        description="Version of the model used for prediction.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 123456.78,
                "model_version": "0.1.0_catboost_dummy",
            }
        }
