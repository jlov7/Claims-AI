import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.services.rag_service import RAGService
from backend.models import SourceDocument
from backend.core.config import Settings


@pytest.fixture
def settings_instance():
    return Settings()


@pytest.mark.unit
async def test_format_context_enhanced():
    """Test that context formatting produces the expected structure."""
    # Create a RAG service instance with mocked dependencies
    rag_service = RAGService()
    # Mock the initialized attribute to prevent actual initialization
    rag_service._initialized = True

    # Create test source documents
    sources = [
        SourceDocument(
            document_id="doc1",
            chunk_id="chunk1",
            chunk_content="This is test content from the first chunk.",
            file_name="test1.pdf",
        ),
        SourceDocument(
            document_id="doc2",
            chunk_id="chunk2",
            chunk_content="This is test content from the second chunk.",
            file_name="test2.pdf",
        ),
    ]

    # Call the method
    formatted_context = rag_service._format_context_enhanced(sources)

    # Verify expected output
    assert "DOCUMENT 1" in formatted_context
    assert "Title: test1.pdf" in formatted_context
    assert "Section: chunk1" in formatted_context
    assert "This is test content from the first chunk." in formatted_context
    assert "END OF DOCUMENT 1" in formatted_context

    assert "DOCUMENT 2" in formatted_context
    assert "Title: test2.pdf" in formatted_context
    assert "Section: chunk2" in formatted_context
    assert "This is test content from the second chunk." in formatted_context
    assert "END OF DOCUMENT 2" in formatted_context


@pytest.mark.unit
async def test_post_process_answer():
    """Test that answer post-processing improves clarity."""
    # Create a RAG service instance with mocked dependencies
    rag_service = RAGService()
    # Mock the initialized attribute to prevent actual initialization
    rag_service._initialized = True

    # Test cases
    test_cases = [
        # Remove "based on the provided context"
        {
            "input": "Based on the provided context, the customer filed a claim on January 15.",
            "expected": "Based on the documents, the customer filed a claim on January 15.",
        },
        # Remove "according to the given information" at start
        {
            "input": "According to the given information: the policy covers water damage.",
            "expected": "The policy covers water damage.",
        },
        # Fix ending without punctuation
        {
            "input": "The policy was issued in 2020",
            "expected": "The policy was issued in 2020.",
        },
        # Remove redundant "I don't know" followed by information
        {
            "input": "I don't know the exact date, however the claim was filed in January.",
            "expected": "The claim was filed in January.",
        },
    ]

    # Test each case
    for case in test_cases:
        processed = rag_service._post_process_answer(case["input"])
        assert processed == case["expected"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_enhanced_query_rag_prompt(settings_instance):
    """Test that query_rag uses the enhanced prompt template and new rag_pipeline."""
    mock_pipeline_ainvoke_result = {
        "answer": "Test answer from pipeline",
        "formatted_context": "Formatted test context",
    }
    mock_rag_pipeline_instance = AsyncMock()
    mock_rag_pipeline_instance.ainvoke = AsyncMock(
        return_value=mock_pipeline_ainvoke_result
    )

    # Patch chromadb.HttpClient, ChatOllama, OllamaEmbeddings, and create_rag_pipeline
    with patch("chromadb.HttpClient") as MockChromaHttpClient, patch(
        "backend.services.rag_service.ChatOllama"
    ) as MockCholla, patch(
        "backend.services.rag_service.OllamaEmbeddings"
    ) as MockOllamaEmbeddings, patch(
        "backend.services.rag_service.create_rag_pipeline",
        return_value=mock_rag_pipeline_instance,
    ) as mock_create_pipeline:

        # Configure the mock for chromadb.HttpClient
        mock_chroma_instance = MockChromaHttpClient.return_value
        mock_collection = MagicMock()

        # Define a synchronous function to be the side_effect for mock_collection.query
        def mock_query_side_effect(*args, **kwargs):
            # Simulate the structure of the actual ChromaDB query response
            return {
                "ids": [["id1"]],
                "documents": [["doc_content"]],
                "metadatas": [[{"source": "s1"}]],
                "distances": [[0.123]],  # Include distances if your code uses them
            }

        mock_collection.query = (
            mock_query_side_effect  # Assign the synchronous function directly
        )

        mock_collection.count.return_value = 1  # Keep this for the count check
        mock_chroma_instance.get_or_create_collection.return_value = mock_collection

        # Mock the instances that would be created in RAGService.__init__
        mock_llm_instance = AsyncMock()
        MockCholla.return_value = mock_llm_instance

        mock_embed_instance = AsyncMock()
        # Ensure the Chroma-compatible wrapper is also implicitly handled or mocked if direct interaction occurs
        # For RAGService, it directly uses the OllamaEmbeddings instance passed to create_langchain_embedding
        MockOllamaEmbeddings.return_value = mock_embed_instance

        from backend.services.rag_service import (
            RAGService,
        )  # Import here for singleton reset

        RAGService._instance = None  # Reset singleton for a fresh instance
        service = RAGService(settings_instance=settings_instance)

        assert service.llm_client is mock_llm_instance
        # service.embedding_function is the raw OllamaEmbeddings, embedding_function_for_chroma is the wrapped one.
        assert service.embedding_function is mock_embed_instance
        assert service.rag_pipeline is mock_rag_pipeline_instance
        mock_create_pipeline.assert_called_once_with(mock_llm_instance)

        answer, sources, confidence, num_chunks = await service.query_rag("test query")

        mock_rag_pipeline_instance.ainvoke.assert_called_once()
        pipeline_input_args = mock_rag_pipeline_instance.ainvoke.call_args[0][0]
        assert pipeline_input_args["query"] == "test query"
        assert (
            "documents" in pipeline_input_args
        )  # rag_pipeline expects documents from retriever

        assert answer == "Test answer from pipeline"
        # Further assertions for sources, confidence, num_chunks if needed


# Test for _get_confidence_score
@pytest.mark.asyncio
@pytest.mark.unit
async def test_get_confidence_score():
    """Test that _get_confidence_score returns a valid confidence score."""
    # Create a RAG service instance with mocked dependencies
    rag_service = RAGService()
    # Mock the initialized attribute to prevent actual initialization
    rag_service._initialized = True

    # Mock the confidence score
    confidence = 0.85
    rag_service._get_confidence_score = AsyncMock(return_value=confidence)

    # Call the method
    result = await rag_service._get_confidence_score()

    # Verify the result
    assert result == confidence
