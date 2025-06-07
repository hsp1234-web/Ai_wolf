import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig, Tool # Ensure Tool is imported
from app.core.config import settings
from app.schemas.chat_schemas import ChatMessage
from typing import List, Optional, cast, Any, Dict
import structlog
# import json # Not strictly needed for this version of the file if not handling function call responses with JSON

logger = structlog.get_logger(__name__)

class AIServiceError(Exception):
    """Custom exception for AI service-related errors."""
    pass

GEMINI_MODEL_NAME = 'gemini-1.5-flash-latest' # Or 'gemini-pro' or other compatible model

# --- Gemini API Client Configuration ---
try:
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY not in ['YOUR_GEMINI_API_KEY_HERE', 'your_gemini_api_key_from_user']:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info('Gemini API client configured successfully.')
    else:
        logger.warn(
            'GEMINI_API_KEY is not configured or is a placeholder. AI service will be non-functional. '
            'Please set a valid GEMINI_API_KEY in .env or environment variables.'
        )
except Exception as e:
    logger.error('Failed to configure Gemini API client during module load.', error_details=str(e), exc_info=True)

# --- Default Generation Configuration ---
DEFAULT_GENERATION_CONFIG = GenerationConfig(
    temperature=0.7,
    # top_p=0.9, # Often, either temperature or top_p is used. If both, ensure model supports it as expected.
                 # For broad compatibility, might start with just one, e.g., temperature.
                 # Re-adding top_p as it was in the provided code.
    top_p=0.9,
    top_k=40    # Top-k sampling can be combined with temperature or top_p.
)

# --- Default Safety Settings ---
# BLOCK_NONE is highly permissive. This should be reviewed for production.
DEFAULT_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- Startup Log for Safety Settings ---
# This code runs when the module is first imported (usually at app startup).
try:
    all_block_none = all(val == HarmBlockThreshold.BLOCK_NONE for val in DEFAULT_SAFETY_SETTINGS.values())
    if all_block_none:
        logger.critical( # Using CRITICAL level for high visibility
            "GEMINI_AI_SAFETY_SETTINGS_REVIEW_NEEDED", # Structured key for easier log searching/alerting
            message="All harm categories are set to BLOCK_NONE. This is highly permissive and MUST be reviewed before production.",
            safety_settings=str(DEFAULT_SAFETY_SETTINGS) # Log the actual settings for record
        )
    else:
        # Check if at least one category is BLOCK_NONE, which still warrants attention.
        any_block_none = any(val == HarmBlockThreshold.BLOCK_NONE for val in DEFAULT_SAFETY_SETTINGS.values())
        if any_block_none:
            block_none_categories = {
                cat.name: val.name for cat, val in DEFAULT_SAFETY_SETTINGS.items() if val == HarmBlockThreshold.BLOCK_NONE
            }
            logger.warning( # Using WARNING level
                "GEMINI_AI_SAFETY_SETTINGS_REVIEW_ADVISED", # Structured key
                message="Some harm categories are set to BLOCK_NONE. Review these settings carefully.",
                block_none_categories=block_none_categories,
                full_safety_settings=str(DEFAULT_SAFETY_SETTINGS)
            )
except Exception as e:
    # Catch errors during safety logging itself, to not break app startup.
    logger.error("Failed to perform startup logging for AI safety settings.", error_details=str(e), exc_info=True)


