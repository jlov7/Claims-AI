# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="/opt/poetry/bin:$PATH"

# Install poetry
RUN apt-get update && apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    apt-get remove -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Install project dependencies using Poetry
# --no-root: Do not install the project itself as a package, only its dependencies.
# This is useful for applications where the project is run from source directly.
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the entire backend directory which includes the reserve_predictor service
# This makes the backend.services.reserve_predictor.app.main path work for uvicorn
COPY ./backend /app/backend

# Copy the sample_data directory which is expected to contain the model
# The model_loader.py looks for sample_data/catboost_model.pkl relative to CWD or a specific path
# By setting WORKDIR to /app and copying sample_data here, this path should resolve if CWD is /app
COPY ./sample_data /app/sample_data

# Expose the port the app runs on
# This should match the port in the CMD instruction and docker-compose.yml
EXPOSE 8001

# Define the command to run the application
# The app is located at backend.services.reserve_predictor.app.main
# We run uvicorn from the /app directory (WORKDIR)
CMD ["uvicorn", "backend.services.reserve_predictor.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Healthcheck (optional, but good practice)
# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
#   CMD curl -f http://localhost:8001/health || exit 1
# Note: curl might not be available in python:3.11-slim. 
# If HEALTHCHECK is desired, curl would need to be installed or a Python script used for the health check.
# For now, keeping it commented out for simplicity as curl is not installed by default. 