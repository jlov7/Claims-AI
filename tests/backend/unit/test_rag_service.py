import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_openai import ChatOpenAI  # Added for spec
from backend.services.rag_service import RAGService
from backend.core.config import Settings


# Minimal settings for testing
@pytest.fixture
def mock_settings():
    return Settings(
        PHI4_API_BASE="http://localhost:1234/v1",
        PHI4_MODEL_NAME="test-phi4",
        LLM_TEMPERATURE=0.1,
        EMBEDDING_MODEL_NAME="test-embedding",
        CHROMA_HOST="localhost",
        CHROMA_PORT=8008,
        CHROMA_USER="test",
        CHROMA_PASSWORD="test",
        CHROMA_COLLECTION_NAME="test_collection",
        RAG_NUM_SOURCES=1,
        CONFIDENCE_THRESHOLD_SELF_HEAL=3,
        SELF_HEAL_MAX_ATTEMPTS=1,
        # Add other required fields with dummy values if Settings validation requires them
        MINIO_URL="test",
        MINIO_ACCESS_KEY="test",
        MINIO_SECRET_KEY="test",
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="test",
        POSTGRES_DB="test",
        POSTGRES_HOST="test",
        POSTGRES_PORT=5432,
        DATABASE_URL="postgresql://test:test@test:5432/test",
    )


@pytest.fixture
@patch("chromadb.HttpClient")
def rag_service_instance(
    MockChromaClient, mock_settings, mocker
):  # mocker is injected by pytest-mock
    # 1. Mock ChromaDB client and collection (as before)
    mock_chroma_instance = MockChromaClient.return_value
    mock_chroma_instance.heartbeat = MagicMock()
    mock_collection = MagicMock()
    mock_collection.name = mock_settings.CHROMA_COLLECTION_NAME
    mock_collection.query = MagicMock(
        return_value={
            "documents": [["Test document content from ChromaDB"]],
            "metadatas": [
                [
                    {
                        "document_id": "chroma_doc1",
                        "chunk_id": "c1",
                        "filename": "chroma_file.txt",
                    }
                ]
            ],
            "distances": [[0.1]],
        }
    )
    mock_chroma_instance.get_or_create_collection = MagicMock(
        return_value=mock_collection
    )

    # 2. Prepare the mock for the ChatOpenAI instance and its ainvoke method
    mock_llm_ainvoke_method = AsyncMock()
    # This mock_chat_openai_llm_instance is what RAGService's self.llm_client will become.
    mock_chat_openai_llm_instance = MagicMock(spec=ChatOpenAI)
    mock_chat_openai_llm_instance.ainvoke = mock_llm_ainvoke_method

    # 3. Patch the ChatOpenAI class *where it's imported by rag_service.py*.
    # When RAGService calls ChatOpenAI(...), it will get mock_chat_openai_llm_instance.
    mocker.patch(
        "backend.services.rag_service.ChatOpenAI",
        return_value=mock_chat_openai_llm_instance,
    )

    # 4. Instantiate RAGService. It will now use the mocked ChatOpenAI.
    RAGService._instance = None  # Reset singleton for test isolation
    service = RAGService(settings_instance=mock_settings)
    service.collection = mock_collection  # Assign mocked Chroma collection

    return service


