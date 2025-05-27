import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
)

from fastapi.testclient import TestClient
import backend.main as main_module

client = TestClient(main_module.app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data and "Welcome to Claims-AI API" in data["message"]


def test_health_check_success():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "Ok"


def test_health_check_failure(monkeypatch):
    # Simulate missing settings causing failure
    monkeypatch.setattr(main_module, "settings", None)
    response = client.get("/health")
    assert response.status_code == 503
