import logging
import os
import uuid
import re
from typing import Optional
from fastapi import HTTPException, Depends
from docx import Document  # For creating .docx files
from pathlib import Path

from backend.core.config import Settings, get_settings, PROJECT_ROOT
from backend.models import (
    DraftStrategyNoteRequest,
)  # QAPair for qa_history typing
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.services.document_loader import (
    DocumentLoaderService,
    get_document_loader_service,
)

logger = logging.getLogger(__name__)


class DraftingService:
    def __init__(
        self,
        settings_instance: Settings,
        doc_loader_service: DocumentLoaderService,
        **kwargs,
    ):
        self.settings = settings_instance
        self.doc_loader = doc_loader_service
        self.llm_client = ChatOpenAI(
            openai_api_base=settings_instance.PHI4_API_BASE,
            openai_api_key="lm-studio",
            model="llama-3.2-3b-instruct",
            temperature=settings_instance.LLM_TEMPERATURE,
            max_tokens=settings_instance.LLM_MAX_TOKENS,
        )
        logger.info(
            "DraftingService initialized with LLM client using model: llama-3.2-3b-instruct"
        )
        # Allow output_dir to be specified, otherwise use settings
        # Ensure output_dir is a Path object for consistency
        self.output_dir = Path(
            kwargs.get(
                "output_dir", Path(PROJECT_ROOT) / "data" / "outputs" / "strategy_notes"
            )
        )

        try:
            logger.info(f"Ensuring output directory exists: {self.output_dir}")
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(
                f"DraftingService initialized. Output directory: {self.output_dir}"
            )
        except Exception as e:
            logger.error(
                f"Failed to ensure output directory exists: {e}", exc_info=True
            )
            raise

    def _get_content_from_doc_id(self, document_id: str) -> Optional[str]:
        """Helper to fetch content for a given document_id using DocumentLoaderService."""
        try:
            # Use the injected document loader service
            # The method in DocumentLoaderService is load_document_content_by_id
            content = self.doc_loader.load_document_content_by_id(document_id)
            if content:
                return content
            logger.warning(
                f"No content found for document_id: {document_id} by DraftingService's loader"
            )
            return None
        except Exception as e:
            logger.error(
                f"DraftingService: Error loading content for document_id {document_id}: {e}",
                exc_info=True,
            )
            return None

    def _build_llm_context(self, request: DraftStrategyNoteRequest) -> str:
        contexts = []
        if request.claim_summary:
            contexts.append(f"Claim Summary:\n{request.claim_summary}")

        if request.document_ids:
            doc_contents = []
            for doc_id in request.document_ids:
                content = self._get_content_from_doc_id(doc_id)
                if content:
                    doc_contents.append(
                        f"Content from Document ID '{doc_id}':\n{content}"
                    )
            if doc_contents:
                contexts.append("\n\n---\n\n".join(doc_contents))

        if request.qa_history:
            qa_strings = []
            for i, pair in enumerate(request.qa_history):
                qa_strings.append(f"Q&A {i+1}:\nQ: {pair.question}\nA: {pair.answer}")
            if qa_strings:
                contexts.append("Relevant Q&A History:\n" + "\n\n".join(qa_strings))

        if request.additional_criteria:
            contexts.append(
                f"Additional Instructions/Criteria for Drafting:\n{request.additional_criteria}"
            )

        if not contexts:
            # This should ideally be caught by Pydantic validator, but as a fallback.
            logger.warning("No context provided for drafting strategy note.")
            # Raise an error that the endpoint can catch and turn into a 400
            raise ValueError(
                "Insufficient context to draft a strategy note. Please provide summary, documents, Q&A, or criteria."
            )

        return "\n\n---\n\n".join(contexts)

    def generate_strategy_note_text(self, context: str) -> str:
        # This prompt needs to be carefully engineered for good results.
        template = """
        You are an AI assistant tasked with drafting a Claim Strategy Note based on the provided information.
        The note should be comprehensive, well-structured, and actionable.
        Consider including sections such as: Introduction/Background, Key Findings, Strengths, Weaknesses, Potential Risks, Recommended Strategy, Next Steps.
        Adapt the structure and content based on the specifics of the provided context.

        Provided Context:
        ---BEGIN CONTEXT---
        {context_for_llm}
        ---END CONTEXT---

        Draft of Claim Strategy Note:
        """
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm_client | StrOutputParser()

        try:
            logger.info(
                f"Requesting strategy note draft from LLM. Context length: {len(context)}"
            )
            draft_text = chain.invoke({"context_for_llm": context})
            logger.info("Successfully generated strategy note draft text from LLM.")
            return draft_text
        except Exception as e:
            logger.error(
                f"LLM call failed during strategy note drafting: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to generate strategy note text due to LLM error.",
            )

    def create_docx_from_text(
        self, *, text: str, filename_suggestion: str | None = None
    ) -> Path:
        """
        Creates a .docx file from the given text and saves it to data/outputs.
        Generates a safe filename, avoiding problematic characters and ensuring uniqueness.
        """
        # 1️⃣ NORMALISE FIRST, *THEN* SPLIT
        cleaned_suggestion = os.path.basename(
            filename_suggestion or "strategy_note.docx"
        )
        original_base_name, ext = os.path.splitext(cleaned_suggestion)

        # Ensure extension is .docx, default if not provided or incorrect
        if not ext.lower() == ".docx":
            ext = ".docx"
            # If the original_base_name was just an extension (e.g. ".txt"),
            # and we are forcing .docx, we should clear original_base_name
            # or we might end up with "txt.docx" if original_base_name was "txt"
            if original_base_name.lower() + ext.lower() == cleaned_suggestion.lower():
                original_base_name = ""

        # Sanitize the base name
        # Remove non-alphanumeric characters (except underscore and hyphen)
        base_name_candidate = re.sub(r"[^\w\-]+", "_", original_base_name)
        # Replace multiple underscores/hyphens with a single one
        base_name_candidate = re.sub(r"[_\-]+", "_", base_name_candidate)
        base_name_candidate = base_name_candidate.strip("_")

        # 2️⃣ FALL BACK IF THE SANITISED NAME IS BLANK **OR JUST THE EXTENSION**
        if (
            not base_name_candidate.strip("_")
            or base_name_candidate.lower() == ext.lstrip(".").lower()
        ):
            final_safe_base_name = f"strategy_note_{uuid.uuid4().hex[:8]}"
        else:
            final_safe_base_name = base_name_candidate

        doc = Document()
        doc.add_heading("Claim Strategy Note", level=1)

        for para_text in text.split("\n\n"):
            if para_text.strip():
                doc.add_paragraph(para_text.strip())

        safe_filename = final_safe_base_name + ext

        # Limit total length
        max_len = 250  # A reasonable max length for a filename
        if len(safe_filename) > max_len:
            base_max_len = max_len - len(ext)
            final_safe_base_name = final_safe_base_name[:base_max_len]
            safe_filename = final_safe_base_name + ext
            if not final_safe_base_name:  # Re-check if it became empty after truncation
                safe_filename = f"strategy_note_{uuid.uuid4().hex[:8]}.docx"

        output_path = os.path.join(self.output_dir, safe_filename)

        try:
            doc.save(output_path)
            logger.info(f"Strategy note DOCX saved to: {output_path}")
            return Path(output_path)
        except Exception as e:
            logger.error(
                f"Failed to save DOCX file to {output_path}: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to save the generated DOCX strategy note.",
            )


