import pickle
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd  # Required by CatBoost, even if not directly used for simple predict
from pydantic_settings import BaseSettings
from catboost import CatBoostRegressor  # Assuming CatBoostRegressor was used

logger = logging.getLogger(__name__)

# Global variable to hold the loaded model
# This is a common pattern for in-memory models in services
_model: Optional[CatBoostRegressor] = None
_model_version: str = (
    "catboost_default_v0.1"  # Could be loaded from model metadata if saved
)


class ReservePredictorSettings(BaseSettings):
    # Path to the pickled CatBoost model file.
    # Default assumes it's in a 'model_artefacts' subdirectory relative to this file's location
    # or in `sample_data` at project root as per task list.
    # Let's prioritize sample_data if it exists, then a local 'model_artefacts'
    # MODEL_PATH: FilePath = Field(default=Path(__file__).parent.parent / "model_artefacts" / "catboost_model.pkl")
    model_path: Path = Path("sample_data/catboost_model.pkl")  # Default path
    # One of the challenges is that Pydantic's FilePath validates at initialization,
    # and the file might not exist when the module is first imported (e.g. before Docker build copies it).
    # Using str and validating in load_model might be more flexible for now.

    # Allow overriding via environment variable
    # e.g., RESERVE_MODEL_PATH=/app/models/catboost_model.pkl
    class Config:
        env_prefix = (
            "RESERVE_"  # Not standard, but illustrates custom prefix if needed.
        )
        # Standard is usually no prefix or direct var name matching.
        # For this, let's assume direct env var `RESERVE_MODEL_PATH`
        # For Pydantic V2, env_prefix is not used in BaseSettings.Config directly.
        # We'll rely on the field name `model_path` matching `RESERVE_MODEL_PATH` if set.


settings = ReservePredictorSettings()


def load_model() -> Optional[CatBoostRegressor]:
    """
    Loads the CatBoost model from a pickle file.
    """
    global _model
    global _model_version

    model_file_path = settings.model_path

    # Resolve path if it's relative (e.g., from project root)
    if not model_file_path.is_absolute():
        # Try resolving from current working directory (likely project root when running uvicorn from there)
        # Or relative to this file's location if running script directly.
        # For robustness in a service, absolute paths or paths relative to a known app root are better.
        # Let's assume it's relative to the project root if not absolute.
        base_path_to_try = Path(os.getenv("APP_ROOT_DIR", Path.cwd()))
        resolved_path = base_path_to_try / model_file_path
        if (
            not resolved_path.exists() and Path.cwd() != base_path_to_try
        ):  # Try relative to actual cwd if different
            resolved_path = Path.cwd() / model_file_path
        model_file_path = resolved_path

    if not model_file_path.exists():
        logger.error(
            f"Model file not found at {model_file_path}. Attempted to resolve from {settings.model_path}"
        )
        # Try a common alternative if in a service context
        alt_path = (
            Path.cwd()
            / "backend"
            / "services"
            / "reserve_predictor"
            / settings.model_path
        )
        if alt_path.exists():
            model_file_path = alt_path
            logger.info(f"Found model at alternative path: {model_file_path}")
        else:
            logger.error(f"Model also not found at alternative path: {alt_path}")
            # For demo, create a dummy model if not found
            logger.warning("No model found. Creating and saving a dummy model.")
            _model = _create_and_save_dummy_model(model_file_path)
            if _model:
                _model_version = "catboost_dummy_v0.1_created"
                logger.info(f"Dummy model created and saved to {model_file_path}")
            return _model

    try:
        with open(model_file_path, "rb") as f:
            model_data = pickle.load(f)
            if (
                isinstance(model_data, dict)
                and "model" in model_data
                and "version" in model_data
            ):
                _model = model_data["model"]
                _model_version = model_data["version"]
            elif isinstance(
                model_data, CatBoostRegressor
            ):  # Legacy format, just the model
                _model = model_data
                # _model_version remains default or can be derived from file name if convention exists
            else:
                logger.error(f"Unexpected model data format in {model_file_path}")
                return None

        logger.info(
            f"Model loaded successfully from {model_file_path}. Version: {_model_version}"
        )
        return _model
    except FileNotFoundError:
        logger.error(f"Model file not found at {model_file_path} during open attempt.")
        return None
    except pickle.UnpicklingError as e:
        logger.error(f"Error unpickling model from {model_file_path}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while loading the model from {model_file_path}: {e}"
        )
        return None


def _create_and_save_dummy_model(path_to_save: Path) -> Optional[CatBoostRegressor]:
    try:
        # Create a very simple dummy model for placeholder purposes
        # This requires pandas and catboost to be installed
        train_data = pd.DataFrame(
            {
                "feature1": [10, 15, 5, 20],
                "feature2": [20, 25, 15, 30],
                "feature3": [30, 35, 25, 40],
                "injury_type": [
                    "WHIPLASH",
                    "BACK_PAIN",
                    "FRACTURE",
                    "WHIPLASH",
                ],  # CatBoost handles categorical
                "settlement_amount": [5000, 7500, 10000, 6000],
            }
        )
        train_labels = train_data["settlement_amount"]
        train_features = train_data.drop("settlement_amount", axis=1)

        # Specify categorical features
        categorical_features_indices = [
            i for i, col in enumerate(train_features.columns) if col == "injury_type"
        ]

        dummy_model = CatBoostRegressor(
            iterations=2, depth=2, learning_rate=0.5, loss_function="RMSE", verbose=0
        )
        dummy_model.fit(
            train_features, train_labels, cat_features=categorical_features_indices
        )

        # Ensure parent directory exists
        path_to_save.parent.mkdir(parents=True, exist_ok=True)

        model_data_to_save = {
            "model": dummy_model,
            "version": "catboost_dummy_v0.1_created",
        }
        with open(path_to_save, "wb") as f:
            pickle.dump(model_data_to_save, f)
        logger.info(f"Dummy model saved to {path_to_save}")
        return dummy_model
    except Exception as e:
        logger.error(f"Failed to create or save dummy model: {e}")
        return None


