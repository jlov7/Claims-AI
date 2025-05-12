import pytest
from pydantic import ValidationError
from backend.services.drafting_service import DraftingService
from backend.models import QAPair, DraftStrategyNoteRequest
from backend.core.config import Settings


class FakeLoader:
    def load_document_content_by_id(self, document_id):
        return "content" if document_id == "exists" else None


class FakePromptChain:
    def __or__(self, other):
        return self

    def invoke(self, args):
        return "DRAFT"


class FakePrompt:
    @staticmethod
    def from_template(template):
        return FakePromptChain()


@pytest.fixture
def service(tmp_path, monkeypatch):
    settings = Settings()
    doc_loader = FakeLoader()
    svc = DraftingService(
        settings_instance=settings, doc_loader_service=doc_loader, output_dir=tmp_path
    )
    return svc


def test_get_content_from_doc_id_success(service):
    assert service._get_content_from_doc_id("exists") == "content"


def test_get_content_from_doc_id_not_found(service):
    assert service._get_content_from_doc_id("nope") is None


def test__build_llm_context_raises_when_no_context():
    with pytest.raises(ValidationError):
        DraftStrategyNoteRequest()


def test__build_llm_context_with_claim_summary(service):
    req = DraftStrategyNoteRequest(claimSummary="Summary")
    context = service._build_llm_context(req)
    assert "Claim Summary" in context


def test__build_llm_context_with_all(service):
    qa = [QAPair(question="Q1", answer="A1")]
    req = DraftStrategyNoteRequest(
        documentIds=["exists"], qaHistory=qa, additionalCriteria="Crit"
    )
    context = service._build_llm_context(req)
    assert "Content from Document ID" in context
    assert "Relevant Q&A History" in context
    assert "Additional Instructions/Criteria" in context


def test_generate_strategy_note_text_success(monkeypatch, service):
    monkeypatch.setattr(
        "backend.services.drafting_service.ChatPromptTemplate", FakePrompt
    )
    monkeypatch.setattr(
        "backend.services.drafting_service.StrOutputParser", lambda: None
    )
    result = service.generate_strategy_note_text("ctx")
    assert result == "DRAFT"


def test_generate_strategy_note_text_error(monkeypatch, service):
    class ErrorChain(FakePromptChain):
        def invoke(self, args):
            raise Exception("fail")

    class ErrorPrompt:
        @staticmethod
        def from_template(template):
            return ErrorChain()

    monkeypatch.setattr(
        "backend.services.drafting_service.ChatPromptTemplate", ErrorPrompt
    )
    monkeypatch.setattr(
        "backend.services.drafting_service.StrOutputParser", lambda: None
    )
    with pytest.raises(Exception):
        service.generate_strategy_note_text("ctx")


def test_create_docx_from_text(tmp_path, monkeypatch, service):
    text = "Para1\n\nPara2"

    class DummyUUID:
        hex = "abcd1234"

    monkeypatch.setattr("backend.services.drafting_service.uuid", DummyUUID)
    path = service.create_docx_from_text(text=text, filename_suggestion="file.txt")
    assert path.exists()
    assert path.suffix == ".docx"
    assert path.name.startswith("file")
