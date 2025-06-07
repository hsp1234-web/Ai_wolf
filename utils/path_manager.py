# utils/path_manager.py
import os
import sys
from config import app_settings
from config.app_settings import DEFAULT_LOG_FILENAME # Import specific setting

IN_COLAB = 'google.colab' in sys.modules

def get_base_data_dir():
    """獲取 Wolf_Data 的基礎路徑 (本地或 Colab Drive)"""
    if IN_COLAB:
        return os.path.join(app_settings.COLAB_DRIVE_BASE_PATH, app_settings.BASE_DATA_DIR_NAME)
    else:
        return os.path.join(os.path.expanduser(app_settings.USER_HOME_DIR), app_settings.BASE_DATA_DIR_NAME)

BASE_DATA_DIR = get_base_data_dir()
APP_LOG_DIR = os.path.join(BASE_DATA_DIR, app_settings.APP_LOG_DIR_NAME)
LOG_FILE_PATH = os.path.join(APP_LOG_DIR, app_settings.DEFAULT_LOG_FILENAME) # Use setting for filename
SOURCE_DOCS_DIR = os.path.join(BASE_DATA_DIR, app_settings.SOURCE_DOCUMENTS_DIR_NAME)

# Ensure the log directory exists when this module is loaded
# This is a side effect, but common for path management modules that define log paths
if not os.path.exists(APP_LOG_DIR):
    try:
        os.makedirs(APP_LOG_DIR, exist_ok=True)
    except Exception as e:
        # In a library module, direct print or st.error is not ideal.
        # Consider logging or raising an error if critical.
        # For now, let's print a warning to stderr for critical infra like logging.
        print(f"Warning: Failed to create log directory {APP_LOG_DIR} from path_manager: {str(e)}", file=sys.stderr)

# Add __init__.py to utils if it doesn't exist, to make it a package
# This step will be done by running a bash command later.
