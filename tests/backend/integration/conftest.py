import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sys
import os
from pathlib import Path

# Add project root to sys.path to allow for `from backend.main import app`
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.main import app  # Import your FastAPI application
from backend.core.config import get_settings
from backend.services.drafting_service import (
    DraftingService,
)  # , get_drafting_service # get_drafting_service is not needed here
from backend.services.document_loader import DocumentLoaderService  # Import new service


@pytest_asyncio.fixture(scope="function")
async def client():
    # Ensure services (like LMStudio, ChromaDB) are running before tests
    # For true integration tests, this might involve setup/teardown logic
    # or ensuring the docker-compose environment is up.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture(scope="function")  # Use function scope for tmp_path
def temp_drafting_service(tmp_path: Path) -> DraftingService:
    """Provides a DraftingService instance that writes to a temporary directory."""
    settings = get_settings()  # Get current settings
    doc_loader = DocumentLoaderService(
        settings=settings
    )  # Create an instance of DocumentLoaderService
    # Override output directory for this service instance
    service = DraftingService(
        settings_instance=settings,
        doc_loader_service=doc_loader,
        output_dir=str(tmp_path),
    )
    return service
