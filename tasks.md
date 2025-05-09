# Claims-AI MVP Implementation

This document outlines the tasks required to build the Claims-AI MVP, an open-source prototype for claim file processing, Q&A, and strategy note generation, utilizing local LLMs and open-source components.

Legend: ☐ Todo | ☑ Done | 🛠 Automated by script | 🔍 Cursor-prompt (human-in-the-loop)
*Cursor will tick the boxes as it runs and write phase reflections to `explanation.txt`.*
*All paths are relative to repo root unless otherwise specified.*

## Completed Tasks

*(Tasks will be moved here as they are completed)*

## In Progress Tasks

*(Tasks will be moved here when active)*

## Future Tasks

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
- [ ] **Pre-commit Hooks:**
  - [ ] `pre-commit install` (Ensure `.pre-commit-config.yaml` is present)

### Phase 0 – Plan & Confirm (🔍)
- [ ] 🔍 **Review and Plan:**
  - [ ] AI to review `project.txt` & `tasks.md`.
  - [ ] AI to outline its execution plan in `explanation.txt`.
  - [ ] AI to ask for clarification if any ambiguity.
- [ ] **Logging:**
  - [ ] Ensure explanations from this phase are logged to `explanation.txt`.

### Phase 1 – Local Infrastructure (Docker-Compose)
- [ ] **P1.1: Environment Configuration:**
  - [ ] Create `.env` from `.env.sample` (`cp .env.sample .env`).
  - [ ] 🔍 AI to assist in filling in necessary ports, secrets, and local paths in `.env`.
