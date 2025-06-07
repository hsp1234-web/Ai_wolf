import sqlite3
from pathlib import Path
from app.core.config import settings # Import the settings object
import structlog

logger = structlog.get_logger(__name__)

# DATABASE_FILE is now derived from settings
DATABASE_FILE: Path = settings.DB_FILE_PATH

def get_db_connection() -> sqlite3.Connection:
    try:
        DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        logger.debug('Database connection established', db_file=str(DATABASE_FILE))
        return conn
    except sqlite3.Error as e: # More specific exception for sqlite connection errors
        logger.error('Failed to connect to database', db_file=str(DATABASE_FILE), error=str(e), exc_info=True)
        # Consider raising a custom exception that can be handled by the global error handler
        # For now, re-raising the original or a generic one.
        raise Exception(f"Database connection error: {e}")

def backup_db(backup_filename: str = '') -> Path:
    '''
    Performs an online backup of the main SQLite database.
    The backup is stored in the same directory as the main database.
    If backup_filename is empty, a default name like 'main_database.YYYYMMDD_HHMMSS.backup.db' is used.
    Returns the path to the backup file.
    '''
    import datetime
    if not backup_filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{DATABASE_FILE.stem}.{timestamp}.backup.db"

    backup_file_path = DATABASE_FILE.parent / backup_filename

    conn = None
    bck_conn = None
    try:
        conn = get_db_connection() # This already logs connection success/failure
        logger.info('Starting database backup', source_db=str(DATABASE_FILE), target_backup_db=str(backup_file_path))

        backup_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure target dir exists

        bck_conn = sqlite3.connect(backup_file_path)
        with bck_conn:
            conn.backup(bck_conn)
        logger.info('Database backup completed successfully', backup_path=str(backup_file_path))
        return backup_file_path
    except sqlite3.Error as e:
        logger.error('SQLite error during backup', error=str(e), db_file=str(DATABASE_FILE), backup_path=str(backup_file_path), exc_info=True)
        raise Exception(f'Database backup failed: {e}')
    finally:
        if bck_conn:
            bck_conn.close()
        if conn:
            conn.close()
            logger.debug('Database connection closed after backup attempt', db_file=str(DATABASE_FILE))

def initialize_db():
    conn = None # Ensure conn is defined in the outer scope for finally block
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        logger.info("Initializing database: Checking/creating 'settings' table...", db_file=str(DATABASE_FILE))
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        # Example: Insert a default setting if not present
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('app_version', '0.1.0'))
        conn.commit()
        logger.info("'settings' table initialized/checked successfully.", db_file=str(DATABASE_FILE)) # Adjusted log message slightly for clarity

        # Initialize the cache table
        initialize_cache_table() # Call the new function

    except sqlite3.Error as e:
        logger.error('Failed to initialize database tables', db_file=str(DATABASE_FILE), error=str(e), exc_info=True) # Adjusted log for multiple tables
        # This error could be critical for app startup. Consider how it should be handled.
        # For now, it logs and the app might continue or fail depending on other factors.
    finally:
        if conn:
            conn.close()
            logger.debug('Database connection closed after initialization attempt.', db_file=str(DATABASE_FILE))


# --- External Data Caching Logic ---
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict # Ensure Any and Dict are imported if not already

# Function to create a stable hash from parameters dictionary
def hash_params(params: Dict[str, Any]) -> str: # Ensure Dict, Any are imported at top of file
    # Sort the dict by keys to ensure consistent hash for same params in different order
    sorted_params_json = json.dumps(params, sort_keys=True)
    return hashlib.sha256(sorted_params_json.encode('utf-8')).hexdigest()

def initialize_cache_table():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        logger.info("Initializing database: Checking/creating 'external_data_cache' table...", db_file=str(DATABASE_FILE))
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS external_data_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                params_hash TEXT NOT NULL, -- SHA256 hash of sorted params JSON
                data TEXT NOT NULL,        -- JSON string of the fetched data
                timestamp DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                UNIQUE(source, params_hash)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_source_params_hash ON external_data_cache (source, params_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON external_data_cache (expires_at)')
        conn.commit()
        logger.info("'external_data_cache' table initialized/checked successfully.", db_file=str(DATABASE_FILE))
    except sqlite3.Error as e:
        logger.error('Failed to initialize "external_data_cache" table', db_file=str(DATABASE_FILE), error=str(e), exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed after 'external_data_cache' initialization attempt.", db_file=str(DATABASE_FILE))


def get_cached_data(source: str, params: Dict[str, Any]) -> Any | None:
    params_h = hash_params(params) # Ensure Dict, Any are imported at top of file
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT data, expires_at FROM external_data_cache WHERE source = ? AND params_hash = ?',
            (source, params_h)
        )
        row = cursor.fetchone()
        if row:
            # Ensure column names match how they're accessed (e.g., row['expires_at'] or row[1])
            # sqlite3.Row allows access by column name.
            expires_at_str: str = row['expires_at']
            data_json: str = row['data']

            expires_at = datetime.fromisoformat(expires_at_str)
            # If expires_at was stored as naive UTC, make it timezone-aware for comparison
            if expires_at.tzinfo is None:
                 expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at > datetime.now(timezone.utc):
                logger.debug('Cache hit', source=source, params_hash=params_h)
                return json.loads(data_json)
            else:
                logger.info('Cache expired', source=source, params_hash=params_h, expired_at=expires_at_str)
                # Optional: Delete expired cache entry
                cursor.execute('DELETE FROM external_data_cache WHERE source = ? AND params_hash = ?', (source, params_h))
                conn.commit()
                logger.debug('Expired cache entry deleted', source=source, params_hash=params_h)
                return None
        logger.debug('Cache miss', source=source, params_hash=params_h)
        return None
    except sqlite3.Error as e:
        logger.error('Error retrieving from cache', source=source, params_hash=params_h, error=str(e), exc_info=True)
        return None # On error, treat as cache miss
    except json.JSONDecodeError as e:
        logger.error('Error decoding cached JSON data', source=source, params_hash=params_h, error=str(e), exc_info=True)
        return None # Data corruption, treat as cache miss
    finally:
        if conn:
            conn.close()

DEFAULT_CACHE_TTL_SECONDS = 3600 # 1 hour

def set_cached_data(source: str, params: Dict[str, Any], data: Any, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
    params_h = hash_params(params)
    try:
        data_json = json.dumps(data)
    except TypeError as e:
        logger.error("Failed to serialize data for caching", source=source, params=params, error=str(e), exc_info=True)
        return # Cannot cache non-serializable data

    now_utc = datetime.now(timezone.utc)
    expires_at_utc = now_utc + timedelta(seconds=ttl_seconds)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO external_data_cache (source, params_hash, data, timestamp, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (source, params_h, data_json, now_utc.isoformat(), expires_at_utc.isoformat()))
        conn.commit()
        logger.info('Data cached successfully', source=source, params_hash=params_h, expires_at=expires_at_utc.isoformat())
    except sqlite3.Error as e:
        logger.error('Error saving to cache', source=source, params_hash=params_h, error=str(e), exc_info=True)
    finally:
        if conn:
            conn.close()
