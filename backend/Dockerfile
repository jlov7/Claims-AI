# Use an official Python runtime as a parent image
FROM python:3.11

# Install Tesseract and its development libraries first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr libtesseract-dev \
    build-essential libyaml-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# The context in docker-compose is ./backend, so this path is relative to that.
COPY ./requirements.txt /app/requirements.txt

# Update pip and install requirements
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code (everything in the build context, which is ./backend)
# into the container at /app/backend
COPY . /app/backend

# Expose port 8000 to the outside world
EXPOSE 8000

# Command to run the application using Uvicorn
# This will look for an 'app' instance in 'main.py' inside the 'backend' directory (which is now /app/backend/main.py)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 