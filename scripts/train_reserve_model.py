import pandas as pd
from catboost import CatBoostRegressor
import pickle
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_VERSION = "catboost_settlements_v1.0"
MODEL_OUTPUT_DIR = Path("sample_data")
MODEL_OUTPUT_FILENAME = "catboost_model.pkl"
MODEL_OUTPUT_PATH = MODEL_OUTPUT_DIR / MODEL_OUTPUT_FILENAME
RAW_DATA_PATH = Path("sample_data/settlements.csv")


def train_and_save_model():
    """
    Trains a CatBoostRegressor model on the settlements data and saves it.
    """
    logger.info(f"Starting model training. Data source: {RAW_DATA_PATH}")

    if not RAW_DATA_PATH.exists():
        logger.error(f"Raw data file not found at {RAW_DATA_PATH}. Aborting training.")
        return

    try:
        data = pd.read_csv(RAW_DATA_PATH)
        logger.info(f"Data loaded successfully. Shape: {data.shape}")
        logger.info(f"Columns: {data.columns.tolist()}")
        logger.info(f"Sample data:\n{data.head()}")

        # Preprocessing
        # Ensure 'injury_type' is treated as categorical for CatBoost, or one-hot encode
        # The model_loader.py expects one-hot encoded features if not using CatBoost's native cat_features handling during predict
        # For consistency with the dummy model creation and predict_reserve in model_loader.py,
        # which manually does one-hot encoding, we should also do it here.

        if "injury_type" not in data.columns:
            logger.error("'injury_type' column not found in the data. Aborting.")
            return

        # Get unique sorted injury categories for consistent one-hot encoding
        # This ensures 'drop_first=True' consistently drops the same category ('BACK_PAIN' if present and first alphabetically)
        known_injury_categories = sorted(data["injury_type"].astype(str).unique())
        logger.info(f"Known injury categories (sorted): {known_injury_categories}")

        if not known_injury_categories:
            logger.error("No injury categories found. Aborting.")
            return

        # It's crucial that the 'drop_first=True' behavior matches what predict_reserve in model_loader.py expects.
        # model_loader.py assumes the first category in an alphabetically sorted list of unique categories is dropped.
        data["injury_type"] = pd.Categorical(
            data["injury_type"], categories=known_injury_categories, ordered=True
        )
        data = pd.get_dummies(
            data, columns=["injury_type"], prefix="injury_type", drop_first=True
        )

        logger.info(f"Data after one-hot encoding for 'injury_type':\n{data.head()}")
        logger.info(f"Columns after OHE: {data.columns.tolist()}")

        if "settlement_amount" not in data.columns:
            logger.error("'settlement_amount' column (target) not found. Aborting.")
            return

        X = data.drop("settlement_amount", axis=1)
        y = data["settlement_amount"]

        # Identify categorical features for CatBoost (if any remain after one-hot encoding)
        # In this case, after one-hot encoding, all features passed to CatBoost will be numeric.
        # If we were to use CatBoost's native handling, we would pass original 'injury_type' and specify its index.
        categorical_features_indices = [
            i
            for i, col in enumerate(X.columns)
            if X.dtypes[col] == "object"
            or pd.api.types.is_categorical_dtype(X.dtypes[col])
        ]
        logger.info(
            f"Categorical feature indices for CatBoost (should be empty if OHE done right): {categorical_features_indices}"
        )

        model = CatBoostRegressor(
            iterations=100,
            learning_rate=0.1,
            depth=6,
            loss_function="RMSE",
            verbose=10,  # Log every 10 iterations
            random_seed=42,
        )

        logger.info("Training CatBoostRegressor model...")
        model.fit(X, y, cat_features=categorical_features_indices)  # Should be empty
        logger.info("Model training complete.")

        # Ensure the output directory exists
        MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Save the model and version
        model_payload = {
            "model": model,
            "version": MODEL_VERSION,
            "feature_columns": X.columns.tolist(),  # Save feature columns for verification
        }
        with open(MODEL_OUTPUT_PATH, "wb") as f:
            pickle.dump(model_payload, f)

        logger.info(f"Model '{MODEL_VERSION}' saved to {MODEL_OUTPUT_PATH}")
        logger.info(f"Model was trained with features: {X.columns.tolist()}")

    except FileNotFoundError:
        logger.error(f"Error: The file {RAW_DATA_PATH} was not found.")
    except pd.errors.EmptyDataError:
        logger.error(f"Error: The file {RAW_DATA_PATH} is empty.")
    except Exception as e:
        logger.error(
            f"An error occurred during model training or saving: {e}", exc_info=True
        )


if __name__ == "__main__":
    train_and_save_model()
