import pytest
from backend.services.precedent_service import PrecedentService
from backend.core.config import Settings
from backend.models import PrecedentResultItem


class DummyClient:
    def heartbeat(self):
        pass

    def get_collection(self, name, embedding_function):
        return self

    def query(self, query_embeddings, n_results, include):
        return {
            "ids": [["id1"]],
            "metadatas": [
                [{"claim_id": "id1", "keywords": "kw", "outcome": "outcome"}]
            ],
            "documents": [["doc_summary"]],
            "distances": [[0.123]],
        }


class DummyEF:
    # def __call__(self, data):
    #     return [0.5]
    def embed_query(self, text: str) -> list[float]:
        """Simulates embedding a single query string."""
        # Return a fixed-size dummy embedding
        # The actual size depends on the model, e.g., nomic-embed-text is 768
        return [0.1] * 768  # Return a list of 768 floats

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Simulates embedding a list of documents."""
        return [[0.2] * 768 for _ in texts]  # Return a list of embeddings


@pytest.fixture
def service(monkeypatch):
    settings = Settings()
    svc = PrecedentService(settings)
    svc.chroma_client = DummyClient()
    svc.embedding_function = DummyEF()
    return svc


def test_singleton():
    s1 = PrecedentService(Settings())
    s2 = PrecedentService(Settings())
    assert s1 is s2


def test_find_precedents_success(service):
    results = service.find_precedents("summary", 1)
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert isinstance(item, PrecedentResultItem)
    assert item.claim_id == "id1"
    assert item.summary == "doc_summary"
    assert item.keywords == "kw"
    assert item.outcome == "outcome"
    assert item.distance == 0.123


def test_find_precedents_without_client_or_ef(service):
    svc = service
    svc.chroma_client = None
    svc.embedding_function = None
    assert svc.find_precedents("summary", 5) == []


def test_get_precedents_collection_fallback(monkeypatch, service):
    class FaultyClient:
        def get_collection(self, name, embedding_function):
            raise Exception("fail")

        def get_or_create_collection(self, name, embedding_function):
            return "collection"

    svc = service
    svc.chroma_client = FaultyClient()
    svc.embedding_function = DummyEF()
    col = svc._get_precedents_collection()
    assert col == "collection"
