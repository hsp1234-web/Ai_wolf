# wolf_debugger.py
import os
import sys
import time
import logging
# Mock colab modules for local testing if needed - Colab will use its own
try:
    from google.colab import drive, userdata
except ImportError:
    class MockDrive:
        def mount(self, *args, **kwargs): print("MockDrive: mount called.")
    class MockUserdata:
        def get(self, key):
            print(f"MockUserdata: get called for {key}.")
            # Example: use env var for local test, Colab will use its secrets
            if key == 'GOOGLE_API_KEY': return os.environ.get('TEST_GEMINI_KEY')
            if key == 'FRED_API_KEY': return os.environ.get('TEST_FRED_KEY')
            raise self.SecretNotFoundError()
        class SecretNotFoundError(Exception): pass
    drive = MockDrive()
    userdata = MockUserdata()
    print("Warning: google.colab modules not found. Using mocks. (Normal if not in Colab)")

# Import heavy libraries, handling potential ImportErrors
try:
    import google.generativeai as genai
    import yfinance as yf
    import pandas as pd
    from fredapi import Fred
    import requests
except ImportError as e:
    # Log this in a way that's visible if the script is run directly or if logging is already set up
    print(f"CriticalImportWarning: One or more libraries (genai, yf, pd, fredapi, requests) not found: {e}. Some tests will fail.")

# Global defaults, will be updated by initialize_paths
LOG_FILE_PATH = "/content/wolfAI/logs/streamlit.log"
GDRIVE_PROJECT_DIR = None
APP_PY_PATH = None
PROJECT_BASE_DIR = "/content/wolfAI"

logging_configured = False

def setup_logging(log_file_path_to_use):
    global logging_configured
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]: # Clear existing handlers
        root_logger.removeHandler(handler)
        handler.close()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path_to_use, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Output to console (and Colab cell output)
        ]
    )
    logging_configured = True # Mark logging as configured
    logging.info(f"Log system initiated. Log file at: {log_file_path_to_use}")

def initialize_paths(use_gdrive=False, project_dir_name="wolfAI"):
    global GDRIVE_PROJECT_DIR, APP_PY_PATH, PROJECT_BASE_DIR, LOG_FILE_PATH
    actual_log_dir = "" # Initialize with a valid string

    if use_gdrive:
        try:
            drive.mount('/content/drive', force_remount=True)
            GDRIVE_PROJECT_DIR = f"/content/drive/MyDrive/{project_dir_name}"
            PROJECT_BASE_DIR = GDRIVE_PROJECT_DIR
            actual_log_dir = os.path.join(GDRIVE_PROJECT_DIR, "logs")
        except Exception as e:
            # Do not log here yet as logging might not be set up. Store error for later.
            # drive_mount_error = e
            GDRIVE_PROJECT_DIR = None # Fallback
            PROJECT_BASE_DIR = f"/content/{project_dir_name}"
            actual_log_dir = os.path.join(PROJECT_BASE_DIR, "logs")
    else:
        PROJECT_BASE_DIR = f"/content/{project_dir_name}"
        actual_log_dir = os.path.join(PROJECT_BASE_DIR, "logs")

    if not os.path.exists(PROJECT_BASE_DIR): os.makedirs(PROJECT_BASE_DIR, exist_ok=True)
    if actual_log_dir and not os.path.exists(actual_log_dir): os.makedirs(actual_log_dir, exist_ok=True)

    LOG_FILE_PATH = os.path.join(actual_log_dir, "streamlit.log")
    APP_PY_PATH = os.path.join(PROJECT_BASE_DIR, "app.py")

    # Crucially, setup logging AFTER all paths are defined.
    if not logging_configured : setup_logging(LOG_FILE_PATH)

    logging.info(f"Project base directory: {PROJECT_BASE_DIR}")
    if use_gdrive:
        if GDRIVE_PROJECT_DIR: logging.info(f"Google Drive successfully mounted. Path: {GDRIVE_PROJECT_DIR}")
        else: logging.error(f"Google Drive mount requested but failed. Using local: {PROJECT_BASE_DIR}")
    else:
        logging.info(f"Google Drive not used. Using local path: {PROJECT_BASE_DIR}")


