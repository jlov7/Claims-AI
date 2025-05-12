import pytest
from langchain_core.documents import Document
from backend.services.document_loader import DocumentLoaderService


class FakeLoader:
    def __init__(self, file_path, encoding=None):
        pass

    def load(self):
        return [Document(page_content="dummy", metadata={})]


class FakeSplitter:
    def split_documents(self, docs):
        return docs


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = DocumentLoaderService(settings=None)
    svc.processed_docs_path = tmp_path
    monkeypatch.setattr(svc, "_get_loader", lambda file_path: FakeLoader(file_path))
    monkeypatch.setattr(svc, "text_splitter", FakeSplitter())
    return svc


def test_invalid_id_none(service):
    assert service.load_document_by_id(None) is None


def test_invalid_id_with_slash(service):
    assert service.load_document_by_id("bad/name.txt") is None
    assert service.load_document_by_id("..\\etc\\passwd") is None


def test_nonexistent_file(service):
    assert service.load_document_by_id("noexist.txt") is None


def test_successful_load_and_split(service):
    file_path = service.processed_docs_path / "test.txt"
    file_path.write_text("hello")
    docs = service.load_document_by_id("test.txt")
    assert docs is not None
    assert len(docs) == 1
    assert docs[0].page_content == "dummy"
    assert docs[0].metadata.get("source_filename") == "test.txt"


def test_load_document_content_by_id(service):
    file_path = service.processed_docs_path / "content.txt"
    file_path.write_text("world")
    content = service.load_document_content_by_id("content.txt")
    assert isinstance(content, str)
    assert "dummy" in content
