# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install Tesseract and its development libraries first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr libtesseract-dev \
    # build-essential and libyaml-dev were likely for something else, 
    # keeping them for now but can be reviewed later if image size is a concern.
    build-essential libyaml-dev git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Create a non-root user
RUN useradd --create-home appuser

# Create directory for generated build files and set ownership for /app and its contents
# This ensures appuser can write to /app and generated_build_files
RUN mkdir -p /app/generated_build_files && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy the rest of the application code into the container, as appuser
COPY --chown=appuser:appuser . /app

# Copy the requirements file into the container, as appuser
COPY --chown=appuser:appuser ./requirements.txt /app/requirements.txt
# COPY --chown=appuser:appuser ./requirements.minimal.txt /app/requirements.minimal.txt # Keep this commented

# Set PYTHONPATH to include the backend directory
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Install poetry (if used, but requirements.txt is primary for this stage)
# RUN pip install poetry
# RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# ---- Pip install block ----
RUN python -m pip install --upgrade pip setuptools wheel \
 && echo "Installing dependencies from /app/requirements.txt..." \
 && pip install --no-cache-dir \
      --index-url https://pypi.org/simple \
      --trusted-host pypi.org --trusted-host files.pythonhosted.org \
      -r /app/requirements.txt \
 && echo "Verifying langserve version and frontend module..." \
 && python -c "import langserve; print(f'LangServe version: {langserve.__version__}'); print(f'Has frontend: {hasattr(langserve, \"frontend\")}')"
# ---- End pip install block ----

# Copy and run the import test script
COPY --chown=appuser:appuser ./docker_import_test.py /app/docker_import_test.py
RUN python /app/docker_import_test.py

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 