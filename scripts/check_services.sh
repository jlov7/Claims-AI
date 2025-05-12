#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Print each command before executing (for debugging) - REMOVED FOR CLEANER OUTPUT

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

overall_status=0

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    overall_status=1
}

check_docker_container() {
    local container_name_to_check=$1 # Renamed to avoid conflict with service_name
    local service_display_name=$2    # Renamed for clarity
    echo "Checking Docker container: $service_display_name ($container_name_to_check)..."
    # Use grep to ensure exact match and handle potential substring issues
    if docker ps --format "{{.Names}}" | grep -q -E "^${container_name_to_check}$"; then
        # Now check if it's running (this check is redundant if using grep on ps output directly, but good for status)
        if [ "$(docker ps -q -f name=^/${container_name_to_check}$ -f status=running)" ]; then
            log_info "$service_display_name container ($container_name_to_check) is running."
        else
            log_error "$service_display_name container ($container_name_to_check) exists but is not running. Status: $(docker inspect -f '{{.State.Status}}' "$container_name_to_check")"
        fi
    else
        log_error "$service_display_name container ($container_name_to_check) does not exist."
    fi
}

check_http_endpoint() {
    local url=$1
    local service_name=$2
    local expected_status_code=${3:-200} # Default to 200 if not provided
    local curl_opts=("-s" "-o" "/dev/null" "-w" "%{http_code}" "--connect-timeout" "5") # Added connect-timeout
    local post_data=$4

    echo "Checking HTTP endpoint: $service_name ($url)..."
    
    http_status=""
    # Ensure curl doesn't fail script if endpoint is down (due to set -e)
    # Capture status and handle error explicitly
    if [ -n "$post_data" ]; then
        http_status=$(curl "${curl_opts[@]}" -X POST -H "Content-Type: application/json" -d "$post_data" "$url" || true)
    else
        http_status=$(curl "${curl_opts[@]}" "$url" || true)
    fi

    if [ "$http_status" -eq "$expected_status_code" ]; then
        log_info "$service_name endpoint ($url) is healthy (HTTP $http_status)."
    elif [ "$http_status" -eq 000 ] || [ -z "$http_status" ]; then # curl returns 000 or empty on timeout/connection error
        log_error "$service_name endpoint ($url) is not reachable (Connection refused, host down, or timeout). Curl status: $http_status"
    else
        log_error "$service_name endpoint ($url) is not healthy (HTTP $http_status). Expected $expected_status_code."
    fi
}

log_info "Starting Claims-AI services health check..."

# Determine project name from directory for Docker container names
PROJECT_NAME_RAW=$(basename "$PWD")
echo "Raw PWD basename: $PROJECT_NAME_RAW"
# For project name like "Claims-AI", docker-compose default is usually "claims-ai"
PROJECT_NAME=$(echo "$PROJECT_NAME_RAW" | tr '[:upper:]' '[:lower:]') 

if [ -z "$PROJECT_NAME" ]; then
    # This case should ideally not be hit if PWD is valid
    log_warn "Could not determine project name from PWD ('$PROJECT_NAME_RAW'). Using fixed 'claims-ai' for container names."
    PROJECT_NAME="claims-ai"
else
    log_info "Using PROJECT_NAME: $PROJECT_NAME (derived from directory name: $PROJECT_NAME_RAW)"
fi

# Check Docker Containers
# Names are <project_name>_<service_name>_1 if docker-compose.yml v1 format or project name not overridden
# Or <project_name>-<service_name>-1 if overridden with COMPOSE_PROJECT_NAME or a newer convention.
# Given the user output, it's <project_name_lowercase_with_hyphen>-<service_name>-1

# The actual container names provided by user: claims-ai-minio-1, etc.
# So, the PROJECT_NAME variable must become "claims-ai"

check_docker_container "${PROJECT_NAME}-minio-1" "Minio"
check_docker_container "${PROJECT_NAME}-chromadb-1" "ChromaDB"
check_docker_container "${PROJECT_NAME}-backend-1" "Backend"
check_docker_container "${PROJECT_NAME}-postgres-1" "PostgreSQL"

# Check Backend Service Health Endpoint
check_http_endpoint "http://localhost:8000/health" "Backend FastAPI /health"

# Check LM Studio Connection
LM_STUDIO_PAYLOAD='{"model":"phi-4-reasoning-plus","messages":[{"role":"user","content":"ping"}]}'
check_http_endpoint "http://localhost:1234/v1/chat/completions" "LM Studio Phi-4" 200 "$LM_STUDIO_PAYLOAD"

# Check PostgreSQL readiness
check_docker_container "${PROJECT_NAME}-postgres-1" "PostgreSQL Database"
check_http_endpoint "http://localhost:${POSTGRES_PORT:-5432}" "PostgreSQL readiness (host port)" "GET" 200 # This is a simplistic check, pg_isready is better done inside container or via exec

# Check Coqui TTS Service
check_docker_container "${PROJECT_NAME}-tts" "Coqui TTS Service"
check_http_endpoint "http://localhost:5002/api/languages" "Coqui TTS API" "GET" 200 # Check /api/languages as per compose healthcheck

echo "-------------------------------------"
if [ "$overall_status" -eq 0 ]; then
    log_info "All services are healthy!"
else
    log_error "One or more services are not healthy. Please check the logs above."
fi

# Turn off command printing before exit (if it was on)
# set +x
exit "$overall_status" 