# services/gemini_service.py
# import streamlit as st # Removed Streamlit import
import google.generativeai as genai
import google.api_core.exceptions
import time # Keep time for potential future use, though not directly for RPM here
import logging
from typing import List, Dict, Optional, Any, Tuple
# Assuming app_settings.py will be moved to backend/app/config/settings.py
from ..config.settings import TOKEN_SAFETY_FACTOR

logger = logging.getLogger(__name__)

def call_gemini_api(
    prompt_parts: List[str],
    current_api_key: str, # Changed from api_keys_list
    selected_model: str,
    # global_rpm and global_tpm removed, to be handled by API router or dedicated service
    generation_config_dict: Optional[Dict[str, Any]] = None,
    cached_content_name: Optional[str] = None,
    logger_object: Optional[logging.Logger] = None # Added logger_object
) -> Tuple[str, bool]: # Return type remains Tuple[str, bool]
    """
    Calls the Gemini API to generate content. Logging is included.
    Key rotation and RPM/TPM limiting are expected to be handled by the caller.

    Args:
        prompt_parts: A list of parts for the prompt.
        current_api_key: The specific Gemini API key to use for this call.
        selected_model: The name of the Gemini model to use.
        generation_config_dict: Gemini generation configuration dictionary.
        cached_content_name: Name of the cached content to use.
        logger_object: Optional logger instance. If None, uses module-level logger.

    Returns:
        Tuple[str, bool]: The text result from the Gemini API (or an error message)
                          and a boolean indicating if truncation occurred.
    """
    effective_logger = logger_object if logger_object else logger
    effective_logger.info(f"Executing call_gemini_api. Model: {selected_model}, Using Cache: {'Yes' if cached_content_name else 'No'}, Prompt Parts Count: {len(prompt_parts)}")
    effective_logger.debug(f"Parameters - API Key (ends with): ...{current_api_key[-4:] if current_api_key else 'N/A'}, Generation Config: {generation_config_dict}, Cached Content Name: {cached_content_name}")

    was_truncated = False # Initialize was_truncated

    if not current_api_key:
        effective_logger.error("Gemini API call aborted: No API key provided.")
        return "Error: No valid Gemini API key was provided.", was_truncated

    # RPM and key rotation logic removed from this function.
    # Assumes current_api_key is valid and respects rate limits.

    try:
        effective_logger.info(f"Configuring Gemini with API key ending in ...{current_api_key[-4:]} (Model: {selected_model})...")
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(model_name=selected_model)
        effective_logger.debug(f"Gemini model instance created: {model}")

        # --- Token Counting and Truncation Logic (using helper function) ---
        final_contents_for_api_call = [str(p) for p in prompt_parts]

        try:
            model_token_limit = model.input_token_limit
            #TOKEN_SAFETY_FACTOR should be imported from new location
            effective_token_limit = int(model_token_limit * TOKEN_SAFETY_FACTOR)
            effective_logger.info(f"call_gemini_api: Model '{selected_model}' input token limit: {model_token_limit}, Effective limit (x{TOKEN_SAFETY_FACTOR}): {effective_token_limit}")

            final_contents_for_api_call, was_truncated = _truncate_prompt_parts(
                prompt_parts, model, effective_token_limit, effective_logger # Pass effective_logger
            )
            if was_truncated:
                effective_logger.info("call_gemini_api: Prompt was truncated due to token limit.")

        except Exception as e_trunc_setup:
            effective_logger.error(f"call_gemini_api: Error during truncation setup or execution: {e_trunc_setup}. Using original prompt.", exc_info=True)
            final_contents_for_api_call = [str(p) for p in prompt_parts]
            was_truncated = False
        # --- End of Token Counting and Truncation ---

        generation_config_obj = genai.types.GenerationConfig(**generation_config_dict) if generation_config_dict else None
        effective_logger.debug(f"Gemini generation config: {generation_config_obj}")

        effective_logger.debug(f"Final content parts count being sent to Gemini: {len(final_contents_for_api_call)}")
        if final_contents_for_api_call:
            effective_logger.debug(f"  First part (first 100 chars): {str(final_contents_for_api_call[0])[:100]}...")
            if len(final_contents_for_api_call) > 1:
                 effective_logger.debug(f"  Last part (first 100 chars): {str(final_contents_for_api_call[-1])[:100]}...")

        effective_logger.info(f"Calling Gemini API (model.generate_content)... Using cache: {cached_content_name if cached_content_name else 'None'}")
        response = model.generate_content(
            final_contents_for_api_call,
            generation_config=generation_config_obj,
            safety_settings=None,
            tools=None,
            tool_config=None,
            cached_content=cached_content_name
        )
        effective_logger.info(f"Gemini API call successful (Key ...{current_api_key[-4:]}, Model {selected_model}).")

        # RPM/TPM tracking based on st.session_state removed.
        # Logging usage from response if available.
        if response.usage_metadata and response.usage_metadata.total_token_count:
            token_count = response.usage_metadata.total_token_count
            effective_logger.info(f"Gemini usage metadata: {response.usage_metadata} (Tokens: {token_count})")
        else:
            effective_logger.warning("Gemini API response did not contain usage metadata or token count.")

        # Key rotation logic removed.

        response_text = "".join(part.text for part in response.parts if hasattr(part, 'text')) if response.parts else ""
        if not response_text and hasattr(response, 'text') and response.text:
             response_text = response.text

        effective_logger.info(f"Response text obtained from Gemini API, length: {len(response_text)}")
        if not response_text:
            effective_logger.warning("Gemini API returned no text content (parts or text were empty/invalid).")
            return "Error: Model returned no text content.", was_truncated

        effective_logger.debug(f"Gemini API raw response (first 100 chars): {response_text[:100]}...")
        return response_text, was_truncated

    except genai.types.BlockedPromptException as bpe:
        effective_logger.error(f"Gemini API Error (BlockedPromptException) with key ...{current_api_key[-4:]}, model {selected_model}: {bpe}", exc_info=True)
        return f"Error: Prompt was blocked by Gemini API. Reason: {bpe}", was_truncated
    except genai.types.generation_types.StopCandidateException as sce:
        effective_logger.error(f"Gemini API Error (StopCandidateException) with key ...{current_api_key[-4:]}, model {selected_model}: {sce}", exc_info=True)
        return f"Error: Content generation stopped due to safety or other reasons. Reason: {sce}", was_truncated
    except google.api_core.exceptions.PermissionDenied as e:
        effective_logger.error(f"Gemini API Error (PermissionDenied) with key ...{current_api_key[-4:]} (Model {selected_model}): {str(e)}. This key might be invalid or lack permissions.", exc_info=True)
        # Logic for marking keys as temporarily invalid (st.session_state) removed.
        # Caller should handle this error, possibly by trying a different key or notifying admin.
        return f"Error: API key ...{current_api_key[-4:]} has insufficient permissions or is invalid. Details: {str(e)}", False
    except google.api_core.exceptions.InvalidArgument as e:
        effective_logger.error(f"Gemini API Error (InvalidArgument) with key ...{current_api_key[-4:]}, model {selected_model}: {str(e)}", exc_info=True)
        return f"Error: Invalid argument when calling Gemini API (e.g., model name '{selected_model}' incorrect or content inappropriate). Details: {str(e)}", was_truncated
    except google.api_core.exceptions.ResourceExhausted as re:
        effective_logger.error(f"Gemini API Error (ResourceExhausted) with key ...{current_api_key[-4:]}, model {selected_model}: {str(re)}", exc_info=True)
        # Key rotation logic removed. Caller should handle rate limit issues.
        return f"Error: Gemini API resource exhausted (key ...{current_api_key[-4:]} may have hit RPM/TPM limits). Details: {str(re)}", False
    except Exception as e:
        effective_logger.error(f"Unexpected error during Gemini API call (Key ...{current_api_key[-4:]}, Model {selected_model}): {type(e).__name__} - {str(e)}", exc_info=True)
        return f"Unexpected error calling Gemini API: {type(e).__name__} - {str(e)}", was_truncated


