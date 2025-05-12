import logging
from typing import List, Optional
from pathlib import Path

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from backend.core.config import Settings, get_settings, PROJECT_ROOT
from fastapi import Depends

logger = logging.getLogger(__name__)


class DocumentLoaderService:  # Renamed to avoid conflict if RAGService has an inner DocumentLoader
    """
    Service to load and split documents from various sources.
    Currently supports loading from the local processed_text directory.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings if settings else get_settings()
        # Define the base path for processed documents relative to project root
        self.processed_docs_path = Path(PROJECT_ROOT) / "data" / "processed_text"

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Adjust as needed
            chunk_overlap=200,  # Adjust as needed
            length_function=len,
            add_start_index=True,
        )

    def _get_loader(self, file_path: Path):
        ext = file_path.suffix.lower()
        if ext == ".txt":
            return TextLoader(str(file_path), encoding="utf-8")
        elif ext == ".pdf":
            return PyPDFLoader(str(file_path))
        elif ext == ".docx":
            return Docx2txtLoader(str(file_path))
        # Add other loaders as needed (e.g., markdown, html)
        # elif ext == ".md":
        #     return UnstructuredMarkdownLoader(str(file_path))
        # elif ext == ".html":
        #     return UnstructuredHTMLLoader(str(file_path))
        else:
            logger.warning(
                f"No specific loader for extension {ext}, attempting TextLoader for {file_path.name}"
            )
            return TextLoader(
                str(file_path), encoding="utf-8"
            )  # Default or raise error

    def load_document_by_id(self, document_id: str) -> Optional[List[Document]]:
        """
        Loads a single document by its ID (filename) from the processed_docs_path.
        The document_id is expected to be the filename (e.g., 'mydoc.txt').
        Returns a list of Langchain Document objects (split into chunks) or None if not found/error.
        """
        if not document_id or not isinstance(document_id, str):
            logger.error(f"Invalid document_id provided: {document_id}")
            return None

        # Basic sanitization to prevent path traversal by ensuring it's just a filename
        if "/" in document_id or "\\" in document_id:
            logger.error(
                f"Invalid characters in document_id (potential path traversal): {document_id}"
            )
            return None

        file_path = self.processed_docs_path / document_id

        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Document not found at path: {file_path}")
            return None

        try:
            logger.info(f"Loading document: {file_path}")
            loader = self._get_loader(file_path)
            docs = (
                loader.load()
            )  # Returns a list of Document objects (usually one per file)

            # Even if loader returns multiple docs (e.g. some PDFs), split them all
            all_split_docs = []
            for doc in docs:
                split_docs = self.text_splitter.split_documents([doc])
                # Add original filename to metadata for all chunks
                for split_doc in split_docs:
                    split_doc.metadata["source_filename"] = document_id
                all_split_docs.extend(split_docs)

            logger.info(
                f"Loaded and split {document_id} into {len(all_split_docs)} chunks."
            )
            return all_split_docs
        except Exception as e:
            logger.error(
                f"Error loading document {document_id} from {file_path}: {e}",
                exc_info=True,
            )
            return None

    def load_document_content_by_id(self, document_id: str) -> Optional[str]:
        """
        Loads a document by ID and returns its full text content as a single string.
        """
        split_docs = self.load_document_by_id(document_id)
        if split_docs:
            return "\n---\n".join([doc.page_content for doc in split_docs])
        return None


# Dependency for FastAPI
_document_loader_service_instance: Optional[DocumentLoaderService] = None


def get_document_loader_service(
    settings: Settings = Depends(get_settings),
) -> DocumentLoaderService:
    global _document_loader_service_instance
    if (
        _document_loader_service_instance is None
        or _document_loader_service_instance.settings != settings
    ):
        _document_loader_service_instance = DocumentLoaderService(settings=settings)
    return _document_loader_service_instance
