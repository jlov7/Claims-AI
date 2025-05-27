import asyncio
import yaml
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

# Placeholder for backend imports - these will need to be adjusted based on actual runnable graph
from core.graph import (
    app as langgraph_app,
)  # Corrected: Assuming compiled graph is 'app'
from core.state import (
    AgentState,
)  # Corrected: AgentState is in backend.core.state
from core.config import get_settings # For any runtime configurations if needed

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# --- Placeholder for invoking the LangGraph Q&A ---
# This needs to be replaced with actual invocation of your QAAgent or full graph
async def get_answer_from_graph(
    document_id: str, query: str, document_content: str
) -> str:
    """Gets an answer from the LangGraph Q&A agent."""
    logger.info(
        f"Invoking LangGraph Q&A for doc: {document_id}, query: '{query[:50]}...'"
    )
    session_id = (
        f"eval_{document_id}_{hash(query)}"  # Ensure unique session for each query
    )

    # Prepare the initial state for the graph
    # The exact fields for AgentState might need adjustment based on the QAAgent's specific input requirements.
    # 'text_content_override' is used to directly provide the document content to the RAG process for this evaluation.
    # 'message_history' might be needed if the QAAgent expects it, initializing as empty for a single Q&A turn.
    initial_state = AgentState(
        session_id=session_id,
        document_id=document_id,
        query=query,
        text_content_override=document_content,
        # Add other necessary fields if AgentState or your graph requires them.
        # For example, if the graph has a specific entry point or initial message structure:
        # messages=[("user", query)], # Example if using a message list format
        # chat_history=[], # if chat history is explicitly managed and needed at input
    )

    try:
        # Invoke the LangGraph application asynchronously
        # Assuming 'langgraph_app' is the compiled LangGraph application instance
        # and it has an 'ainvoke' method.
        # The input to ainvoke should match what the graph's input schema expects.
        # This might be the AgentState directly, or a dictionary derived from it.
        # For a typical Q&A agent, the 'query' and context (via document_id/text_content_override) are key.
        final_state_result = await langgraph_app.ainvoke(
            initial_state,
            # Optionally, specify a config if needed, e.g., to select a specific runnable within the graph
            # config={"run_name": "qa_evaluation_run", "configurable": {"thread_id": session_id}}
            # If the QAAgent is a specific node or entry point, ensure config targets it if necessary.
            # For now, assuming the graph's default entry point handles AgentState with a 'query'.
        )

        # Extract the answer from the final state.
        # The key for the answer ("answer", "response", "output", etc.) depends on how the QAAgent
        # and the graph store the final result in the AgentState.
        # Using .get("answer", ...) is a safe way to access it.
        if isinstance(final_state_result, dict):
            answer = final_state_result.get("answer")
            if (
                not answer and "messages" in final_state_result
            ):  # Check last message if 'answer' not present
                last_message = final_state_result["messages"][-1]
                if hasattr(last_message, "content"):
                    answer = last_message.content
                elif isinstance(
                    last_message, str
                ):  # Or if last message is just a string
                    answer = last_message

            if not answer:
                logger.error(
                    f"Could not extract answer from final_state_result for doc {document_id}. Result: {final_state_result}"
                )
                return "Error: Could not extract answer from graph."
        elif isinstance(
            final_state_result, AgentState
        ):  # If ainvoke returns the full state object
            answer = final_state_result.get(
                "answer"
            )  # Adapt if AgentState has a different way to get messages/answer
            if not answer and final_state_result.messages:
                last_message = final_state_result.messages[-1]
                if hasattr(last_message, "content"):
                    answer = last_message.content
                elif isinstance(last_message, str):
                    answer = last_message
            if not answer:
                logger.error(
                    f"Could not extract answer from AgentState for doc {document_id}. State: {final_state_result}"
                )
                return "Error: Could not extract answer from graph state."
        else:
            logger.error(
                f"Unexpected result type from langgraph_app.ainvoke: {type(final_state_result)}. For doc {document_id}. Result: {final_state_result}"
            )
            return "Error: Unexpected result type from graph."

        return answer if answer else "Error: No answer found in graph response."

    except Exception as e:
        logger.error(
            f"Error invoking LangGraph for doc {document_id}, query '{query[:50]}...': {e}",
            exc_info=True,
        )
        return f"Error during LangGraph invocation: {str(e)}"


def load_golden_set(yaml_path: Path) -> List[Dict[str, Any]]:
    """Loads the golden set Q&A from a YAML file."""
    if not yaml_path.exists():
        logger.error(f"Golden set YAML file not found: {yaml_path}")
        sys.exit(1)
    with open(yaml_path, "r", encoding="utf-8") as f:
        try:
            golden_set = yaml.safe_load(f)
            if not isinstance(golden_set, list):
                logger.error(
                    f"Golden set YAML should be a list of documents. Found: {type(golden_set)}"
                )
                sys.exit(1)
            return golden_set
        except yaml.YAMLError as e:
            logger.error(f"Error parsing golden set YAML: {e}")
            sys.exit(1)


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