def _truncate_prompt_parts(prompt_parts: List[str], model: Any, effective_token_limit: int, logger_object: logging.Logger) -> Tuple[List[str], bool]:
    """
    Intelligently truncates a list of prompt parts to fit within the token limit.

    Args:
        prompt_parts: Original list of prompt parts.
        model: Gemini model object (for count_tokens).
        effective_token_limit: Effective token limit after applying safety factor.
        logger_object: Logger instance for logging.

    Returns:
        Tuple[List[str], bool]: List of truncated prompt parts and a boolean (True if truncation occurred).
    """
    was_truncated = False
    # Ensure all parts are strings for token counting and processing
    contents_for_token_count = [str(p) for p in prompt_parts]

    try:
        token_count_response = model.count_tokens(contents_for_token_count)
        current_tokens = token_count_response.total_tokens
        logger_object.info(f"_truncate_prompt_parts: Initial token count: {current_tokens}, Limit: {effective_token_limit}")
    except Exception as e_count_tokens:
        logger_object.error(f"_truncate_prompt_parts: Error counting tokens: {e_count_tokens}. Truncation cannot be performed.", exc_info=True)
        return prompt_parts, False # Return original parts, not truncated

    if current_tokens > effective_token_limit:
        logger_object.warning(f"_truncate_prompt_parts: Token count {current_tokens} exceeds effective limit {effective_token_limit}. Starting truncation...")
        was_truncated = True
        num_parts_original = len(contents_for_token_count)

        # Strategy: Preserve system prompt (first part) and user question (last part) if possible,
        # truncate middle parts (e.g., context, history).
        if num_parts_original <= 1: # Cannot truncate if only one part or empty
            logger_object.warning(f"_truncate_prompt_parts: Cannot truncate further, only {num_parts_original} part(s). Content might still exceed limit.")
            # Even if it exceeds, we can't do much here with this strategy.
            # The API call might fail, or the model might truncate internally.
            return contents_for_token_count, was_truncated

        # Identify parts: system (first), user (last), middle (context/history)
        system_prompt_part = [contents_for_token_count[0]] if num_parts_original > 0 else []
        # Handle case where there's only one part, it becomes system_prompt, user_question is empty
        user_question_part = [contents_for_token_count[-1]] if num_parts_original > 1 else []

        # Middle parts are those between the first and the last.
        # If num_parts_original is 2, middle_parts_to_truncate will be empty.
        # If num_parts_original is 1, user_question_part is empty, this slice is also empty.
        middle_parts_to_truncate = list(contents_for_token_count[len(system_prompt_part):-len(user_question_part)] if num_parts_original > 1 else [])

        # Iteratively remove from the beginning of middle_parts_to_truncate
        while current_tokens > effective_token_limit and middle_parts_to_truncate:
            middle_parts_to_truncate.pop(0) # Remove the oldest/earliest middle part
            temp_contents = system_prompt_part + middle_parts_to_truncate + user_question_part

            try:
                token_count_response = model.count_tokens(temp_contents)
                current_tokens = token_count_response.total_tokens
                logger_object.info(f"_truncate_prompt_parts: After removing a middle part, new token count: {current_tokens}")
            except Exception as e_recount:
                logger_object.error(f"_truncate_prompt_parts: Error re-counting tokens during truncation: {e_recount}. Stopping truncation.", exc_info=True)
                # Return current state of truncation, even if recount failed
                return temp_contents, was_truncated

        contents_for_token_count = system_prompt_part + middle_parts_to_truncate + user_question_part

        # Final check if still over limit (e.g., system + user prompt alone are too big)
        if current_tokens > effective_token_limit:
            logger_object.warning(f"_truncate_prompt_parts: After truncating middle parts, token count ({current_tokens}) might still be over limit. The first/last parts might be too large.")
            # If only system and user parts remain (or just system), and it's still too long,
            # we don't truncate them further here. The API call might fail.
            # A more aggressive strategy could truncate the content of these parts too.
    else:
        logger_object.info(f"_truncate_prompt_parts: Token count {current_tokens} is within the limit. No truncation needed.")

    return contents_for_token_count, was_truncated

