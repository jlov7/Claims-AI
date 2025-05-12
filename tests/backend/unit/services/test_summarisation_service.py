import pytest
import json
from fastapi import HTTPException
from backend.services.summarisation_service import (
    SummarisationService,
    get_summarisation_service,
)
from backend.core.config import Settings
import builtins


class FakeChain:
    def __or__(self, other):
        return self

    def invoke(self, args):
        if args.get("text_to_summarise") == "error":
            raise Exception("LLM error")
        return "SUMMARY"


class FakePrompt:
    @staticmethod
    def from_template(template):
        return FakeChain()


@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    import backend.services.summarisation_service as ss

    monkeypatch.setattr(ss, "ChatPromptTemplate", FakePrompt)
    monkeypatch.setattr(ss, "StrOutputParser", lambda: None)


@pytest.fixture
def settings():
    return Settings()


def test_get_summarisation_service_singleton(settings):
    # Factory now takes no parameters
    s1 = get_summarisation_service()
    s2 = get_summarisation_service()
    assert s1 is s2


def test_get_content_from_id_invalid_format(settings):
    svc = SummarisationService(settings)
    with pytest.raises(HTTPException) as excinfo:
        svc._get_content_from_id("bad/id")
    assert excinfo.value.status_code == 400


def test_get_content_from_id_not_found(settings, tmp_path, monkeypatch):
    svc = SummarisationService(settings)

    # Redirect open to the tmp_path file; this file does not exist, triggering FileNotFoundError
    def fake_open(path, mode="r", encoding=None):
        return builtins.open(str(tmp_path / "doc.json"), mode, encoding=encoding)

    monkeypatch.setattr(
        "backend.services.summarisation_service.open", fake_open, raising=False
    )
    with pytest.raises(HTTPException) as excinfo:
        svc._get_content_from_id("doc.json")
    assert excinfo.value.status_code == 404


def test_get_content_from_id_invalid_json(settings, tmp_path, monkeypatch):
    path = tmp_path / "doc.json"
    path.write_text("notjson")
    svc = SummarisationService(settings)

    def fake_open(path_arg, mode="r", encoding=None):
        return builtins.open(str(path), mode, encoding=encoding)

    monkeypatch.setattr(
        "backend.services.summarisation_service.open", fake_open, raising=False
    )
    with pytest.raises(HTTPException) as excinfo:
        svc._get_content_from_id("doc.json")
    assert excinfo.value.status_code == 500


def test_get_content_from_id_missing_text_key(settings, tmp_path, monkeypatch):
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({}))
    svc = SummarisationService(settings)

    def fake_open_missing(path_arg, mode="r", encoding=None):
        return builtins.open(str(path), mode, encoding=encoding)

    monkeypatch.setattr(
        "backend.services.summarisation_service.open", fake_open_missing, raising=False
    )
    with pytest.raises(HTTPException) as excinfo:
        svc._get_content_from_id("doc.json")
    assert excinfo.value.status_code == 500


def test_get_content_from_id_success(settings, tmp_path, monkeypatch):
    path = tmp_path / "doc.json"
    path.write_text(json.dumps({"text": "hello"}))
    svc = SummarisationService(settings)

    def fake_open_success(path_arg, mode="r", encoding=None):
        return builtins.open(str(path), mode, encoding=encoding)

    monkeypatch.setattr(
        "backend.services.summarisation_service.open", fake_open_success, raising=False
    )
    content = svc._get_content_from_id("doc.json")
    assert content == "hello"


def test_summarise_text_empty(settings):
    svc = SummarisationService(settings)
    msg = svc.summarise_text("   ", "docid")
    assert "empty" in msg


def test_summarise_text_success(settings):
    svc = SummarisationService(settings)
    result = svc.summarise_text("text", None)
    assert result == "SUMMARY"


def test_summarise_text_error(settings):
    svc = SummarisationService(settings)
    with pytest.raises(HTTPException) as excinfo:
        svc.summarise_text("error", "docid")
    assert excinfo.value.status_code == 500
