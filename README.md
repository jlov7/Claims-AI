# Claims-AI MVP

**Claims-AI** is an open-source prototype designed to transform how legal professionals process and analyze complex insurance claims. By combining document ingestion, OCR, Retrieval-Augmented Generation (RAG), and local large language models (LLMs), this toolchain dramatically reduces manual review time and empowers users with AI-driven insights.

---

## 1. Executive Summary & Motivation

Claims processing in insurance and legal contexts often involves hours—if not days—of manual review across multiple document types (PDFs, TIFFs, DOCX). Claims-AI was created to:

- **Reduce manual review time** by ≥60% (O-1).
- **Improve answer accuracy** to ≥90% with grounded citations (O-2).
- **Produce high-quality strategy notes** with ≥4/5 handler ratings (O-3).
- **Surface relevant precedents** and self-heal uncertain answers (O-4).
- **Keep latency under 5s for chat** and under 20s for draft notes (O-5).
- **Maintain automated test coverage ≥85%**, with live CI/CD and documentation (O-6).

This MVP runs entirely on open-source components and a locally hosted Phi-4 model via LM Studio.

---

## 2. Core Features

### 2.1 Document Ingestion & OCR

- Drag-and-drop or API-driven upload of PDFs, TIFFs, DOCX.
- Automated text extraction via Tesseract OCR, PDFMiner, and python-docx.
- Metadata storage in PostgreSQL and JSON output in `data/processed_text/`.

### 2.2 RAG Q&A Endpoint (`/api/v1/ask`)

- Converts questions into embeddings, performs semantic + keyword hybrid search on ChromaDB.
- Builds contextual prompts, invokes Phi-4 for answers, and returns grounded citations.

### 2.3 Summarisation Endpoint (`/api/v1/summarise`)

- Accepts **either** a `document_id` **or** raw text.
- Generates concise, factual summaries via the Phi-4 model.

### 2.4 Draft Strategy Note (`/api/v1/draft`)

- Takes claim summary, document IDs, Q&A history, and criteria.
- Compiles context, prompts Phi-4, and exports a Word (`.docx`) strategy note.

### 2.5 Innovation Layer

- **Nearest Precedent Finder** (`/api/v1/precedents`): Retrieves top-k similar past claims.
- **Confidence Meter & Self-Healing**: Scores answers 1–5, auto-reprompts on low confidence.
- **Voice-Over Playback** (`/api/v1/speech`): Text-to-speech with Coqui TTS and Minio storage.
- **Interactive Red-Team Evaluation** (`/api/v1/redteam/run`): Runs adversarial prompt suite for robustness testing.

---

## 3. Architecture

![Architecture Diagram](docs/architecture.svg)

Core Components:

1. **Frontend**: React + Chakra UI (Vite) customer-facing UI (port 5173).
2. **Backend**: FastAPI gateway (port 8000) with modular routers and services.
3. **PostgreSQL**: Metadata and ingestion pipeline records.
4. **ChromaDB**: Vector store for RAG and precedent embeddings.
5. **Minio**: S3-compatible storage for TTS audio and files.
6. **LM Studio (Phi-4)**: Local LLM for chat, summarisation, drafting, and embeddings.
7. **Coqui TTS**: Dockerized service for generating MP3s.

All backed by Docker Compose for reproducible stacks.

---

## 4. Getting Started

### 4.1 Prerequisites

- **macOS/Linux** with Docker Desktop
- **LM Studio** desktop app with `phi-4-reasoning-plus` model → REST on port 1234
- **Python 3.11**
- **Node.js 20** & **pnpm**

### 4.2 Local Setup

```bash
# 1. Clone
git clone git@github.com:jlov7/Claims-AI.git
cd Claims-AI

# 2. Environment
cp .env.sample .env   # Update keys & hosts

# 3. Python backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 4. Frontend
npm install -g pnpm
cd frontend && pnpm install && cd ..

# 5. Demo data
./scripts/load_demo_data.sh
``` 

### 4.3 Running

#### Docker Compose Mode (All-in-One)
```bash
docker-compose up --build -d
``` 
- FastAPI: http://localhost:8000/docs
- UI: http://localhost:5173

#### Local Dev Mode
```bash
# Backend (requires Docker services for DB, Chroma, Minio, TTS)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && pnpm dev
``` 

---

## 5. Usage Examples

### Ask a Question
```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is the claimant asking for?"}'
```

### Summarise a Document
```bash
curl -X POST http://localhost:8000/api/v1/summarise \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"demo_claim_01.pdf.json"}'
```

