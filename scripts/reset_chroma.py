#!/usr/bin/env python
import chromadb
import os
from dotenv import load_dotenv
import argparse
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def reset_collection(collection_name, host="chromadb", port=8000):
    """Reset a ChromaDB collection by deleting and recreating it"""
    try:
        print(f"Connecting to ChromaDB at {host}:{port}...")
        client = chromadb.HttpClient(host=host, port=port)

        # Check connection
        client.heartbeat()
        print("Connected to ChromaDB successfully.")

        # List all collections
        collections = client.list_collections()
        print(f"Found {len(collections)} collections.")

        # Check if the collection exists
        collection_exists = False
        for collection in collections:
            if collection.name == collection_name:
                collection_exists = True
                print(f"Found collection: {collection_name}")

                # Get item count
                count = collection.count()
                print(f"Collection has {count} items.")

                # Delete the collection
                print(f"Deleting collection: {collection_name}")
                client.delete_collection(name=collection_name)
                print(f"Collection {collection_name} deleted successfully.")
                break

        if not collection_exists:
            print(f"Collection {collection_name} does not exist. Nothing to reset.")

        # Create a new empty collection
        print(f"Creating new empty collection: {collection_name}")
        client.create_collection(name=collection_name)
        print(f"Empty collection {collection_name} created successfully.")

        return True
    except Exception as e:
        print(f"Error resetting ChromaDB collection: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset a ChromaDB collection")
    parser.add_argument(
        "--collection",
        type=str,
        default="claims_documents_mvp",
        help="Name of the collection to reset",
    )
    parser.add_argument("--host", type=str, default="localhost", help="ChromaDB host")
    parser.add_argument("--port", type=int, default=8000, help="ChromaDB port")

    args = parser.parse_args()

    success = reset_collection(args.collection, args.host, args.port)

    if success:
        print("Collection reset completed successfully.")
    else:
        print("Collection reset failed.")
        sys.exit(1)
