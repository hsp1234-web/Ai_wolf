from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.chat_schemas import ChatRequest, ChatResponse, ChatMessage, ChatContext # Ensured ChatContext is imported
from app.services.ai_service import get_ai_chat_completion, AIServiceError
from app.services.prompt_engineering_service import build_initial_analysis_prompt, build_final_report_preview_prompt
from app.core.dependencies import get_current_user
from app.schemas.auth_schemas import User
import structlog
from typing import List, Optional # Added Optional
import re
# import json # No longer needed for parsing sections from user_message for final_report_preview

logger = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/chat",
    tags=["AI Chat"]
)

# Keywords for simple search intent detection
SEARCH_INTENT_KEYWORDS = [
    '幫我查', '查一下', '搜尋', '搜索', 'google一下', '最新', '現在', '股價', '天氣', '匯率', '新聞',
    'what is', 'who is', 'search for', 'find information on', 'latest', 'current', 'price of', 'weather in'
]

def check_for_search_intent(message: str) -> bool:
    """
    Heuristically checks if the user's message likely implies a need for real-time information search.
    """
    msg_lower = message.lower()
    if any(keyword in msg_lower for keyword in SEARCH_INTENT_KEYWORDS):
        return True
    if '?' in message and ('誰' in message or '什麼' in message or '哪裡' in message or '何時' in message or
                           'how ' in msg_lower or 'what ' in msg_lower or 'when ' in msg_lower or 'where ' in msg_lower):
        return True
    return False

@router.post(
    '',
    response_model=ChatResponse,
    tags=['AI Chat'],
    summary='Send a message or context to the AI for a response'
)
async def process_chat_message(
    request_data: ChatRequest, # Pydantic will validate request_data against ChatRequest model
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    trigger_action = request_data.trigger_action
    user_message = request_data.user_message # Still available for logging or general chat
    chat_context = request_data.context     # Now contains specific fields like date_range_for_analysis

    logger.info(
        'Chat request received',
        user_id=user_id,
        trigger_action=trigger_action,
        user_message_length=len(user_message),
        # Log new context fields if present and relevant for this log level
        date_range_for_analysis=chat_context.date_range_for_analysis,
        has_confirmed_sections=bool(chat_context.confirmed_sections_for_report)
    )

    # Pydantic's @model_validator in ChatRequest now handles dependency checks for trigger_action.
    # If the request passes model validation, the required fields for specific actions are guaranteed to be there.

    enable_ai_search = False
    if not trigger_action: # Only enable search for general conversational turns
        if check_for_search_intent(user_message):
            logger.info('Search intent detected in user message. Enabling search tool for AI.', user_id=user_id, user_message=user_message)
            enable_ai_search = True

    try:
        ai_reply_text: str
        prompt_to_send: Optional[str] = None
        history_for_ai: List[ChatMessage] = [
            msg for msg in chat_context.chat_history
            if msg.role.lower() in ['user', 'assistant', 'model']
        ]
        user_message_for_ai: Optional[str] = user_message

        if trigger_action == 'initial_analysis':
            # context.file_content and context.date_range_for_analysis are now guaranteed by Pydantic validator
            prompt_to_send = build_initial_analysis_prompt(
                shan_jia_lang_post=chat_context.file_content,
                date_range=chat_context.date_range_for_analysis,
                external_data=chat_context.external_data,
                selected_modules=chat_context.selected_modules
            )
            history_for_ai = []
            user_message_for_ai = None # Using the fully constructed prompt
            enable_ai_search = False # Typically, specific analysis prompts don't need general search unless designed to
            logger.debug('Built "initial_analysis" prompt using structured context.', user_id=user_id, prompt_length=len(prompt_to_send or ''))

        elif trigger_action == 'final_report_preview':
            # context.confirmed_sections_for_report is guaranteed by Pydantic validator
            prompt_to_send = build_final_report_preview_prompt(
                sections=chat_context.confirmed_sections_for_report
            )
            history_for_ai = []
            user_message_for_ai = None # Using the fully constructed prompt
            enable_ai_search = False # Search not relevant for assembling pre-defined text
            logger.debug('Built "final_report_preview" prompt using structured context.', user_id=user_id, prompt_length=len(prompt_to_send or ''))

        # Call AI Service
        if prompt_to_send is not None:
            ai_reply_text = get_ai_chat_completion(prompt=prompt_to_send, enable_search=enable_ai_search)
        elif user_message_for_ai is not None: # General conversational turn
            ai_reply_text = get_ai_chat_completion(chat_history=history_for_ai, user_message=user_message_for_ai, enable_search=enable_ai_search)
        else:
            # This state should ideally be unreachable due to request validation and logic flow
            logger.error('No valid prompt or (history+user_message) for AI service. Should be caught by validation.', user_id=user_id, trigger_action=trigger_action)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Internal error: Could not determine AI input based on request.')

        logger.info('AI reply generated successfully.', user_id=user_id, reply_length=len(ai_reply_text), search_enabled_for_call=enable_ai_search)
        return ChatResponse(reply=ai_reply_text)

    except AIServiceError as aise:
        logger.error('AIServiceError in chat endpoint.', error_message=str(aise), user_id=user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(aise))
    # Pydantic ValidationErrors (from our custom validator raising ValueError) are automatically handled by FastAPI
    # and typically return a 422 Unprocessable Entity response. So, no specific catch block for ValueError needed here.
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Unexpected error in chat endpoint.', error_details=str(e), user_id=user_id, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'An unexpected error occurred: {str(e)}')