gemini_api_key_global = None
fred_api_key_global = None

def check_env_and_packages():
    logging.info("--- [Test 1/8] Checking Python environment and key packages ---")
    all_ok = True
    try: logging.info(f"Python Version: {sys.version.splitlines()[0]}")
    except Exception as e: logging.error(f"Error getting Python version: {e}"); all_ok = False

    try: import streamlit as st_check; logging.info(f"Streamlit Version: {st_check.__version__}")
    except ImportError as e: logging.error(f"Streamlit not found: {e}"); all_ok = False

    try: import google.generativeai as genai_check; logging.info(f"google-generativeai Version: {genai_check.__version__}")
    except ImportError as e: logging.error(f"google.generativeai not found: {e}"); all_ok = False

    try: import yfinance as yf_check; logging.info(f"yfinance Version: {yf_check.__version__}")
    except ImportError as e: logging.error(f"yfinance not found: {e}"); all_ok = False

    try: import pandas as pd_check; logging.info(f"pandas Version: {pd_check.__version__}")
    except ImportError as e: logging.error(f"pandas not found: {e}"); all_ok = False

    try: from fredapi import Fred as Fred_check_import; logging.info(f"fredapi imported successfully.")
    except ImportError as e: logging.error(f"fredapi not found: {e}"); all_ok = False

    try: import requests as req_check; logging.info(f"requests Version: {req_check.__version__}")
    except ImportError as e: logging.error(f"requests not found: {e}"); all_ok = False

    if all_ok: logging.info("Test 1 Result: Success. Key packages appear to be available.")
    else: logging.error("Test 1 Result: Failed. One or more key packages are missing.")
    return all_ok

def check_project_structure():
    logging.info(f"--- [Test 2/8] Checking project structure ---")
    logging.info(f"Verifying project directory: {PROJECT_BASE_DIR}")

    if os.path.isdir(PROJECT_BASE_DIR):
        logging.info(f"Project directory exists: {PROJECT_BASE_DIR}.")
        if os.path.isfile(APP_PY_PATH):
            logging.info(f"Main application file 'app.py' found at: {APP_PY_PATH}.")
            logging.info("Test 2 Result: Success. Project structure appears correct.")
            return True
        else:
            logging.warning(f"Main application file 'app.py' not found at: {APP_PY_PATH}. Server mode may fail.")
            return "app_not_found" # String to indicate partial success/warning
    else:
        logging.error(f"Project directory does not exist: {PROJECT_BASE_DIR}.")
        return False

def get_api_keys_with_input_option():
    global gemini_api_key_global, fred_api_key_global
    logging.info("--- [Test 3/8] Checking API key access (Colab Secrets) ---")
    gemini_api_key_global = None; fred_api_key_global = None # Reset

    try: gemini_api_key_global = userdata.get('GOOGLE_API_KEY'); logging.info("Successfully read 'GOOGLE_API_KEY' from Colab Secrets.")
    except userdata.SecretNotFoundError: logging.warning("'GOOGLE_API_KEY' not found in Colab Secrets.")
    except Exception as e: logging.warning(f"Error reading 'GOOGLE_API_KEY': {e}.")

    try: fred_api_key_global = userdata.get('FRED_API_KEY'); logging.info("Successfully read 'FRED_API_KEY' from Colab Secrets.")
    except userdata.SecretNotFoundError: logging.warning("'FRED_API_KEY' not found in Colab Secrets.")
    except Exception as e: logging.warning(f"Error reading 'FRED_API_KEY': {e}.")

    if not gemini_api_key_global or not fred_api_key_global:
        logging.info("Hint: Store API keys in Colab Secrets (Key icon) named 'GOOGLE_API_KEY' and 'FRED_API_KEY'.")
        provide_now_decision = ""
        try: provide_now_decision = input("One or more API keys missing. Enter them now? (yes/no): ").strip().lower()
        except Exception as e: logging.error(f"Error reading user input (non-interactive?): {e}.")
        if provide_now_decision == 'yes':
            if not gemini_api_key_global:
                try:
                    gemini_input = input("Enter Google Gemini API Key: ").strip()
                    if gemini_input: gemini_api_key_global = gemini_input; logging.info("Received one-time Gemini key.")
                    else: logging.warning("No Gemini key provided.")
                except Exception as e: logging.error(f"Error reading Gemini key input: {e}.")
            if not fred_api_key_global:
                try:
                    fred_input = input("Enter FRED API Key: ").strip()
                    if fred_input: fred_api_key_global = fred_input; logging.info("Received one-time FRED key.")
                    else: logging.warning("No FRED key provided.")
                except Exception as e: logging.error(f"Error reading FRED key input: {e}.")
        else: logging.info("Skipping manual API key entry. Some tests may be skipped.")

    if gemini_api_key_global and fred_api_key_global: logging.info("Test 3 Result: All API keys ready."); return True
    elif gemini_api_key_global: logging.warning("Test 3 Result: Only Gemini key available. FRED tests skipped."); return "gemini_only"
    elif fred_api_key_global: logging.warning("Test 3 Result: Only FRED key available. Gemini tests skipped."); return "fred_only"
    else: logging.error("Test 3 Result: No API keys available. API tests skipped."); return False

