from pydantic import BaseModel, Field, field_validator, model_validator # model_validator for Pydantic v2 root validation
from typing import List, Optional, Dict, Any, Literal

class ChatMessage(BaseModel):
    role: Literal['user', 'assistant', 'system', 'model']
    content: str

class ChatContext(BaseModel):
    chat_history: List[ChatMessage] = Field(default_factory=list, description='Ongoing conversation history')
    file_content: Optional[str] = Field(None, description='Content of an uploaded file, e.g., 善甲狼貼文 for initial analysis')
    external_data: Optional[Dict[str, Any]] = Field(None, description='Fetched external data, e.g., from FRED')
    selected_modules: List[str] = Field(default_factory=list, description='List of selected analysis modules, e.g., ["經濟學家視角"]')

    # New fields based on review:
    date_range_for_analysis: Optional[str] = Field(None, description='Specific date range for analysis, e.g., "2023-W40" or "2023-10-01 to 2023-10-07". Used with initial_analysis trigger.')
    confirmed_sections_for_report: Optional[Dict[str, str]] = Field(None, description='Confirmed sections (A-E) for final report preview. E.g., {"A": "Text for A...", ...}. Used with final_report_preview trigger.')

class ChatRequest(BaseModel):
    user_message: str = Field(description='The latest message/query from the user. For some trigger_actions, this might be supplemental or ignored if dedicated context fields are used.')
    trigger_action: Optional[str] = Field(None, description='Specific action to trigger, e.g., "initial_analysis", "final_report_preview"')
    context: ChatContext = Field(description='The complete context for the AI.')

    # Using model_validator for cross-field validation in Pydantic v2
    @model_validator(mode='after') # 'before' or 'after' depending on when you need to validate
    def validate_trigger_action_dependencies(cls, values: 'ChatRequest') -> 'ChatRequest':
        trigger_action = values.trigger_action
        context = values.context # context is guaranteed to be present as it's not Optional

        if trigger_action == 'initial_analysis':
            if not context.file_content:
                raise ValueError('context.file_content is required for trigger_action="initial_analysis".')
            if not context.date_range_for_analysis:
                raise ValueError('context.date_range_for_analysis is required for trigger_action="initial_analysis".')
        elif trigger_action == 'final_report_preview':
            if not context.confirmed_sections_for_report:
                raise ValueError('context.confirmed_sections_for_report is required for trigger_action="final_report_preview".')
        return values


class ChatResponse(BaseModel):
    reply: str
