from fastapi import APIRouter
import structlog # Add this import

router = APIRouter()
logger = structlog.get_logger(__name__) # Get a logger for this module

@router.get('/health', tags=['Health'])
async def health_check():
    logger.info('Health check endpoint was called', extra_data={'details': 'testing logging'})
    return {'status': 'OK', 'message': 'Logging configured! Check console/logs.'}

@router.get('/error-test', tags=['Test'])
async def trigger_error():
    logger.info('Triggering a test error') # This log should appear
    raise ValueError('This is a deliberate test error for global exception handling.')

@router.get('/api-error-test', tags=['Test'])
async def trigger_api_error():
    from app.core.exceptions import BadRequestError # Import here to avoid circular dependency if exceptions module grows
    logger.info('Triggering a test API specific error (BadRequestError)')
    raise BadRequestError(message='This is a deliberate BadRequestError for testing.')

from fastapi import Depends # Add Depends import
from app.core.dependencies import get_current_user
from app.schemas.auth_schemas import User # For response model or type hint

@router.get('/me', tags=['Users'], response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    '''
    Test endpoint to get current authenticated user's details.
    Requires a valid JWT in the Authorization header.
    '''
    logger.info('Accessing /me endpoint.', user_id=current_user.id)
    return current_user
