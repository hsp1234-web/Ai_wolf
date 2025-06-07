from fastapi import APIRouter, Depends, HTTPException, status
from app.db.database import backup_db # backup_db function from your database module
from app.schemas.db_management_schemas import BackupResponse
from app.core.dependencies import get_current_user # To protect the endpoint
from app.schemas.auth_schemas import User # For current_user type hint
# from app.core.config import settings # Not directly needed if backup_db uses settings internally for path
import structlog
# from pathlib import Path # Not directly needed if backup_db handles path logic
# import datetime # Not directly needed if backup_db handles timestamping

logger = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/db",  # This router's prefix
    tags=["Database Management"]
)

@router.post(
    '/backup',
    response_model=BackupResponse,
    summary='Perform an online backup of the SQLite database.',
    description='Triggers an online (atomic) backup of the main application database. '
                'The backup file will be stored in the database directory, typically with a timestamp. '
                'Requires user to be authenticated.'
)
async def trigger_database_backup(current_user: User = Depends(get_current_user)):
    logger.info('Database backup requested.', user_id=current_user.id)
    try:
        # The backup_db function from app/db/database.py is expected to handle
        # the logic of creating a timestamped backup filename and performing the backup.
        # It should return the Path object to the backup file.
        backup_file_path = backup_db()

        logger.info(
            'Database backup successful.',
            backup_path=str(backup_file_path),
            user_id=current_user.id
        )
        return BackupResponse(
            success=True,
            message='Database backup completed successfully.',
            backup_path=str(backup_file_path) # Ensure path is converted to string for JSON response
        )
    except Exception as e:
        # This catches exceptions raised by backup_db (e.g., sqlite3.Error, or custom ones)
        logger.error(
            'Database backup failed during operation.',
            error_message=str(e),
            user_id=current_user.id,
            exc_info=True # Include traceback in logs
        )
        # Return a 500 Internal Server Error to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Database backup failed: {str(e)}'
        )
