# Claims-AI MVP Implementation

This document outlines the tasks required to build the Claims-AI MVP, an open-source prototype for claim file processing, Q&A, and strategy note generation, utilizing local LLMs and open-source components.

Legend: ☐ Todo | ☑ Done | 🛠 Automated by script | 🔍 Cursor-prompt (human-in-the-loop)
*Cursor will tick the boxes as it runs and write phase reflections to `explanation.txt`.*
*All paths are relative to repo root unless otherwise specified.*

## Completed Tasks

### Global Prerequisites (Run once per dev machine)
- [x] **Core Tooling:**
  - [x] `brew install git docker docker-compose node@20 pnpm python@3.11 jq tesseract ffmpeg graphviz`
- [x] **LM Studio Setup:**
  - [x] Download LM Studio `.dmg` and install to `/Applications`.
  - [x] Launch LM Studio → Model Gallery → Search `phi-4-reasoning-plus` → Download & Serve (ensure REST API is available on port 1234).
- [x] **Docker Desktop Configuration:**
  - [x] Enable Docker Desktop.
  - [x] Allocate ≥ 8 GB RAM & 4 CPU to Docker.
- [x] **Repository Setup:**
  - [x] Clone repository: `git clone git@github.com:pwc/claims-ai.git && cd claims-ai` (or appropriate repo URL)
  - [x] Create `project.txt` (copy of Requirements from user prompt).
  - [x] Confirm `tasks.md` (this file) is in the repo root.
