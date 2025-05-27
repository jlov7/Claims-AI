import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
)

import pytest
import sys as _sys

from backend.core.config import get_settings


def test_default_settings(monkeypatch):
    # Set env variables for PostgreSQL
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_HOST", "host")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "db")
    monkeypatch.setenv("CHROMA_PORT", "1234")
    # Simulate non-pytest run
    monkeypatch.setattr(_sys, "argv", ["uvicorn", "backend.main:app"])
    get_settings.cache_clear()  # Clear lru_cache for get_settings
    settings = get_settings()
    assert settings.POSTGRES_HOST == "host"
    assert settings.CHROMA_PORT == 1234
    # Check DATABASE_URL constructed
    assert settings.DATABASE_URL.startswith("postgresql://")


@pytest.mark.skip(reason="Pytest-specific override logic has been removed")
def test_pytest_override(monkeypatch):
    # Provide necessary env variables
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_HOST", "host")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "db")
    # Set CHROMA_PORT default
    monkeypatch.setenv("CHROMA_PORT", "9000")
    # Simulate pytest run
    monkeypatch.setattr(_sys, "argv", ["pytest"])
    settings = get_settings()
    # Overrides when pytest detected
    assert settings.CHROMA_HOST == "localhost"
    assert settings.CHROMA_PORT == 8008
    assert settings.PHI4_API_BASE == "http://localhost:1234/v1"
