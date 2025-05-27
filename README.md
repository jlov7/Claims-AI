# Claims-AI: Exploring an Agentic Architecture for Long-Tail Claims Processing

## 1. Project Overview & Purpose

**The Challenge:** Processing long-tail insurance claims, particularly for complex cases like asbestos and Noise-Induced Hearing Loss (NIHL), is a time-consuming and labor-intensive endeavor. Claims handlers often wade through hundreds, if not thousands, of pages of scanned documents, medical reports, and legal correspondence to extract critical information, assess liability, and determine appropriate reserves. This manual effort leads to extended cycle times, increased operational costs, and potential inconsistencies.

**Architectural Exploration:** This project explores a potential agent-based Generative AI architecture designed to assist claims handlers. The goal is to demonstrate and test a system that can intelligently navigate and synthesize vast amounts of unstructured data, providing handlers with actionable insights, accurate summaries, and well-reasoned draft strategy notes. It serves as a proof-of-concept for a solution that could significantly reduce manual reading and drafting time.

**Core Ambition & Design Philosophy:** The primary aim is to test the feasibility of a sophisticated, locally-runnable AI agent system for augmenting human expertise in claims management. This exploration prioritizes a modular design that, while demonstrated locally (Mistral-7B via Ollama on a MacBook Pro), could be adapted for enterprise-grade cloud platforms like Google Cloud Vertex AI (with Gemini models and Agent Development Kit - ADK) or Azure OpenAI with focused effort on environment and configuration changes.

## 2. Demonstrated Features & Functionality (Architectural Test Scope)

This project demonstrates the following capabilities through a multi-agent system architecture:

*   **Smart-Skim Heat-Map:** Utilizes layout-aware Optical Character Recognition (OCR) and embedding-based relevance scoring to create a "heat-map" of large documents. This visually guides handlers to the most pertinent sections, potentially reducing manual review time.
*   **SummariseAgent:** After a section is identified via Smart-Skim (or an entire document is processed), this agent generates concise, bullet-point summaries of key information.
*   **QAAgent (Question-Answering Agent):** Provides answers to handler queries, grounded in the document content, complete with citations to the source material for verifiability.
*   **DraftAgent:**
    *   Generates a draft strategy note based on the claim summary, Q&A history, and any user-defined criteria.
    *   Integrates with a mock "Reserve Predictor" microservice to suggest initial reserve values.
    *   Incorporates tips from a mock "Negotiation Coach" tool based on case parameters.
*   **Agentic Retry & Quality Gate:** Implements a self-correction loop. If any agent's output confidence score falls below a predefined threshold (e.g., 0.7), the system can trigger a retry (up to a maximum number of attempts) or flag the output for human review.
*   **Kafka Publication:** Upon successful completion of its tasks (e.g., facts approved or strategy note drafted), the system publishes a structured JSON payload of `claim-facts` to a Kafka topic (Redpanda for local demo).
*   **Kafka Inspector Panel (Frontend):** A simple React-based UI component allows for real-time viewing of messages published to the `claim-facts` Kafka topic, demonstrating data flow for downstream system integration.
*   **Evaluation & Observability (Demonstrated):**
    *   **LangSmith Integration:** Leverages LangSmith for detailed tracing of agent interactions, LLM calls, and tool usage, enabling robust debugging and performance analysis.
    *   **Automated Evaluation Scripts:** Includes scripts for evaluating summarization (ROUGE, BERTScore), Q&A (Faithfulness, RAGAS metrics), and tool use against golden datasets.
    *   **Playwright Smoke Tests:** Contains end-to-end UI tests to ensure critical user flows are functional.

## 3. System Architecture

This project architecture is designed as a modular system, leveraging Docker for containerization of its backend services and a React-based frontend for user interaction. The core logic revolves around a LangGraph-powered multi-agent system orchestrated via LangServe.

<img src="docs/diagrams/system_architecture.svg" alt="System Architecture Diagram">

**Architectural Overview:**

*   **Frontend (React):** Provides the user interface for document upload, heatmap visualization, Q&A interaction, draft review, and the Kafka Inspector panel.
*   **Backend (FastAPI):** The main API gateway built with FastAPI. It handles HTTP requests, serves the frontend (in a production setup or via a separate server in development), and importantly, hosts the LangServe application.
    *   **LangServe Sub-Application:** The core agentic workflows are exposed as LangServe runnables. These are encapsulated within a FastAPI sub-application, typically mounted at a prefixed path like `/langserve`. This sub-app provides:
        *   Individual API endpoints for each runnable (e.g., `/langserve/query/invoke`).
        *   Individual interactive playgrounds for each runnable (e.g., `/langserve/query/playground/`).
        *   A main catalog playground (`/langserve/playground/`) that lists all available runnables.
