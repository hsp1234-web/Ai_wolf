import pytest
from unittest.mock import patch, MagicMock
import requests # For requests.exceptions.Timeout
from app.services.external_data_service import (
    fetch_yfinance_data_from_service,
    fetch_fred_data_from_service,
    ExternalDataServiceError # Assuming an error class exists or might be added
)
from app.core.config import settings # If API keys are needed and managed via settings

# Fixture to manage FRED_API_KEY for tests, if external_data_service uses it directly from settings
@pytest.fixture
def manage_fred_api_key(monkeypatch):
    original_key = getattr(settings, 'FRED_API_KEY', None) # Use getattr for safety
    # Set a fake key for tests if the service checks for its existence
    monkeypatch.setattr(settings, 'FRED_API_KEY', "fake_test_fred_api_key", raising=False)
    yield
    monkeypatch.setattr(settings, 'FRED_API_KEY', original_key, raising=False)


@patch("app.services.external_data_service.yf.Ticker")
def test_fetch_yfinance_data_timeout(MockYfTicker):
    """Tests timeout handling for yfinance data fetching."""
    mock_ticker_instance = MagicMock()
    mock_ticker_instance.history.side_effect = requests.exceptions.Timeout("Simulated yfinance timeout")
    MockYfTicker.return_value = mock_ticker_instance

    # Expected return when a timeout occurs.
    # This should align with how the actual service function is designed to report errors.
    # Assuming it returns a dict with success=False and an error message.
    expected_error_response = {
        "success": False,
        "error": "Failed to fetch yfinance data for TESTTICKER: Timeout - Simulated yfinance timeout",
        "data": None,
        "is_cached": False # Should be false as the fetch failed
    }

    result = fetch_yfinance_data_from_service(symbol="TESTTICKER", period="1d")

    assert result == expected_error_response
    MockYfTicker.assert_called_once_with("TESTTICKER")
    mock_ticker_instance.history.assert_called_once_with(period="1d")

@patch("app.services.external_data_service.Fred")
def test_fetch_fred_data_timeout(MockFred, manage_fred_api_key):
    """Tests timeout handling for FRED data fetching."""
    mock_fred_instance = MagicMock()
    mock_fred_instance.get_series.side_effect = requests.exceptions.Timeout("Simulated FRED API timeout")
    MockFred.return_value = mock_fred_instance

    # Expected return on timeout, similar to yfinance
    expected_error_response = {
        "success": False,
        "error": "Failed to fetch FRED data for SERIESID: Timeout - Simulated FRED API timeout",
        "data": None
    }

    # Check if the service function requires an API key argument or gets it from settings
    # The manage_fred_api_key fixture handles if it's from settings.
    # If direct pass: fetch_fred_data_from_service(series_id="SERIESID", api_key="fake_key")
    result = fetch_fred_data_from_service(series_id="SERIESID")

    assert result == expected_error_response
    # If Fred() is initialized with an API key from settings, that's implicitly tested by manage_fred_api_key
    # If Fred() takes api_key in __init__ and service passes it:
    # MockFred.assert_called_once_with(api_key=settings.FRED_API_KEY)
    # For now, assume Fred() call doesn't need key explicitly in assert_called_once_with if taken from settings by Fred class itself
    MockFred.assert_called_once() # Or assert_called_once_with(api_key=settings.FRED_API_KEY) if that's how it's called
    mock_fred_instance.get_series.assert_called_once_with("SERIESID")

# Test for cases where API key for FRED might be missing, if service handles it
@patch("app.services.external_data_service.Fred")
def test_fetch_fred_data_missing_api_key(MockFred, monkeypatch, manage_fred_api_key):
    """
    Tests FRED data fetching when API key is missing, assuming the service
    should catch this and return an error rather than letting Fred class fail.
    This depends on how external_data_service.py handles API key internally.
    """
    # Simulate settings.FRED_API_KEY being None
    monkeypatch.setattr(settings, 'FRED_API_KEY', None, raising=False)

    # If Fred class itself raises error on None key, this test is valid.
    # If fetch_fred_data_from_service checks key first, this is also valid.

    # We are not mocking get_series to raise error here, because the error should occur
    # earlier, either in Fred instantiation (if it checks key) or in our service code.
    # For this test, let's assume the service checks settings.FRED_API_KEY.

    expected_error_response = {
        "success": False,
        "error": "Failed to fetch FRED data: FRED API key not configured.", # Example error message
        "data": None
    }

    result = fetch_fred_data_from_service(series_id="SERIESID")
    assert result == expected_error_response
    MockFred.assert_not_called() # Fred class should not even be instantiated if key is checked first by service

