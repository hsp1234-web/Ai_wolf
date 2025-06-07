# backend/app/utils/path_manager.py
import os
import sys
# Import settings from the backend config
from ..config import settings # Assuming settings.py contains needed configurations

# Define base paths relative to this file's location (backend/app/utils)
# BACKEND_APP_UTILS_DIR = os.path.dirname(__file__)
# BACKEND_APP_DIR = os.path.dirname(BACKEND_APP_UTILS_DIR) # backend/app
# BACKEND_DIR = os.path.dirname(BACKEND_APP_DIR) # backend

# More robust way to get project root for backend (assuming this file stays in backend/app/utils)
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_APP_DIR = os.path.dirname(CURRENT_FILE_DIR)  # Should be /app
BACKEND_ROOT_DIR = os.path.dirname(BACKEND_APP_DIR) # Should be /backend

# Log directory configuration
# Default log directory name, can be overridden by settings.py if needed
LOG_DIR_NAME = getattr(settings, 'BACKEND_LOG_DIR_NAME', 'logs')
APP_LOG_DIR = os.path.join(BACKEND_ROOT_DIR, LOG_DIR_NAME)

# Log file name, can be overridden by settings.py
DEFAULT_BACKEND_LOG_FILENAME = getattr(settings, 'DEFAULT_BACKEND_LOG_FILENAME', 'backend_app.log')
LOG_FILE_PATH = os.path.join(APP_LOG_DIR, DEFAULT_BACKEND_LOG_FILENAME)

# SOURCE_DOCS_DIR is removed as its backend equivalent is not directly clear
# and should be handled by specific services if needed, possibly configured via settings.py

# Ensure the log directory exists when this module is loaded.
if not os.path.exists(APP_LOG_DIR):
    try:
        os.makedirs(APP_LOG_DIR, exist_ok=True)
        # print(f"PathManager: Log directory {APP_LOG_DIR} created.", file=sys.stdout) # For debugging setup
    except Exception as e:
        # Use print for this critical bootstrap error, as logging might not be fully set up.
        print(f"PathManager Warning: Failed to create log directory {APP_LOG_DIR}: {str(e)}", file=sys.stderr)
# else:
    # print(f"PathManager: Log directory {APP_LOG_DIR} already exists.", file=sys.stdout) # For debugging setup

# print(f"PathManager Debug: CURRENT_FILE_DIR={CURRENT_FILE_DIR}", file=sys.stdout)
# print(f"PathManager Debug: BACKEND_APP_DIR={BACKEND_APP_DIR}", file=sys.stdout)
# print(f"PathManager Debug: BACKEND_ROOT_DIR={BACKEND_ROOT_DIR}", file=sys.stdout)
# print(f"PathManager Debug: APP_LOG_DIR={APP_LOG_DIR}", file=sys.stdout)
# print(f"PathManager Debug: LOG_FILE_PATH={LOG_FILE_PATH}", file=sys.stdout)
