import aiosqlite
import logging
import os # For path creation

# Import settings from the correct location
from app.config.settings import DATABASE_URL, AI_DATA_PATH # Assuming settings.py is in app/config

logger = logging.getLogger(__name__)

async def create_tables():
    """
    Asynchronously creates database tables if they don't already exist.
    Ensures that the directory for the SQLite database exists.
    """
    db_path = DATABASE_URL.split("///")[-1] # Gets the path part of the URL
    db_dir = os.path.dirname(db_path)

    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Successfully created database directory: {db_dir}")
        except OSError as e:
            logger.error(f"Error creating database directory {db_dir}: {e}")
            # Depending on the desired behavior, we might want to raise an exception here
            # or let the aiosqlite.connect fail, which it will if the directory doesn't exist.
            return # Exit if directory creation fails

    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS http_cache (
                    key TEXT PRIMARY KEY,
                    response_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires DATETIME
                )
            """)
            await db.commit()
            logger.info("Table 'http_cache' checked/created successfully.")
    except Exception as e:
        logger.error(f"Error during database table creation: {e}")
        # Consider re-raising the exception if startup should halt on DB error
        raise

if __name__ == '__main__':
    # This allows running the script directly for manual initialization if needed.
    # For example, during development or for setting up a new environment.
    import asyncio
    async def main():
        # Basic logging setup for standalone execution
        logging.basicConfig(level=logging.INFO)
        logger.info("Attempting to initialize database schema...")

        # Ensure AI_DATA_PATH exists, as db might be inside it.
        # This is also done in main.py startup, but good for standalone too.
        if AI_DATA_PATH and not os.path.exists(AI_DATA_PATH):
            try:
                os.makedirs(AI_DATA_PATH, exist_ok=True)
                logger.info(f"Successfully created AI_DATA_PATH directory: {AI_DATA_PATH}")
            except OSError as e:
                logger.error(f"Error creating AI_DATA_PATH directory {AI_DATA_PATH}: {e}")
                return

        await create_tables()
        logger.info("Database schema initialization process finished.")

    asyncio.run(main())