def create_gemini_cache(
    api_key: str,
    model_name: str,
    cache_display_name: str,
    system_instruction: str,
    ttl_seconds: int
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Creates or updates a Gemini content cache. Logging is included.

    Args:
        api_key: Gemini API key for the operation.
        model_name: Model name for the cache (e.g., "gemini-1.5-pro-latest").
        cache_display_name: Display name for the cache.
        system_instruction: System instruction/content to cache.
        ttl_seconds: Time-to-live for the cache in seconds.

    Returns:
        Tuple[Optional[genai.CachedContent], Optional[str]]:
            - genai.CachedContent object if successful.
            - Error message string if failed.
    """
    logger.info(f"Starting to create/update content cache. Display Name: '{cache_display_name}', Model: '{model_name}', TTL: {ttl_seconds}s")
    logger.debug(f"API Key ends with: ...{api_key[-4:] if api_key else 'N/A'}, System instruction length: {len(system_instruction)}")

    if not all([api_key, model_name, cache_display_name, system_instruction]):
        msg = "Cache creation failed: API key, model name, cache display name, and content must not be empty."
        logger.error(msg)
        return None, msg

    try:
        logger.debug(f"Configuring genai with API key ...{api_key[-4:]} for cache operation.")
        genai.configure(api_key=api_key)
        ttl_str = f"{ttl_seconds}s"

        # Ensure model name for caching API is correctly formatted
        model_for_caching_api = f"models/{model_name}" if not model_name.startswith("models/") else model_name
        logger.debug(f"Model API name for caching: {model_for_caching_api}")

        logger.info(f"Calling genai.create_cached_content API. Display Name: '{cache_display_name}'")
        # Note: The parameter for the main content might vary (e.g. `system_instruction` or `contents`)
        # depending on the specific version of the Gemini API client library and model.
        # Adjust if `system_instruction` is not the correct parameter name for your genai version.
        cached_content = genai.create_cached_content(
            model=model_for_caching_api,
            display_name=cache_display_name,
            system_instruction=system_instruction,
            # contents=[genai.types.Content(parts=[genai.types.Part(text=system_instruction)])], # Alternative if system_instruction is not direct
            ttl=ttl_str
        )
        logger.info(f"Successfully created/updated cache. Display Name: '{cached_content.display_name}', Full Name: {cached_content.name}, Expires: {cached_content.expire_time}")
        logger.debug(f"Cache object details: {cached_content}")
        return cached_content, None
    except Exception as e:
        logger.error(f"Error creating/updating cache '{cache_display_name}' (Model: {model_name}): {type(e).__name__} - {str(e)}", exc_info=True)
        return None, f"Cache creation/update failed (Model: {model_name}): {type(e).__name__} - {str(e)}"


def list_gemini_caches(api_key: str) -> Tuple[List[Any], Optional[str]]:
    """
    Lists available Gemini content caches. Logging is included.

    Args:
        api_key: Gemini API key for the operation.

    Returns:
        Tuple[List[genai.CachedContent], Optional[str]]:
            - List of genai.CachedContent objects.
            - Error message string if failed.
    """
    logger.info(f"Starting to list Gemini content caches. API Key ends with: ...{api_key[-4:] if api_key else 'N/A'}")
    if not api_key:
        msg = "List caches failed: API key must not be empty."
        logger.error(msg)
        return [], msg
    try:
        logger.debug(f"Configuring genai with API key ...{api_key[-4:]} to list caches.")
        genai.configure(api_key=api_key)
        caches = list(genai.list_cached_contents()) # list_cached_contents() returns an iterator
        logger.info(f"Successfully listed {len(caches)} content caches.")
        if caches:
            for i, c in enumerate(caches):
                logger.debug(f"  Cache {i+1}: DisplayName='{c.display_name}', Name='{c.name}', Model='{c.model}', CreateTime='{c.create_time}', ExpireTime='{c.expire_time}'")
        return caches, None
    except Exception as e:
        logger.error(f"Error listing content caches: {type(e).__name__} - {str(e)}", exc_info=True)
        return [], f"List caches failed: {type(e).__name__} - {str(e)}"

def delete_gemini_cache(api_key: str, cache_name: str) -> Tuple[bool, Optional[str]]:
    """
    Deletes a specified Gemini content cache. Logging is included.

    Args:
        api_key: Gemini API key for the operation.
        cache_name: Full name of the cache to delete (e.g., "cachedContents/...").

    Returns:
        Tuple[bool, Optional[str]]:
            - True if deletion was successful.
            - Error message string if failed.
    """
    logger.info(f"Starting to delete Gemini content cache. Cache Name: '{cache_name}', API Key ends with: ...{api_key[-4:] if api_key else 'N/A'}")
    if not api_key or not cache_name:
        msg = "Delete cache failed: API key and cache name must not be empty."
        logger.error(msg)
        return False, msg
    try:
        logger.debug(f"Configuring genai with API key ...{api_key[-4:]} to delete cache '{cache_name}'.")
        genai.configure(api_key=api_key)
        genai.delete_cached_content(name=cache_name)
        logger.info(f"Successfully deleted content cache: {cache_name}")
        return True, None
    except google.api_core.exceptions.NotFound:
        logger.warning(f"Cache to delete not found: {cache_name}")
        return False, f"Delete failed: Cache '{cache_name}' not found."
    except Exception as e:
        logger.error(f"Error deleting content cache '{cache_name}': {type(e).__name__} - {str(e)}", exc_info=True)
        return False, f"Delete cache '{cache_name}' failed: {type(e).__name__} - {str(e)}"

# if __name__ == "__main__":
    # Simple test (requires Streamlit environment and valid API Key / network connection).
    # Test code here is mainly for demonstration, actual execution requires proper
    # setup of mocked st.session_state and API keys.
    # Assume st.session_state is appropriately initialized (e.g., API keys, active_gemini_key_index)

    # Mock st.session_state
    # class MockSessionState:
    #     def __init__(self):
    #         self._state = {
    #             "active_gemini_key_index": 0,
    #             "gemini_api_key_usage": {}
    #             # "gemini_api_key_1": "YOUR_GEMINI_KEY_1", # Fill in your key
    #             # "gemini_api_key_2": "YOUR_GEMINI_KEY_2"  # Fill in your key
    #         }
    #     def get(self, key, default=None):
    #         return self._state.get(key, default)
    #     def __setitem__(self, key, value):
    #         self._state[key] = value
    #     def __contains__(self, key):
    #         return key in self._state

    # st.session_state = MockSessionState()
    # gemini_keys = [st.session_state.get("gemini_api_key_1",""), st.session_state.get("gemini_api_key_2","")]
    # valid_keys = [k for k in gemini_keys if k]

    # if valid_keys:
    #     logger.info("--- Testing call_gemini_api ---")
    #     # Modify this call according to the new signature for testing
    #     # response, _ = call_gemini_api(
    #     #     prompt_parts=["Hello, Gemini! Introduce yourself."],
    #     #     current_api_key=valid_keys[0],
    #     #     selected_model="gemini-1.0-pro", # or "gemini-1.5-flash-latest"
    #     #     generation_config_dict={"temperature": 0.7}
    #     # )
    #     # print("Gemini API Response:", response)

    #     logger.info("--- Testing Cache Management (requires a valid API key) ---")
    #     test_api_key = valid_keys[0]
    #     cache_model = "gemini-1.0-pro" # Caching is often associated with specific model types

        # logger.info("--- Testing Create Cache ---")
        # new_cache, err = create_gemini_cache(test_api_key, cache_model, "my_test_cache_02", "This is cached test content", 3600)
        # if err: print("Create Cache Error:", err)
        # if new_cache: print("Created Cache:", new_cache.name, new_cache.display_name)

        # logger.info("--- Testing List Caches ---")
        # caches, err = list_gemini_caches(test_api_key)
        # if err: print("List Caches Error:", err)
        # if caches:
        #     print(f"Found {len(caches)} caches:")
        #     for c in caches: print(f"- {c.display_name} ({c.name}), Model: {c.model}")

        # logger.info("--- Testing Delete Cache ---")
        # if new_cache:
        #     cache_to_delete_name = new_cache.name
        #     success, err = delete_gemini_cache(test_api_key, cache_to_delete_name)
        #     if err: print("Delete Cache Error:", err)
        #     if success: print(f"Cache {cache_to_delete_name} deleted successfully.")
        # else:
        #     print("Skipping delete test as no cache was created or name is unknown.")
    # else:
    #     print("Please set valid Gemini API keys in MockSessionState for testing.")
    # pass
