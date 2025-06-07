from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = 'Ai_wolf Backend'
    LOG_LEVEL: str = 'INFO'

    # For direct sqlite3 connection
    DB_FILE_PATH: Path = Path('AI_data/main_database.db')
    # For SQLAlchemy or other ORMs that expect a URL
    # Ensure the path is absolute or relative to a known location if needed by ORM
    DATABASE_URL: str = f"sqlite:///./{DB_FILE_PATH.as_posix()}" # Use as_posix() for cross-platform path strings in URL

    FRED_API_KEY: str | None = None # Optional, for accessing FRED data. Loaded from .env if set.

    GEMINI_API_KEY: str = 'YOUR_GEMINI_API_KEY_HERE' # User must provide this

    JWT_SECRET_KEY: str = 'a_very_secret_and_random_key_please_change_this' # Should be complex, .env will override
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 # As per .env in step 1, this default will be overridden if .env is set

    # model_config is the new way for Pydantic V2 settings (pydantic-settings uses this)
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()

# For debugging purposes (optional, uncomment locally if needed)
# print(f"Settings loaded:")
# print(f"  APP_NAME: {settings.APP_NAME}")
# print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
# print(f"  DB_FILE_PATH: {settings.DB_FILE_PATH}")
# print(f"  DATABASE_URL: {settings.DATABASE_URL}")
# print(f"  GEMINI_API_KEY: {'Set' if settings.GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE' else 'Not Set (Default)'}")
# print(f"  JWT_SECRET_KEY: {'Set (likely from .env)' if settings.JWT_SECRET_KEY != 'a_very_secret_and_random_key_please_change_this' else 'Default (Not Secure)'}")
# print(f"  ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
