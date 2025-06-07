from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
import uvicorn
import logging # Standard logging

# Assuming settings.py is in backend/app/config
# and path_manager.py, log_utils.py are in backend/app/utils
from app.config import settings # Access LOG_LEVEL, etc.
# Ensure LOG_LEVEL is used from settings, not just APP_LOG_LEVEL which might be a local var
from app.utils.path_manager import LOG_FILE_PATH # Get the configured log file path
from app.utils.log_utils import setup_logging # Import the setup function
from app.api import endpoints_config # Import the new router

# Configure logging as early as possible
# Use log level from settings.LOG_LEVEL if available, otherwise default to INFO
# The LOG_FILE_PATH from path_manager will be used by setup_logging
# Note: settings.LOG_LEVEL was defined as logging.INFO directly
setup_logging(log_level=settings.LOG_LEVEL, log_file_path=LOG_FILE_PATH)

# Get a logger for this module AFTER setup_logging has run
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="後端 API 服務，用於 Ai_wolf 專案的前後端分離架構。",
    version=settings.APP_VERSION
)

# --- CORS Configuration ---
# TODO: Replace "*" with the actual frontend URL in production.
# origins = getattr(settings, "ALLOWED_ORIGINS", ["*"]) # Example if ALLOWED_ORIGINS is in settings
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allow cookies/auth headers if your frontend sends them
    allow_methods=["*"],    # Allow all HTTP methods
    allow_headers=["*"],    # Allow all HTTP headers
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"應用程式 {settings.APP_NAME} v{settings.APP_VERSION} 啟動...")
    logger.info(f"日誌級別設定為: {logging.getLevelName(settings.LOG_LEVEL)}")
    logger.info(f"日誌檔案路徑: {LOG_FILE_PATH}")
    # You can add other startup logic here, e.g., DB connections, loading models

# Include API routers
app.include_router(endpoints_config.router, prefix="/api", tags=["Configuration"])
from app.api import endpoints_data # Import the data router
app.include_router(endpoints_data.router, prefix="/api/data", tags=["Data Fetching"]) # Mount at /api/data
from app.api import endpoints_chat # Import the chat router
app.include_router(endpoints_chat.router, prefix="/api", tags=["Chat"]) # Mount at /api

@app.get("/")
async def read_root():
    logger.info("API CALL: GET / (root)")
    return {"message": f"歡迎來到 {settings.APP_NAME} 後端服務 v{settings.APP_VERSION}！"}

# 允許直接運行 uvicorn (主要用於開發)
if __name__ == "__main__":
    # When running with `python backend/main.py`, Uvicorn's own logging might take over
    # or conflict if not configured carefully. `setup_logging` configures the root logger.
    # Uvicorn also has options for log configuration via command line or programmatically.
    # For development, this setup should be okay. For production, consider Gunicorn + Uvicorn workers
    # and more robust logging configuration.

    # Uvicorn default log level is INFO. Our setup_logging also defaults to INFO.
    # If APP_LOG_LEVEL is DEBUG, our handlers will process DEBUG, but Uvicorn's own messages might still be INFO.
    # This is generally fine for app-level logging.
    uvicorn.run(app, host="0.0.0.0", port=8000)
