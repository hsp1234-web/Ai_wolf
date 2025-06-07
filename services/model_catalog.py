# services/model_catalog.py
import streamlit as st
import google.generativeai as genai
import logging
from config import app_settings # Import app_settings

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


@st.cache_data(ttl=app_settings.DEFAULT_CACHE_TTL_SECONDS)
def get_available_models(api_key: str):
    """
    Fetches available generative models from the Google AI API, filters and sorts them.
    Returns a list of model objects.
    """
    if not api_key:
        logger.warning("get_available_models_list called without an API key.")
        return []
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()

        filtered_models = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                filtered_models.append(model)

        # Sort models:
        # 1. "flash" models first, then "pro", then others.
        # 2. For versions like "latest" or numeric (e.g., -001), sort "latest" first, then numerically descending.
        # 3. Fallback to alphabetical for others or if version parsing is ambiguous.
        # The model name used for sorting should be model.name (e.g. "models/gemini-1.5-flash-latest")
        # or model.display_name if model.name is not suitable for direct sorting.
        # Let's assume model.name is the identifier like "models/gemini-1.5-pro-latest"

        # Using a custom sort key function
        # sorted_models = sorted(filtered_models, key=lambda m: _get_model_sort_key(m.name))

        # Simpler sorting: flash, pro, then reverse alphabetical on name (hoping latest/higher versions come later)
        # This might be less accurate than a dedicated version parser.
        def sort_key(m):
            name = m.name.lower() # e.g., "models/gemini-1.5-flash-latest"
            is_flash = "flash" in name
            is_pro = "pro" in name

            if is_flash:
                primary = 0
            elif is_pro:
                primary = 1
            else:
                primary = 2

            # Secondary sort: by name, hoping "latest" or higher numbers sort later (reverse=True for name)
            # This is a simplification. For true version sorting, more complex parsing of m.name is needed.
            return (primary, name)

        # Sort with primary criteria (flash, pro, other) and then by name alphabetically (ascending)
        # To make "latest" or higher numbers appear first if they are alphabetically last,
        # we might need a more specific version parsing in _get_model_sort_key or make name sort descending.
        # For now, let's use the _get_model_sort_key which is more robust.
        sorted_models = sorted(filtered_models, key=lambda m: _get_model_sort_key(m.name))

        logger.info(f"Fetched and sorted {len(sorted_models)} models.")
        return sorted_models

    except Exception as e:
        logger.error(f"Error fetching or sorting models: {e}", exc_info=True)
        # st.error(f"無法獲取模型列表: {e}") # Avoid calling st.error directly in service layer
        return [] # Return empty list on error

def format_model_display_name(model_obj) -> str:
    """
    Formats a model object for display in a Streamlit selectbox.
    Example: "Gemini 1.5 Flash (Tokens: In:1048576, Out:8192)"
    """
    if not model_obj:
        return "N/A"

    # Adjust attribute names based on actual API response.
    # These are common attributes, but verify with google.generativeai.types.Model
    input_limit = getattr(model_obj, 'input_token_limit', 'N/A')
    output_limit = getattr(model_obj, 'output_token_limit', 'N/A')

    # display_name is usually more friendly, e.g., "Gemini 1.5 Pro"
    # name is the full identifier, e.g., "models/gemini-1.5-pro-latest"
    base_display_name = getattr(model_obj, 'display_name', model_obj.name)

    # RPM/TPM are not directly available as model attributes in google-generativeai library's Model type.
    # These are typically service-level quotas rather than model-specific attributes.
    # For now, we'll just show token limits.
    return f"{base_display_name} (In: {input_limit}, Out: {output_limit})"

if __name__ == '__main__':
    # For local testing (requires a GOOGLE_API_KEY environment variable or manual setup)
    # Note: This test won't work directly in Streamlit's execution environment without an API key
    # and might not be runnable by the agent directly.
    print("Attempting to test model catalog functions (requires API key).")

    # This part is for manual testing and might need adjustment based on how API key is provided.
    # It's unlikely the agent can run this directly.
    # import os
    # test_api_key = os.environ.get("GOOGLE_API_KEY")
    # if test_api_key:
    #     print(f"Using API key from environment for testing.")
    #     models = get_available_models(test_api_key)
    #     if models:
    #         print(f"Found {len(models)} models:")
    #         for model in models:
    #             print(f"  - {model.name} -> {format_model_display_name(model)}")
    #             print(f"    Supported methods: {model.supported_generation_methods}")
    #             print(f"    Sort key: {_get_model_sort_key(model.name)}")
    #     else:
    #         print("No models found or error occurred.")
    # else:
    #     print("GOOGLE_API_KEY environment variable not set. Skipping live test.")
    pass
