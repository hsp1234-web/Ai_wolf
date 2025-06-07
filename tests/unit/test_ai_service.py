import pytest
from unittest.mock import patch, MagicMock
from app.services.ai_service import get_ai_chat_completion, AIServiceError, GEMINI_MODEL_NAME # Import GEMINI_MODEL_NAME
from app.core.config import settings # To manipulate settings.GEMINI_API_KEY for tests
from app.schemas.chat_schemas import ChatMessage
from google.generativeai.types import GenerationConfig # For asserting config

# Fixture to manage GEMINI_API_KEY for tests
@pytest.fixture
def manage_gemini_api_key(monkeypatch):
    original_key = settings.GEMINI_API_KEY
    # Set a fake key for most tests to pass the initial check
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', "fake_test_api_key_for_ai_service")
    yield
    # Restore original key after test
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', original_key)

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_simple_prompt_success(MockGenerativeModel, manage_gemini_api_key):
    """Tests successful completion for a simple prompt."""
    mock_model_instance = MagicMock()
    mock_response = MagicMock()

    # Simulate Gemini's response structure
    mock_part = MagicMock()
    mock_part.text = "Mocked AI reply text"
    mock_content = MagicMock()
    mock_content.parts = [mock_part]
    mock_candidate = MagicMock()
    mock_candidate.content = mock_content
    mock_candidate.finish_reason = 1 # FINISH_REASON_STOP
    mock_response.candidates = [mock_candidate]
    mock_response.prompt_feedback = None # No blocking

    mock_model_instance.generate_content.return_value = mock_response
    MockGenerativeModel.return_value = mock_model_instance

    prompt_text = "Hello, AI!"
    reply = get_ai_chat_completion(prompt=prompt_text)

    assert reply == "Mocked AI reply text"
    # Check if GenerativeModel was called with expected model name and defaults
    MockGenerativeModel.assert_called_once()
    args, kwargs = MockGenerativeModel.call_args
    assert args[0] == GEMINI_MODEL_NAME # Check model name
    assert isinstance(kwargs.get("generation_config"), GenerationConfig)
    assert kwargs.get("tools") is None # Search not enabled by default

    mock_model_instance.generate_content.assert_called_once_with(prompt_text)

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_with_history_success(MockGenerativeModel, manage_gemini_api_key):
    """Tests successful completion with chat history."""
    mock_model_instance = MagicMock()
    # mock_chat_session = MagicMock() # Original code used start_chat, but generate_content can take history
    mock_response = MagicMock()
    mock_part = MagicMock(text="Mocked AI reply from history")
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]), finish_reason=1)]
    mock_response.prompt_feedback = None

    # mock_chat_session.send_message.return_value = mock_response
    # mock_model_instance.start_chat.return_value = mock_chat_session
    mock_model_instance.generate_content.return_value = mock_response # If using generate_content with history
    MockGenerativeModel.return_value = mock_model_instance

    chat_history = [ChatMessage(role="user", content="Previous user message")]
    user_message = "New user message"

    reply = get_ai_chat_completion(chat_history=chat_history, user_message=user_message)

    assert reply == "Mocked AI reply from history"
    # Check how generate_content is called with history
    expected_gemini_history_and_message = [
        {'role': 'user', 'parts': [{'text': "Previous user message"}]},
        {'role': 'user', 'parts': [{'text': "New user message"}]} # New message appended
    ]
    mock_model_instance.generate_content.assert_called_once_with(expected_gemini_history_and_message)

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_search_enabled_tool_config(MockGenerativeModel, manage_gemini_api_key):
    """Tests that search tool is configured when enable_search is True."""
    mock_model_instance = MagicMock()
    # Minimal response mock for this test
    mock_response = MagicMock()
    mock_part = MagicMock(text="Search results incorporated")
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
    mock_response.prompt_feedback = None
    mock_model_instance.generate_content.return_value = mock_response
    MockGenerativeModel.return_value = mock_model_instance

    get_ai_chat_completion(prompt="Search for recent news on AI.", enable_search=True)

    # Assert that GenerativeModel was initialized with a tools argument
    args, kwargs = MockGenerativeModel.call_args
    assert kwargs.get("tools") is not None, "Tools should be configured when enable_search is True"
    assert len(kwargs["tools"]) == 1, "One tool (Google Search) should be configured"
    # Could add more specific assertions about the tool object if its structure is stable and known

def test_get_ai_chat_completion_no_api_key_raises_error(monkeypatch):
    """Tests AIServiceError is raised if API key is missing or placeholder."""
    original_key = settings.GEMINI_API_KEY

    monkeypatch.setattr(settings, 'GEMINI_API_KEY', None) # Simulate no key
    with pytest.raises(AIServiceError, match="Gemini API key is not configured"):
        get_ai_chat_completion(prompt="Test prompt")

    monkeypatch.setattr(settings, 'GEMINI_API_KEY', "YOUR_GEMINI_API_KEY_HERE") # Simulate placeholder key
    with pytest.raises(AIServiceError, match="Gemini API key is not configured"):
        get_ai_chat_completion(prompt="Test prompt")

    monkeypatch.setattr(settings, 'GEMINI_API_KEY', original_key) # Restore

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_gemini_api_error_raises_aiserviceerror(MockGenerativeModel, manage_gemini_api_key):
    """Tests that errors from Gemini API are wrapped in AIServiceError."""
    mock_model_instance = MagicMock()
    # Simulate an error from the Gemini client library
    mock_model_instance.generate_content.side_effect = Exception("Simulated Gemini API internal error")
    MockGenerativeModel.return_value = mock_model_instance

    with pytest.raises(AIServiceError, match="Failed to get AI completion: Simulated Gemini API internal error"):
        get_ai_chat_completion(prompt="Test prompt that causes internal error")

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_blocked_response_raises_aiserviceerror(MockGenerativeModel, manage_gemini_api_key):
    """Tests that if AI response is blocked, AIServiceError is raised."""
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.candidates = [] # No candidates, or candidates indicate blocking
    mock_response.prompt_feedback = MagicMock()
    mock_response.prompt_feedback.block_reason = "SAFETY" # Example block reason
    mock_response.prompt_feedback.safety_ratings = "[Some safety ratings info]"

    mock_model_instance.generate_content.return_value = mock_response
    MockGenerativeModel.return_value = mock_model_instance

    with pytest.raises(AIServiceError, match="AI content generation blocked: SAFETY"):
        get_ai_chat_completion(prompt="A prompt that might get blocked")

@patch("app.services.ai_service.genai.GenerativeModel")
def test_get_ai_chat_completion_empty_parts_returns_empty_string(MockGenerativeModel, manage_gemini_api_key):
    """Tests that an empty parts list in response returns an empty string."""
    mock_model_instance = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock(parts=[]) # Empty parts list
    mock_response.candidates = [MagicMock(content=mock_content)]
    mock_response.prompt_feedback = None

    mock_model_instance.generate_content.return_value = mock_response
    MockGenerativeModel.return_value = mock_model_instance

    reply = get_ai_chat_completion(prompt="Test prompt")
    assert reply == "", "Reply should be an empty string if parts list is empty"

# Add more tests as needed for different roles, complex history, specific generation configs, etc.