def test_gemini_api():
    logging.info("--- [Test 4/8] Testing Google Gemini API ---")
    if not gemini_api_key_global: logging.warning("Skipping Gemini test: Key not available."); return False
    try: import google.generativeai as genai # Ensure it's imported for this function
    except ImportError: logging.error("Gemini test failed: google.generativeai library not found."); return False
    try:
        genai.configure(api_key=gemini_api_key_global)
        model = genai.GenerativeModel('gemini-1.0-pro')
        logging.info("Sending test request to Gemini (gemini-1.0-pro)...")
        response = model.generate_content("用中文回复 '测试成功'.") # "Reply in Chinese 'Test Succeeded'."
        response_text = getattr(response, 'text', None) or "".join(part.text for part in getattr(response, 'parts', []) if hasattr(part, 'text')) or f"Feedback: {getattr(response, 'prompt_feedback', 'N/A')}"

        if "测试成功" in response_text or "測試成功" in response_text:
            logging.info(f"Gemini API Response: '{response_text.strip()}'. Test 4 Result: Success.")
            return True
        else: # Try fallback if main model fails or gives unexpected response
            logging.error(f"Gemini API (gemini-1.0-pro) response not as expected: {response_text}. Trying fallback.")
            model_old = genai.GenerativeModel('gemini-pro')
            response_old = model_old.generate_content("用中文回复 '测试成功'.")
            response_old_text = getattr(response_old, 'text', None) or "".join(part.text for part in getattr(response_old, 'parts', []) if hasattr(part, 'text'))
            if "测试成功" in response_old_text or "測試成功" in response_old_text:
                logging.info(f"Gemini API (gemini-pro) Response: '{response_old_text.strip()}'. Test 4 Result: Success (fallback).")
                return True
            else: logging.error(f"Gemini API (gemini-pro) also failed: {response_old_text}. Test 4 Result: Failed."); return False
    except Exception as e: logging.error(f"Error during Gemini API test: {e}. Test 4 Result: Failed."); return False

def test_yfinance_data():
    logging.info("--- [Test 5/8] Testing yfinance data retrieval ---")
    try: import yfinance as yf # Ensure imported
    except ImportError: logging.error("yfinance test failed: library not found."); return False
    try:
        logging.info("Fetching ^TWII data (last 5 days)...")
        twii_data = yf.download('^TWII', period='5d', progress=False)
        if not twii_data.empty:
            logging.info(f"yfinance data fetched successfully:\n{twii_data.head().to_string()}. Test 5 Result: Success.")
            return True
        else: logging.error("yfinance data fetch was empty. Test 5 Result: Failed."); return False
    except Exception as e: logging.error(f"Error with yfinance: {e}. Test 5 Result: Failed."); return False

def test_fred_api():
    logging.info("--- [Test 6/8] Testing FRED data retrieval ---")
    if not fred_api_key_global: logging.warning("Skipping FRED test: Key not available."); return False
    try: from fredapi import Fred # Ensure imported
    except ImportError: logging.error("FRED test failed: fredapi library not found."); return False
    try:
        logging.info("Fetching US GDP data via FRED API...")
        fred = Fred(api_key=fred_api_key_global)
        gdp_data = fred.get_series('GDP')
        if not gdp_data.empty:
            logging.info(f"FRED data fetched successfully:\n{gdp_data.tail().to_string()}. Test 6 Result: Success.")
            return True
        else: logging.error("FRED data fetch was empty. Test 6 Result: Failed."); return False
    except Exception as e: logging.error(f"Error with FRED API: {e}. Test 6 Result: Failed."); return False

