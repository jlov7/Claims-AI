import pytest
import yaml
from pathlib import Path
from fastapi import HTTPException
from backend.services.redteam_service import RedTeamService
from backend.core.config import Settings
from backend.models import RedTeamPrompt


@pytest.fixture
def settings():
    return Settings()


def test_load_prompts_success(settings, tmp_path, monkeypatch):
    data = {
        "prompts": [
            {"id": "1", "category": "cat", "text": "t", "expected_behavior": "e"}
        ]
    }
    yaml_file = tmp_path / "redteam.yaml"
    yaml_file.write_text(yaml.dump(data))
    monkeypatch.setattr("backend.services.redteam_service.PROMPTS_YAML", yaml_file)
    svc = RedTeamService(settings, rag_service=None)
    prompts = svc._load_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) == 1
    assert isinstance(prompts[0], RedTeamPrompt)


def test_load_prompts_not_found(monkeypatch, settings):
    monkeypatch.setattr(
        "backend.services.redteam_service.PROMPTS_YAML", Path("nonexistent")
    )
    with pytest.raises(HTTPException):
        RedTeamService(settings, rag_service=None)._load_prompts()


@pytest.mark.asyncio
async def test_run_red_team_evaluation_success(settings):
    prompt = RedTeamPrompt(id="1", category="cat", text="t", expected_behavior="e")

    class FakeRAG:
        async def query_rag(self, query, user_id, session_id):
            return ("resp", ["src"], 0.7)

    svc = RedTeamService(settings, rag_service=FakeRAG())
    svc.prompts = [prompt]
    result = await svc.run_red_team_evaluation()
    assert result.summary_stats["prompts_run"] == 1
    assert result.summary_stats["successful_executions"] == 1
    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_run_red_team_evaluation_error(settings):
    prompt = RedTeamPrompt(id="1", category="cat", text="t", expected_behavior="e")

    class BadRAG:
        async def query_rag(self, query, user_id, session_id):
            raise Exception("fail")

    svc = RedTeamService(settings, rag_service=BadRAG())
    svc.prompts = [prompt]
    result = await svc.run_red_team_evaluation()
    assert result.summary_stats["prompts_run"] == 1
    assert result.summary_stats["failed_executions"] == 1
    assert "<system_error>" in result.results[0].response_text
