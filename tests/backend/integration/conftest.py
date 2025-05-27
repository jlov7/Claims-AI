import pytest
from httpx import AsyncClient
import sys
import os
from pathlib import Path
from fastapi import FastAPI
from typing import AsyncGenerator
import asyncio
from fastapi.testclient import TestClient
import pytest_asyncio
from httpx import ASGITransport

# Add project root to sys.path to allow for `from backend.main import app`
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the module itself, not just the app, to allow modification of module-level 'settings'
import backend.main
from backend.core.config import get_settings  # For typing and direct calls
from backend.services.drafting_service import (
    DraftingService,
)


@pytest.fixture(scope="session")
def event_loop():
    # This fixture is already provided by pytest_asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def test_app() -> FastAPI:
    get_settings.cache_clear()
    # Update the settings object within the already imported backend.main module
    backend.main.settings = get_settings()
    return backend.main.app  # Return the app from the (now updated) main module


@pytest_asyncio.fixture(scope="module")
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    # get_settings.cache_clear() # Redundant, test_app fixture handles this
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture(scope="module")  # Add new synchronous client fixture
def sync_client(test_app: FastAPI) -> TestClient:
    with TestClient(app=test_app, base_url="http://testserver") as tc:
        return (
            tc  # Note: TestClient is a context manager but typically returned directly
        )


@pytest.fixture(scope="function")  # Use function scope for tmp_path
def temp_drafting_service(tmp_path: Path) -> DraftingService:
    """Provides a DraftingService instance that writes to a temporary directory."""
    svc_settings = get_settings()
    service = DraftingService(settings_param=svc_settings)
    service.output_dir = tmp_path
    return service