*   **Agentic Core (LangGraph):** LangGraph is used to define and orchestrate the multi-agent system. This includes:
    *   **Agent Nodes:** Individual agents (Summarise, QA, Draft, Orchestrator) are defined as nodes in the graph.
    *   **Tool Nodes:** Tools used by agents (Smart-Skim, Reserve Predictor, Negotiation Coach) are integrated via LangGraph's `ToolNode` or similar mechanisms.
    *   **Graph Edges:** Define the flow of control and data between agents, including conditional edges for retries and quality gates.
*   **Tools & Microservices (Local Mocks):**
    *   **Smart-Skim:** A Python tool for document processing and relevance scoring.
    *   **Reserve Predictor:** A mock FastAPI microservice endpoint (`/predict`) to simulate reserve calculation.
    *   **Negotiation Coach:** A Python function providing negotiation tips based on input parameters.
*   **Data & Infrastructure Layer (Local Demo Setup):**
    *   **Ollama (Mistral-7B):** Serves the local LLM (Mistral-7B-Instruct GGUF Q4_K_M by default) via a REST API.
    *   **ChromaDB:** Provides local vector storage for document embeddings, enabling semantic search for RAG.
    *   **Minio:** Offers an S3-compatible object storage solution for raw documents and processed data.
    *   **Redpanda:** A Kafka-compatible event streaming platform used for publishing `claim-facts` and other inter-service messages.

**Data Flow Example (Simplified Q&A):**
1. User asks a question through the React UI.
2. The UI sends the request to the FastAPI backend, specifically to the `/langserve/query/invoke` endpoint.
3. LangServe routes this to the `QAAgent` runnable within the LangGraph orchestrator.
4. The `QAAgent` retrieves relevant document chunks from `Minio` (via `ChromaDB` for semantic search), constructs a prompt with the question and context, and calls the `Ollama` LLM.
5. The LLM generates an answer.
6. The `QAAgent` returns the answer and source citations, which LangServe sends back to the UI.

## 4. Project Structure

Brief overview of the key directories and their purpose.
- `backend/`: Contains all backend FastAPI, LangServe, and agent logic.
- `frontend/`: Contains the React user interface.
- `scripts/`: Utility scripts for data processing, evaluation, model training, etc.
- `data/`: Sample data, outputs, and other data assets (e.g., trained models, evaluation sets).
- `docs/`: Project documentation and diagrams.

## 5. Getting Started

Follow these steps to get the project up and running locally:

