import asyncio
import yaml
import argparse
import logging
from pathlib import Path
import httpx  # For making API calls to LangServe
from rouge_score import rouge_scorer  # for ROUGE scores
from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator, EvaluationResult

# from bert_score import score as bert_scorer # for BERTScore, requires: pip install bert_score torch torchvision
# Ensure you have torch and a suitable model for bert_score if you enable it.
# e.g., pip install torch torchvision torchaudio
# For bert_score, you might also need to specify a model, e.g., lang="en", model_type="bert-base-uncased"

LANGSERVE_BASE_URL = "http://localhost:8000"  # Assuming LangServe runs here
SUMMARISE_ENDPOINT_URL = (
    f"{LANGSERVE_BASE_URL}/summarise/invoke"  # As per previous conventions
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Placeholder for invoking the LangGraph Summarization ---
async def get_summary_from_graph(document_id: str, document_content: str) -> str:
    """Placeholder function to simulate getting a summary from the LangGraph.
    Replace this with the actual call to your summarization agent/graph.
    """
    logger.info(
        f"Simulating summarization for doc: {document_id} ({len(document_content)} chars)..."
    )
    # Example: initial_state = AgentState(session_id=f"eval_summary_{document_id}", document_id=document_id, text_content_override=document_content, query="summarize") # query might be implicit for summarizer
    # final_state = await langgraph_app.ainvoke(initial_state) # Use ainvoke for async
    # summary = final_state.get("summary", "") # Or whatever field contains the summary
    await asyncio.sleep(0.1)  # Simulate async work
    return f"This is a dummy system-generated summary for {document_id}. It is {len(document_content)//10} chars long and mentions key aspects from the input text."


def load_human_summaries(file_path="sample_data/eval/human_summaries.yaml"):
    """Loads human summaries and source texts from a YAML file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            print(f"Warning: {file_path} is empty or invalid.")
            return []
        return data
    except FileNotFoundError:
        print(f"Error: Human summaries file not found at {file_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        return []


def load_document_content(doc_path: Path) -> str:
    """Loads document content from a .pdf.txt file."""
    if not doc_path.exists():
        logger.warning(f"Document file not found: {doc_path}. Returning empty content.")
        return ""
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading document {doc_path}: {e}")
        return ""


async def get_model_summary(
    client: httpx.AsyncClient, document_text: str
) -> str | None:
    """Calls the LangServe summarization endpoint."""
    payload = {
        "input": {"text": document_text}
    }  # Assuming the chain expects input like this
    try:
        response = await client.post(SUMMARISE_ENDPOINT_URL, json=payload, timeout=60.0)
        response.raise_for_status()  # Raise an exception for bad status codes
        # The actual structure of the response might vary based on LangServe setup.
        # Assuming it returns a JSON with an "output" key, and within that, a "summary" key.
        # Adjust based on your actual LangServe output structure.
        response_data = response.json()
        if (
            "output" in response_data
            and isinstance(response_data["output"], dict)
            and "summary" in response_data["output"]
        ):
            return response_data["output"]["summary"]
        elif (
            "output" in response_data
        ):  # Fallback if output is directly the summary string
            return str(response_data["output"])
        else:
            print(
                f"Warning: 'output.summary' or 'output' not found in response: {response_data}"
            )
            return None
    except httpx.RequestError as e:
        print(f"Error calling summarization API: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while getting model summary: {e}")
        return None


def calculate_rouge_scores(candidate_summary: str, reference_summaries: list[str]):
    """Calculates ROUGE scores (R-1, R-2, R-L)."""
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    # Aggregate scores if multiple references, though often one primary reference is used per candidate.
    # For simplicity, we'll score against each and could average or take max.
    # Here, let's just take the first reference for a simple score, or average if desired.

    # If scoring against multiple references, you'd typically calculate precision/recall/fmeasure
    # for each reference and then aggregate (e.g., average or max).
    # For this example, let's score against all and print them.

    all_scores = {}
    for i, ref in enumerate(reference_summaries):
        scores = scorer.score(ref, candidate_summary)
        all_scores[f"ref_{i+1}"] = scores
    return all_scores


# Placeholder for BERTScore calculation
# def calculate_bert_score(candidate_summary: str, reference_summaries: list[str]):
# """Calculates BERTScore."""
# # Note: bert_score.score expects lists of candidates and references
# # P, R, F1 = bert_scorer([candidate_summary], [reference_summaries], lang="en", verbose=False)
# # return {"precision": P.mean().item(), "recall": R.mean().item(), "f1": F1.mean().item()}
# print("\nBERTScore calculation requires 'bert_score', 'torch', and a model.")
# print("Uncomment the import and this function, then install dependencies if needed.")
# return {"precision": 0.0, "recall": 0.0, "f1": 0.0} # Placeholder


async def main():
    """Main function to run the summarization evaluation."""
    human_data = load_human_summaries()
    if not human_data:
        print("No human data loaded. Exiting.")
        return

    all_results = []

    async with httpx.AsyncClient() as client:
        for item in human_data:
            doc_id = item.get("document_id", "Unknown_ID")
            source_text = item.get("source_text")
            human_references = item.get("human_references", [])

            if not source_text or not human_references:
                print(f"Skipping {doc_id} due to missing source text or references.")
                continue

            print(f"\nProcessing document: {doc_id}")
            model_summary = await get_model_summary(client, source_text)

            if model_summary:
                print(f"  Model Summary: {model_summary[:100]}...")  # Print a snippet

                rouge_results = calculate_rouge_scores(model_summary, human_references)
                print("  ROUGE Scores:")
                for ref_key, scores in rouge_results.items():
                    print(f"    {ref_key}:")
                    for metric, values in scores.items():
                        print(
                            f"      {metric}: P={values.precision:.4f}, R={values.recall:.4f}, F={values.fmeasure:.4f}"
                        )

                # bert_results = calculate_bert_score(model_summary, human_references)
                # print(f"  BERTScore: P={bert_results['precision']:.4f}, R={bert_results['recall']:.4f}, F={bert_results['f1']:.4f}")

                all_results.append(
                    {
                        "document_id": doc_id,
                        "model_summary": model_summary,
                        "human_references": human_references,
                        "rouge_scores": rouge_results,
                        # "bert_score": bert_results
                    }
                )
            else:
                print(f"  Failed to generate model summary for {doc_id}.")
                all_results.append(
                    {"document_id": doc_id, "error": "Failed to generate summary"}
                )

    # Optionally, save results to a file
    # with open("sample_data/outputs/summary_evaluation_results.yaml", "w", encoding="utf-8") as f:
    # yaml.dump(all_results, f, allow_unicode=True, sort_keys=False)
    # print("\nEvaluation results saved to sample_data/outputs/summary_evaluation_results.yaml")

    print("\n--- Summarization Evaluation Complete ---")
    print(
        "To enable BERTScore, uncomment the relevant lines and install 'bert_score' and 'torch'."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run summarization evaluation using ROUGE and BERTScore."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("sample_data/docs/golden_set_pdfs/"),
        help="Directory containing the document files (e.g., .pdf.txt).",
    )
    parser.add_argument(
        "--human-summaries-yaml",
        type=Path,
        default=Path("sample_data/eval/human_summaries.yaml"),
        help="Path to the YAML file containing human reference summaries.",
    )

    args = parser.parse_args()

    # Placeholder for actual graph invocation
    # from backend.core.graph import app as langgraph_app
    # from backend.core.memory import AgentState

    asyncio.run(main())
