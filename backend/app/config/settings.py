# backend/app/config/settings.py
import os
from dotenv import load_dotenv
import logging # For LOG_LEVEL

# --- General App Settings ---
APP_NAME = "Ai_wolf Backend"
APP_VERSION = "0.1.0" # Application version
LOG_LEVEL = logging.INFO # Default log level for the application
# To change log level via environment variable, you could use:
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)
LOG_FILE = os.getenv("LOG_FILE") # If None, logging might go to stderr or as configured by root logger
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 1024 * 1024 * 10)) # Default 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5)) # Default 5 backup files


# --- API Key and Path Loading ---
# Path to the .env file (expected to be in the 'backend' directory, one level up from 'app')
# settings.py is in backend/app/config/
# .env is in backend/
# So, go up three levels from settings.py to the root of 'backend', then select '.env'.
# Correction: dirname(__file__) is .../backend/app/config
# dirname(dirname(__file__)) is .../backend/app
# dirname(dirname(dirname(__file__))) is .../backend
DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(DOTENV_PATH)

# Database and File Paths
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./AI_data/main_database.db")
AI_DATA_PATH = os.getenv("AI_DATA_PATH", "./AI_data")
BACKUP_PATH = os.getenv("BACKUP_PATH", "./AI_data/backups")

# Gemini API Keys
# Loads a comma-separated string of keys from .env and splits them into a list
GEMINI_API_KEYS_STR = os.getenv("GEMINI_API_KEYS", "")
AVAILABLE_GEMINI_API_KEYS = [key.strip() for key in GEMINI_API_KEYS_STR.split(',') if key.strip()]

# FRED API Key
FRED_API_KEY = os.getenv("FRED_API_KEY")

# --- Gemini API Configuration ---
DEFAULT_MODEL_NAME = "models/gemini-1.5-pro-latest" # Default model for the application
TOKEN_SAFETY_FACTOR = 0.90 # Safety factor for calculating effective token limit for prompts
DEFAULT_GEMINI_RPM_LIMIT = 3  # Default RPM for a single key, useful for client-side awareness or future server-side limiting
DEFAULT_GEMINI_TPM_LIMIT = 100000 # Default TPM for a single key

DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 32,
    "max_output_tokens": 8192
}

# --- Prompts ---
# PROMPTS_DIR could be relative to the app directory, e.g., 'app/prompts'
# For use within backend services, direct path construction might be better.
# Example: os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts') # app/prompts
PROMPTS_DIR_NAME = "prompts" # Name of the prompts directory within 'app'

DEFAULT_MAIN_GEMINI_PROMPT = """
請作為一個多才多藝的AI助理，根據我提供的上下文資訊（如上傳的檔案內容、外部數據源的數據）和我的問題，提供精確且有深度的回答。
請確保你的回答不僅僅是重複資訊，而是能提供洞察、分析或創造性的內容。
如果涉及到數據分析，請清晰地展示你的分析過程和結果。
如果需要，請向我提問以澄清我的需求。
"""

# --- Cache Settings ---
# These TTLs were used by st.cache_data. Backend might use different caching strategies.
# Retaining them here if any backend caching logic might want to refer to them.
YFINANCE_CACHE_TTL_SECONDS = 3600
FRED_CACHE_TTL_SECONDS = 86400
DEFAULT_CACHE_TTL_SECONDS = 3600 # General default

# --- Data Fetcher Defaults (can be used by API endpoints) ---
DEFAULT_YFINANCE_TICKERS = "SPY, ^GSPC, BTC-USD, ETH-USD"
DEFAULT_FRED_SERIES_IDS = "GDP,CPIAUCSL"
NY_FED_REQUEST_TIMEOUT_SECONDS = 30

# --- External Service URLs & Configs for Data Fetchers (already migrated) ---
NY_FED_POSITIONS_URLS = [
    {
        "name": "SOMA Holdings (Securities Held Outright)",
        "url": "https://markets.newyorkfed.org/api/soma/summary.xml",
        "type": "xml"
    },
    {
        "name": "Agency MBS Holdings (Agency Mortgage-Backed Securities)",
        "url": "https://markets.newyorkfed.org/api/ambs/all/summary.xml",
        "type": "xml"
    }
]

SBP_XML_SUM_COLS_CONFIG = {
    "soma/summary": ["currentFaceValue", "parValue"],
    "ambs/all/summary": ["currentFaceValue", "parValue"],
    # Fallback or general key if needed, though specific is better
    'summary': ['Current Face Value', 'Par Value'],
}

# Add other backend-specific settings here as needed
# For example:
# MAX_FILE_UPLOAD_SIZE_MB = 100
# CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8501"] # If frontend is served from these
ALLOWED_ORIGINS = [
    "http://localhost:3000", # Next.js frontend default
    "http://localhost:8501", # Streamlit default (if used for any auxiliary UI)
    # Add production frontend URLs here
]

# --- Path Configs (defaults used by path_manager if not set here) ---
# BACKEND_LOG_DIR_NAME = "logs" # Default is 'logs' in path_manager
# DEFAULT_BACKEND_LOG_FILENAME = "backend_app.log" # Default is 'backend_app.log' in path_manager
