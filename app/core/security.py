from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
# from passlib.context import CryptContext # Not used for API key login
from app.core.config import settings
from app.core.exceptions import AuthenticationError
import structlog

logger = structlog.get_logger(__name__)

# pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto') # Not used

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY # Loaded from .env via pydantic settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add 'iat' (issued at) claim
    to_encode.update({'exp': expire, 'iat': datetime.now(timezone.utc)})

    # Ensure SECRET_KEY is appropriate (bytes or string based on jose version/expectation)
    # Typically, it should be a string.
    if not isinstance(SECRET_KEY, str) or not SECRET_KEY:
        logger.error("JWT_SECRET_KEY is not configured properly. It must be a non-empty string.")
        # This is a server configuration error, should ideally stop the process or raise a critical alert.
        # For now, to prevent insecure operation:
        raise ValueError("JWT_SECRET_KEY is not configured. Cannot create token.")

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug("Access token created.", subject=data.get("sub"))
    return encoded_jwt

def verify_token_and_get_payload(token: str) -> dict[str, Any]:
    if not token:
        raise AuthenticationError(message='No token provided.')
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id: Optional[str] = payload.get('sub')
        if user_id is None:
            logger.warn("Token verification failed: Subject (sub) missing in token payload.", token_payload=payload)
            raise AuthenticationError(message='Token missing subject (sub) claim.')

        # Check for expiration ('exp' claim is automatically handled by jwt.decode)
        # Optionally, check 'iat' (issued at) if you want to enforce token age limits beyond 'exp'

        logger.debug("Token successfully verified.", subject=user_id)
        return payload
    except jwt.ExpiredSignatureError:
        logger.warn("Token verification failed: Expired signature.", token_provided=bool(token))
        raise AuthenticationError(message='Token has expired.')
    except JWTError as e:
        logger.warn("Token verification failed: JWTError.", error_details=str(e), token_provided=bool(token))
        raise AuthenticationError(message=f'Could not validate credentials: {e}')
    except Exception as e: # Catch any other unexpected error during decode
        logger.error("Unexpected error during token verification.", error_details=str(e), exc_info=True)
        raise AuthenticationError(message=f'Token verification failed due to an unexpected error.')

# Password hashing functions (not used for API key login, but kept for potential future use)
# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)
