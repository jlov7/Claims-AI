import httpx
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

RESERVE_PREDICTOR_URL = "http://localhost:8001/predict"


# Pydantic model for the request, mirroring backend/services/reserve_predictor/app/main.py
class ReservePredictionFeatures(BaseModel):
    feature1: float = Field(..., description="Continuous feature 1 for prediction.")
    feature2: float = Field(..., description="Continuous feature 2 for prediction.")
    feature3: float = Field(..., description="Continuous feature 3 for prediction.")
    injury_type: str = Field(..., description="Categorical injury type for prediction.")


@tool
async def get_reserve_prediction(
    feature1: float, feature2: float, feature3: float, injury_type: str
) -> str:
    """
    Tool to get a claim reserve prediction from the Reserve Predictor microservice.

    Args:
        feature1: Continuous feature 1.
        feature2: Continuous feature 2.
        feature3: Continuous feature 3.
        injury_type: The type of injury (e.g., 'WHIPLASH', 'FRACTURE').
    """
    try:
        payload = ReservePredictionFeatures(
            feature1=feature1,
            feature2=feature2,
            feature3=feature3,
            injury_type=injury_type,
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(
                RESERVE_PREDICTOR_URL, json=payload.model_dump()
            )

        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

        response_data = response.json()
        prediction = response_data.get("prediction")
        model_version = response_data.get("model_version", "N/A")

        if prediction is not None:
            return f"Reserve Prediction: {prediction:.2f} (Model: {model_version})"
        else:
            logger.error(
                f"Prediction not found in response from Reserve Predictor: {response_data}"
            )
            return "Error: Prediction not found in response from Reserve Predictor."

    except httpx.RequestError as e:
        logger.error(f"HTTP request error calling Reserve Predictor: {e}")
        return f"Error: Could not connect to Reserve Predictor service: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP status error from Reserve Predictor: {e.response.status_code} - {e.response.text}"
        )
        return f"Error: Reserve Predictor service returned status {e.response.status_code}: {e.response.text}"
    except Exception as e:
        logger.error(f"Unexpected error calling Reserve Predictor: {e}")
        return f"Error: An unexpected error occurred while getting reserve prediction: {str(e)}"


if __name__ == "__main__":
    import asyncio

    async def main():
        # Test the tool
        # Ensure the Reserve Predictor service is running on port 8001
        print("Testing get_reserve_prediction tool...")

        # Example 1: Valid request
        result1 = await get_reserve_prediction.ainvoke(
            {
                "feature1": 10.0,
                "feature2": 20.0,
                "feature3": 30.0,
                "injury_type": "WHIPLASH",
            }
        )
        print(f"Test 1 Result: {result1}")

        # Example 2: Potentially different features
        result2 = await get_reserve_prediction.ainvoke(
            {
                "feature1": 5.0,
                "feature2": 15.0,
                "feature3": 25.0,
                "injury_type": "FRACTURE",
            }
        )
        print(f"Test 2 Result: {result2}")

        # Example 3: Invalid injury type (if model/service handles it gracefully or errors)
        # Depending on the service's validation, this might return an error from the service
        # or the dummy model might handle it.
        result3 = await get_reserve_prediction.ainvoke(
            {
                "feature1": 7.0,
                "feature2": 17.0,
                "feature3": 27.0,
                "injury_type": "UNKNOWN_INJURY_TYPE_FOR_TESTING",
            }
        )
        print(
            f"Test 3 Result (expecting potential error or default if dummy model handles it): {result3}"
        )

    asyncio.run(main())