def normalize_text(text: str) -> str:
    """Lowercase and remove basic punctuation for keyword matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)  # Keep alphanumeric, whitespace, hyphens
    text = re.sub(r"\s+", " ", text).strip()  # Normalize whitespace
    return text


def calculate_f1_score(
    generated_answer: str, expected_keywords: List[str]
) -> Tuple[float, float, float]:
    """Calculates Precision, Recall, and F1 score based on keyword matching."""
    if not generated_answer and not expected_keywords:
        return 1.0, 1.0, 1.0  # Both empty, perfect match
    if not expected_keywords:  # No keywords to find, but answer exists
        return (
            0.0,
            1.0,
            0.0,
        )  # Precision 0 (no true positives possible), Recall 1 (no expected keywords missed)
    if not generated_answer:  # Keywords expected, but no answer
        return (
            1.0,
            0.0,
            0.0,
        )  # Precision 1 (no false positives), Recall 0 (all expected keywords missed)

    norm_answer = normalize_text(generated_answer)
    norm_expected_keywords = {
        normalize_text(kw) for kw in expected_keywords if normalize_text(kw)
    }

    answer_tokens = set(norm_answer.split())

    true_positives = len(answer_tokens.intersection(norm_expected_keywords))
    false_positives = len(answer_tokens - norm_expected_keywords)
    false_negatives = len(norm_expected_keywords - answer_tokens)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0.0
    )
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1


async def run_evaluation(
    docs_dir_path: Path, golden_set_yaml_path: Path, f1_threshold: float
):
    golden_set = load_golden_set(golden_set_yaml_path)
    all_f1_scores: List[float] = []
    detailed_results = []

    logger.info(f"Starting evaluation for {len(golden_set)} documents...")

    for i, item in enumerate(golden_set):
        document_id = item.get("document_id")
        questions = item.get("questions")

        if not document_id or not isinstance(questions, list):
            logger.warning(
                f"Skipping invalid item in golden set (index {i}): missing document_id or questions."
            )
            continue

        doc_file_path = docs_dir_path / document_id
        document_content = load_document_content(doc_file_path)
        if not document_content:
            logger.warning(
                f"Skipping document {document_id} due to missing or empty content."
            )
            # Decide if this should count as a failure or be skipped for F1 calculation
            # For now, skipping means it won\'t drag down the average F1 if docs are missing.
            continue

        logger.info(f"Processing document: {document_id} ({len(questions)} questions)")
        doc_f1_scores = []
        for q_idx, q_data in enumerate(questions):
            query_text = q_data.get("text")
            expected_keywords = q_data.get("expected_answer_keywords", [])
            eval_type = q_data.get("evaluation_type", "keyword_match")
            question_id = q_data.get("question_id", f"q_{q_idx}")

            if not query_text or not expected_keywords or eval_type != "keyword_match":
                logger.warning(
                    f"Skipping question '{question_id}' for doc '{document_id}': missing text/keywords or unsupported eval_type ('{eval_type}')."
                )
                continue

            generated_answer = await get_answer_from_graph(
                document_id, query_text, document_content
            )
            precision, recall, f1 = calculate_f1_score(
                generated_answer, expected_keywords
            )
            all_f1_scores.append(f1)
            doc_f1_scores.append(f1)
            detailed_results.append(
                {
                    "document_id": document_id,
                    "question_id": question_id,
                    "query": query_text,
                    "expected_keywords": expected_keywords,
                    "generated_answer": generated_answer,
                    "precision": precision,
                    "recall": recall,
                    "f1_score": f1,
                }
            )
            logger.info(
                f"  Q: {query_text[:60]}... | F1: {f1:.4f} (P: {precision:.4f}, R: {recall:.4f})"
            )

        if doc_f1_scores:
            avg_doc_f1 = sum(doc_f1_scores) / len(doc_f1_scores)
            logger.info(f"Average F1 for document {document_id}: {avg_doc_f1:.4f}")

    if not all_f1_scores:
        logger.error(
            "No F1 scores were calculated. Ensure golden set is valid and documents are present."
        )
        sys.exit(1)

    average_f1 = sum(all_f1_scores) / len(all_f1_scores)
    logger.info("\n--- Evaluation Summary ---")
    logger.info(f"Total questions evaluated: {len(all_f1_scores)}")
    logger.info(f"Average F1 Score: {average_f1:.4f}")

    # Print detailed results for inspection
    # logger.info("\n--- Detailed Results ---")
    # for res in detailed_results:
    #     logger.info(json.dumps(res, indent=2))

    if average_f1 < f1_threshold:
        logger.error(
            f"Evaluation FAILED: Average F1 score {average_f1:.4f} is below the threshold of {f1_threshold:.4f}."
        )
        sys.exit(1)
    else:
        logger.info(
            f"Evaluation PASSED: Average F1 score {average_f1:.4f} meets or exceeds the threshold of {f1_threshold:.4f}."
        )
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation against a golden set.")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("sample_data/docs/golden_set_pdfs/"),
        help="Directory containing the document files (e.g., .pdf.txt).",
    )
    parser.add_argument(
        "--golden-set-yaml",
        type=Path,
        default=Path("sample_data/eval/golden_set_qa.yaml"),
        help="Path to the golden set YAML file.",
    )
    parser.add_argument(
        "--f1-threshold",
        type=float,
        default=0.85,
        help="Minimum average F1 score to pass the evaluation.",
    )

    args = parser.parse_args()

    # This is where you would import and use the actual LangGraph app
    # For now, the placeholder get_answer_from_graph is used.
    # Ensure your LangGraph app (`langgraph_app`) can be imported and its `ainvoke` method used here.
    # Example (commented out, needs actual app and state management):
    # from backend.core.graph import app as langgraph_app # This is now imported at the top
    # from backend.core.state import AgentState # This is now imported at the top

    asyncio.run(run_evaluation(args.docs_dir, args.golden_set_yaml, args.f1_threshold))
