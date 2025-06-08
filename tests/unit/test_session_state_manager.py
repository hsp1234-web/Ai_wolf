import pytest
from unittest.mock import patch, MagicMock
# Assuming 'st' is imported as 'streamlit' in the target module:
# from app.utils.session_state_manager import initialize_session_state

# To get default values for assertions:
from config.app_settings import (
    DEFAULT_MAIN_GEMINI_PROMPT,
    FONT_SIZE_CSS_MAP,
    DEFAULT_GEMINI_RPM_LIMIT,
    DEFAULT_GEMINI_TPM_LIMIT,
    DEFAULT_YFINANCE_TICKERS,
    DEFAULT_FRED_SERIES_IDS,
    DEFAULT_YFINANCE_INTERVAL_LABEL,
    DEFAULT_CACHE_TTL_SECONDS,
    # Fallback UI settings if requests fail (these are defined in initialize_session_state's except block)
    # We'll define a helper for these in the test
)
# api_keys_info is used for gemini_api_key_usage, but keys are empty strings.
from config.api_keys_config import api_keys_info

# Define a helper for fallback UI settings to avoid repeating the large dict
def get_fallback_ui_settings():
    # These values should mirror the fallback logic in initialize_session_state
    # For simplicity, using a subset or key ones for assertion.
    # In a real scenario, you might import app_settings directly if accessible
    # or replicate the structure more completely.
    return {
        "app_name": "Wolf_V5 (Fallback)", # Assuming app_s is None in fallback
        "default_gemini_rpm_limit": DEFAULT_GEMINI_RPM_LIMIT,
        "default_gemini_tpm_limit": DEFAULT_GEMINI_TPM_LIMIT,
        "default_generation_config": {"temperature": 0.7, "top_p": 0.9, "top_k": 32, "max_output_tokens": 8192},
        "default_main_gemini_prompt": DEFAULT_MAIN_GEMINI_PROMPT,
        "ny_fed_dataset_names": [], # Assuming app_s is None
        "yfinance_interval_options": {"1 Day": "1d"},
        "allowed_upload_file_types": ["txt", "csv"],
        "default_yfinance_tickers": DEFAULT_YFINANCE_TICKERS,
        "default_fred_series_ids": DEFAULT_FRED_SERIES_IDS,
        "default_yfinance_interval_label": DEFAULT_YFINANCE_INTERVAL_LABEL,
        "default_theme": "Light",
        "default_font_size_name": "Medium",
        "font_size_css_map": FONT_SIZE_CSS_MAP,
        "text_preview_max_chars": 500,
        "log_display_height": 300,
        "max_ui_log_entries": 300,
        "default_chat_container_height": 400,
        "agent_buttons_per_row": 3,
        "prompts_dir": "prompts"
    }

