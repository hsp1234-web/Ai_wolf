import aiosqlite
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.config.settings import DATABASE_URL

logger = logging.getLogger(__name__)

def generate_cache_key(*args, prefix: str = "cache", **kwargs) -> str:
    """
    Generates a unique cache key based on a prefix, function arguments, and keyword arguments.
    """
    key_parts = [str(prefix)]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()): # Sort kwargs for consistent key generation
        key_parts.append(f"{k}:{v}")

    serialized_parts = "_".join(key_parts)
    return hashlib.md5(serialized_parts.encode('utf-8')).hexdigest()

async def get_cached_data(key: str) -> Optional[Any]:
    """
    Retrieves cached data from the http_cache table if it exists and has not expired.
    """
    db_path = DATABASE_URL.split("///")[-1]
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT response_data, expires FROM http_cache WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()

        if row:
            response_data_str, expires_str = row
            expires_dt = datetime.fromisoformat(expires_str)

            if expires_dt > datetime.now(timezone.utc):
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(response_data_str)
            else:
                logger.debug(f"Cache expired for key: {key}")
                # Optionally, delete expired cache item
                # async with aiosqlite.connect(db_path) as db:
                # await db.execute("DELETE FROM http_cache WHERE key = ?", (key,))
                # await db.commit()
                return None
        else:
            logger.debug(f"Cache miss for key: {key}")
            return None
    except Exception as e:
        logger.error(f"Error getting cached data for key {key}: {e}")
        return None

async def set_cached_data(key: str, data: Any, ttl_seconds: int):
    """
    Stores data into the http_cache table with a specified time-to-live (TTL).
    """
    db_path = DATABASE_URL.split("///")[-1]
    expires_dt = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    expires_str = expires_dt.isoformat()
    timestamp_str = datetime.now(timezone.utc).isoformat()

    try:
        response_data_str = json.dumps(data)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO http_cache (key, response_data, timestamp, expires)
                VALUES (?, ?, ?, ?)
                """,
                (key, response_data_str, timestamp_str, expires_str),
            )
            await db.commit()
            logger.debug(f"Cache set for key: {key}, expires at {expires_str}")
    except Exception as e:
        logger.error(f"Error setting cached data for key {key}: {e}")

async def clear_cache(key: Optional[str] = None):
    """
    Clears a specific cache entry by key, or the entire cache if no key is provided.
    """
    db_path = DATABASE_URL.split("///")[-1]
    try:
        async with aiosqlite.connect(db_path) as db:
            if key:
                await db.execute("DELETE FROM http_cache WHERE key = ?", (key,))
                logger.info(f"Cache cleared for key: {key}")
            else:
                await db.execute("DELETE FROM http_cache")
                logger.info("Entire cache cleared.")
            await db.commit()
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")

# Example Usage (can be removed or kept for testing)
if __name__ == '__main__':
    import asyncio
    logging.basicConfig(level=logging.DEBUG)

    async def test_cache():
        test_key_args = generate_cache_key("users", "get_user", id=1, type="details")
        print(f"Generated key (args): {test_key_args}")

        test_key_kwargs = generate_cache_key(prefix="data", source="yfinance", tickers="AAPL,GOOG", period="1y")
        print(f"Generated key (kwargs): {test_key_kwargs}")

        # Test data
        sample_data = {"name": "Test User", "id": 1, "details": {"email": "test@example.com"}}

        # Set cache
        await set_cached_data(test_key_args, sample_data, ttl_seconds=60)
        print(f"Data set for key: {test_key_args}")

        # Get cache
        retrieved_data = await get_cached_data(test_key_args)
        if retrieved_data:
            print(f"Retrieved data: {retrieved_data}")
            assert retrieved_data == sample_data
        else:
            print("Data not found or expired.")

        # Test expiration
        await set_cached_data("expired_key", {"data": "old_data"}, ttl_seconds=1) # Expires in 1 sec
        print("Set data for 'expired_key', expires in 1 sec.")
        await asyncio.sleep(2)
        expired_retrieved = await get_cached_data("expired_key")
        if expired_retrieved:
            print(f"ERROR: Retrieved expired data: {expired_retrieved}")
            assert expired_retrieved is None
        else:
            print("'expired_key' data correctly not retrieved or expired.")

        await clear_cache(test_key_args)
        print(f"Cache cleared for key: {test_key_args}")
        retrieved_data_after_clear = await get_cached_data(test_key_args)
        assert retrieved_data_after_clear is None
        print(f"Data for {test_key_args} is None after clearing: {retrieved_data_after_clear is None}")

        # To run this test, ensure your DATABASE_URL is correctly configured in settings
        # and the init_db.py script has been run to create the table.
        # Example: AI_DATA_PATH=./AI_data DATABASE_URL=sqlite+aiosqlite:///./AI_data/test_cache.db python backend/app/db/cache_manager.py
        # Don't forget to create ./AI_data directory if it doesn't exist or if DATABASE_URL points there.
        # Also, you might need to adjust PYTHONPATH or run as a module if imports fail:
        # (cd backend && AI_DATA_PATH=./AI_data DATABASE_URL=sqlite+aiosqlite:///./AI_data/test_cache.db python -m app.db.cache_manager)

    # Create dummy db and table for standalone test if db doesn't exist
    # This is a simplified version of init_db for the sake of this standalone test.
    async def init_dummy_db_for_test():
        from app.db.init_db import create_tables as init_actual_tables
        # Ensure AI_DATA_PATH exists if db is there
        ai_data_dir = DATABASE_URL.split("///")[-1].rsplit('/',1)[0]
        if ai_data_dir and not os.path.exists(ai_data_dir):
            os.makedirs(ai_data_dir, exist_ok=True)
        await init_actual_tables()

    # asyncio.run(init_dummy_db_for_test()) # Ensure DB is ready
    # asyncio.run(test_cache())
    # Commenting out direct execution for now to prevent issues in automated runs
    # For manual testing, uncomment the above two lines and ensure DATABASE_URL and AI_DATA_PATH are set.
    pass