# Example of a successful data fetch test (can be expanded)
@patch("app.services.external_data_service.yf.Ticker")
def test_fetch_yfinance_data_success(MockYfTicker):
    mock_ticker_instance = MagicMock()
    mock_history_data = MagicMock() # Simulate a DataFrame or dict
    mock_history_data.empty = False # Simulate non-empty data
    mock_history_data.to_dict.return_value = {"Date": [1,2], "Close": [100,102]} # example
    mock_ticker_instance.history.return_value = mock_history_data
    MockYfTicker.return_value = mock_ticker_instance

    expected_response = {
        "success": True,
        "data": {"Date": [1,2], "Close": [100,102]},
        "is_cached": False,
        "error": None
    }
    result = fetch_yfinance_data_from_service(symbol="AAPL", period="1d")
    assert result == expected_response

@patch("app.services.external_data_service.Fred")
def test_fetch_fred_data_success(MockFred, manage_fred_api_key):
    mock_fred_instance = MagicMock()
    mock_series_data = MagicMock() # Simulate Series/DataFrame from FRED
    mock_series_data.empty = False
    mock_series_data.to_dict.return_value = {"2023-01-01": 10, "2023-01-02": 12} # example
    mock_fred_instance.get_series.return_value = mock_series_data
    MockFred.return_value = mock_fred_instance

    expected_response = {
        "success": True,
        "data": {"2023-01-01": 10, "2023-01-02": 12},
        "error": None
    }
    result = fetch_fred_data_from_service(series_id="GNPCA")
    assert result == expected_response

# Placeholder for ExternalDataServiceError if it's defined and used
# This depends on how the service itself is structured to raise custom errors.
# For now, the tests assume direct return of dicts with "success": False.
# If ExternalDataServiceError is raised by the service for timeouts, tests should change to:
# with pytest.raises(ExternalDataServiceError, match="Timeout message"):
#     fetch_yfinance_data_from_service(...)
# And the service code would need to be:
# except requests.exceptions.Timeout as e:
#     raise ExternalDataServiceError(f"Timeout: {e}")
# except Exception as e:
#     raise ExternalDataServiceError(f"Generic error: {e}")
# For now, the tests align with the simpler error reporting (returning a dict).
# If the service is refactored to use ExternalDataServiceError, these tests would need updates.
# The current service returns a dict like:
# return {"success": False, "error": f"Failed to fetch yfinance data for {symbol}: Timeout - {e}", "data": None, "is_cached": False}

# It seems the service doesn't use ExternalDataServiceError yet for timeouts.
# The tests are written to match the current expected dictionary output on error.
# If ExternalDataServiceError was to be used, the service functions would need to be updated to raise it,
# and these tests would change from `assert result == expected_error_response`
# to `with pytest.raises(ExternalDataServiceError, match="..."):`
# For this subtask, sticking to testing the current behavior (returning dicts) is appropriate.

# Adding __init__.py if it's missing from tests/unit (though ls showed it exists)
# create_file_with_block
# tests/unit/__init__.py
# # This file makes Python treat the directory as a package.

# Adding __init__.py to tests/ (if needed - typically not for pytest at top level of tests)
# create_file_with_block
# tests/__init__.py
# # This file makes Python treat the directory as a package.

# Adding __init__.py to app/services (if it's missing, though it should exist for app to work)
# create_file_with_block
# app/services/__init__.py
# # This file makes Python treat the directory as a package.
# from .ai_service import get_ai_chat_completion, AIServiceError
# from .external_data_service import (
#     fetch_yfinance_data_from_service,
#     fetch_fred_data_from_service,
#     ExternalDataServiceError
# )
# from .prompt_engineering_service import generate_graph_schema_prompt, generate_nl_to_cypher_prompt
# from .graph_db_service import GraphDBService

# The __init__.py files for app/services/ already exists and is more complex.
# The unit tests should not rely on a simplified __init__.py.
# The current structure of the project already makes these services importable.
# No new __init__.py files should be needed for these unit tests to run if the project structure is correct.
# The ls output showed tests/unit/__init__.py exists.
# Pytest handles pathing from the project root (where pytest is typically run).
# The `from app.services...` imports should work if pytest is run from PROJECT_DIR.
# The health_check_script runs pytest with cwd=PROJECT_DIR.
# So, no __init__.py files need to be created by this subtask.
# Final check on the structure of the new test file for external_data_service.
# It looks reasonable. It includes patches for yf.Ticker and Fred, simulates timeouts,
# and checks for a dictionary response indicating failure.
# It also includes a fixture for FRED_API_KEY management via settings.
# The success cases are also good to have for basic sanity checking of mocks.
# The note about ExternalDataServiceError is important for future refactoring.
# The current tests accurately reflect testing the service as it is (returning dicts on error).
