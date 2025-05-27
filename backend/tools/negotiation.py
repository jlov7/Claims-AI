import csv
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from functools import lru_cache

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Path to the negotiation data CSV file
# Assumes it's in sample_data at the project root
NEGOTIATION_DATA_CSV = Path.cwd() / "sample_data" / "negotiation_stats.csv"


@lru_cache(maxsize=1)  # Cache the loaded data to avoid repeated file I/O
def load_negotiation_data(
    csv_path: Path = NEGOTIATION_DATA_CSV,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Loads negotiation statistics from a CSV file into a structured dictionary.
    The dictionary is keyed by (solicitor_id, injury_type) tuples.
    """
    data: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not csv_path.exists() or not csv_path.is_file():
        logger.warning(
            f"Negotiation data CSV not found or is not a file: {csv_path}. Negotiation Coach will have no specific data."
        )
        return data

    try:
        with open(csv_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames or not all(
                f in reader.fieldnames for f in ["solicitor_id", "injury_type"]
            ):
                logger.error(
                    f"CSV file {csv_path} is missing required columns (solicitor_id, injury_type)."
                )
                return data

            for row_num, row in enumerate(reader):
                solicitor_id = (
                    row.get("solicitor_id", "").strip().upper()
                    or f"UNKNOWN_SOLICITOR_ROW_{row_num}"
                )
                injury_type = (
                    row.get("injury_type", "").strip().upper()
                    or f"UNKNOWN_INJURY_ROW_{row_num}"
                )

                # Convert numeric fields safely
                avg_settlement_str = row.get("average_settlement_gbp", "0")
                try:
                    avg_settlement = (
                        int(float(avg_settlement_str)) if avg_settlement_str else 0
                    )
                except ValueError:
                    logger.warning(
                        f"Could not parse average_settlement_gbp '{avg_settlement_str}' for {(solicitor_id, injury_type)}. Defaulting to 0."
                    )
                    avg_settlement = 0

                data[(solicitor_id, injury_type)] = {
                    "average_settlement_gbp": avg_settlement,
                    "negotiation_tip_key_points": row.get(
                        "negotiation_tip_key_points", "No specific tip available."
                    ),
                    "settlement_percentile_rank": row.get(
                        "settlement_percentile_rank", "N/A"
                    ),
                    "common_pitfall": row.get("common_pitfall", "N/A"),
                }
        logger.info(f"Successfully loaded {len(data)} records from {csv_path}.")
    except FileNotFoundError:
        logger.error(
            f"Negotiation data CSV file not found at {csv_path}. No data loaded."
        )
    except Exception as e:
        logger.error(
            f"Error loading negotiation data from {csv_path}: {e}", exc_info=True
        )

    return data


# class NegotiationTipInput(BaseModel):
#     solicitor_id: str = Field(description="The ID of the solicitor firm.")
#     injury_type: str = Field(description="The type of injury.")


# @tool(args_schema=NegotiationTipInput)
@tool
def get_negotiation_tip(solicitor_id: str, injury_type: str) -> str:
    """
    Retrieves a negotiation tip based on solicitor_id and injury_type.
    Provides fallback tips if specific matches are not found.
    Use this tool to get advice on how to negotiate a claim given the solicitor and injury type.

    Args:
        solicitor_id: The ID or name of the solicitor firm (e.g., 'S001', 'ACME Solicitors').
        injury_type: The type of injury (e.g., 'ASB001', 'WHIPLASH').
    """
    negotiation_data = load_negotiation_data()

    solicitor_id_upper = solicitor_id.strip().upper() if solicitor_id else ""
    injury_type_upper = injury_type.strip().upper() if injury_type else ""

    if not negotiation_data:
        return "Negotiation data is not loaded. Please check the data file and logs. Generic tip: Prepare thoroughly and document all claim aspects."

    # Try exact match
    specific_match = negotiation_data.get((solicitor_id_upper, injury_type_upper))
    if specific_match:
        return (
            f"Tip for {solicitor_id}/{injury_type}: {specific_match['negotiation_tip_key_points']}. "
            f"Avg Settlement: £{specific_match['average_settlement_gbp']:,}. "
            f"Common Pitfall: {specific_match['common_pitfall']}"
        )

    # Try general solicitor match (any injury for that solicitor)
    # This would require a different data structure or iterating through keys.
    # For simplicity, this fallback is not implemented here but could be an enhancement.

    # Try general injury match (any solicitor for that injury)
    general_injury_key_any_solicitor = ("GENERAL", injury_type_upper)
    general_injury_key_specific_type = (
        "GENERAL",
        (
            f"{injury_type_upper.split('_')[0]}_ANY"
            if "_" in injury_type_upper
            else injury_type_upper
        ),
    )

    general_injury_match = negotiation_data.get(
        general_injury_key_any_solicitor
    ) or negotiation_data.get(general_injury_key_specific_type)
    if general_injury_match:
        return (
            f"General tip for {injury_type}: {general_injury_match['negotiation_tip_key_points']}. "
            f"Avg Settlement (General): £{general_injury_match['average_settlement_gbp']:,}. "
            f"Common Pitfall: {general_injury_match['common_pitfall']}"
        )

    # Try Default match
    default_match = negotiation_data.get(("DEFAULT", "DEFAULT"))
    if default_match:
        return (
            f"Default Tip: {default_match['negotiation_tip_key_points']}. "
            f"Avg Settlement (Default): £{default_match['average_settlement_gbp']:,}. "
            f"Common Pitfall: {default_match['common_pitfall']}"
        )

    return "No specific negotiation tip found. Ensure all claim details are well-documented and argue based on merit and comparable cases."


# Example usage (for local testing)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Ensure the dummy CSV is created in sample_data/negotiation_stats.csv for this to work
    # The load_negotiation_data function will try to load it from there.
    if not NEGOTIATION_DATA_CSV.exists():
        print(
            f"Please create a dummy CSV at {NEGOTIATION_DATA_CSV} to run these examples."
        )
        print(
            "Example CSV header: solicitor_id,injury_type,average_settlement_gbp,negotiation_tip_key_points,settlement_percentile_rank,common_pitfall"
        )
    else:
        print("--- Negotiation Coach Examples ---")
        print(f"Data loaded from: {NEGOTIATION_DATA_CSV}")

        tip1 = get_negotiation_tip("S001", "ASB001")
        print(f"\nTip for S001, ASB001: \n{tip1}")

        tip2 = get_negotiation_tip("S002", "NIHL001")
        print(f"\nTip for S002, NIHL001: \n{tip2}")

        tip3 = get_negotiation_tip("S001", "NON_EXISTENT_INJURY")
        print(
            f"\nTip for S001, NON_EXISTENT_INJURY (expecting general or default): \n{tip3}"
        )  # Might hit general ASB_ANY or DEFAULT

        tip4 = get_negotiation_tip("NON_EXISTENT_SOLICITOR", "ASB001")
        print(
            f"\nTip for NON_EXISTENT_SOLICITOR, ASB001 (expecting general or default): \n{tip4}"
        )  # Might hit general ASB_ANY or DEFAULT

        tip5 = get_negotiation_tip("S003", "ASB001")
        print(f"\nTip for S003, ASB001: \n{tip5}")

        tip_general_asb = get_negotiation_tip(
            "ANY_SOLICITOR", "ASB_ANY"
        )  # Should hit GENERAL,ASB_ANY
        print(f"\nTip for General Asbestos (ASB_ANY): \n{tip_general_asb}")

        tip_default = get_negotiation_tip(
            "RANDOM_SOLICITOR", "RANDOM_INJURY"
        )  # Should hit DEFAULT,DEFAULT
        print(f"\nTip for Random/Default: \n{tip_default}")
