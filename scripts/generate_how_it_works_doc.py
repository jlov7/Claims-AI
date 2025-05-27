import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import graphviz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define project root and paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DOC_DIR = PROJECT_ROOT / "docs" / "diagrams"
OUTPUT_MD_FILE = PROJECT_ROOT / "how-it-works.md"


def generate_workflow_dot() -> str:
    """Generates the DOT representation of the agent workflow."""
    dot_string = """
    digraph AgentWorkflow {
        rankdir=TB;
        node [shape=box, style="rounded,filled", fillcolor=lightblue, fontname="Arial"];
        edge [fontname="Arial"];

        Start [shape=circle, fillcolor=lightgreen];
        EndNode [label="END", shape=circle, fillcolor=lightcoral]; // Renamed from END to EndNode

        Orchestrator [label="OrchestratorAgent"];
        Summarise [label="SummariseAgent"];
        QA [label="QAAgent"];
        IncrementRetry [label="Increment Q&A Retry", shape=ellipse, fillcolor=lightyellow];
        Draft [label="DraftAgent"];
        PublishToKafka [label="Publish to Kafka", shape=ellipse, fillcolor=lightyellow];

        Start -> Orchestrator;
        Orchestrator -> Summarise [label="Delegate"];
        Summarise -> QA [label="Summary Ready"];
        QA -> Draft [label="Confidence OK / Max Retries"];
        QA -> IncrementRetry [label="Low Confidence"];
        IncrementRetry -> QA [label="Retry (Max 2)"];
        Draft -> PublishToKafka [label="Draft Complete"];
        PublishToKafka -> EndNode;
    }
    """
    return dot_string


def get_workflow_steps_data() -> list:
    """Defines the data for the workflow steps section of the markdown document."""
    # This data should ideally be derived or kept in sync with the actual graph
    # For now, it's manually curated based on backend/core/graph.py
    return [
        {
            "name": "Start & Orchestration",
            "description": "The process begins when a user request is received. The OrchestratorAgent takes charge.",
            "details": [
                "Receives initial user request, document ID, and any other parameters.",
                "Sets up the initial state for the agentic workflow.",
                "Determines the overall goal and sequence of agent execution (e.g., Summarise -> QA -> Draft).",
            ],
        },
        {
            "name": "Summarisation (SummariseAgent)",
            "description": "The SummariseAgent processes the input document(s) to create a concise summary.",
            "details": [
                "Utilizes RAG pipeline or direct text content.",
                "Generates a summary of the key information from the claim documents.",
                "May use tools like Smart-Skim (conceptually) to identify important sections.",
            ],
        },
        {
            "name": "Question & Answering (QAAgent)",
            "description": "The QAAgent answers specific questions based on the document content and summary, providing cited sources.",
            "details": [
                "Takes user queries (can be pre-defined or ad-hoc).",
                "Uses the RAG pipeline to find relevant context in documents.",
                "Generates answers and provides source information (e.g., page numbers, document snippets).",
                "Includes a self-correction/retry loop: if confidence in an answer is low (and retries < max), it attempts to refine the answer (via IncrementRetry node).",
            ],
        },
        {
            "name": "Drafting (DraftAgent)",
            "description": "The DraftAgent creates a comprehensive strategy note using the accumulated information.",
            "details": [
                "Gathers context from the summary and Q&A history.",
                "Can utilize tools to enrich the draft:",
                "  - `get_reserve_prediction`: Calls the Reserve Predictor microservice.",
                "  - `get_negotiation_tip`: Calls the Negotiation Coach tool for tactical advice.",
                "The LLM integrates tool outputs and other context into a coherent strategy note (DOCX format).",
            ],
        },
        {
            "name": "Publish to Kafka (PublishToKafka Node)",
            "description": "Key facts and outcomes from the completed workflow are published to a Kafka topic.",
            "details": [
                "Serializes relevant data from the agent state (e.g., session ID, document ID, summary, final answer, draft file path, negotiation tip).",
                "Sends this data as a JSON payload to the `claim-facts` Kafka topic.",
                "This allows other systems or UI components (like the Kafka Inspector) to consume these results.",
            ],
        },
        {
            "name": "End",
            "description": "The workflow concludes after publishing to Kafka.",
        },
    ]


def main():
    logger.info("Starting generation of how-it-works.md...")

    # Ensure output directory for diagram exists
    OUTPUT_DOC_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured diagram directory exists: {OUTPUT_DOC_DIR}")

    # 1. Generate DOT string for the workflow
    dot_content = generate_workflow_dot()
    logger.info("Generated DOT string for the workflow diagram.")

    # 2. Render DOT to an image file (e.g., SVG)
    graph_image_filename = "agent_workflow.svg"
    graph_image_path_for_md = f"./docs/diagrams/{graph_image_filename}"  # Path relative to project root for MD
    graph_image_abs_path = OUTPUT_DOC_DIR / graph_image_filename

    try:
        s = graphviz.Source(
            dot_content,
            filename=str(graph_image_abs_path.with_suffix("")),
            format="svg",
        )
        s.render(cleanup=True)
        logger.info(f"Workflow diagram saved to: {graph_image_abs_path}")
    except graphviz.ExecutableNotFound:
        logger.error(
            "Graphviz executable not found. Please install Graphviz (e.g., `brew install graphviz` or `apt-get install graphviz`) "
            "and ensure it's in your system PATH. Diagram will not be generated."
        )
        # Use a placeholder if graphviz is not found, so the doc can still generate
        graph_image_path_for_md = "./docs/diagrams/placeholder_diagram.svg"  # Assume a placeholder exists or create one
        # You might want to create a simple placeholder SVG here if it doesn't exist
        placeholder_svg_content = """<svg width="100" height="50" xmlns="http://www.w3.org/2000/svg">
<rect width="100%" height="100%" fill="lightgray"/>
<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="black">Graphviz Not Found</text>
</svg>"""
        with open(OUTPUT_DOC_DIR / "placeholder_diagram.svg", "w") as f:
            f.write(placeholder_svg_content)
        logger.info(
            f"Created placeholder diagram at {OUTPUT_DOC_DIR / 'placeholder_diagram.svg'}"
        )

    except Exception as e:
        logger.error(f"Error rendering graph: {e}. Diagram will not be generated.")
        graph_image_path_for_md = "./docs/diagrams/placeholder_diagram.svg"
        # Create placeholder as above if not already handled

    # 3. Get workflow steps data
    workflow_steps = get_workflow_steps_data()
    logger.info("Prepared workflow steps data.")

    # 4. Set up Jinja2 environment and render the template
    environment = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = environment.get_template("how-it-works.md.j2")

    context = {
        "graph_image_path": graph_image_path_for_md,
        "workflow_steps": workflow_steps,
    }

    rendered_md_content = template.render(context)
    logger.info("Rendered markdown content using Jinja2 template.")

    # 5. Save the rendered markdown to how-it-works.md
    with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as f:
        f.write(rendered_md_content)
    logger.info(
        f"Successfully generated and saved how-it-works.md to: {OUTPUT_MD_FILE}"
    )


if __name__ == "__main__":
    main()
