# Makefile for Claims-AI MVP

.PHONY: help install setup run-docker run-dev-backend run-dev-frontend stop clean check-services load-demo embed-precedents test-backend test-frontend test-e2e lint format arch-diagram eval docs demo-readme model-switch

# Default target: Show help
help:
	@echo "Available commands:"
	@echo "  install         - Install backend and frontend dependencies"
	@echo "  setup           - Full setup: Install dependencies and setup pre-commit hooks"
	@echo "  run-docker      - Start all services using Docker Compose (Recommended)"
	@echo "  run-dev-backend - Start backend in local dev mode (Uvicorn, requires Docker services)"
	@echo "  run-dev-frontend- Start frontend in local dev mode (Vite)"
	@echo "  stop            - Stop all Docker Compose services"
	@echo "  clean           - Stop services and remove Docker volumes/networks (Use with caution!)"
	@echo "  check-services  - Run health checks for all services"
	@echo "  load-demo       - Copy demo files into data/raw/demo/"
	@echo "  process-demo    - Run OCR extraction and embedding for demo data (requires Docker services running)"
	@echo "  embed-precedents- Run script to embed precedent data (requires Docker services running)"
	@echo "  test-backend    - Run backend unit and integration tests with coverage"
	@echo "  test-frontend   - Run frontend unit tests (Vitest)"
	@echo "  test-e2e        - Run end-to-end tests (Playwright)"
	@echo "  lint            - Run backend (Ruff) and frontend linters"
	@echo "  format          - Run backend (Black, Ruff fix) and frontend formatters"
	@echo "  arch-diagram    - Generate architecture diagram SVG from Markdown source"
	@echo "  eval            - Run evaluation script"
	@echo "  docs            - Generate project documentation (e.g., Sphinx, MkDocs) - Placeholder"
	@echo "  demo-readme     - Generate the how-it-works.md demo documentation"
	@echo "  model-switch    - Switch LLM provider (e.g., make model-switch llm=ollama/mistral or make model-switch llm=gemini)"

# Variables
PYTHON = .venv/bin/python
PIP = .venv/bin/pip
PNPM = pnpm
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.dev.yml
BACKEND_DIR = backend
FRONTEND_DIR = frontend
CHECK_SCRIPT = ./scripts/check_services.sh
DEMO_SCRIPT = ./scripts/load_demo_data.sh
EXTRACT_SCRIPT = ./scripts/extract_text.py
EMBED_SCRIPT = ./scripts/chunk_embed.py
PRECEDENT_SCRIPT = ./scripts/embed_precedents.py
VENV_EXISTS = $(wildcard .venv)

# Check if venv exists
check-venv:
ifndef VENV_EXISTS
	@echo "Python virtual environment (.venv) not found. Please run 'make setup' first."
	@exit 1
endif

# Installation
install: install-backend install-frontend

install-backend:
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

install-frontend:
	cd $(FRONTEND_DIR) && $(PNPM) install

# Setup
setup:
	@echo "Setting up Python virtual environment..."
	python3 -m venv .venv
	@echo "Activating virtual environment and installing backend dependencies..."
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && $(PNPM) install
	@echo "Installing pre-commit hooks..."
	$(PYTHON) -m pre_commit install
	@echo "Setup complete. Activate venv with 'source .venv/bin/activate'"

# Running Services
run-docker:
	@echo "Starting all services via Docker Compose..."
	$(DOCKER_COMPOSE) up --build -d
	@echo "Waiting a few seconds for services to initialize..."
	@sleep 5
	@$(CHECK_SCRIPT) || echo "Some services might still be starting. Run 'make check-services' again shortly."

run-dev-backend: check-venv
	@echo "Starting backend in local dev mode (Uvicorn)..."
	@echo "Ensure dependent Docker services (Postgres, Minio, ChromaDB, TTS) are running!"
	@echo "Hint: Use 'docker-compose up -d postgres minio chromadb tts' (adjust 'tts' if needed)"
	@echo "Ensure .env POSTGRES_HOST, MINIO_URL, CHROMA_HOST, COQUI_TTS_URL point to 'localhost' or correct host ports."
	$(PYTHON) $(BACKEND_DIR)/main.py --reload --host 0.0.0.0 --port $${BACKEND_PORT:-8000}

run-dev-frontend:
	@echo "Starting frontend in local dev mode (Vite)..."
	cd $(FRONTEND_DIR) && $(PNPM) dev

stop:
	@echo "Stopping Docker Compose services..."
	$(DOCKER_COMPOSE) down --remove-orphans
	-@$(DOCKER_COMPOSE_DEV) down --remove-orphans 2>/dev/null || true # Attempt to stop dev services if they exist

clean: stop
	@echo "Removing Docker volumes and networks (WARNING: Data will be lost!)..."
	$(DOCKER_COMPOSE) down --volumes --remove-orphans
	-@$(DOCKER_COMPOSE_DEV) down --volumes --remove-orphans 2>/dev/null || true

# Health Checks
check-services:
	@echo "Running service health checks..."
	@$(CHECK_SCRIPT)

# Data Processing
load-demo:
	@echo "Loading demo documents..."
	@$(DEMO_SCRIPT)

process-demo:
	@echo "Running OCR extraction for demo data..."
	@docker-compose exec backend python /app/./scripts/extract_text.py --src /app/data/raw/demo --out /app/data/processed_text
	@echo "Running chunking and embedding for demo data..."
	@docker-compose exec backend python /app/./scripts/chunk_embed.py --in /app/data/processed_text

