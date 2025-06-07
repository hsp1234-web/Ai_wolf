import os
import shutil
import logging
from datetime import datetime, timezone # Ensure timezone awareness for ISO format
from typing import Tuple

# Assuming settings are correctly imported from app.config
from app.config.settings import AI_DATA_PATH, BACKUP_PATH
# DATABASE_URL might not be needed if we directly construct the source path
# from app.config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

# Define the standard database filename, could also be moved to settings if it might change
DB_FILENAME = "main_database.db"

def backup_database() -> Tuple[bool, str, str | None]:
    """
    Backs up the main application database.

    The source database path is constructed using AI_DATA_PATH and a predefined DB_FILENAME.
    Backups are stored in BACKUP_PATH.

    Returns:
        Tuple[bool, str, Optional[str]]: (success_status, message, backup_file_name)
    """
    source_db_path = os.path.join(AI_DATA_PATH, DB_FILENAME)

    logger.info(f"Attempting to backup database from: {source_db_path}")

    if not os.path.exists(source_db_path):
        msg = f"Database backup failed: Source database file not found at '{source_db_path}'."
        logger.error(msg)
        return False, msg, None

    if not BACKUP_PATH:
        msg = "Database backup failed: BACKUP_PATH is not configured in settings."
        logger.error(msg)
        return False, msg, None

    try:
        os.makedirs(BACKUP_PATH, exist_ok=True)
        logger.info(f"Backup directory ensured: {BACKUP_PATH}")
    except OSError as e:
        msg = f"Database backup failed: Could not create backup directory '{BACKUP_PATH}'. Error: {e}"
        logger.error(msg, exc_info=True)
        return False, msg, None

    # Generate a platform-friendly ISO timestamp (replace colons)
    # Use UTC for consistency
    timestamp_str = datetime.now(timezone.utc).isoformat(timespec='seconds').replace(":", "-")
    backup_file_name = f"{os.path.splitext(DB_FILENAME)[0]}_{timestamp_str}.db"
    backup_file_path = os.path.join(BACKUP_PATH, backup_file_name)

    try:
        shutil.copy2(source_db_path, backup_file_path)
        msg = f"Database backup successful. File saved as '{backup_file_name}' in '{BACKUP_PATH}'."
        logger.info(msg)
        return True, msg, backup_file_name
    except Exception as e:
        msg = f"Database backup failed: Could not copy database file from '{source_db_path}' to '{backup_file_path}'. Error: {e}"
        logger.error(msg, exc_info=True)
        # Attempt to remove partially created backup file if copy failed
        if os.path.exists(backup_file_path):
            try:
                os.remove(backup_file_path)
                logger.info(f"Cleaned up partially created backup file: {backup_file_path}")
            except OSError as remove_err:
                logger.error(f"Failed to clean up partial backup file '{backup_file_path}': {remove_err}")
        return False, msg, None

if __name__ == '__main__':
    # Example usage for direct testing (requires settings to be available)
    # You might need to set up environment variables or a .env file for settings to load.
    # Also, create dummy AI_DATA_PATH and main_database.db for testing.

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Setup for standalone test ---
    # Create dummy directories and file if they don't exist
    if not os.path.exists(AI_DATA_PATH):
        os.makedirs(AI_DATA_PATH, exist_ok=True)
        logger.info(f"Created dummy AI_DATA_PATH: {AI_DATA_PATH}")

    dummy_db_path = os.path.join(AI_DATA_PATH, DB_FILENAME)
    if not os.path.exists(dummy_db_path):
        with open(dummy_db_path, 'w') as f:
            f.write("This is a dummy database file for testing backup.")
        logger.info(f"Created dummy database file: {dummy_db_path}")

    if not BACKUP_PATH:
        # For local testing, if BACKUP_PATH is not in .env, define a default
        # In a real scenario, BACKUP_PATH should be properly configured.
        # temp_backup_path = os.path.join(AI_DATA_PATH, "backups_test") # Example
        # logger.warning(f"BACKUP_PATH not configured, using temporary: {temp_backup_path}")
        # settings.BACKUP_PATH = temp_backup_path # This line won't work as settings are usually read-only after load
        # Instead, ensure your .env or settings provide BACKUP_PATH for testing.
        logger.warning("BACKUP_PATH not set in environment/settings. Standalone test might fail or use defaults.")
        # For this example, let's assume BACKUP_PATH might be defaulted in settings.py if not in .env
    # --- End of setup ---

    # success, message, bk_file = backup_database()
    # print(f"Backup Test Result: Success={success}, Message='{message}', File='{bk_file}'")

    # To run this test:
    # 1. Ensure backend/.env.example has AI_DATA_PATH and BACKUP_PATH defined.
    # 2. Copy backend/.env.example to backend/.env and fill in actual paths if needed.
    # 3. Run from the root of the project: python -m backend.app.services.db_service
    #    (cd backend && python -m app.services.db_service)
    # Make sure AI_DATA_PATH and BACKUP_PATH are writable.
    pass
