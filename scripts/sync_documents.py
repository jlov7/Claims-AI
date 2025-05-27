#!/usr/bin/env python
import sys
import os
from pathlib import Path
import logging
import chromadb
import argparse
import asyncio

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the RAG service to use its embedding function
from services.rag_service import get_rag_service

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def sync_documents_to_chroma(
    host="chromadb", port=8000, collection_name="claims_documents_mvp"
):
    """
    Syncs all processed documents with ChromaDB.

    This script reads all JSON files from the processed_text directory,
    and adds their content to ChromaDB to ensure the document content
    is available for RAG queries.
    """
    # Get the RAG service to use its embedding function
    rag_service = get_rag_service()

    # Path to the processed text directory
    app_base_dir = Path(__file__).resolve().parent.parent
    processed_text_dir = app_base_dir / "data" / "processed_text"

    # Ensure the directory exists
    if not processed_text_dir.exists():
        logger.error(
            f"Processed documents directory does not exist: {processed_text_dir}"
        )
        return False

    # Connect to ChromaDB
    try:
        logger.info(f"Connecting to ChromaDB at {host}:{port}...")
        client = chromadb.HttpClient(host=host, port=port)

        # Check connection
        client.heartbeat()
        logger.info("Connected to ChromaDB successfully.")

        # Delete the collection if it exists
        logger.info(f"Resetting collection: {collection_name}")
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except Exception as e:
            logger.info(
                f"Collection {collection_name} not found or could not be deleted: {e}"
            )

        # Create a new collection with the embedding function
        logger.info(f"Creating collection: {collection_name}")
        collection = client.create_collection(
            name=collection_name, embedding_function=rag_service.embedding_function
        )
        logger.info(f"Created collection: {collection_name}")

        # Get a list of all files in the directory
        documents_processed = 0
        chunks_added = 0

        for file_path in processed_text_dir.glob("*.json"):
            try:
                doc_id = file_path.name  # filename including .json extension
                original_name = file_path.stem  # filename without .json extension

                # Read JSON content
                with open(file_path, "r") as f:
                    content = f.read()

                if content:
                    # Split content into chunks for better retrieval
                    chunks = content.split("\n---\n")

                    # Add each chunk with metadata
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue

                        chunk_id = f"{doc_id}_chunk_{i}"

                        try:
                            collection.add(
                                documents=[chunk],
                                metadatas=[
                                    {
                                        "document_id": doc_id,
                                        "chunk_id": chunk_id,
                                        "file_name": doc_id,
                                    }
                                ],
                                ids=[chunk_id],
                            )
                            chunks_added += 1
                            logger.info(
                                f"Added chunk {i+1}/{len(chunks)} for document {doc_id}"
                            )
                        except Exception as chunk_error:
                            logger.error(
                                f"Failed to add chunk {i+1}/{len(chunks)} for document {doc_id}: {chunk_error}"
                            )

                documents_processed += 1
                logger.info(f"Processed document {documents_processed}: {doc_id}")

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")

        # Count documents after syncing
        doc_count = (
            len(collection.get(include=["metadatas"])["ids"])
            if collection.count() > 0
            else 0
        )
        logger.info(f"Collection has {doc_count} documents after syncing")
        logger.info(
            f"Sync complete. Processed {documents_processed} documents, added {chunks_added} chunks."
        )

        return True
    except Exception as e:
        logger.error(f"Error syncing documents: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync processed documents with ChromaDB"
    )
    parser.add_argument("--host", default="chromadb", help="ChromaDB host")
    parser.add_argument("--port", type=int, default=8000, help="ChromaDB port")
    parser.add_argument(
        "--collection", default="claims_documents_mvp", help="ChromaDB collection name"
    )

    args = parser.parse_args()

    success = sync_documents_to_chroma(args.host, args.port, args.collection)
    if success:
        logger.info("Document sync completed successfully")
    else:
        logger.error("Document sync failed")
        sys.exit(1)
