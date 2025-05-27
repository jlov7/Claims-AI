import argparse
import os
from dotenv import dotenv_values, set_key, unset_key

# Path to the .env file in the project root
DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")


def configure_env(provider: str, model: str):
    """Configures the .env file for the specified LLM provider and model."""
    print(f"Updating .env file at: {DOTENV_PATH}")
    print(f"Setting LLM_PROVIDER to '{provider}' and MODEL_NAME to '{model}'")

    try:
        # Load existing .env values (creates file if it doesn't exist, though it should)
        if not os.path.exists(DOTENV_PATH):
            print(f"Warning: .env file not found at {DOTENV_PATH}. Creating a new one.")
            open(DOTENV_PATH, "a").close()  # Create empty file if it doesn't exist

        # Set common provider and model name
        set_key(DOTENV_PATH, "LLM_PROVIDER", provider)

        if provider == "ollama":
            set_key(DOTENV_PATH, "OLLAMA_MODEL_NAME", model)
            set_key(
                DOTENV_PATH, "OLLAMA_BASE_URL", "http://localhost:11434"
            )  # Default for local Ollama
            # Comment out or remove Gemini specific vars
            unset_key(DOTENV_PATH, "GEMINI_API_KEY")
            unset_key(DOTENV_PATH, "GEMINI_MODEL_NAME")
            print("Configured for Ollama.")

        elif provider == "gemini":
            set_key(DOTENV_PATH, "GEMINI_MODEL_NAME", model)
            # Ensure GEMINI_API_KEY is present or remind user to set it (cannot set it here)
            env_vars = dotenv_values(DOTENV_PATH)
            if "GEMINI_API_KEY" not in env_vars or not env_vars["GEMINI_API_KEY"]:
                print(
                    "Warning: GEMINI_API_KEY is not set in .env. Please add it manually."
                )
            # Comment out or remove Ollama specific vars
            unset_key(DOTENV_PATH, "OLLAMA_MODEL_NAME")
            unset_key(DOTENV_PATH, "OLLAMA_BASE_URL")
            print("Configured for Gemini.")
        else:
            print(f"Error: Unsupported LLM provider '{provider}'. No changes made.")
            return

        print(f".env file updated successfully for {provider} with model {model}.")

    except Exception as e:
        print(f"Error updating .env file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Configure .env file for different LLM providers."
    )
    parser.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["ollama", "gemini"],
        help="The LLM provider to configure (e.g., 'ollama', 'gemini')",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="The model name to use (e.g., 'mistral' for ollama, 'gemini-pro' for gemini)",
    )

    args = parser.parse_args()
    configure_env(args.provider, args.model)