- [ ] **P1.2: Start Core Services:**
  - [ ] Execute `docker-compose -f docker-compose.dev.yml up -d` (or `docker-compose.yml` if that's the final name).
  - [ ] **Outcome:** Minio, Postgres, ChromaDB, Coqui TTS containers are running.
- [ ] **P1.3: Verify LM Studio Connection:**
  - [ ] Run `curl -X POST http://localhost:1234/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"phi-4-reasoning-plus","messages":[{"role":"user","content":"ping"}]}'`
  - [ ] **Outcome:** Successful JSON response from LM Studio.
- [ ] **P1.4: Health Check Script:**
  - [ ] Develop `scripts/check_services.sh`.
  - [ ] Script should verify all Docker containers (Minio, Postgres, Chroma, Coqui TTS) AND the LM Studio API endpoint are healthy.
  - [ ] **Outcome:** Script returns exit code 0 when all services are healthy.
- [ ] 🔍 **Logging:** Document phase learnings and setup in `explanation.txt`.

### Phase 2 – Document Ingestion Pipeline
- [ ] **P2.1: OCR Pipeline Script:**
  - [ ] Develop `scripts/extract_text.py`.
  - [ ] Command: `python scripts/extract_text.py --src data/raw --out data/processed_text` (adjust paths as needed).
  - [ ] Handles PDF, TIFF, DOCX; outputs structured text (e.g., JSON per document) to `data/processed_text`.
  - [ ] Stores metadata (original filename, processing status, text path) in Postgres.
- [ ] **P2.2: Chunking and Embedding Script:**
  - [ ] Develop `scripts/chunk_embed.py`.
  - [ ] Command: `python scripts/chunk_embed.py --in data/processed_text --db chromadb_store` (adjust paths/DB name).
  - [ ] Chunks text from `data/processed_text`.
  - [ ] Generates embeddings using `text-embedding-3-small`.
  - [ ] Stores chunks and embeddings in ChromaDB.
- [ ] **P2.3: Unit Tests for Ingestion:**
  - [ ] Create and run unit tests: `pytest tests/ingestion/`.
  - [ ] Cover OCR extraction, text processing, chunking, and embedding logic.
- [ ] 🔍 **Logging:** Document phase learnings, script details, and data flow in `explanation.txt`.

### Phase 3 – Core RAG API (FastAPI)
- [ ] **P3.1: FastAPI Application Scaffold:**
  - [ ] Set up FastAPI application in `backend/` directory.
  - [ ] Include basic structure: `main.py`, `api/` routes, `services/`, `models/`, `core/config.py`.
  - [ ] Integrate with LM Studio Phi-4 endpoint.
- [ ] **P3.2: `/ask` Route:**
  - [ ] Implement FastAPI endpoint `/api/v1/ask`.
  - [ ] Performs hybrid search (semantic search on ChromaDB + keyword search if beneficial).
  - [ ] Constructs prompt with retrieved context for Phi-4.
  - [ ] Returns answer and grounded citations.
- [ ] **P3.3: `/summarise` Route:**
  - [ ] Implement FastAPI endpoint `/api/v1/summarise`.
  - [ ] Accepts document ID or content.
  - [ ] Generates single document summary using Phi-4.
- [ ] **P3.4: `/draft` Route:**
  - [ ] Implement FastAPI endpoint `/api/v1/draft`.
  - [ ] Accepts criteria or context (e.g., multiple document IDs, Q&A history).
  - [ ] Generates claim strategy note using Phi-4.
  - [ ] Exports to DOCX format using `python-docx`.
- [ ] **P3.5: API Integration Tests:**
  - [ ] Create and run integration tests: `pytest -m api tests/backend/integration/`.
  - [ ] Test all API endpoints with mock data and (if possible) live services.
- [ ] 🔍 **Logging:** Document API design, endpoint details, and RAG pipeline in `explanation.txt`.

### Phase 4 – Innovation Layer Features
- [ ] **P4.A: Nearest Precedent Finder**
  - [ ] **P4.A.1:** Create `data/precedents/precedents.csv` (or JSON) with synthetic/anonymised precedent data.
  - [ ] **P4.A.2:** Develop `scripts/embed_precedents.py` to process and store precedent embeddings in ChromaDB (potentially in a separate collection).
  - [ ] **P4.A.3:** Implement FastAPI endpoint `/api/v1/precedents` that accepts a claim summary/embedding and returns top-k (e.g., 5) nearest precedents.
  - [ ] **P4.A.4:** (Frontend) Implement React side-panel component to display precedent information.
- [ ] **P4.B: Confidence Meter & Self-Healing Answers**
  - [ ] **P4.B.1:** Research and implement a Reflexion-style or similar confidence scoring mechanism for LLM responses from the `/ask` route.
  - [ ] **P4.B.2:** If confidence score < threshold (e.g., 3/5), implement a self-healing mechanism (e.g., re-prompt Phi-4 with refined context, try alternative prompt strategy).
  - [ ] **P4.B.3:** (Frontend) Implement UI color glow based on confidence score and a progress bar/indicator for self-healing attempts.
- [ ] **P4.C: Voice-Over Playback**
  - [ ] **P4.C.1:** Ensure Coqui TTS container is correctly configured in `docker-compose.dev.yml`.
  - [ ] **P4.C.2:** Implement FastAPI endpoint `/api/v1/speech` that accepts text and returns an MP3 audio stream/file generated by Coqui TTS. Store generated MP3s in Minio.
  - [ ] **P4.C.3:** (Frontend) Implement React audio controls to play back the MP3.
- [ ] **P4.D: Interactive Red-Team Button**
  - [ ] **P4.D.1:** Create `security/redteam_prompts.yml` (or JSON) with 5 diverse adversarial prompts.
  - [ ] **P4.D.2:** Implement FastAPI endpoint `/api/v1/redteam` that executes these prompts against the RAG system and returns success/failure metrics or qualitative results.
  - [ ] **P4.D.3:** (Frontend) Implement a UI button to trigger red-teaming and a modal/display area for the results.
- [ ] 🔍 **Logging:** Document each innovation feature's design and implementation in `explanation.txt`.

### Phase 5 – Front-End Development (React + Chakra UI)
- [ ] **P5.1: Project Setup & Basic Layout:**
  - [ ] Initialize React project using Vite in `frontend/`.
  - [ ] Integrate Chakra UI.
  - [ ] Set up basic app structure, routing, and API communication layer with the FastAPI backend.
- [ ] **P5.2: Core Feature UI:**
  - [ ] **Chat Panel:** Input for questions, display for answers with markdown rendering and citation chips.
  - [ ] **File Uploader:** Drag-and-drop zone for document uploads.
  - [ ] **Strategy Note:** Interface to trigger generation, view/edit (basic), and export drafted strategy notes (Word).
- [ ] **P5.3: Innovation Feature UI Integration:**
  - [ ] **Precedent Panel:** Display for nearest precedents.
  - [ ] **Confidence Glow:** Visual feedback for answer confidence.
  - [ ] **Voice-Over Button:** Controls for TTS playback.
  - [ ] **Red-Team Modal:** Button to trigger and display red-team results.
- [ ] **P5.4: Demo Experience UI:**
  - [ ] **Info Overlay/Sidebar:** For architecture diagram (SVG/Mermaid) and "how-it-works" text.
  - [ ] **Guided Tour Modal:** (Optional, if time permits) First-visit walkthrough.
- [ ] 🔍 **Logging:** Document UX choices, component design, and demo tips in `explanation.txt`.

### Phase 6 – Testing & CI/CD
- [ ] **P6.1: Test Coverage:**
  - [ ] Ensure backend `pytest` unit and integration test coverage ≥ 85%.
  - [ ] `pytest --cov=backend --cov-report=html`
- [ ] **P6.2: End-to-End Testing:**
  - [ ] Develop Playwright E2E tests for key user flows (upload, ask, summarise, draft, view precedent).
  - [ ] Store tests in `tests/e2e/`.
- [ ] **P6.3: GitHub Actions CI Workflow:**
  - [ ] Create `.github/workflows/ci.yml`.
  - [ ] Workflow steps:
    - [ ] Linting (Ruff, Black, Prettier for frontend).
    - [ ] Backend tests (pytest).
    - [ ] Frontend tests (e.g., Jest/Vitest if implemented).
    - [ ] Playwright E2E tests.
    - [ ] Build Docker images (backend, frontend).
    - [ ] (Optional) Publish images to GHCR (GitHub Container Registry).
  - [ ] Configure workflow to fail build if test coverage drops or tests fail.
- [ ] 🔍 **Logging:** Explain CI setup, test strategies, and interpret initial CI results in `explanation.txt`.

### Phase 7 – Documentation & Demo Assets
- [ ] **P7.1: Architecture Diagram:**
  - [ ] Create/update architecture diagram (e.g., using Mermaid or Graphviz).
  - [ ] Consider a `make arch-diagram` command or similar in a `Makefile` to generate/update SVG from source.
- [ ] **P7.2: Demo Data:**
  - [ ] Prepare a set of 5-10 redacted/synthetic claim documents for demo purposes.
  - [ ] Optionally, a script `scripts/load_demo_data.sh` to populate `data/raw`