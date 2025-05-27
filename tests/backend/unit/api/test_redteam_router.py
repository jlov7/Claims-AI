import pytest
from fastapi.testclient import TestClient
import backend.api.v1.redteam_router as redteam_router
from backend.main import app
from backend.models import RedTeamRunResult, RedTeamAttempt, SourceDocument

client = TestClient(app)


class DummyRedTeamService:
    async def run_red_team_evaluation(self):
        # Return a dummy successful run result
        attempts = [
            RedTeamAttempt(
                prompt_id="p1",
                category="test",
                prompt_text="dummy prompt",
                response_text="dummy response",
                rag_sources=[SourceDocument(chunk_content="chunk content")],
                rag_confidence=4.0,
                evaluation_notes="dummy notes",
            )
        ]
        summary_stats = {"prompts_run": 1}
        return RedTeamRunResult(results=attempts, summary_stats=summary_stats)


@pytest.fixture(autouse=True)
def override_redteam_service(monkeypatch):
    # Stub out actual redteam service
    dummy = DummyRedTeamService()
    monkeypatch.setattr(redteam_router, "get_redteam_service", lambda: dummy)


def test_redteam_success():
    response = client.get("/api/v1/redteam/run")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data and isinstance(data["results"], list)
    assert data["summary_stats"]["prompts_run"] == 1


def test_redteam_error(monkeypatch):
    class ErrorService:
        async def run_red_team_evaluation(self):
            raise Exception("Service failure")

    monkeypatch.setattr(redteam_router, "get_redteam_service", lambda: ErrorService())
    response = client.get("/api/v1/redteam/run")
    assert response.status_code == 500
    detail = response.json().get("detail", "").lower()
    assert "unexpected error occurred during red team evaluation" in detail
