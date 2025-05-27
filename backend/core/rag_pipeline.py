import logging
import re  # Import re for post_process_answer
from typing import List
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from operator import itemgetter
from typing import List, Dict, Any, Tuple

from models import SourceDocument
from langchain_core.documents import Document as LangchainDocument # Alias to avoid confusion with our SourceDocument model

# Removed: from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Enhanced RAG Prompt Template
RAG_PROMPT_TEMPLATE = """\
You are an expert AI assistant for answering questions based on provided legal and insurance documents.
Your goal is to provide accurate, concise, and helpful answers.
Use the provided context from the documents to answer the user's query.
If the information is not in the context, clearly state that. Do not make up information.

CONTEXT:
{context}

USER QUERY:
{query}

ASSISTANT ANSWER:
"""


def format_documents_for_context(sources: List[SourceDocument]) -> str:
    """
    Format context with better structure to improve LLM understanding.
    Includes section breaks, clearer source documentation, and document titles.
    (Migrated from RAGService._format_context_enhanced)
    """
    if not sources:
        return "No relevant documents found to answer your query."

    formatted_chunks = []
    for i, source in enumerate(sources):
        doc_content = source.chunk_content or "No content available for this chunk."
        # doc_id = source.document_id or "unknown_document" # Not currently used in this formatting
        chunk_id = source.chunk_id or "unknown_chunk"
        file_name = source.file_name or "unknown_file"

        formatted_chunk = (
            f"DOCUMENT {i+1}\n"
            f"Title: {file_name}\n"
            f"Section: {chunk_id}\n"
            f"Content:\n{doc_content}\n"
            f"END OF DOCUMENT {i+1}\n"
        )
        formatted_chunks.append(formatted_chunk)

    return "\n\n".join(formatted_chunks)


def post_process_llm_answer(answer: str) -> str:
    """
    Post-process the LLM-generated answer to ensure clarity and readability.
    (Migrated from RAGService._post_process_answer)
    """
    if not isinstance(answer, str):
        return ""  # Or handle non-string answers appropriately

    # Remove phrases that reduce clarity or appear uncertain when not needed
    answer = re.sub(
        r"(?i)Based on the (provided|given|available) (context|information|documents)",
        "Based on the documents",
        answer,
    )

    # Fix formatting issues
    answer = re.sub(r"\n{3,}", "\n\n", answer)  # Remove excessive newlines
    answer = answer.strip()  # Remove leading/trailing whitespace

    # Ensure the answer doesn't start with common unnecessary phrases
    answer = re.sub(
        r"(?i)^(according to the (provided|given) (context|documents|information)[:,.]\s*)",
        "",
        answer,
        flags=re.IGNORECASE,
    )
    answer = answer.strip()  # Strip again after potential removal

    # Remove redundant "I don't know" statements followed by actual information
    # This regex might be too aggressive or need refinement based on LLM behavior
    answer = re.sub(
        r"(?i)I (don'?t know|can'?t determine|am not sure).*?(however|but|nevertheless)",
        "",
        answer,
        flags=re.IGNORECASE,
    )
    answer = answer.strip()

    # Make sure the answer doesn't end abruptly if it has content
    if answer and not re.search(
        r'([.!?"]$|"\s*$)', answer
    ):  # Corrected regex for ending punctuation or quote
        answer = answer.rstrip() + "."

    # If after all processing, the answer is empty, return a default.
    if not answer:
        return "I was unable to find a relevant answer in the provided documents."

    return answer


def create_rag_pipeline(llm: ChatOpenAI) -> Runnable:
    """
    Creates the core RAG LangChain Runnable pipeline.
    The pipeline expects a dictionary with "query" and "documents" (List[SourceDocument])
    and outputs a dictionary with "answer" and "formatted_context".

    Args:
        llm: The ChatOpenAI instance to use for generation.

    Returns:
        A LangChain Runnable.
    """
    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

    # Chain to prepare context and then pass through the original query and documents
    # The main RAG chain that processes query and documents
    core_rag_chain = (
        RunnablePassthrough.assign(
            context=(lambda x: format_documents_for_context(x["documents"]))
        )
        | prompt
        | llm
        | StrOutputParser()
        | RunnableLambda(post_process_llm_answer)
    )

    # Final chain to structure the output
    # It takes the input, passes "query" and "documents" to core_rag_chain for the answer
    # and also formats documents for the "formatted_context" output field.
    final_chain = RunnablePassthrough.assign(
        answer=core_rag_chain,
        formatted_context=lambda x: format_documents_for_context(x["documents"]),
    )

    return final_chain


# Example of how it might be used (for testing or by RAGService later)
if __name__ == "__main__":  # Ensure this line is correct
    pass
