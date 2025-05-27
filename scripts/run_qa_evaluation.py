import argparse
import asyncio
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx  # For making API calls to LangServe

# Placeholder for RAGAS and other eval metrics. User needs to install these.
# from ragas import evaluate
# from ragas.metrics import (
#     faithfulness,
#     answer_relevancy,
#     context_precision,
#     context_recall,
#     answer_similarity,
#     answer_correctness
# )
# from datasets import Dataset # RAGAS expects data in huggingface datasets format

# For simpler metrics like Exact Match (EM) or F1 for text similarity
# from sklearn.metrics.pairwise import cosine_similarity
# from sklearn.feature_extraction.text import TfidfVectorizer
# import string
# from collections import Counter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Define paths - these should ideally come from a config file or args
# Assumes that the script is run from the project root directory.
DEFAULT_DOCS_DIR = Path.cwd() / "sample_data" / "docs" / "golden_set_pdfs"
DEFAULT_QA_PAIRS_FILE = Path.cwd() / "sample_data" / "eval" / "human_qa_pairs.yaml"

LANGSERVE_BASE_URL = "http://localhost:8000"
QUERY_ENDPOINT_URL = f"{LANGSERVE_BASE_URL}/query/invoke"  # As per task list: /api/v1/query -> /langserve/query/invoke