@pytest.mark.asyncio
async def test_query_rag_high_initial_confidence(rag_service_instance: RAGService):
    """Test RAG query processing when initial confidence is high."""
    service = rag_service_instance  # Fixture is now synchronous
    user_query = "What is claims processing?"
    initial_answer = "Claims processing is the series of steps taken to manage a claim."
    high_confidence_score_str = "4"  # LLM returns string

    # Configure the side_effect on the already mocked ainvoke method
    service.llm_client.ainvoke.side_effect = [initial_answer, high_confidence_score_str]

    # Expect 4 return values now
    answer, sources, confidence, self_heal_attempts = await service.query_rag(
        user_query
    )

    assert answer == initial_answer
    assert confidence == 4
    assert len(sources) == 1
    assert sources[0].chunk_content == "Test document content from ChromaDB"
    assert service.llm_client.ainvoke.call_count == 2

    # Verify the prompts
    args_call1, kwargs_call1 = service.llm_client.ainvoke.call_args_list[0]
    prompt_call1_args = args_call1[0]  # The prompt is a ChatPromptValue
    assert (
        "Context:" in prompt_call1_args.messages[1].content
    )  # Check user message content
    assert (
        user_query in prompt_call1_args.messages[1].content
    )  # Check user message content

    args_call2, kwargs_call2 = service.llm_client.ainvoke.call_args_list[1]
    prompt_call2_args = args_call2[0]  # The prompt is a ChatPromptValue
    # Check system message and user message for confidence prompt content
    assert (
        "rate your confidence" in prompt_call2_args.messages[0].content
    )  # System message
    assert (
        "Confidence Score (1-5):" in prompt_call2_args.messages[1].content
    )  # User message
    # Verify that the original inputs were part of the rendered user message for confidence scoring
    assert user_query in prompt_call2_args.messages[1].content
    assert initial_answer in prompt_call2_args.messages[1].content


@pytest.mark.asyncio
async def test_query_rag_low_confidence_successful_heal(
    rag_service_instance: RAGService,
):
    """Test RAG query processing with low initial confidence and successful self-healing."""
    service = rag_service_instance
    user_query = "Explain the nuances of subrogation in insurance claims."
    initial_answer = "Subrogation is when one party takes over another's rights."
    low_confidence_score_str = "2"
    revised_answer = "Subrogation in insurance allows an insurer, after paying a loss, to pursue recovery from a third party who was responsible for that loss. It prevents the insured from recovering twice and holds the at-fault party accountable."
    healed_confidence_score_str = "5"

    service.llm_client.ainvoke.side_effect = [
        initial_answer,
        low_confidence_score_str,
        revised_answer,
        healed_confidence_score_str,
    ]

    # Expect 4 return values now
    answer, sources, confidence, self_heal_attempts = await service.query_rag(
        user_query
    )

    assert answer == revised_answer
    assert confidence == 5
    assert len(sources) == 1
    assert service.llm_client.ainvoke.call_count == 4

    # Verify prompts (self-heal call is the 3rd call to ainvoke)
    args_call3, _ = service.llm_client.ainvoke.call_args_list[2]
    prompt_call3_args = args_call3[0]  # ChatPromptValue
    assert (
        "Previous Low-Confidence Answer:" in prompt_call3_args.messages[1].content
    )  # Check user message content
    # Verify that the previous answer was part of the rendered user message for self-healing
    assert initial_answer in prompt_call3_args.messages[1].content


@pytest.mark.asyncio
async def test_query_rag_low_confidence_heal_still_low(
    rag_service_instance: RAGService,
):
    """Test RAG query processing with low initial confidence, and self-healing still results in low confidence."""
    service = rag_service_instance
    user_query = "What about quantum insurance protocols?"
    initial_answer = "It's... complicated."
    low_confidence_score_str_1 = "1"
    revised_answer = (
        "Quantum insurance protocols are highly theoretical and not yet implemented."
    )
    low_confidence_score_str_2 = "2"  # Still below threshold

    service.llm_client.ainvoke.side_effect = [
        initial_answer,
        low_confidence_score_str_1,
        revised_answer,
        low_confidence_score_str_2,
    ]

    # Expect 4 return values now
    answer, sources, confidence, self_heal_attempts = await service.query_rag(
        user_query
    )

    assert answer == revised_answer
    assert confidence == 2
    assert service.llm_client.ainvoke.call_count == 4


@pytest.mark.asyncio
async def test_query_rag_empty_query_direct_return(rag_service_instance: RAGService):
    """Test that an empty query is handled directly by query_rag and does not call LLM."""
    service = rag_service_instance
    user_query = ""

    # service.llm_client.ainvoke is already an AsyncMock from the fixture.
    # We just need to check it wasn't called.

    # Expect 4 return values now
    answer, sources, confidence, self_heal_attempts = await service.query_rag(
        user_query
    )

    assert answer == "Please provide a query."
    assert sources == []
    assert confidence == 3  # Default for empty query
    service.llm_client.ainvoke.assert_not_called()
