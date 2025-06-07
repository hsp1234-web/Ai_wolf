from fastapi import Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)

class APIBaseException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)

class InternalServerError(APIBaseException):
    def __init__(self, message: str = 'An unexpected internal server error occurred.'):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code='INTERNAL_SERVER_ERROR',
            message=message
        )

class NotFoundError(APIBaseException):
    def __init__(self, message: str = 'Resource not found.'):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code='NOT_FOUND',
            message=message
        )

class BadRequestError(APIBaseException):
    def __init__(self, message: str = 'Bad request.'):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code='BAD_REQUEST',
            message=message
        )

class AuthenticationError(APIBaseException):
    def __init__(self, message: str = 'Authentication failed.'):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code='AUTHENTICATION_FAILED',
            message=message
        )

# Standardized error response model
def create_error_response(code: str, message: str):
    return {'success': False, 'error': {'code': code, 'message': message}}

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        'Unhandled exception caught by global handler',
        exc_info=exc,
        method=str(request.method),
        url=str(request.url)
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            code='INTERNAL_SERVER_ERROR',
            message='An unexpected internal server error occurred. Please contact support.'
        )
    )

async def api_base_exception_handler(request: Request, exc: APIBaseException):
    logger.error(
        'API specific exception caught',
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        method=str(request.method),
        url=str(request.url),
        exc_info=True
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(code=exc.code, message=exc.message)
    )
