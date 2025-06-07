from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import verify_token_and_get_payload
from app.schemas.auth_schemas import User # TokenData is internal to security.py for payload structure if not exposed
from app.core.exceptions import AuthenticationError # Custom exception
import structlog

logger = structlog.get_logger(__name__)

# This scheme will look for an 'Authorization: Bearer <token>' header.
# tokenUrl should point to your login endpoint, prefixed with the main API prefix.
# If your auth router has prefix="/auth" and main app has prefix="/api", then tokenUrl="/api/auth/login".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/login')

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    '''
    Dependency to extract, verify token, and return the current user.
    To be used with routes that require authentication.
    '''
    try:
        payload = verify_token_and_get_payload(token)
        user_id: Optional[str] = payload.get('sub') # 'sub' is the standard claim for subject (user ID)

        if user_id is None:
            # This case should ideally be caught by verify_token_and_get_payload,
            # but double-checking here provides defense in depth.
            logger.warn('Token verification succeeded but subject (sub) missing in payload.', payload=payload)
            raise AuthenticationError(message='Invalid token: Subject (user ID) missing.')

        # In a more complex application, you might fetch user details from a database here using user_id.
        # For this project, the User model is simple and can be constructed directly from the user_id (token subject).
        logger.debug('Current user retrieved from token.', user_id=user_id)
        return User(id=user_id)

    except AuthenticationError as e:
        # Log the specific authentication error that occurred.
        logger.warn(
            'Authentication failed in get_current_user dependency.',
            error_message=e.message,
            token_present=bool(token) # Log if a token was present at all
        )
        # Convert custom AuthenticationError into HTTPException for FastAPI's handling.
        # This ensures the client receives a standard 401 response.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message, # Use the message from the AuthenticationError
            headers={'WWW-Authenticate': 'Bearer'}, # Standard header for Bearer token auth
        )
    except Exception as e:
        # Catch-all for any other unexpected errors during dependency resolution.
        logger.error(
            'Unexpected error in get_current_user dependency.',
            error_message=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while authenticating.",
            headers={'WWW-Authenticate': 'Bearer'},
        )