### Generate Strategy Note
```bash
curl -X POST http://localhost:8000/api/v1/draft \
  -H 'Content-Type: application/json' \
  -d '{"claim_summary":"Auto accident summary...","output_filename":"MyClaimNote.docx"}' --output MyClaimNote.docx
```

### Find Precedents
```bash
curl -X POST http://localhost:8000/api/v1/precedents \
  -H 'Content-Type: application/json' \
  -d '{"claim_summary":"water damage claim"}'
```

### Text-to-Speech
```bash
curl -X POST http://localhost:8000/api/v1/speech \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello, Claims-AI user!"}'
```

### Run Red-Team Evaluation
```bash
curl http://localhost:8000/api/v1/redteam/run | jq .
```

---

## 6. Testing & Quality

- **Unit & Integration:** `pytest --cov=backend --cov-report=html`
- **E2E:** `npx playwright test`
- **Lint & Format:** `ruff .`, `black .`, `pnpm lint`

Check `htmlcov/index.html` for coverage metrics (goal ≥85%).

---

## 7. Continuous Integration

GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push/PR:
1. Linting: Black & Ruff & Prettier
2. Backend tests + coverage
3. Frontend lint & build

---

## 8. Future Roadmap & Enterprise Migration

This section outlines how the Claims-AI POC can evolve into a robust, enterprise-grade solution on Azure, AWS, or GCP.

1. Production Infrastructure
   - Container orchestration: Kubernetes (AKS, EKS, GKE) with Helm or Terraform.
   - Secrets & configuration management: Azure Key Vault, AWS Secrets Manager, GCP Secret Manager.
   - Observability: Prometheus/Grafana on K8s or cloud-native (Azure Monitor, CloudWatch, Cloud Logging).
   - CI/CD pipelines: GitHub Actions integrated with Azure DevOps Pipelines, AWS CodePipeline/CodeBuild, or Google Cloud Build & Cloud Deploy.

2. Data Storage & Vector Search
   - RDBMS: Azure Database for PostgreSQL, Amazon RDS (PostgreSQL), Google Cloud SQL.
   - Object storage: Azure Blob Storage, Amazon S3, Google Cloud Storage for documents & audio.
   - Vector database: ChromaDB ➔ Azure Cognitive Search vector store, Amazon OpenSearch Serverless (with vector plugin), or Vertex AI Matching Engine.

3. Large Language Models & Embeddings
   - Local Phi-4 via LM Studio ➔ Managed LLMs: Azure OpenAI (GPT-4), AWS Bedrock (Claude, Titan), GCP Vertex AI (Gemini).
   - Embeddings: Replace LM Studio embeddings with cloud APIs or self-hosted embeddings service (e.g., Azure OpenAI embeddings, Amazon SageMaker, Vertex AI Embeddings API).

4. Text-to-Speech
   - Coqui TTS container ➔ Azure Speech Service, Amazon Polly, or Google Cloud Text-to-Speech.
   - High-throughput streaming via serverless or auto-scaled microservices.

5. API Gateway & Security
   - FastAPI behind API gateway: Azure API Management, Amazon API Gateway + Cognito authorizers, GCP API Gateway + IAM.
   - Authentication & authorization: OAuth2/OIDC via Azure AD, AWS Cognito, Google Identity Platform.
   - Network security: VNet/VPC, private endpoints, firewall rules.

6. Scalability & Resilience
   - Horizontal autoscaling: Kubernetes HPA, AWS Fargate/EKS, GCP Cloud Run.
   - Batch ingestion: Serverless functions (Azure Functions, AWS Lambda, Cloud Functions) for OCR & embedding pipelines.
   - Asynchronous processing: Message queues (Azure Service Bus, Amazon SQS, Pub/Sub) and worker pools.
   - Disaster recovery & multi-region failover.

7. Monitoring, Logging, & Compliance
   - Centralized logging: ELK stack or cloud logging services.
   - Metrics & alerting: Prometheus, CloudWatch Alarms, Azure Alerts.
   - Audit trails & data governance: GDPR/CCPA compliance, role-based access.

8. Advanced Enhancements
   - Model lifecycle management: Automated retraining, A/B testing, drift detection.
   - Explainability & fairness: Integrate interpretability frameworks (SHAP, LIME).
   - Reporting & analytics dashboard: Business intelligence with Power BI, QuickSight, or Looker.
   - Plugin architecture: Custom connectors for additional data sources (e.g., Salesforce, SharePoint).

By mapping each POC component to managed cloud services, Claims-AI can transition from a local prototype into a scalable, secure, and compliant enterprise application.

---

For deeper background and intermediate steps, see [project.md](project.md), [tasks.md](tasks.md), and `explanations.txt` for per-phase narratives. 