import os
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()


def get_llm_model():
    """
    Factory function to create an LLM model based on environment variables.

    Returns:
        An instance of a language model (ChatOpenAI, ChatGoogleGenerativeAI, etc.)
    """

    # Get provider type
    provider = os.getenv("PROVIDER", "google").lower()

    # Get API keys the same way for all providers
    api_keys_str = os.getenv("API_KEYS")
    if not api_keys_str:
        raise ValueError("API_KEYS not found in environment variables.")

    # Split API keys string and randomly select one
    api_keys = [key.strip() for key in api_keys_str.split(", ")]
    selected_api_key = random.choice(api_keys)

    if provider == "google":
        # Create Google Generative AI model
        model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash-preview-04-17")
        # print("Using Google Generative AI model:", model_name)
        # print("Using API key:", selected_api_key)
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
