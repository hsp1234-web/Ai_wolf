from fastapi import APIRouter, HTTPException, status
from app.core.security import create_access_token
from app.schemas.auth_schemas import LoginRequest, Token, User
from app.core.exceptions import AuthenticationError # Using custom AuthenticationError
from app.core.config import settings
import structlog
import hashlib # For creating a user ID from API key

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _is_api_key_placeholder(api_key: str) -> bool:
    """Checks if the API key is one of the known default placeholders."""
    placeholders = [
        "YOUR_GEMINI_API_KEY_HERE", # From initial config.py
        "your_gemini_api_key_from_user" # From initial .env
    ]
    if settings.GEMINI_API_KEY in placeholders and api_key == settings.GEMINI_API_KEY:
        # If the currently configured GEMINI_API_KEY in settings is a placeholder itself,
        # and the provided key matches it, then it's a placeholder.
        return True
    return api_key in placeholders


def verify_gemini_api_key(api_key: str) -> bool:
    '''
    MOCK VERIFICATION: Checks if the API key is not empty and not a known placeholder.
    In a real scenario, this would involve a call to Google's API or a more robust check.
    '''
    if not api_key:
        logger.warn('Gemini API key validation failed: Key is empty.')
        return False

    if _is_api_key_placeholder(api_key):
        logger.warn('Gemini API key validation failed: Using a known placeholder key.')
        return False

    # MOCK: For demonstration, any other non-empty key is considered valid.
    # In a real application, you would:
    # 1. Call the Gemini API with this key (e.g., a simple list_models call).
    # 2. If the call succeeds, the key is valid. If it fails with an authentication error, it's invalid.
    # This mock assumes any non-placeholder, non-empty key is valid.
    logger.info('Gemini API key validation successful (MOCK).', key_suffix=api_key[-4:] if len(api_key) >=4 else api_key)
    return True


@router.post('/login', response_model=Token)
async def login_for_access_token(form_data: LoginRequest):
    submitted_api_key = form_data.apiKey
    logger.info('Login attempt received.', provided_key_suffix=submitted_api_key[-4:] if len(submitted_api_key) >= 4 else submitted_api_key)

    if not verify_gemini_api_key(submitted_api_key):
        logger.warn('Login failed: Invalid Gemini API Key provided for login.')
        # Use the custom AuthenticationError, which will be handled by api_base_exception_handler
        raise AuthenticationError(message='Invalid Gemini API Key provided.')

    # Create a unique but stable user ID from the API key (e.g., a hash).
    # This is for the 'user' object in the token response and the 'sub' claim in JWT.
    # IMPORTANT: Do NOT store or log the raw API key. Only use its hash for identification.
    # Using SHA256 for hashing.
    user_id_hash = hashlib.sha256(submitted_api_key.encode('utf-8')).hexdigest()

    # Create a user object. The ID is derived from the API key's hash.
    # This ID will be the subject ('sub') of the JWT.
    user_data = User(id=f"user_{user_id_hash[:16]}") # Use a shortened part of the hash for the user ID if desired

    # Create JWT
    # The 'sub' (subject) of the JWT should be this user_data.id or another stable identifier.
    access_token = create_access_token(data={'sub': user_data.id})

    logger.info('Login successful, token generated.', user_id=user_data.id)
    return Token(access_token=access_token, user=user_data)
