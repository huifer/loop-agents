import os
import random
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()

# Global variable to store the last used API key
_last_used_api_key = None
# Set to track all API keys used in the current cycle
_used_api_keys = set()


def get_llm_model():
    """
    Factory function to create an LLM model based on environment variables.

    Returns:
        An instance of a language model (ChatOpenAI, ChatGoogleGenerativeAI, etc.)
    """
    global _last_used_api_key, _used_api_keys

    # Get provider type
    provider = os.getenv("PROVIDER", "google").lower()

    # Get API keys the same way for all providers
    api_keys_str = os.getenv("API_KEYS")
    if not api_keys_str:
        raise ValueError("API_KEYS not found in environment variables.")

    # Split API keys string
    api_keys = [key.strip() for key in api_keys_str.split(", ")]

    # Check if all API keys have been used
    if len(_used_api_keys) >= len(api_keys):
        print(
            "All API keys have been used. Pausing for 10 seconds to reset usage cycle..."
        )
        time.sleep(10)
        # Reset the used keys tracking
        _used_api_keys.clear()

    # Find keys that haven't been used yet
    available_keys = [key for key in api_keys if key not in _used_api_keys]

    if available_keys:
        # Prefer unused keys
        selected_api_key = random.choice(available_keys)
    else:
        # This should not happen due to the reset above, but just in case
        selected_api_key = random.choice(api_keys)
        _used_api_keys.clear()  # Reset again as a safety measure

    # Update tracking
    _last_used_api_key = selected_api_key
    _used_api_keys.add(selected_api_key)

    if provider == "google":
        # Create Google Generative AI model
        model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash-preview-04-17")
        # print("Using Google Generative AI model:", model_name)
        # print("Using API key:", selected_api_key)
        time.sleep(1)
        return ChatGoogleGenerativeAI(
            model=model_name,
            api_key=selected_api_key,
        )
    else:  # Default to OpenAI
        # Get configuration for OpenAI model
        model_name = os.getenv("MODEL_NAME", "qwen-max")
        base_url = os.getenv(
            "BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        return ChatOpenAI(
            model_name=model_name,
            base_url=base_url,
            api_key=selected_api_key,
        )


# Example usage
if __name__ == "__main__":
    try:
        llm = get_llm_model()
        print(f"Successfully created LLM model: {type(llm).__name__}")
    except Exception as e:
        print(f"Error creating LLM model: {str(e)}")