def get_ai_chat_completion(
    prompt: Optional[str] = None,
    chat_history: Optional[List[ChatMessage]] = None,
    user_message: Optional[str] = None,
    enable_search: bool = False
) -> str:
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY in ['YOUR_GEMINI_API_KEY_HERE', 'your_gemini_api_key_from_user']:
        logger.error('Gemini API key not configured. Cannot get AI completion.')
        raise AIServiceError('Gemini API key is not configured. AI service is unavailable.')

    active_tools_list: Optional[List[Tool]] = None # Ensure Tool is imported from google.generativeai.types
    if enable_search:
        try:
            # For enabling Google Search (or "Browse" like features in newer models),
            # the SDK might expect a specific Tool object or a string identifier.
            # Using `genai.protos.Tool` and `genai.protos.GoogleSearchRetrieval` is one way for explicit tool definition.
            # Ensure `Tool` is `google.generativeai.types.Tool` if using higher-level abstractions,
            # or `genai.protos.Tool` if building the proto directly. The provided code used protos.
            # Assuming `Tool` from `google.generativeai.types` can wrap protos or has its own way.
            # The example `Tool(google_search_retrieval=...)` implies `Tool` from `google.generativeai.types`
            # might accept protos in its constructor arguments or that `genai.protos.Tool` should be used directly.
            # Let's stick to `genai.protos.Tool` for consistency with the provided code if `Tool` itself doesn't take these as kwargs.

            # Simpler way if SDK supports it (hypothetical, check SDK docs for current best practice):
            # active_tools_list = [Tool.from_google_search()]

            # Using the proto method as in previous step:
            search_tool_proto = genai.protos.Tool(
                 google_search_retrieval=genai.protos.GoogleSearchRetrieval()
            )
            active_tools_list = [search_tool_proto] # List of proto Tool objects
            logger.info('Google Search tool explicitly configured for this AI completion call.')
        except AttributeError as ae: # If genai.protos.Tool or GoogleSearchRetrieval isn't as expected
             logger.warn(f'AttributeError configuring Google Search tool via genai.protos: {ae}. Search may not be available.', exc_info=True)
             active_tools_list = None
        except Exception as e:
            logger.error('Failed to instantiate Google Search tool for Gemini. Search may not be available for this call.', error_details=str(e), exc_info=True)
            active_tools_list = None

    model = genai.GenerativeModel(
        GEMINI_MODEL_NAME,
        generation_config=DEFAULT_GENERATION_CONFIG,
        safety_settings=DEFAULT_SAFETY_SETTINGS,
        tools=active_tools_list # Pass the list of tools
    )

    log_model_config = {"model_name": GEMINI_MODEL_NAME, "search_tool_configured_for_call": bool(active_tools_list)}
    logger.debug("Gemini Model instance created.", **log_model_config)

    try:
        response_text = ''
        gemini_history_content = []

        if chat_history:
            for msg in chat_history:
                role = msg.role.lower()
                if role == 'assistant': role = 'model'
                if role not in ['user', 'model']:
                    logger.debug(f"Skipping message with role '{msg.role}' for Gemini history.")
                    continue
                gemini_history_content.append({'role': role, 'parts': [{'text': msg.content}]})

        final_content_to_send: Any
        log_message_details: Dict[str, Any] = {"search_enabled_flag_for_call": enable_search}

        if user_message:
            final_content_to_send = gemini_history_content + [{'role': 'user', 'parts': [{'text': user_message}]}]
            log_message_details.update({"interaction_type": "chat", "history_length": len(gemini_history_content)})
        elif prompt:
            # If prompt is used, history is usually not passed unless it's a specific combined scenario.
            # For now, assuming prompt means single-turn or history is embedded in prompt.
            final_content_to_send = prompt
            log_message_details.update({"interaction_type": "prompt"})
        else:
            logger.error('Either prompt or user_message must be provided for AI completion.')
            raise ValueError('Invalid arguments: Missing prompt or user_message.')

        logger.info('Sending request to Gemini API.', **log_message_details, **log_model_config)

        response = model.generate_content(
            final_content_to_send
            # `tool_config` can be added here for more control over tool execution if needed
        )

        # Process response, expecting text potentially incorporating search results
        if response.candidates and response.candidates[0].content.parts:
            full_response_parts = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    full_response_parts.append(part.text)
                # Could log other part types if necessary (e.g., function_call, tool_code_parts)
            response_text = ''.join(full_response_parts)

        if not response_text: # Check for blocking or empty response
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason_str = str(response.prompt_feedback.block_reason)
                logger.warn(
                    "AI response was empty due to blocking.",
                    block_reason=block_reason_str,
                    safety_ratings=str(response.prompt_feedback.safety_ratings),
                )
                raise AIServiceError(f"AI content generation blocked: {block_reason_str}. Please revise query or check safety settings.")
            else:
                 logger.warn('AI response received, but no usable text content found and not due to explicit blocking.',
                             candidates_info=str(response.candidates),
                             prompt_feedback_info=str(response.prompt_feedback))

        logger.info('AI completion received.', reply_length=len(response_text))
        return response_text.strip()

    except Exception as e:
        logger.error('Error during Gemini API communication or response processing.', error_details=str(e), exc_info=True)
        raise AIServiceError(f'Failed to get AI completion: {e}')