def test_file_rw():
    logging.info(f"--- [Test 7/8] Testing file R/W in {PROJECT_BASE_DIR} ---")
    if not os.path.exists(PROJECT_BASE_DIR): logging.warning(f"Base dir {PROJECT_BASE_DIR} missing. Skipping R/W test."); return False
    test_file = os.path.join(PROJECT_BASE_DIR, 'debug_rw_test.txt')
    content = f"Test content. Timestamp: {time.ctime()}."
    try:
        with open(test_file, 'w', encoding='utf-8') as f: f.write(content)
        logging.info(f"Test file written to {test_file}.")
        with open(test_file, 'r', encoding='utf-8') as f: read_c = f.read()
        if read_c == content: logging.info("File content verified. Test 7 Result: Success."); result = True
        else: logging.error("File content mismatch. Test 7 Result: Failed."); result = False
        os.remove(test_file); logging.info("Test file removed.")
        return result
    except Exception as e: logging.error(f"File R/W error: {e}. Test 7 Result: Failed."); return False

def test_log_file_write_check():
    logging.info("--- [Test 8/8] Verifying log file write ---")
    log_line = f"Log verification line. Timestamp: {time.ctime()}."
    logging.info(log_line) # This should write to the file via handler
    try:
        if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > 0:
            with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f: lines = f.readlines()
            if any("Log verification line." in l for l in lines[-5:]): # Check recent lines
                logging.info(f"Log file {LOG_FILE_PATH} verified. Test 8 Result: Success.")
                return True
            else: logging.warning(f"Log file {LOG_FILE_PATH} written, but verification line not found in recent entries. Partial success."); return "partial_success"
        else: logging.error(f"Log file {LOG_FILE_PATH} missing or empty. Test 8 Result: Failed."); return False
    except Exception as e: logging.error(f"Error verifying log file: {e}. Test 8 Result: Failed."); return False

def run_all_tests(use_gdrive=False, project_dir_name="wolfAI"):
    if not logging_configured: initialize_paths(use_gdrive=use_gdrive, project_dir_name=project_dir_name)
    else: logging.info("Logging already configured. Skipping re-initialization of paths for this run_all_tests call if not intended.")


    logging.info("============================================================")
    logging.info(f"Starting Wolf Debug Module Tests (Drive: {use_gdrive}, Project: {project_dir_name})")
    logging.info("============================================================")
    results = {
        "Env & Packages": check_env_and_packages(),
        "Project Structure": check_project_structure(),
        "API Key Access": get_api_keys_with_input_option(),
        "Gemini API": test_gemini_api(),
        "yfinance Data": test_yfinance_data(),
        "FRED API": test_fred_api(),
        "File R/W Test": test_file_rw(),
        "Log File Write": test_log_file_write_check()
    }
    logging.info("\n============================================================")
    logging.info("All Debug Tests Completed.")
    logging.info("============================================================")
    logging.info("\nTest Results Summary:")
    all_ok = True
    for name, status in results.items():
        if status is True: sym = "✅ Success"
        elif status is False: sym = "❌ Failed"; all_ok = False
        else: sym = f"⚠️ Warning ({status})"; all_ok = False # Any non-True is a problem
        logging.info(f"- {name}: {sym}")
    if all_ok: logging.info("\n🎉 All critical tests passed successfully.")
    else: logging.warning("\n⚠️ Some tests failed or had warnings. Review logs.")
    return results

# Example of direct execution (主にローカルテスト用)
# if __name__ == "__main__":
#     print("Running wolf_debugger.py directly for testing...")
#     # Initialize paths and logging for direct run
#     # This will use default local paths unless overridden by env or args
#     if not logging_configured:
#          initialize_paths(use_gdrive=False, project_dir_name="wolfAITestRun")
#     run_all_tests(use_gdrive=False, project_dir_name="wolfAITestRun")