# --- Helper Functions ---
def load_human_qa_pairs(yaml_file: Path) -> List[Dict[str, Any]]:
    """Loads human-annotated Q&A pairs from a YAML file."""
    if not yaml_file.exists():
        logger.error(f"Human Q&A pairs file not found: {yaml_file}")
        return []
    with open(yaml_file, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or []
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {yaml_file}: {e}")
            return []


def load_document_content(doc_path: Path) -> Optional[str]:
    """Loads content from a .pdf.txt file."""
    text_file = doc_path.with_suffix(
        ".pdf.txt"
    )  # Assuming .txt files exist alongside .pdf files
    if not text_file.exists():
        logger.warning(f"Text file not found for document: {text_file}")
        # Potentially try to extract from PDF if .txt isn't found, as a fallback for a more robust script
        # For now, we rely on pre-extracted .txt files.
        return None
    try:
        with open(text_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading document content from {text_file}: {e}")
        return None


async def get_model_answer(
    client: httpx.AsyncClient, question: str, context: str
) -> dict | None:
    """Calls the LangServe Q&A endpoint."""
    # The payload structure depends on how your Q&A chain is set up.
    # Common patterns: {"input": {"question": "...", "context": "..."}}
    # or {"input": "question text", "config": {"configurable": {"context": "..."}}}
    # Adjust this payload based on your actual LangServe Q&A chain input schema.
    payload = {"input": {"question": question, "context": context}}
    # Example if context is passed via config:
    # payload = {"input": question, "config": {"configurable": {"retriever_context": context}}}

    print(f"  Querying model with: {payload}")
    try:
        response = await client.post(QUERY_ENDPOINT_URL, json=payload, timeout=60.0)
        response.raise_for_status()
        # The response structure will also vary. We expect an answer and possibly cited sources.
        # Assuming response.json() = {"output": {"answer": "...", "citations": [...]}}
        # Or simply {"output": "answer text"}
        response_data = response.json()
        print(f"  Model raw response: {response_data}")
        if "output" in response_data:
            if (
                isinstance(response_data["output"], dict)
                and "answer" in response_data["output"]
            ):
                return {
                    "answer": response_data["output"]["answer"],
                    "full_output": response_data["output"],
                }
            elif isinstance(
                response_data["output"], str
            ):  # If output is just the answer string
                return {
                    "answer": response_data["output"],
                    "full_output": response_data["output"],
                }
        print(
            f"Warning: 'output.answer' or 'output' not found in response: {response_data}"
        )
        return {
            "answer": "Error: Could not parse answer from model output",
            "full_output": response_data,
        }

    except httpx.RequestError as e:
        print(f"Error calling Q&A API: {e}")
        return {"answer": f"Error: API request failed: {e}", "full_output": {}}
    except Exception as e:
        print(f"An unexpected error occurred while getting model answer: {e}")
        return {"answer": f"Error: Unexpected error: {e}", "full_output": {}}


# --- Main Evaluation Logic ---
async def run_evaluation(docs_dir: Path, qa_pairs_file: Path):
    logger.info("Starting Q&A evaluation...")
    logger.info(f"Loading human Q&A pairs from: {qa_pairs_file}")
    logger.info(f"Looking for documents in: {docs_dir}\n")

    human_eval_sets = load_human_qa_pairs(qa_pairs_file)
    if not human_eval_sets:
        logger.error("No human Q&A pairs loaded. Exiting evaluation.")
        return

    all_results = []  # For RAGAS or detailed logging
    metrics_summary = {
        "total_questions": 0,
        "questions_with_system_answer": 0,
        # Add placeholders for other aggregate metrics like avg_faithfulness, avg_answer_relevancy etc.
    }

    async with httpx.AsyncClient() as client:
        for eval_set in human_eval_sets:
            document_id = eval_set.get("document_id")
            questions_data = eval_set.get("questions", [])
            if not document_id or not questions_data:
                logger.warning(f"Skipping invalid Q&A set: {eval_set}")
                continue

            logger.info(f"--- Evaluating Document: {document_id} ---")
            doc_content_path = (
                docs_dir / document_id
            )  # Assumes document_id includes .pdf extension
            full_document_content = load_document_content(
                doc_content_path.with_suffix("")
            )  # Pass path without extension to loader

            if not full_document_content:
                logger.warning(
                    f"Skipping document {document_id} due to content loading issues."
                )
                continue

            for qa_pair in questions_data:
                question = qa_pair.get("question")
                human_answer = qa_pair.get("human_answer")
                human_contexts = qa_pair.get(
                    "human_contexts", []
                )  # Ground truth contexts from YAML

                if not question or not human_answer:
                    logger.warning(
                        f"Skipping incomplete Q&A pair in {document_id}: {qa_pair}"
                    )
                    continue

                metrics_summary["total_questions"] += 1
                logger.info(f"  Question: {question}")
                logger.info(f"    Human Answer: {human_answer}")

                model_response = await get_model_answer(
                    client, question, full_document_content
                )
                model_answer = (
                    model_response["answer"]
                    if model_response
                    else "Error: No response from model"
                )

                if model_answer:
                    logger.info(f"    Model Answer: {model_answer}")
                    metrics_summary["questions_with_system_answer"] += 1

                    # Prepare data for RAGAS (if using)
                    # This structure is typical for RAGAS evaluation datasets
                    result_for_ragas = {
                        "question": question,
                        "answer": model_answer,  # Generated answer
                        "contexts": [
                            full_document_content
                        ],  # Retrieved contexts by the system
                        "ground_truth": human_answer,  # Ground truth answer (RAGAS calls this ground_truth or ground_truths)
                        "ground_truth_contexts": human_contexts,  # Ground truth contexts from YAML
                    }
                    all_results.append(result_for_ragas)

                    # TODO: Implement specific metric calculations here (EM, F1, or call RAGAS)
                    # Example: Simple Exact Match (case-insensitive, punctuation-insensitive)
                    # clean_human = human_answer.lower().translate(str.maketrans('', '', string.punctuation))
                    # clean_system = model_answer.lower().translate(str.maketrans('', '', string.punctuation))
                    # if clean_human == clean_system:
                    #     logger.info("    Metric: Exact Match = YES")
                    # else:
                    #     logger.info("    Metric: Exact Match = NO")
                else:
                    logger.warning(
                        f"    Model failed to provide an answer for question: {question}"
                    )
                logger.info("    ---")

    logger.info("=== Q&A Evaluation Summary ===")
    logger.info(f"Total Questions Evaluated: {metrics_summary['total_questions']}")
    logger.info(
        f"Questions with a System Answer: {metrics_summary['questions_with_system_answer']}"
    )

    # If RAGAS is integrated and all_results is populated:
    # try:
    #     if all_results:
    #         logger.info("\nCalculating RAGAS metrics...")
    #         logger.info("Ensure you have RAGAS installed: pip install ragas")
    #         logger.info("And set up any necessary API keys (e.g., OpenAI for some metrics).")

    #         dataset_dict = {
    #             'question': [res['question'] for res in all_results],
    #             'answer': [res['answer'] for res in all_results],
    #             'contexts': [res['contexts'] for res in all_results],
    #             'ground_truth': [res['ground_truth'] for res in all_results],
    #             'ground_truth_contexts': [res['ground_truth_contexts'] for res in all_results]
    #         }
    #         dataset = Dataset.from_dict(dataset_dict)

    #         ragas_metrics_to_compute = [
    #             faithfulness, context_precision, context_recall, answer_relevancy,
    #             # answer_similarity, # requires ground_truth (pl.)
    #             # answer_correctness # requires ground_truth (pl.)
    #         ]
    #         # Note: answer_similarity and answer_correctness might need `ground_truths` (plural list) if your human_answer is a list.
    #         # For single ground truth string, you might need to wrap human_answer in a list for these specific metrics in some RAGAS versions.

    #         # Some RAGAS metrics require an LLM for evaluation (e.g., faithfulness)
    #         # User needs to configure this (e.g., by setting OPENAI_API_KEY or providing an llm instance to evaluate call)
    #         # Example (ensure your environment or RAGAS setup can find an LLM):
    #         # from ragas.llms import LangchainLLM
    #         # from langchain_openai import ChatOpenAI # Or your chosen LLM
    #         # ragas_llm = LangchainLLM(llm=ChatOpenAI(model="gpt-3.5-turbo"))
    #         # result = evaluate(dataset, metrics=ragas_metrics_to_compute, llm=ragas_llm)

    #         result = evaluate(dataset, metrics=ragas_metrics_to_compute)
    #         logger.info(f"RAGAS Evaluation Results:\n{result}")

    #         # You can also access individual scores from the result dataframe
    #         # For example: result_df = result.to_pandas()
    #         # logger.info(f"Average Faithfulness: {result_df['faithfulness'].mean()}")

    # except ImportError:
    #     logger.warning("RAGAS library not found. Skipping RAGAS metrics. Install with: pip install ragas")
    # except Exception as e:
    #     logger.error(f"Error during RAGAS evaluation: {e}. Ensure LLM for evaluation is configured if needed.")

    logger.info("Q&A evaluation finished.")
    logger.warning(
        "REMEMBER: The core logic in `get_model_answer` must be implemented by the user."
    )
    logger.warning(
        "Consider adding specific metric calculations (EM, F1, RAGAS) as per your project needs."
    )
    logger.warning(
        "Ensure RAGAS and other dependencies like 'datasets', 'scikit-learn' are installed if used."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Q&A Evaluation Script.")
    parser.add_argument(
        "--docs_dir",
        type=Path,
        default=DEFAULT_DOCS_DIR,
        help="Directory containing the source documents (e.g., .pdf.txt files).",
    )
    parser.add_argument(
        "--qa_pairs_file",
        type=Path,
        default=DEFAULT_QA_PAIRS_FILE,
        help="YAML file containing human-annotated Q&A pairs.",
    )
    args = parser.parse_args()

    # Handle potential RAGAS/datasets import warnings if not fully set up
    print("NOTE: This script is a skeleton for Q&A evaluation.")
    print("User needs to:")
    print("1. Implement `get_model_answer` to call the actual Q&A system.")
    print(
        "2. Install necessary libraries (e.g., `pip install ragas datasets scikit-learn`)."
    )
    print("3. Populate `sample_data/eval/human_qa_pairs.yaml` with more data.")
    print("4. Configure LLMs for RAGAS if using metrics like faithfulness.")
    print("----------------------------------------------------------------")

    asyncio.run(run_evaluation(args.docs_dir, args.qa_pairs_file))