# Dependency injector for DraftingService
_drafting_service_instance = None


def get_drafting_service(
    settings_instance: Settings = Depends(get_settings),
    doc_loader: DocumentLoaderService = Depends(get_document_loader_service),
) -> DraftingService:
    global _drafting_service_instance
    # Invalidate instance if settings or doc_loader change, or simply create new one for simplicity in FastAPI context
    # For true singleton behavior with multiple dependencies, keying the instance might be needed.
    # Here, we assume settings_instance is the primary key for the service instance.
    # A more robust singleton would consider all its dependencies for instance caching.
    # For now, let's simplify and assume if settings object is same, we can reuse,
    # but this isn't strictly correct if doc_loader could be different for same settings.
    # Simplest for FastAPI: always create, or manage a more complex cache.
    # Let's go with creating a new one each time if not exact match or simply always if dependencies are complex.

    # For testing, output_dir is handled by the fixture overriding this whole function.
    # For production, it uses its default output_dir.
    # This dependency injector should provide a production-ready DraftingService.

    # A basic singleton approach based on settings only (doc_loader is now a dependency)
    if (
        _drafting_service_instance is None
        or _drafting_service_instance.settings != settings_instance
    ):
        _drafting_service_instance = DraftingService(
            settings_instance=settings_instance, doc_loader_service=doc_loader
        )
    # If we want to be stricter about the doc_loader instance too for the singleton:
    # if _drafting_service_instance is None or \
    #    _drafting_service_instance.settings != settings_instance or \
    #    _drafting_service_instance.doc_loader != doc_loader:
    #     _drafting_service_instance = DraftingService(settings_instance=settings_instance, doc_loader_service=doc_loader)
    return _drafting_service_instance