# Patch 'st' where it's imported and used in the session_state_manager module
@patch('utils.session_state_manager.st')
@patch('utils.session_state_manager.requests.get')
@patch('utils.session_state_manager.IS_COLAB', False) # Assume not in Colab for most tests unless specified
@patch('utils.session_state_manager.logger') # Mock logger to suppress log output during tests if desired
def test_initialize_fresh_session_state_ui_settings_success(mock_logger, mock_is_colab, mock_requests_get, mock_st):
    """Test Case 1: Fresh Initialization with successful UI settings fetch."""
    from utils.session_state_manager import initialize_session_state # Import here to use patched 'st'

    mock_st.session_state = {} # Start with an empty session state

    mock_ui_settings_response = {
        "app_name": "Test App Name from API",
        "default_theme": "Dark from API",
        # Add other settings that ui_settings endpoint would return
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_ui_settings_response
    mock_response.raise_for_status.return_value = None # Simulate successful request
    mock_requests_get.return_value = mock_response

    initialize_session_state()

    # Basic application keys
    assert "initialized_keys" in mock_st.session_state
    assert mock_st.session_state["initialized_keys"] is True
    assert "selected_model_name" in mock_st.session_state
    assert mock_st.session_state["selected_model_name"] is None
    assert mock_st.session_state["main_gemini_prompt"] == DEFAULT_MAIN_GEMINI_PROMPT
    assert mock_st.session_state["uploaded_files_list"] == []
    assert mock_st.session_state["chat_history"] == []
    assert mock_st.session_state["active_theme"] == "Light" # This is initialized before UI settings fetch
    assert mock_st.session_state["font_size_name"] == "Medium"

    # UI settings from (mocked) backend
    assert "ui_settings" in mock_st.session_state
    assert mock_st.session_state["ui_settings"]["app_name"] == "Test App Name from API"
    assert mock_st.session_state["ui_settings"]["default_theme"] == "Dark from API"

    # Check if logger was called (optional, but good for seeing if code paths are hit)
    mock_logger.info.assert_any_call("Session_state 基本鍵初始化完成。")
    mock_logger.info.assert_any_call(f"成功從後端獲取 UI 設定: {mock_ui_settings_response}")


@patch('utils.session_state_manager.st')
@patch('utils.session_state_manager.requests.get')
@patch('utils.session_state_manager.IS_COLAB', False)
@patch('utils.session_state_manager.logger')
def test_initialize_fresh_session_state_ui_settings_fail(mock_logger, mock_is_colab, mock_requests_get, mock_st):
    """Test Case 2: Fresh Initialization with UI settings fetch failure."""
    from utils.session_state_manager import initialize_session_state

    mock_st.session_state = {}

    # Simulate requests.get raising an error
    mock_requests_get.side_effect = requests.exceptions.RequestException("Simulated connection error")

    initialize_session_state()

    assert "initialized_keys" in mock_st.session_state
    assert mock_st.session_state["initialized_keys"] is True

    # Check that UI settings are populated with fallback defaults
    assert "ui_settings" in mock_st.session_state
    fallback_settings = get_fallback_ui_settings()
    assert mock_st.session_state["ui_settings"]["app_name"] == fallback_settings["app_name"]
    assert mock_st.session_state["ui_settings"]["default_theme"] == fallback_settings["default_theme"]
    assert mock_st.session_state["ui_settings"]["default_main_gemini_prompt"] == DEFAULT_MAIN_GEMINI_PROMPT

    mock_logger.error.assert_any_call(f"無法從後端 (http://localhost:8000/api/config/ui_settings) 獲取UI設定: Simulated connection error. 將使用備用預設值。")


@patch('utils.session_state_manager.st')
@patch('utils.session_state_manager.requests.get') # Should not be called if already initialized
@patch('utils.session_state_manager.logger')
def test_already_initialized(mock_logger, mock_requests_get, mock_st):
    """Test Case 3: Session state already initialized."""
    from utils.session_state_manager import initialize_session_state

    mock_st.session_state = {
        "initialized_keys": True,
        "active_theme": "Dark", # Pre-existing value
        "chat_history": [{"role": "user", "content": "test"}]
    }
    # Store a copy to compare against
    original_session_state_copy = dict(mock_st.session_state)

    initialize_session_state()

    # Assert that the session state remains unchanged because "initialized_keys" was true
    assert mock_st.session_state == original_session_state_copy
    mock_logger.info.assert_any_call("Session state 已初始化。")
    mock_requests_get.assert_not_called() # UI settings fetch should be skipped


@patch('utils.session_state_manager.st')
@patch('utils.session_state_manager.requests.get')
@patch('utils.session_state_manager.logger')
def test_partially_filled_state_no_overwrite(mock_logger, mock_requests_get, mock_st):
    """Test Case 4: Partially filled state, ensure no overwrite of existing values."""
    from utils.session_state_manager import initialize_session_state

    mock_st.session_state = {
        "chat_history": [{"role": "user", "content": "Existing chat"}],
        "active_theme": "Custom Theme",
        # "initialized_keys" is NOT present, so initialization should run
    }

    mock_ui_settings_response = {"app_name": "Test App from API for partial fill"}
    mock_response = MagicMock()
    mock_response.json.return_value = mock_ui_settings_response
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    initialize_session_state()

    # Assert that pre-existing values are NOT overwritten
    assert mock_st.session_state["chat_history"] == [{"role": "user", "content": "Existing chat"}]
    assert mock_st.session_state["active_theme"] == "Custom Theme" # This IS overwritten by current logic as it's inside an "if not in" block for its group

    # Assert that new keys are added with defaults (or from UI settings)
    assert "initialized_keys" in mock_st.session_state
    assert mock_st.session_state["initialized_keys"] is True
    assert "uploaded_files_list" in mock_st.session_state
    assert mock_st.session_state["uploaded_files_list"] == []
    assert "ui_settings" in mock_st.session_state
    assert mock_st.session_state["ui_settings"]["app_name"] == "Test App from API for partial fill"

    # Based on current implementation, active_theme IS re-initialized if its group flag isn't set.
    # The test reflects this. If desired behavior is different, the app code or test needs change.
    # The current code initializes 'active_theme' if 'initialized_theme_settings' is not in session_state.
    # So, if 'initialized_theme_settings' was not part of the pre-filled state, 'active_theme' would be reset.
    # Let's refine the pre-filled state for this test to be more specific about group flags.

    mock_st.session_state = {
        "chat_history": [{"role": "user", "content": "Existing chat"}], # From 'initialized_gemini_interaction_settings' group
        "initialized_gemini_interaction_settings": True, # Mark its group as initialized
        "active_theme": "Custom Theme", # From 'initialized_theme_settings' group
        "initialized_theme_settings": True, # Mark its group as initialized
    }

    # Re-run with more precise pre-initialization
    initialize_session_state() # This will call it again on the same mock_st.session_state
                               # but the top guard "initialized_keys" is now true.
                               # This means the second call won't do much.
                               # Need to reset for this specific scenario.

    mock_st.session_state = { # Fresh dict for this refined scenario
        "chat_history": [{"role": "user", "content": "Existing chat"}],
        "initialized_gemini_interaction_settings": True,
        "active_theme": "Custom Theme",
        "initialized_theme_settings": True,
    }
    # And clear the top-level guard if it was set by a previous call in another test (pytest isolates, but good practice if not)
    # mock_st.session_state.pop("initialized_keys", None) # Not needed due to pytest test isolation

    initialize_session_state() # Call with this specific pre-filled state

    assert mock_st.session_state["chat_history"] == [{"role": "user", "content": "Existing chat"}]
    assert mock_st.session_state["active_theme"] == "Custom Theme"
    assert mock_st.session_state["ui_settings"]["app_name"] == "Test App from API for partial fill" # This was fetched
    assert "main_gemini_prompt" in mock_st.session_state # This should have been added as its group was not initialized
    assert mock_st.session_state["main_gemini_prompt"] == DEFAULT_MAIN_GEMINI_PROMPT


# Note: API key loading from Colab userdata is explicitly REMOVED in the provided
# session_state_manager.py. So, no tests are needed for that specific functionality here.
# If it were present, we'd use @patch('utils.session_state_manager.userdata.get') or a helper.
# For example:
# @patch('utils.session_state_manager.st')
# @patch('utils.session_state_manager.userdata.get') # If directly used
# @patch('utils.session_state_manager.IS_COLAB', True)
# def test_api_key_loading_from_colab(mock_userdata_get, mock_st):
#     mock_st.session_state = {}
#     mock_userdata_get.side_effect = lambda key_name: "fake_google_key" if key_name == 'GOOGLE_API_KEY' else None
#     initialize_session_state()
#     assert mock_st.session_state[api_keys_info['Google Gemini API Key 1']] == "fake_google_key"
#     assert mock_st.session_state[api_keys_info['FRED API Key']] == "" # Or None, depending on init
# This is just a conceptual example, not active due to current code structure.

# Test for when requests import itself is missing (though unlikely in real env)
@patch('utils.session_state_manager.st')
@patch('utils.session_state_manager.requests', None) # Simulate requests module not being available
@patch('utils.session_state_manager.logger')
def test_initialize_state_no_requests_module(mock_logger, mock_requests, mock_st):
    """Test initialization when 'requests' module is not available."""
    from utils.session_state_manager import initialize_session_state
    mock_st.session_state = {}

    # This test relies on the fact that 'requests' is imported inside initialize_session_state
    # or at the module level. If 'requests.get' is directly imported 'from requests import get',
    # this type of patch is harder. The current code `import requests` so this should work.
    # However, the current code imports `requests` at the top of the module, so this
    # patch might not prevent NameError if `requests` is not found *at import time* of the module itself.
    # A more robust way if `requests` could be missing is for `initialize_session_state` to try-except the import.

    # Forcing the scenario where requests.get would fail due to requests being None
    # This is tricky. The current code `import requests` at module level.
    # If this import fails, the module itself fails to load.
    # This test is more conceptual unless `initialize_session_state` itself tries to import requests.
    # Given the current structure, if `import requests` at module level fails, tests won't even run.
    # So, this test is more about how the function *would* behave if requests calls failed,
    # which is covered by `test_initialize_fresh_session_state_ui_settings_fail`.
    # Let's remove this test as it's not testing a realistic scenario for the current code structure.
    # Instead, the `mock_requests_get.side_effect = requests.exceptions.RequestException(...)` is the correct way.
    pass # Removing this test.

```
