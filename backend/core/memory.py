import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Define a base path for session memory files
# This could be configured via settings eventually
DEFAULT_SESSION_MEMORY_DIR = Path("data/sessions")


class SessionMemory:
    """
    Manages shared memory for an agentic session using JSON files.
    Each session is identified by a unique session_id.
    """

    def __init__(self, session_id: str, memory_dir: Optional[Path] = None):
        if not session_id:
            raise ValueError("session_id cannot be empty.")
        self.session_id = session_id
        self.memory_dir = memory_dir if memory_dir else DEFAULT_SESSION_MEMORY_DIR
        self.memory_file_path = self.memory_dir / f"{self.session_id}.json"
        self._ensure_memory_dir_exists()

    def _ensure_memory_dir_exists(self):
        """Ensures the directory for storing session memory files exists."""
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Error creating session memory directory {self.memory_dir}: {e}"
            )
            # Depending on desired behavior, could re-raise or handle differently
            raise

    def load_memory(self) -> Dict[str, Any]:
        """
        Loads the session memory from its JSON file.
        Returns an empty dictionary if the file doesn't exist or an error occurs.
        """
        if not self.memory_file_path.exists():
            return {}

        try:
            with open(self.memory_file_path, "r", encoding="utf-8") as f:
                memory_data = json.load(f)
            if not isinstance(memory_data, dict):
                logger.warning(
                    f"Memory file {self.memory_file_path} did not contain a JSON object (dict). Returning empty memory."
                )
                return {}
            return memory_data
        except json.JSONDecodeError as e:
            logger.error(
                f"Error decoding JSON from {self.memory_file_path}: {e}. Returning empty memory."
            )
            return {}
        except IOError as e:
            logger.error(
                f"IOError reading from {self.memory_file_path}: {e}. Returning empty memory."
            )
            return {}
        except Exception as e:
            logger.error(
                f"Unexpected error loading memory from {self.memory_file_path}: {e}. Returning empty memory."
            )
            return {}

    def save_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        Saves the provided session memory data to its JSON file.
        Returns True if successful, False otherwise.
        """
        if not isinstance(memory_data, dict):
            logger.error("Memory data to save must be a dictionary.")
            return False

        try:
            with open(self.memory_file_path, "w", encoding="utf-8") as f:
                json.dump(memory_data, f, indent=4)
            return True
        except IOError as e:
            logger.error(f"IOError writing to {self.memory_file_path}: {e}")
            return False
        except TypeError as e:  # e.g. if data is not JSON serializable
            logger.error(
                f"TypeError (data not JSON serializable?) writing to {self.memory_file_path}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error saving memory to {self.memory_file_path}: {e}"
            )
            return False

    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieves a value from session memory by key."""
        memory = self.load_memory()
        return memory.get(key, default)

    def set_value(self, key: str, value: Any) -> bool:
        """Sets a value in session memory by key and saves the memory."""
        memory = self.load_memory()
        memory[key] = value
        return self.save_memory(memory)

    def update_memory(self, update_dict: Dict[str, Any]) -> bool:
        """Updates the session memory with keys/values from update_dict and saves."""
        memory = self.load_memory()
        memory.update(update_dict)
        return self.save_memory(memory)

    def clear_key(self, key: str) -> bool:
        """Removes a key from session memory and saves."""
        memory = self.load_memory()
        if key in memory:
            del memory[key]
            return self.save_memory(memory)
        return True  # Key wasn't there, effectively cleared

    def clear_all_memory(self) -> bool:
        """Clears all data from session memory (writes an empty JSON object)."""
        return self.save_memory({})

    def delete_memory_file(self) -> bool:
        """Deletes the session memory file entirely."""
        if self.memory_file_path.exists():
            try:
                os.remove(self.memory_file_path)
                return True
            except OSError as e:
                logger.error(f"Error deleting memory file {self.memory_file_path}: {e}")
                return False
        return True  # File didn't exist


# Example usage (optional, for testing or demonstration):
# if __name__ == '__main__':
#     test_session_id = "test_session_123"
#
#     # Create and use memory
#     session_mem = SessionMemory(test_session_id)
#     print(f"Initial memory for {test_session_id}: {session_mem.load_memory()}")
#
#     session_mem.set_value("user_name", "Alice")
#     session_mem.set_value("preferred_language", "en")
#     print(f"Memory after setting values: {session_mem.load_memory()}")
#
#     user_name = session_mem.get_value("user_name")
#     print(f"Retrieved user_name: {user_name}")
#
#     session_mem.update_memory({"preferred_language": "fr", "theme": "dark"})
#     print(f"Memory after update: {session_mem.load_memory()}")
#
#     session_mem.clear_key("theme")
#     print(f"Memory after clearing theme: {session_mem.load_memory()}")
#
#     # Clean up by deleting the test memory file
#     # session_mem.delete_memory_file()
#     # print(f"Memory file deleted. Check {DEFAULT_SESSION_MEMORY_DIR}")
#
#     # Test another session
#     session_mem_2 = SessionMemory("test_session_456")
#     session_mem_2.set_value("item_count", 5)
#     print(f"Memory for {session_mem_2.session_id}: {session_mem_2.load_memory()}")
#     # session_mem_2.delete_memory_file()
