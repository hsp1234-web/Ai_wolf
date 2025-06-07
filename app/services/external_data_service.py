import requests
from app.core.config import settings
import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger(__name__)

FRED_API_URL = 'https://api.stlouisfed.org/fred/series/observations'

class ExternalDataError(Exception):
    """Custom exception for errors related to external data fetching."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

def fetch_fred_data(symbol: str, api_key: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Any:
    resolved_api_key = api_key or settings.FRED_API_KEY

    # Prepare params for logging, redacting sensitive parts like api_key
    log_params_for_request = {'series_id': symbol, 'file_type': 'json'}
    if parameters:
        log_params_for_request.update(parameters)
    # Add placeholder for api_key in log_params for clarity, but not the key itself
    log_params_for_request['api_key_present'] = bool(resolved_api_key)

    # Actual parameters to be sent in the request
    actual_request_params = {
        'series_id': symbol,
        'api_key': resolved_api_key, # The actual key is used here
        'file_type': 'json',
    }
    if parameters:
        actual_request_params.update(parameters)

    if not resolved_api_key:
        logger.warn(
            'FRED_API_KEY not configured. Data fetching might fail or be limited for some series.',
            request_params=log_params_for_request # Log the redacted params
        )
        # Policy: try without key, as some FRED series are public. FRED will error if key is needed.

    try:
        logger.info(
            'Fetching data from FRED API.',
            symbol=symbol,
            request_details=log_params_for_request # Log redacted params
        )
        response = requests.get(FRED_API_URL, params=actual_request_params, timeout=15) # Increased timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

        data = response.json()
        observation_count = len(data.get('observations', [])) if isinstance(data.get('observations'), list) else 0
        logger.info(
            'Successfully fetched data from FRED.',
            symbol=symbol,
            observation_count=observation_count
        )
        return data

    except requests.exceptions.HTTPError as http_err:
        status_code_from_err = http_err.response.status_code
        response_text_summary = http_err.response.text[:200] # Log only a summary of response text
        logger.error(
            'HTTP error occurred while fetching FRED data.',
            symbol=symbol,
            status_code=status_code_from_err,
            response_text_summary=response_text_summary,
            error_details=str(http_err)
            # exc_info=True will log stack trace, usually good for unexpected errors.
            # For HTTPError, the status and response text are often primary info.
        )
        raise ExternalDataError(f'FRED API request failed with status {status_code_from_err}. Check logs for details.', status_code=status_code_from_err)

    except requests.exceptions.Timeout as timeout_err:
        logger.error('Timeout occurred while fetching FRED data.', symbol=symbol, timeout_seconds=15, error_details=str(timeout_err))
        raise ExternalDataError(f'Timeout occurred (15s) while fetching data for {symbol} from FRED.', status_code=408)

    except requests.exceptions.RequestException as req_err:
        logger.error(
            'Request exception occurred while fetching FRED data (e.g., connection error).',
            symbol=symbol,
            error_details=str(req_err),
            exc_info=True # Good for unexpected network/request setup issues
        )
        raise ExternalDataError(f'Failed to connect to FRED API or other request error: {req_err}')

    except json.JSONDecodeError as json_err: # If FRED returns non-JSON response unexpectedly
        logger.error(
            'Failed to decode JSON response from FRED API.',
            symbol=symbol,
            error_details=str(json_err),
            response_text_summary=response.text[:200] if 'response' in locals() else "N/A",
            exc_info=True
        )
        raise ExternalDataError(f'Failed to decode JSON response from FRED: {json_err}')

    except Exception as e:
        logger.error(
            'An unexpected error occurred during FRED data fetching.',
            symbol=symbol,
            error_details=str(e),
            exc_info=True
        )
        raise ExternalDataError(f'An unexpected error occurred: {e}')