embed-precedents:
	@echo "Embedding precedents from data/precedents/precedents.csv..."
	@docker-compose exec backend python /app/./scripts/embed_precedents.py

# Testing
test-backend: check-venv
	@echo "Running backend tests with coverage..."
	$(PYTHON) -m pytest --cov=$(BACKEND_DIR) --cov-report=html tests/backend/
	@echo "Coverage report generated in htmlcov/index.html"

test-frontend:
	@echo "Running frontend tests..."
	cd $(FRONTEND_DIR) && $(PNPM) test

test-e2e:
	@echo "Running end-to-end tests (Playwright)..."
	@echo "Ensure the application stack (frontend + backend + services) is running."
	cd $(FRONTEND_DIR) && npx playwright test

# Linting and Formatting
lint: lint-backend lint-frontend

lint-backend: check-venv
	@echo "Running backend linters (Ruff)..."
	$(PYTHON) -m ruff check .

lint-frontend:
	@echo "Running frontend linters..."
	cd $(FRONTEND_DIR) && $(PNPM) lint

format: format-backend format-frontend

format-backend: check-venv
	@echo "Running backend formatters (Black, Ruff fix)..."
	$(PYTHON) -m black .
	$(PYTHON) -m ruff check . --fix

format-frontend:
	@echo "Running frontend formatters (Prettier)..."
	cd $(FRONTEND_DIR) && $(PNPM) format

# New specific targets for the agentic demo task list
ruff: check-venv
	@echo "Running Ruff linter and fixer..."
	$(PYTHON) -m ruff check . --fix

black: check-venv
	@echo "Running Black formatter..."
	$(PYTHON) -m black .

pytest: check-venv
	@echo "Running backend Pytests..."
	$(PYTHON) -m pytest tests/backend/

# Composite target for convenience if needed, though the task asks for individual targets
lint-format-test-backend: ruff black pytest
	@echo "Backend linting, formatting, and testing complete."

# Documentation
arch-diagram:
	@echo "Generating architecture diagram..."
	mkdir -p docs
	npx -y @mermaid-js/mermaid-cli@latest -i docs/architecture.md -o docs/architecture.svg -b transparent
	@echo "SVG diagram generated at docs/architecture.svg"

# Evaluation
eval:
	@echo "Running evaluation script..."
	PYTHONPATH=. python scripts/run_evaluation.py --f1-threshold 0.85

# You might need to adjust python to python3 or ensure correct PYTHONPATH
# if the script has trouble importing backend modules.
# Example for PYTHONPATH if run_evaluation.py needs to import from parent 'backend' directory:
# eval-with-pythonpath:
# 	@echo "Running evaluation script with PYTHONPATH adjustment..."
# 	PYTHONPATH=. python scripts/run_evaluation.py --f1-threshold 0.85 

# Documentation
docs: ## Generate project documentation (e.g., Sphinx, MkDocs) - Placeholder
	@echo "Generating project documentation... (Placeholder)"

.PHONY: demo-readme
demo-readme: ## Generate the how-it-works.md demo documentation
	@echo "Generating how-it-works.md from template..."
	python scripts/generate_how_it_works_doc.py
	@echo "how-it-works.md has been regenerated."

# Deployment - Placeholder
# .PHONY: deploy
# deploy: ## Deploy application to a specified environment (e.g., staging, production)
# 	@echo "Deploying application... (Placeholder)"

# Model Switching - Placeholder for now
.PHONY: model-switch
model-switch: ## Switch LLM provider (e.g., make model-switch llm=ollama/mistral or make model-switch llm=gemini)
	@echo "Switching LLM to $(llm)..."
	@if [ "$(llm)" = "ollama/mistral" ]; then \
		python scripts/configure_env.py --provider ollama --model mistral; \
		echo "Switched to Ollama/Mistral. Please ensure Ollama server is running."; \
	elif [ "$(llm)" = "gemini" ]; then \
		python scripts/configure_env.py --provider gemini --model gemini-2.5-flash-preview-04-17; \
		echo "Switched to Gemini. Ensure GEMINI_API_KEY is set in .env and valid, and model is gemini-2.5-flash-preview-04-17."; \
	elif [ "$(llm)" = "gemini-2.5-flash-preview-04-17" ]; then \
		python scripts/configure_env.py --provider gemini --model gemini-2.5-flash-preview-04-17; \
		echo "Switched to Gemini model gemini-2.5-flash-preview-04-17. Ensure GEMINI_API_KEY is set."; \
	else \
		echo "Unsupported LLM provider/model: $(llm). Supported: ollama/mistral, gemini, gemini-2.5-flash-preview-04-17"; \
		exit 1; \
	fi
	@echo "Running smoke tests for new LLM configuration... (Placeholder)"
	# Add smoke test commands here, e.g.:
	# curl -X POST -H "Content-Type: application/json" -d '{"input": {"text_content_override": "This is a test."}}' http://localhost:8000/langserve/summarise/invoke || echo "Smoke test failed!"
	@echo "LLM switch and smoke test placeholder complete for $(llm)."

# Miscellaneous
.PHONY: clean
clean: ## Remove temporary files (e.g., __pycache__, .pytest_cache, .coverage, build artifacts)
# ... existing code ... 