1.  **Prerequisites:**
    *   Git
    *   Python 3.11+ (recommended to manage with `pyenv`)
    *   Docker & Docker Compose
    *   Node.js & npm (for Mermaid CLI, if you wish to regenerate diagrams, and for frontend development if applicable)
    *   Ollama: Visit [ollama.com](https://ollama.com/) for installation instructions.

2.  **Clone the Repository:**
    ```bash
    git clone <YOUR_REPOSITORY_URL_HERE> # <-- TODO: Replace with your repository URL
    cd Claims-AI
    ```

3.  **Set up Python Environment:**
    *   It's recommended to use `pyenv` to manage Python versions (see `.python-version` file):
        ```bash
        # Example: pyenv install 3.11.9 && pyenv local 3.11.9
        # Ensure your pyenv setup matches the version in .python-version
        ```
    *   Create a virtual environment and install dependencies:
        ```bash
        python -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        ```

4.  **Configure Environment Variables:**
    *   Copy the sample environment file:
        ```bash
        cp .env.sample .env
        ```
    *   Review and update `.env` with your specific configurations. The defaults are set for local development with Ollama. API keys for cloud LLMs (like Gemini) will need to be added if you switch providers.

5.  **Pull LLM Model (Mistral):**
    *   Ensure Ollama is running (you might need to start the Ollama application or run `ollama serve &` in your terminal).
    *   Pull the default Mistral model (or the one specified in your `.env` if changed):
        ```bash
        ollama pull mistral:7b-instruct # Or your configured OLLAMA_MODEL_NAME
        ```

6.  **Start Docker Services:**
    *   This will start Minio, Redpanda, and other backing services defined in `docker-compose.yml`.
        ```bash
        docker compose up -d
        ```

7.  **Run Backend Application:**
    *   The backend FastAPI application (which includes the LangServe agentic system) can be started using Uvicorn. A common way is:
        ```bash
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        ```
    *   Alternatively, if a `make` command is configured (check the `Makefile`):
        ```bash
        # Example: make run-backend
        ```

8.  **Access the Application:**
    *   The main application API should be available at `http://localhost:8000`.
    *   LangServe endpoints and playgrounds will be at `http://localhost:8000/langserve/playground/`.
    *   The React frontend (Kafka Inspector, etc.) is served by the FastAPI backend at `http://localhost:8000/`.

9.  **Run Tests (Optional but Recommended):**
    ```bash
    make test # Or: pytest, make ruff, make black individually
    ```

## 6. Key Technologies

This project leverages a range of modern technologies to build and test an agentic AI system:

*   **Programming Language:** Python 3.11+
*   **Core AI/LLM Frameworks:**
    *   LangChain: For building applications with LLMs, including agentic systems.
    *   LangGraph: For creating robust and stateful multi-agent architectures.
    *   LangServe: For deploying LangChain runnables and graphs as REST APIs with interactive playgrounds.
*   **Local LLM Serving:** Ollama (with Mistral-7B-Instruct as the default model).
*   **Web Framework (Backend):** FastAPI for building the main API, serving the LangServe application, and static frontend files.
*   **Data Storage & Handling:**
    *   Minio: S3-compatible object storage for documents.
    *   ChromaDB: Vector database for embeddings and semantic search.
*   **Event Streaming:** Redpanda (Kafka-compatible for asynchronous messaging).
*   **Containerization:** Docker & Docker Compose for managing services and ensuring consistent environments.
*   **Frontend (Demonstration UI):** React (via Vite) for the Kafka Inspector and basic interactions, served by the backend.
*   **Testing & Linting:** Pytest, Ruff, Black.
*   **Observability:** LangSmith for tracing and debugging LLM applications.
*   **Diagramming:** Mermaid (via `mmdc` CLI) for generating system architecture diagrams from text.

## 7. Switching Language Models

This project supports switching between different Large Language Model (LLM) providers using a Makefile command. This command updates the `.env` file with the necessary configurations for the selected provider.

**Command:**

```bash
make model-switch llm=<provider_config>
```

**Supported Provider Configurations:**

1.  **Ollama (with Mistral or other local models):**
    *   **Command:** `make model-switch llm=ollama/mistral`
        *   Replace `mistral` with any other Ollama model name you have pulled (e.g., `ollama/llama2`). The command will use the part after `ollama/` as the `OLLAMA_MODEL_NAME`.
    *   **`.env` Variables Set:**
        *   `LLM_PROVIDER="ollama"`
        *   `OLLAMA_MODEL_NAME="<your_model_name>"` (e.g., "mistral")
        *   `OLLAMA_BASE_URL="http://localhost:11434"` (default Ollama API endpoint)
    *   **Requirements:**
        *   Ollama must be installed and running.
        *   The specified model (e.g., `mistral`) must be pulled via `ollama pull <model_name>`.
    *   **Note:** This will unset/comment out Gemini-specific variables (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME`) in your `.env` file.

2.  **Google Gemini:**
    *   **Command:** `make model-switch llm=gemini` or `make model-switch llm=gemini/<model_name>` (e.g., `make model-switch llm=gemini/gemini-2.5-flash-latest`).
        *   If only `gemini` is provided, the Makefile may use a default model (e.g., `gemini-2.5-flash-latest`). Check the `Makefile` for specific behavior.
    *   **`.env` Variables Set:**
        *   `LLM_PROVIDER="gemini"`
        *   `GEMINI_MODEL_NAME="<your_gemini_model_name>"`
    *   **Variables You Must Set Manually:**
        *   `GEMINI_API_KEY="YOUR_GEMINI_API_KEY"` **<-- TODO: Add your actual API key here in the .env file**
    *   **Requirements:**
        *   `google-generativeai` Python package installed (should be in `requirements.txt`).
        *   A valid `GEMINI_API_KEY` set in your `.env` file.
    *   **Note:** This will unset/comment out Ollama-specific variables (`OLLAMA_MODEL_NAME`, `OLLAMA_BASE_URL`) in your `.env` file.

**After Switching:**
It's recommended to restart the backend application to ensure the new LLM configuration is loaded. The `make model-switch` command may include a placeholder for smoke tests, which you can expand to verify the new LLM is working.

