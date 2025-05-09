Claims-AI MVP – Project Requirements (Open-Source Prototype with Phi-4)
1 Executive Summary
Build a MacBook-hosted, end-to-end prototype that:
Uploads, OCRs and classifies large claim files (pdf, tiff, docx).
Provides semantic search, instant Q&A with grounded citations and document summaries.
Drafts a claim-strategy note in Word (DOCX) format.
Adds four innovation features: Nearest Precedent Finder, Confidence Meter & Self-Healing Answers, Voice-Over Playback, Interactive Red-Team Button.
Runs entirely on free/open-source components, centred on Microsoft Phi-4-Reasoning-Plus served locally via LM Studio.
Ships with a full automated test suite, GitHub Actions CI and an explanation.txt learning log that Cursor populates at every phase.
Every component has a one-to-one mapping to Azure, AWS and GCP managed services so the codebase can graduate to an enterprise, regulated cloud deployment with minimal change.

2 Objectives & Success Criteria
 ID 
Objective
Metric / Acceptance
 O-1 
Reduce manual review time per complex claim
≥ 60 % reduction vs baseline (benchmarked on 50 real cases)
 O-2 
Answer accuracy (Q&A)
≥ 90 % correct & fully cited (eval harness)
 O-3 
Strategy note draft quality
≥ 4 / 5 average handler rating
 O-4 
Innovation layer usefulness
≥ 70 % handlers say feature is useful (survey)
 O-5 
Latency ≤ 5 s chat, 20 s note
P95 in local tests
 O-6 
Automated tests & docs
Coverage ≥ 85 %, explanation.txt updated at each phase


3 Feature Set
3.1 Core
Upload & OCR – Tesseract via Python, PDF → text JSON.
Vector DB – Chroma (local) with text-embedding-3-small.
RAG Chat – Phi-4 via LM Studio completion endpoint (http://localhost:1234/v1/chat/completions).
Doc Summaries & Strategy Note – prompt chains (+ python-docx export).
3.2 Innovation Layer
Nearest Precedent Finder – k-NN on historic claim embeddings; UI side-panel.
Confidence Meter + Self-Healing – Reflexion scoring; auto-retry on low score.
Voice-Over Playback – Coqui TTS container → mp3 response.
Interactive Red-Team – 5 adversarial prompts; score overlay.
3.3 Learning Artefacts
explanation.txt – Cursor appends a plain-language (ELI5 + technical) summary after finishing each phase.
Final Developer Guide (Markdown) auto-generated from explanation log + diagrams.

4 Local Prototype Architecture
[Browser]──HTTPS──┐
                  │React + Chakra UI (Vite)
                  ▼
            FastAPI Gateway  <─>  Postgres (metadata)
                  │
                  │REST
                  ▼
           RAG Orchestrator (LangChain)
            │   │    │
            │   │    └── Chroma (Vector Store)
            │   │
            │   └── Phi-4 via LM Studio (localhost:1234)
            │
            ├── Coqui TTS (docker)  →  Minio (mp3)
            └── Security / Eval harness
Everything runs under Docker-Compose except LM Studio, which is launched as a desktop app exposing its REST port.

5 Enterprise-Ready Migration Paths
Layer
Local PoC Component
Azure Option
AWS Option
GCP Option
Vector DB
Chroma
Azure AI Search (vector store)
OpenSearch Serverless
Vertex AI Matching Engine
LLM
Phi-4 via LM Studio
Azure OpenAI GPT-4o / Phi (when GA)
Bedrock Claude 3
Vertex AI Gemini 1.5 Pro
Storage
Minio (S3-API)
Azure Blob Storage
S3 Standard
GCS Standard
TTS
Coqui TTS
Azure AI Speech
Polly
Media TTS
Auth & API
FastAPI local
Azure APIM + AAD
API Gateway + Cognito
API Gateway + IAP
CI/CD
GitHub Actions
GitHub Actions + Azure Container Registry + AKS
CodeBuild → EKS
Cloud Build → GKE

Each mapping has been validated for feature parity; config files (docker-compose.azure.yml, aws.yml, gcp.yml) are provided in repo for a one-command switch-over.

6 DevOps & Learning Workflow
Cursor AI -assistant loop – every task begins with plan → validate (HITL) → implement per cursorrules.mdc.
Pre-commit: ruff, black, pytest.
GitHub Actions pipeline: lint, unit, integration, Playwright e2e, build & push image, kind smoke test.
Explanation generation: scripts/log_phase.py appends bullet ELI5 & technical notes to explanation.txt; called at end of each phase.

7 Front-End & Demo Experience
Guided Tour Modal – first-visit walkthrough of features & architecture diagram.
Info Sidebar – expandable panel explaining how the app works (text + Mermaid diagram) for stakeholders.
Colour-coded Confidence Glow – immediate visual cue for answer reliability.
Demo Script (docs/demo_script.md): ordered clicks, what to say, fallback screenshots.

8 Assumptions & Constraints
LM Studio macOS app ≥ 0.2.20; Phi-4 RP weights downloaded locally.
Dev machine has 16 GB RAM / 8 GB VRAM or Rosetta-opt-in.
Initial precedent dataset is synthetic or anonymised.

9 Acceptance Criteria
All objectives O-1 … O-6 met.
End-to-end Playwright test passes on local and Azure swap.
explanation.txt accurately reflects each phase in both ELI5 and technical language.

10 Open Questions
Do we need OCR for handwritten witness statements? (Plug Tesseract LSTM models?)
Licensing of Phi-4 weights for production—await Microsoft terms.