def get_model() -> Optional[CatBoostRegressor]:
    """Returns the loaded model. If not loaded, attempts to load it first."""
    global _model
    if _model is None:
        logger.info("Model not yet loaded. Attempting to load now.")
        load_model()  # Try to load with default path
    return _model


def get_model_version() -> str:
    global _model_version
    if _model is None:  # Ensure model is loaded to get its version
        get_model()
    return _model_version


def predict_reserve(features_dict: Dict[str, Any]) -> float:
    """
    Predicts a reserve amount based on input features using the loaded CatBoost model.
    The `features_dict` should contain keys and values expected by the model.
    """
    model = get_model()
    if model is None:
        logger.error("Prediction cannot be made: Model is not loaded.")
        raise ValueError("Model not available. Cannot make prediction.")

    try:
        # Prepare dataframe for prediction, matching the training script
        # Expected features from PredictionRequest: feature1, feature2, feature3, injury_type

        # Create a DataFrame from the input features
        df_input = pd.DataFrame([features_dict])

        # Define all possible injury categories seen during training (alphanetically sorted for consistency)
        # From dummy settlements.csv: BACK_PAIN, FRACTURE, SOFT_TISSUE, WHIPLASH
        known_injury_categories = sorted(
            ["BACK_PAIN", "FRACTURE", "SOFT_TISSUE", "WHIPLASH"]
        )

        # One-hot encode 'injury_type'.
        # The training script (train_reserve_model.py) used pd.get_dummies(data, columns=['injury_type'], drop_first=True)
        # This means if 'BACK_PAIN' is the first category alphabetically, it's dropped.
        # The resulting columns would be 'injury_type_FRACTURE', 'injury_type_SOFT_TISSUE', 'injury_type_WHIPLASH'.

        # Get the input injury type
        input_injury_type = df_input.at[0, "injury_type"]

        # Remove the original injury_type column as it's now encoded
        df_input = df_input.drop("injury_type", axis=1)

        # Add the one-hot encoded columns, initially all set to 0
        # The first category ('BACK_PAIN') is dropped, so we create columns for the rest.
        for cat in known_injury_categories[1:]:  # Skip the first category (dropped)
            df_input[f"injury_type_{cat}"] = 0

        # Set the appropriate one-hot encoded column to 1 if the input_injury_type is not the dropped category
        if input_injury_type in known_injury_categories[1:]:
            df_input[f"injury_type_{input_injury_type}"] = 1

        # Ensure the column order matches the training data if model is sensitive (CatBoost usually isn't if trained with DFs)
        # The training script created X as: data.drop('settlement_amount', axis=1) after get_dummies.
        # Original numeric features: feature1, feature2, feature3
        # Encoded features: injury_type_FRACTURE, injury_type_SOFT_TISSUE, injury_type_WHIPLASH
        # The order in the training DataFrame X would be: feature1, feature2, feature3, then the dummy columns.
        expected_column_order = ["feature1", "feature2", "feature3"] + [
            f"injury_type_{cat}" for cat in known_injury_categories[1:]
        ]
        df_input = df_input[expected_column_order]

        prediction = model.predict(df_input)

        return float(prediction[0])

    except AttributeError as ae:
        logger.error(
            f"Model object does not have a 'predict' method. Is it a valid CatBoost model? Error: {ae}"
        )
        raise ValueError("Invalid model loaded. Cannot make prediction.")
    except KeyError as ke:
        logger.error(
            f"Missing expected feature in input for prediction: {ke}. Features provided: {features_dict.keys()}"
        )
        raise ValueError(
            f"Missing feature: {ke}. Ensure all required features are provided."
        )
    except Exception as e:
        logger.error(f"Error during prediction: {e}")
        raise ValueError(f"Prediction failed due to an internal error: {str(e)}")


# Example of how features might look based on a typical settlements CSV (to be confirmed)
# {
#   "claimant_age": 55,
#   "solicitor_id": "S123",
#   "injury_type_code": "ASB001",
#   "years_of_exposure": 10,
#   "asbestos_type": "Crocidolite",
#   ... etc.
# }

if __name__ == "__main__":
    # Example usage and testing
    print("Attempting to load model...")
    loaded_model = get_model()
    if loaded_model:
        print(f"Model loaded. Version: {get_model_version()}")
        sample_features_ok = {
            "feature1": 10.0,
            "feature2": 20.0,
            "feature3": 30.0,
            "injury_type": "WHIPLASH",
        }
        sample_features_missing = {"feature1": 5.0, "injury_type": "FRACTURE"}

        try:
            print(
                f"Predicting for {sample_features_ok}: {predict_reserve(sample_features_ok)}"
            )
        except Exception as e:
            print(f"Error predicting for sample_features_ok: {e}")

        try:
            print(
                f"Predicting for {sample_features_missing} (expecting potential warning/error): {predict_reserve(sample_features_missing)}"
            )
        except Exception as e:
            print(f"Error predicting for sample_features_missing: {e}")

    else:
        print("Failed to load or create a model.")

    # Test settings override with environment variable
    # You can run this script with:
    # RESERVE_MODEL_PATH="non_existent_model.pkl" python backend/services/reserve_predictor/app/model_loader.py
    # to test the model not found path.
    print(f"Model path from settings: {settings.model_path}")
