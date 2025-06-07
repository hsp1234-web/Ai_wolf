# services/model_catalog.py
# import streamlit as st # Removed Streamlit import
import google.generativeai as genai
import logging
from ..config import settings # Changed import path

logger = logging.getLogger(__name__)

# Helper for sorting
def _get_model_sort_key(model_name):
    """
    Generates a sort key for model names.
    Prioritizes 'flash', then 'pro'. For versions, 'latest' is prioritized,
    then numerically descending, then alphabetically.
    """
    name_lower = model_name.lower()

    # Primary priority: flash, pro, others
    if "flash" in name_lower:
        priority = 0
    elif "pro" in name_lower:
        priority = 1
    else:
        priority = 2

    # Version sorting: attempt to extract version info
    # This is a simplified approach; more robust parsing might be needed for complex version schemes
    version_part = name_lower
    parts = name_lower.split('-')
    if len(parts) > 1:
        # Look for 'latest' or numeric parts
        if parts[-1] == "latest":
            version_metric = 0 # Highest priority for 'latest'
        elif parts[-1].isdigit():
            try:
                version_metric = -int(parts[-1]) # Negative for descending numeric sort
            except ValueError:
                version_metric = float('inf') # Fallback if not a simple number
        else:
            version_metric = float('inf') # Fallback for non-standard versions
    else:
        version_metric = float('inf')

    return (priority, version_metric, name_lower)


# @st.cache_data(ttl=settings.DEFAULT_CACHE_TTL_SECONDS) # Decorator removed
def get_available_models(api_key: str = None): # Made api_key optional
    """
    Fetches available generative models from the Google AI API, filters and sorts them.
    Returns a list of model objects. If api_key is not provided, it attempts to use one from settings.
    # TODO: Implement caching for this function in the API layer or via a dedicated caching library.
    """
    used_api_key = api_key
    if not used_api_key:
        if settings.AVAILABLE_GEMINI_API_KEYS:
            used_api_key = settings.AVAILABLE_GEMINI_API_KEYS[0] # Use the first available key
            logger.info("get_available_models: API key not provided, using the first available key from settings.")
        else:
            logger.warning("get_available_models: No API key provided and no keys available in settings.")
            return []

    try:
        genai.configure(api_key=used_api_key)
        models = genai.list_models()

        filtered_models = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                filtered_models.append(model)

        # Using the more robust _get_model_sort_key function
        sorted_models = sorted(filtered_models, key=lambda m: _get_model_sort_key(m.name))

        logger.info(f"Fetched and sorted {len(sorted_models)} models.")
        return sorted_models

    except Exception as e:
        logger.error(f"Error fetching or sorting models: {e}", exc_info=True)
        # st.error call removed
        return [] # Return empty list on error

def format_model_display_name(model_obj) -> str:
    """
    Formats a model object for display (e.g., in logs or API responses).
    Example: "Gemini 1.5 Flash (Tokens: In:1048576, Out:8192)"
    """
    if not model_obj:
        return "N/A"

    input_limit = getattr(model_obj, 'input_token_limit', 'N/A')
    output_limit = getattr(model_obj, 'output_token_limit', 'N/A')
    base_display_name = getattr(model_obj, 'display_name', model_obj.name)

    return f"{base_display_name} (In: {input_limit}, Out: {output_limit})"

# if __name__ == '__main__':
    # For local testing (requires a GOOGLE_API_KEY environment variable or manual setup)
    # Note: This test won't work directly in Streamlit's execution environment without an API key
    # and might not be runnable by the agent directly.
    # print("Attempting to test model catalog functions (requires API key).")

    # This part is for manual testing and might need adjustment based on how API key is provided.
    # It's unlikely the agent can run this directly.
    # import os
    # from dotenv import load_dotenv # Ensure python-dotenv is installed for this local test
    # load_dotenv() # Load .env file if present (for local GOOGLE_API_KEY)
    # test_api_key = os.environ.get("GOOGLE_API_KEY")

    # if not test_api_key: # Fallback for manual input if not in env
        # print("Trying to load from settings.py (if it has a direct key, not typical)")
        # try:
            # from backend.app.config.settings import GEMINI_API_KEY_1 # Example, adjust if needed
            # test_api_key = GEMINI_API_KEY_1
        # except ImportError:
            # print("Could not import a specific key from settings for testing.")
            # test_api_key = None # Ensure it's None

    # if test_api_key:
    #     print(f"Using API key for testing (ends with ...{test_api_key[-4:]}).")
    #     # Need to ensure settings.DEFAULT_CACHE_TTL_SECONDS is available if ttl was used by @st.cache_data
    #     # Since it's removed, we don't need settings.DEFAULT_CACHE_TTL_SECONDS for the function call itself.
    #     # However, if settings.py is not correctly found due to path issues during local test,
    #     # the import `from ..config import settings` might fail if run directly.
    #     # This __main__ block is best run with `python -m backend.app.services.model_catalog` from project root.
    #     models = get_available_models(test_api_key)
    #     if models:
    #         print(f"Found {len(models)} models:")
    #         for model in models:
    #             print(f"  - {model.name} -> {format_model_display_name(model)}")
    #             # print(f"    Supported methods: {model.supported_generation_methods}")
    #             # print(f"    Sort key: {_get_model_sort_key(model.name)}")
    #     else:
    #         print("No models found or error occurred.")
    # else:
    #     print("GOOGLE_API_KEY (or equivalent for testing) not set. Skipping live test.")
    # pass