- [x] **Python Environment:**
  - [x] `pyenv install 3.11.7` (or latest stable 3.11.x)
  - [x] `pyenv local 3.11.7`
  - [x] `python -m venv .venv`
  - [x] `source .venv/bin/activate`
  - [x] `pip install -r requirements.txt` (Create `requirements.txt` first if it doesn't exist)
- [x] **Node.js Dependencies:**
  - [x] `pnpm install` (Ensure `package.json` is present)
- [x] **Pre-commit Hooks:**
  - [x] Create/verify `.pre-commit-config.yaml` (with `black`, `ruff`).
  - [x] `pre-commit install` (Run after `git init` and first commit).

### Phase 1 – Local Infrastructure (Docker-Compose)
- [x] **P1.A: Docker Compose & Backend Stubs**
  - [x] P1.A.1: Draft `docker-compose.yml` with `backend`, `minio`, `chromadb` services.
  - [x] P1.A.2: Create stub `backend/Dockerfile`, `backend/main.py` (FastAPI stub), `backend/requirements.txt`.
- [x] **P1.B: Basic Directory Structure & Initial Data (🔍)**
  - [x] Create `data/raw`, `data/processed_text`, `data/embeddings`, `data/outputs`, `data/precedents`, `scripts/`, `tests/`.
  - [x] Add `.gitkeep` to empty directories.
  - [x] Create `data/precedents/precedents.csv.sample`.
  - [x] Create `.env.sample` (user manually created this based on provided content).
- [x] **P1.C: Environment Configuration (🔍)**
  - [x] Create `.env` from `.env.sample` (`cp .env.sample .env`).
- [x] **P1.D: Start Core Services (Docker Compose)**
  - [x] Execute `docker-compose up -d`. (Note: `docker-compose.yml` is used by default if no `-f` flag specified)
  - [x] **Outcome:** Minio, ChromaDB containers are running (backend also started successfully after Dockerfile fix).
- [x] **P1.E: Verify LM Studio Connection (🔍)**
  - [x] Run `curl -X POST http://localhost:1234/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"phi-4-reasoning-plus","messages":[{"role":"user","content":"ping"}]}'`
  - [x] **Outcome:** Successful JSON response from LM Studio.
- [x] **P1.F: Health Check Script (🛠️)**
  - [x] Develop `scripts/check_services.sh`.
  - [x] Script should verify all Docker containers (Minio, ChromaDB, Backend) AND the LM Studio API endpoint are healthy.
  - [x] **Outcome:** Script returns exit code 0 when all services are healthy.
- [x] **P1.G: Logging for Phase 1 (🔍)**
  - [x] Ensure explanations from this phase are logged to `explanations.txt`.

- [x] **P1.H: PostgreSQL Setup ( precursor to P2.1)**
  - [x] Update `docker-compose.yml` to include a `postgres` service.
  - [x] Update `backend` service in `docker-compose.yml` (add `postgres` to `depends_on`, add `POSTGRES_*` env vars from `.env` file).
  - [x] Create/Update `.env.sample` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` and move other service credentials here.
  - [x] Update `backend/requirements.txt` to include `psycopg2-binary`.
  - [x] User to create/update `.env` with actual PostgreSQL credentials.
  - [x] Run `docker-compose up -d --build` to bring up Postgres and rebuild the backend.
  - [x] Update `scripts/check_services.sh` to verify Postgres health.
  - [x] Run `scripts/check_services.sh` to confirm Postgres is healthy.
  - [x] Document PostgreSQL setup in `explanations.txt`.

## In Progress Tasks

### Phase 2 – Document Ingestion Pipeline
- [x] **P2.1: OCR Pipeline Script:** (Completed)
  - [x] Develop `scripts/extract_text.py` (initial script structure created).
  - [x] Add required Python packages (e.g., `pytesseract`, `Pillow`, `python-docx`, `psycopg2-binary`, PDF libraries) to `backend/requirements.txt`.
  - [x] Implement text extraction logic for PDF, TIFF, DOCX in `scripts/extract_text.py`.
  - [x] Implement PostgreSQL metadata storage in `scripts/extract_text.py` (define table, insert/update records).
  - [x] Test script with sample documents: `python scripts/extract_text.py --src data/raw --out data/processed_text` (script now operational via Docker exec).
  - [x] Ensure structured text output (e.g., JSON per document) to `data/processed_text` (verified from test run).

- [x] **P2.2: Chunking and Embedding Script:** (Completed)
  - [x] Develop `scripts/chunk_embed.py` (initial script structure created).
  - [x] Add required Python packages (e.g., `chromadb`, `langchain-text-splitters`, `langchain-openai`, `tiktoken`) to `backend/requirements.txt`.
  - [x] Implement text chunking logic in `scripts/chunk_embed.py`.
  - [x] Implement embedding generation (using `text-embedding-3-small` via LM Studio or OpenAI SDK) in `scripts/chunk_embed.py`.
  - [x] Implement storage of chunks and embeddings into ChromaDB collection.
  - [x] Test script with sample processed JSON files: `python scripts/chunk_embed.py --in data/processed_text`.

- [x] **P2.3: RAG API Endpoint in FastAPI (`backend/main.py`)**
  - [x] Define request/response models for RAG.
  - [x] Implement a RAG function that:
    - [x] Takes a user query.
    - [x] Generates an embedding for the query using the LM Studio model.
    - [x] Queries ChromaDB for relevant chunks.
    - [x] Constructs a prompt with context from retrieved chunks.
    - [x] Sends the prompt to the LM Studio Phi-4 model for answer generation.
  - [x] Create an API endpoint (e.g., `/api/v1/query`) that uses the RAG function.
  - [x] Add necessary error handling and logging.
  - [x] Test the endpoint thoroughly (integration test coverage confirmed).

### Phase 3 – Core RAG API (FastAPI)
- [x] **P3.1: FastAPI Application Scaffold:** (Completed)
  - [x] Set up FastAPI application in `backend/` directory.
  - [x] Include basic structure: `main.py`, `api/` routes, `services/`, `models/`, `core/config.py`.
  - [x] Integrate with LM Studio Phi-4 endpoint (via centralized config).
- [x] **P3.2: `/ask` Route:** (Completed)
  - [x] Implement FastAPI endpoint `/api/v1/ask` (renamed from `/query`).
  - [x] Performs hybrid search (semantic search on ChromaDB + basic keyword filter using `where_document`).
  - [x] Constructs prompt with retrieved context for Phi-4 (existing logic).
  - [x] Returns answer and grounded citations (existing logic).
- [x] **P3.3: `/summarise` Route:** (Completed)
  - [x] Implement FastAPI endpoint `/api/v1/summarise`.
  - [x] Accepts document ID or content (with validation).
  - [x] Generates single document summary using Phi-4 (via `SummarisationService`).
- [x] **P3.4: `/draft` Route:** (Completed)
  - [x] Implement FastAPI endpoint `/api/v1/draft`.
  - [x] Accepts criteria or context (e.g., multiple document IDs, Q&A history, summary, criteria).
  - [x] Generates claim strategy note using Phi-4 (via `DraftingService`).
  - [x] Exports to DOCX format using `python-docx` (via `DraftingService` and `FileResponse`).
- [x] **P3.5: API Integration Tests:** (Completed)
  - [x] Create and run integration tests: `pytest -m api tests/backend/integration/` (tests created).
  - [x] Test all API endpoints (`/ask`, `/summarise`, `/draft`) with mock data and (if possible) live services (achieved via TestClient and dummy data files).
- [x] 🔍 **Logging:** Document API design, endpoint details, and RAG pipeline in `explanations.txt`.

### Phase 4 – Innovation Layer Features
- [x] **P4.A: Nearest Precedent Finder**
  - [x] **P4.A.1:** Create `data/precedents/precedents.csv` (or JSON) with synthetic/anonymised precedent data.
  - [x] **P4.A.2:** Develop `scripts/embed_precedents.py` to process and store precedent embeddings in ChromaDB (potentially in a separate collection).
  - [x] **P4.A.3:** Implement FastAPI endpoint `/api/v1/precedents` that accepts a claim summary/embedding and returns top-k (e.g., 5) nearest precedents. *(Integration tests passing)*
- [x] **P4.B: Confidence Meter & Self-Healing Answers**
  - [x] **P4.B.1:** Research and implement a Reflexion-style or similar confidence scoring mechanism for LLM responses from the `/ask` route.
  - [x] **P4.B.2:** If confidence score < threshold (e.g., 3/5), implement a self-healing mechanism (e.g., re-prompt Phi-4 with refined context, try alternative prompt strategy). *(Unit tests passing)*
  - [x] **P4.B.3:** (Frontend) Implement UI color glow based on confidence score and a progress bar/indicator for self-healing attempts. *(ChatPanel.tsx updated to include confidence glow and a spinner/text for self-healing attempts.)*
- [x] **P4.C: Voice-Over Playback** (Backend complete and tested)
  - [x] **P4.C.1:** Ensure Coqui TTS container is correctly configured in `docker-compose.dev.yml`. (Verified: container running, model loaded, correct image and platform, network configured, server command fixed)
  - [x] **P4.C.2:** (Backend) Implement MinIO integration in `SpeechService` to upload the generated MP3 and return a presigned URL.
  - [x] **P4.C.3:** (Frontend) Implement React audio controls to play back the MP3. *(Completed as part of P5.3: ChatPanel.tsx includes play/stop/loading buttons for AI messages.)*
- [x] **P4.D: Interactive Red-Team Button (Backend)**
  - [x] **P4.D.1:** Create `backend/security/redteam_prompts.yml` with 6 diverse adversarial prompts.
  - [x] **P4.D.2:** Implement FastAPI endpoint `/api/v1/redteam/run` that executes these prompts against the RAG system and returns qualitative results. *(Integration tests created and are now passing after resolving environment/tooling issues and code corrections.)*
  - [x] **P4.D.3:** (Frontend) Implement a button in the UI (e.g., in a settings or admin panel) that triggers the `/api/v1/redteam/run` endpoint and displays the results in a readable format. *(Completed as part of P5.3: RedTeamModal.tsx created and integrated.)*
  - [x] **P4.D.4:** 🔍 **Logging (P4.D):** Documented P4.D (Interactive Red-Team Button - Backend) design and implementation in `explanations.txt`.
- [x] 🔍 **Logging (Phase 4 - Innovation Layer):** All innovation features (P4.A, P4.B, P4.C-Backend, P4.D-Backend) have had their design and implementation documented in `explanation.txt` as part of their respective sub-tasks.

### Phase 5 – Front-End Development (React + Chakra UI)

**Note on Backend Operational Modes for Phase 5 & Beyond:**
*   **Local Uvicorn Mode (Current for P5.1, P5.2):** Backend (FastAPI) runs directly on host (`python backend/main.py` or `uvicorn backend.main:app --reload`), dependent Docker services (Postgres, Minio, etc.) started manually via `docker-compose up -d <service_names>`. `.env` host variables should be `localhost` (e.g., `POSTGRES_HOST=localhost`). Ideal for rapid backend iteration.
*   **Full Docker Compose Mode (Recommended for P5.3 onwards):** Backend runs inside a Docker container, started with all other services via `docker-compose up [--build]`. `.env` host variables should use Docker service names (e.g., `POSTGRES_HOST=postgres`, `CHROMA_HOST=chromadb`). Offers a more integrated and stable environment for testing complex inter-service features.
*   **Switching:** To switch modes, primarily update the service hostnames in your `.env` file and use the corresponding startup command for the backend.

- [x] **P5.1: Project Setup & Basic Layout:** (Completed)
  - [x] Initialize React project using Vite in `frontend/`.
  - [x] Integrate Chakra UI.
  - [x] Set up basic app structure, routing, and API communication layer with the FastAPI backend.
    *   `frontend/` directory created and Vite project initialized.
    *   `frontend/package.json`, `frontend/pnpm-lock.yaml` created/updated.
    *   `frontend/src/main.tsx` updated with ChakraProvider.
    *   `frontend/src/App.tsx` updated with React Router and basic structure.
    *   `frontend/src/pages/HomePage.tsx` created to display welcome and backend health.
    *   `frontend/src/components/.gitkeep` created.
    *   `frontend/src/services/.gitkeep` created.
    *   `frontend/src/services/apiClient.ts` created (Axios instance for backend API).
    *   `frontend/src/services/healthService.ts` created (fetches backend `/health`).
- [x] **P5.2: Core Feature UI:** (Completed)
  - [x] **Chat Panel:** Input for questions, display for answers with markdown rendering and citation chips. *(Chakra UI v2 migration resolved linter/type errors; component functional.)*
  - [x] **File Uploader:** Drag-and-drop zone for document uploads. *(FileUploader.tsx and backend DocumentService/API endpoint implemented and debugged.)*
  - [x] **Summarise Panel:** Interface to request document summaries by ID or pasted text, display results. *(SummarisePanel.tsx, summariseService.ts integrated into HomePage.tsx.)*
  - [x] **Strategy Note:** Interface to trigger generation, view/edit (basic), and export drafted strategy notes (Word). *(StrategyNoteGenerator.tsx, draftService.ts, draft.ts integrated.)*
- [x] **P5.3: Innovation Feature UI Integration:** (Completed)
  - [x] **Precedent Panel:** Display for nearest precedents. *(Frontend component PrecedentPanel.tsx, service precedentService.ts, and models precedent.ts implemented. Integrated into HomePage.tsx.)*
  - [x] **Confidence Glow & Self-Healing Indicator:** Visual feedback for answer confidence and self-healing attempts. *(ChatPanel.tsx modified to display a border/shadow color based on AI message confidence score and a spinner/text for self-healing; score also displayed textually. Addresses P4.B.3)*
  - [x] **Voice-Over Button:** Controls for TTS playback. *(ChatPanel.tsx modified to include play/stop/loading buttons for AI messages, integrating with speechService.ts to fetch and play audio. Addresses P4.C.3)*
  - [x] **Red-Team Modal:** Button to trigger and display red-team results. *(RedTeamModal.tsx component created and integrated into HomePage.tsx. Allows running backend red team evaluation and displays results. Addresses P4.D.3)*
- [x] **P5.4: Demo Experience UI:**
  - [x] **Info Overlay/Sidebar:** For architecture diagram (SVG/Mermaid) and "how-it-works" text.
  - [x] **Guided Tour Modal:** First-visit walkthrough mode (with some sort of option/button to allow the user to re-run/access it whenever they desire). User needs to be able to demonstrate this to technical and non-technical business stakeholders and ensure they can effectively use it (great UI & UX) and can see the key features that match what the client required for their MVP (as per projects.md). All features, how you use them, and technical aspects must be crystal clear for all users.
- [x] **P5.5: Transition to Full Docker Compose Mode for Backend Operation**
  - Ensure all backend services (API, RAG, Minio, Postgres, LM Studio Phi-4, Coqui TTS) are orchestrated via `docker-compose.yml`.
  - Verify local development environment can run entirely through `docker compose up --build`.
  - Update `.env` to reflect Docker service names for inter-service communication (e.g., `CHROMA_HOST=chromadb`).
  - Run backend tests (`pytest`) to ensure all integrations work correctly in Dockerized mode. (All backend tests passing after fixes to .env, validation_exception_handler, and RedTeamService tests)

### Phase 6 – Testing & CI/CD
- [x] **P6.1: Test Coverage:**
  - [x] Ensure backend `pytest` unit and integration test coverage ≥ 85% (Overall).
    - [x] `backend/services/document_service.py` coverage is ≥ 85% (Achieved 86%).
  - [x] Run `pytest --cov=backend --cov-report=html` to generate HTML report.
  - [x] **API Router Tests:** Add unit tests for routers:
    - [x] `backend/api/v1/document_router.py`
    - [x] `backend/api/v1/draft_router.py`
    - [x] `backend/api/v1/precedent_router.py`
    - [x] `backend/api/v1/redteam_router.py`
    - [x] `backend/api/v1/speech_router.py`
    - [x] `backend/api/v1/summarise_router.py`
  - [x] **Core & Config Tests:** Add tests for main.py, config.py.
    - [x] `tests/backend/unit/api/test_main.py`
    - [x] `tests/backend/unit/core/test_config.py`
  - [x] **Service Layer Tests:** Add tests for services with <80% coverage:
    - [x] `backend/services/document_loader.py`
    - [x] `backend/services/drafting_service.py`
    - [x] `backend/services/minio_service.py`
    - [x] `backend/services/precedent_service.py`
    - [x] `backend/services/redteam_service.py`
    - [x] `backend/services/speech_service.py`
    - [x] `backend/services/summarisation_service.py`
- [x] **P6.2: End-to-End Testing:**
  - [x] Develop Playwright E2E tests for key user flows (upload, ask, summarise, draft, view precedent).
  - [x] Store tests in `tests/e2e/`.
- [ ] **P6.3: GitHub Actions CI Workflow:**
  - [x] Create `.github/workflows/ci.yml`.
  - [x] Linting (Ruff, Black, Prettier for frontend).
  - [x] Backend tests (pytest).
  - [x] Frontend tests (Vitest + React Testing Library implemented).
  - [ ] Playwright E2E tests (scaffold only; defer full implementation until LM Studio container or CI stub is available).
  - [x] Build Docker images (backend).
  - [x] (Optional) Publish images to GHCR (GitHub Container Registry) – backend image publishing implemented via CI; frontend publishing can be added once a `frontend/Dockerfile` is in place.
  - [ ] Configure workflow to fail build if test coverage drops or tests fail.
- [x] 🔍 **Logging:** Explain CI setup, test strategies, and interpret initial CI results in `explanations.txt`.

### Phase 7 – Documentation & Demo Assets
- [x] **P7.1: Architecture Diagram:**
  - [x] Create/update architecture diagram (e.g., using Mermaid or Graphviz).
  - [x] Consider a `make arch-diagram` command or similar in a `Makefile` to generate/update SVG from source.
- [x] **P7.2: Demo Data:**
  - [x] Prepare a set of 15-20 redacted/synthetic claim documents for demo purposes.
  - [x] Optionally, a script `scripts/load_demo_data.sh` to populate `data/raw`
- [x] **P7.3: Readme:**
  - [x] Create a very thorough, detailed and complete readme.md file that will allow anyone who accesses the GitHub repo/page for this to get a fantastic, clear and informative overview of this project, including all technical aspects and features explained, and detailed, step-by-step instructions around how to set this up and use it for themselves. This should also include outputs from P7.1, and explanations around future upgrade paths to make this enterprise-ready, as outlined in project.md

## Future Tasks