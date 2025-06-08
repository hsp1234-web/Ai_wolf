import os
import sys
import subprocess
import shutil
import datetime
import json
import re
import requests
import time
import signal
import importlib.util
from IPython.display import HTML, display, clear_output

# --- Global Variables/Setup ---

# Mocking Colab Userdata for controlled testing
MOCK_COLAB_USERDATA_STORE = {}
MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED = False # Flag to check if mock error was raised

class MockColabErrors:
    class SecretNotFoundError(Exception):
        pass

class MockColabUserdata:
    def get(self, key, default=None):
        global MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED
        MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED = False # Reset flag
        if key in MOCK_COLAB_USERDATA_STORE:
            if MOCK_COLAB_USERDATA_STORE[key] == MockColabErrors.SecretNotFoundError:
                MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED = True
                raise MockColabErrors.SecretNotFoundError(f"Secret '{key}' not found.")
            return MOCK_COLAB_USERDATA_STORE[key]
        elif default is not None:
            return default
        MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED = True # Should raise if default is None and key not found
        raise MockColabErrors.SecretNotFoundError(f"Secret '{key}' not found (no default).")

# Attempt to import real Colab modules, fall back to mocks if not available or for testing
try:
    from google.colab import userdata as colab_userdata
    from google.colab import errors as colab_errors
    # If actual Colab environment, for these specific tests, we might still want to use mock
    # For now, let's assume if import works, we MIGHT use it, but tests will primarily set up mocks.
    # A more explicit flag could control this: USE_MOCK_FOR_COLAB_TESTS = True
    log_message("Successfully imported google.colab.userdata and errors.", level="DEBUG")
    # For the purpose of these specific tests, we will override with mocks.
    # If other parts of the script were to use live secrets, this would need careful conditional mocking.
    userdata = MockColabUserdata()
    errors = MockColabErrors()
    log_message("Using MOCK google.colab.userdata and errors for API key testing.", level="INFO")
except ImportError:
    log_message("google.colab.userdata or errors not found. Using MOCK implementation.", level="WARN")
    userdata = MockColabUserdata()
    errors = MockColabErrors()

def setup_mock_userdata(api_keys_config: dict):
    """Primes the mock userdata store."""
    global MOCK_COLAB_USERDATA_STORE
    MOCK_COLAB_USERDATA_STORE.clear()
    MOCK_COLAB_USERDATA_STORE.update(api_keys_config)
    log_message(f"Mock userdata store configured: {api_keys_config}", level="DEBUG")

PROJECT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
PROJECT_DIR = "/content/wolfAI"
RESULTS_DATA = {"categories": []}
LOG_MESSAGES = []

FASTAPI_PORT = 8008 # Using a non-default port for testing
FASTAPI_BASE_URL = f"http://127.0.0.1:{FASTAPI_PORT}"
FASTAPI_LOG_PATH = "/content/temp_fastapi_health_check.log" # Will be kept for inspection
fastapi_process = None # To store the FastAPI server process
test_api_auth_token = None # To store API auth token for authenticated endpoint tests

STREAMLIT_TEST_PORT = 8502
STREAMLIT_STARTUP_TIMEOUT = 30 # seconds
# --- Helper Functions ---
def log_message(message, level="INFO"):
    timestamp = datetime.datetime.now().isoformat()
    formatted_message = f"[{timestamp}] [{level}] {message}"
    LOG_MESSAGES.append(formatted_message)
    print(formatted_message) # Keep printing for live feedback

def run_shell_command(command_list, cwd=None, use_shell=False, pass_through_env=False):
    log_message(f"Running command: {' '.join(command_list) if not use_shell else command_list}", level="DEBUG")
    env = os.environ.copy() if pass_through_env else None
    try:
        process = subprocess.Popen(
            command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            cwd=cwd, shell=use_shell, preexec_fn=os.setsid if not use_shell else None, env=env
        )
        stdout, stderr = process.communicate(timeout=90) # Increased timeout for pip install
        return stdout, stderr, process.returncode
    except subprocess.TimeoutExpired:
        cmd_str = ' '.join(command_list) if not use_shell else command_list
        log_message(f"Command timed out: {cmd_str}", level="ERROR")
        # Try to kill process group if shell=False and pgid is available
        # For shell=True, this is less reliable.
        try:
            if not use_shell and hasattr(process, 'pgid') and process.pgid is not None:
                os.killpg(process.pgid, signal.SIGKILL)
            else: # Fallback for shell=True or if pgid not set
                process.kill()
        except Exception as kill_e:
            log_message(f"Error trying to kill timed-out process {cmd_str}: {kill_e}", level="ERROR")
        return "", "TimeoutExpired", -1
    except Exception as e:
        cmd_str = ' '.join(command_list) if not use_shell else command_list
        log_message(f"Error running command {cmd_str}: {e}", level="ERROR")
        return "", str(e), -2

def add_test_result(category_name, test_name, status, details="", value=""):
    category = next((cat for cat in RESULTS_DATA["categories"] if cat["name"] == category_name), None)
    if not category:
        category = {"name": category_name, "tests": []}
        RESULTS_DATA["categories"].append(category)

    # Sanitize details and value to prevent HTML injection if directly embedding user content
    # For this script, it's mostly system output, but good practice
    details_safe = str(details).replace("<", "&lt;").replace(">", "&gt;")
    value_safe = str(value).replace("<", "&lt;").replace(">", "&gt;")

    category["tests"].append({
        "name": test_name,
        "status": status,
        "details": details_safe,
        "value": value_safe,
        "timestamp": datetime.datetime.now().isoformat()
    })

# --- Phase 1: Environment Setup ---
def phase_1_environment_setup():
    log_message("--- Phase 1: Environment Setup ---")
    if os.path.exists(FASTAPI_LOG_PATH): # Clean up old health check log
        os.remove(FASTAPI_LOG_PATH)

    log_message(f"Cleaning up old project directory: {PROJECT_DIR}...")
    cleanup_status, cleanup_details = "PASS", f"Directory {PROJECT_DIR} did not exist or was successfully removed."
    if os.path.exists(PROJECT_DIR):
        try:
            shutil.rmtree(PROJECT_DIR)
            log_message(f"Successfully removed {PROJECT_DIR}.")
        except Exception as e:
            log_message(f"Failed to remove {PROJECT_DIR}: {e}", level="ERROR")
            cleanup_status, cleanup_details = "FAIL", f"Failed to remove {PROJECT_DIR}: {e}"
    else:
        log_message(f"{PROJECT_DIR} does not exist, no need to clean up.")
    add_test_result("Environment Setup", "Cleanup Old Project", cleanup_status, cleanup_details)

    log_message(f"Cloning project from {PROJECT_REPO_URL} into {PROJECT_DIR}...")
    stdout, stderr, returncode = run_shell_command(["git", "clone", "--depth", "1", PROJECT_REPO_URL, PROJECT_DIR])
    clone_successful = (returncode == 0)
    if clone_successful:
        log_message("Project cloned successfully.")
        add_test_result("Environment Setup", "Clone Project Repository", "PASS", f"Cloned from {PROJECT_REPO_URL}")
        add_test_result("Project Structure and Dependencies", "Git Clone Success", "PASS", f"Cloned from {PROJECT_REPO_URL}")
    else:
        log_message(f"Failed to clone project. RC: {returncode}\nStdout: {stdout}\nStderr: {stderr}", level="CRITICAL")
        add_test_result("Environment Setup", "Clone Project Repository", "FAIL", f"RC: {returncode}. Error: {stderr or stdout}")
        add_test_result("Project Structure and Dependencies", "Git Clone Success", "FAIL", f"RC: {returncode}. Error: {stderr or stdout}")
        return False

    log_message("Installing dependencies from requirements.txt...")
    requirements_path = os.path.join(PROJECT_DIR, "requirements.txt")
    dep_status, dep_details = "N/A", "Project clone failed, skipping."
    if clone_successful:
        if os.path.exists(requirements_path):
            stdout, stderr, pip_returncode = run_shell_command(
                [sys.executable, "-m", "pip", "install", "-q", "-r", requirements_path],
                cwd=PROJECT_DIR, pass_through_env=True
            )
            if pip_returncode == 0:
                dep_status, dep_details = "PASS", "Successfully installed dependencies."
            else:
                dep_status, dep_details = "FAIL", f"pip install failed. RC: {pip_returncode}. Error: {stderr or stdout}"
                log_message(dep_details, level="ERROR")
        else:
            dep_status, dep_details = "WARN", f"requirements.txt not found at {requirements_path}."
            log_message(dep_details, level="WARN")

    add_test_result("Environment Setup", "Install Dependencies", dep_status, dep_details)
    add_test_result("Project Structure and Dependencies", "Dependency Install Success", dep_status, dep_details)

    # Install pytest if main dependencies were installed
    pytest_install_status, pytest_install_details = "N/A", "Skipped due to main dependency install failure."
    if dep_status == "PASS":
        log_message("Attempting to install pytest...")
        stdout_pytest, stderr_pytest, pip_pytest_returncode = run_shell_command(
            [sys.executable, "-m", "pip", "install", "-q", "pytest"],
            cwd=PROJECT_DIR # or None if PROJECT_DIR might not exist yet or not relevant
        )
        if pip_pytest_returncode == 0:
            pytest_install_status, pytest_install_details = "PASS", "pytest successfully installed."
            log_message(pytest_install_details)
        else:
            pytest_install_status, pytest_install_details = "FAIL", f"pytest installation failed. RC: {pip_pytest_returncode}. Error: {stderr_pytest or stdout_pytest}"
            log_message(pytest_install_details, level="ERROR")
    add_test_result("Environment Setup", "Install Pytest", pytest_install_status, pytest_install_details)


    # Call new dependency integrity checks if install was successful
    if dep_status == "PASS":
        check_requirements_integrity()
        verify_core_package_imports()
    else:
        add_test_result("Dependency Integrity", "Requirements Integrity Check", "SKIPPED", "Dependency installation failed.")
        add_test_result("Dependency Integrity", "Core Package Import Check", "SKIPPED", "Dependency installation failed.")

    # Call new API key reading tests
    test_api_key_reading()

    # Call new structure and permission tests
    if os.path.exists(os.path.join(PROJECT_DIR, "COMPONENTS_OVERVIEW.md")):
        check_components_overview_consistency()
    else:
        add_test_result("Project Structure and Dependencies", "COMPONENTS_OVERVIEW.md Check", "WARN", "COMPONENTS_OVERVIEW.md not found, skipping consistency check.")

    test_log_directory_write_permission() # Test log directory permissions

    # Run Pytest unit tests if pytest was installed
    if pytest_install_status == "PASS":
        run_unit_tests_with_pytest()
    else:
        add_test_result("Unit Tests (pytest)", "Pytest Execution", "SKIPPED", "Pytest not installed.")

    # Streamlit application tests
    test_streamlit_startup_and_log_initialization()

    # AI Functionality and Data Integration Tests
    if server_started_ok and test_api_auth_token: # Depends on FastAPI server and auth
        test_ai_market_review_with_specific_date()
    else:
        add_test_result("AI 功能與資料整合測試", "AI Market Review with Specific Date", "SKIPPED", "FastAPI server not running or auth token not available.")


    return clone_successful


# --- New Function: test_streamlit_startup_and_log_initialization ---

def test_streamlit_url_acquisition_internal(category_name):
    log_message("Running Streamlit URL Acquisition tests (Internal)...")
    # This function is called while Streamlit process is expected to be running.

    try:
        from google.colab.output import eval_js
        log_message("google.colab.output.eval_js imported successfully.", level="DEBUG")

        eval_js_command = f'google.colab.kernel.proxyPort({STREAMLIT_TEST_PORT})'
        log_message(f"Attempting to get Streamlit URL via eval_js: {eval_js_command}", level="INFO")
        streamlit_url_eval_js = None
        try:
            streamlit_url_eval_js = eval_js(eval_js_command, timeout_sec=10) # Increased timeout slightly
            if streamlit_url_eval_js and (streamlit_url_eval_js.startswith("http://") or streamlit_url_eval_js.startswith("https://")):
                add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "PASS", f"Successfully obtained URL via eval_js: {streamlit_url_eval_js}")
                # Overall success if eval_js works
                add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "PASS", f"URL obtained via eval_js: {streamlit_url_eval_js}")
                return True # Indicates URL acquired
            else:
                add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "FAIL", f"eval_js did not return a valid URL. Received: '{streamlit_url_eval_js}'")
        except Exception as e_evaljs:
            log_message(f"google.colab.output.eval_js failed: {e_evaljs}", level="ERROR")
            add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "FAIL", f"eval_js call failed: {e_evaljs}")

    except ImportError:
        log_message("google.colab.output.eval_js not available. Skipping eval_js test for Streamlit URL.", level="WARN")
        add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "SKIPPED", "Not in a Colab environment with google.colab.output.")
        # Fall through to cloudflared check if eval_js is not even available

    # Conceptual Cloudflared Fallback Check (if eval_js failed or was skipped)
    log_message("eval_js did not yield a URL or was skipped. Checking for cloudflared as a conceptual fallback.", level="INFO")
    cloudflared_check_details = "This check only verifies cloudflared presence, not actual tunnel functionality which is complex to automate here."
    stdout_cf, stderr_cf, rc_cf = run_shell_command(["cloudflared", "--version"])
    if rc_cf == 0:
        add_test_result(category_name, "Streamlit URL Acquisition - Cloudflared Check", "PASS", f"cloudflared is installed ({stdout_cf.strip()}). {cloudflared_check_details}")
        # Overall status is WARN because we have a fallback but didn't get URL from primary method
        add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "WARN", "eval_js failed/skipped, but cloudflared (fallback) is present. Actual URL not obtained by this script.")
    else:
        add_test_result(category_name, "Streamlit URL Acquisition - Cloudflared Check", "WARN", f"cloudflared not found or version check failed (RC:{rc_cf}). {cloudflared_check_details}", value=stderr_cf)
        # Overall status is FAIL because primary failed and fallback is not present
        add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "FAIL", "eval_js failed/skipped, and cloudflared (fallback) is not available.")

    return False # Indicates URL not acquired by primary method

def check_streamlit_application_log(category_name, streamlit_log_path):
    """Checks the application's own Streamlit log file."""
    log_message(f"Checking Streamlit application log: {streamlit_log_path}", level="INFO")
    if os.path.exists(streamlit_log_path):
        try:
            with open(streamlit_log_path, 'r', encoding='utf-8', errors='replace') as f_log:
                log_head = f_log.read(500) # Read first 500 chars
            if "streamlit" in log_head.lower() or "info" in log_head.lower() or "debug" in log_head.lower() or "logger" in log_head.lower():
                add_test_result(category_name, "Streamlit App Log Initialization", "PASS", f"App log '{os.path.basename(streamlit_log_path)}' exists and contains initial log patterns.", value=f"Log snippet: {log_head[:100]}...")
            else:
                add_test_result(category_name, "Streamlit App Log Initialization", "WARN", f"App log '{os.path.basename(streamlit_log_path)}' exists but expected patterns not found. Manual check advised.", value=f"Log snippet: {log_head[:100]}...")
        except Exception as e:
            add_test_result(category_name, "Streamlit App Log Initialization", "FAIL", f"Error reading app log {os.path.basename(streamlit_log_path)}: {e}")
    else:
        add_test_result(category_name, "Streamlit App Log Initialization", "WARN", f"App log file '{os.path.basename(streamlit_log_path)}' not found. App might not be configured to log here or did not start/log correctly.")


def test_streamlit_startup_and_log_initialization():
    log_message("Running Streamlit Startup, URL Acquisition, and Log Initialization tests...")
    category_name = "Frontend Application (Streamlit)"
    streamlit_app_path = os.path.join(PROJECT_DIR, "app.py")
    streamlit_log_dir = os.path.join(PROJECT_DIR, "logs")
    # App's own log, configured by the app itself:
    application_streamlit_log_path = os.path.join(streamlit_log_dir, "streamlit.log")
    # Log for the Streamlit process started by this health check:
    health_check_streamlit_process_log_path = os.path.join(streamlit_log_dir, "health_check_streamlit_process.log")

    if not os.path.exists(streamlit_app_path):
        add_test_result(category_name, "Streamlit App File Check", "FAIL", f"Streamlit app.py not found at {streamlit_app_path}.")
        # Add SKIPPED for all sub-tests if app.py is missing
        for test_name_suffix in ["App Startup", "URL Acquisition - Overall Status", "App Log Initialization"]:
            add_test_result(category_name, f"Streamlit {test_name_suffix}", "SKIPPED", "app.py not found.")
        return

    if not os.path.exists(streamlit_log_dir):
        try:
            os.makedirs(streamlit_log_dir)
            log_message(f"Created logs directory for Streamlit: {streamlit_log_dir}", level="INFO")
        except Exception as e:
            log_message(f"Failed to create Streamlit logs directory {streamlit_log_dir}: {e}", level="ERROR")
            add_test_result(category_name, "Streamlit Log Directory Setup", "FAIL", f"Failed to create {streamlit_log_dir}: {e}.")
            # Do not return; attempt startup anyway, but URL/log tests might be affected or save to different locations.

    cmd = [
        sys.executable, "-m", "streamlit", "run", streamlit_app_path,
        "--server.port", str(STREAMLIT_TEST_PORT), "--server.headless", "true",
        "--server.runOnSave", "false", "--server.fileWatcherType", "none"
    ]
    process = None
    startup_presumed_ok = False

    try:
        log_message(f"Executing Streamlit command: {' '.join(cmd)} for startup test.", level="DEBUG")
        with open(health_check_streamlit_process_log_path, 'wb') as proc_log_f:
            process = subprocess.Popen(cmd, cwd=PROJECT_DIR, stdout=proc_log_f, stderr=proc_log_f)

        log_message(f"Streamlit process (PID: {process.pid}) launched. Waiting ~15s for initial stability check.", level="INFO")
        try:
            process.wait(timeout=15)
            rc = process.returncode
            log_message(f"Streamlit process terminated early with RC: {rc}", level="WARN")
            add_test_result(category_name, "Streamlit App Startup", "FAIL" if rc != 0 else "WARN",
                            f"Process terminated early. RC: {rc}. Check '{os.path.basename(health_check_streamlit_process_log_path)}'.")
            startup_presumed_ok = False
        except subprocess.TimeoutExpired:
            log_message(f"Streamlit process (PID: {process.pid}) running after 15s. Presuming successful headless startup.", level="INFO")
            add_test_result(category_name, "Streamlit App Startup", "PASS", f"Process running after 15s (PID: {process.pid}). Headless startup presumed OK.")
            startup_presumed_ok = True

            # If startup is OK, attempt URL acquisition
            log_message("Proceeding to Streamlit URL acquisition tests while process is running...", level="INFO")
            test_streamlit_url_acquisition_internal(category_name) # Call the internal function

            # Allow a little more time if needed before forced termination, e.g. for eval_js to complete.
            # The URL acquisition has its own timeout for eval_js.
            time.sleep(2) # Brief pause before terminating.

    except Exception as e:
        log_message(f"Exception during Streamlit process management: {e}", level="ERROR")
        add_test_result(category_name, "Streamlit App Startup", "FAIL", f"Exception: {e}. Check '{os.path.basename(health_check_streamlit_process_log_path)}'.")
        startup_presumed_ok = False
    finally:
        if process:
            log_message(f"Ensuring Streamlit process (PID: {process.pid}) is terminated.", level="INFO")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log_message(f"Streamlit process (PID: {process.pid}) did not terminate gracefully, killing.", level="WARN")
                process.kill()
            except Exception as e_term: # Handle cases where process might already be dead
                log_message(f"Error during Streamlit process termination (PID: {process.pid if hasattr(process, 'pid') else 'N/A'}): {e_term}", level="ERROR")
            log_message(f"Streamlit process (PID: {process.pid if hasattr(process, 'pid') else 'N/A'}) cleanup finished.", level="INFO")

        if os.path.exists(health_check_streamlit_process_log_path):
            with open(health_check_streamlit_process_log_path, 'r', encoding='utf-8', errors='replace') as f_log_proc_read:
                log_content = f_log_proc_read.read()
            if not startup_presumed_ok and log_content:
                 add_test_result(category_name, "Streamlit Process Output (Health Check Log)", "INFO", f"Contents of '{os.path.basename(health_check_streamlit_process_log_path)}' (last 1000 chars): ...{log_content[-1000:]}")
            elif not log_content :
                 add_test_result(category_name, "Streamlit Process Output (Health Check Log)", "INFO", f"'{os.path.basename(health_check_streamlit_process_log_path)}' was empty.")


    # Check application's own log file AFTER Streamlit process has been handled
    # This part is independent of whether startup_presumed_ok is True, as the app might have logged errors before failing.
    # However, it makes more sense to check it if we believe the app at least tried to start.
    # For now, let's check it regardless, as it might contain useful diagnostic info even on failed startup.
    check_streamlit_application_log(category_name, application_streamlit_log_path)


# --- New Function: run_unit_tests_with_pytest ---
def run_unit_tests_with_pytest():
    log_message("Running Unit Tests with Pytest...")
    category_name = "Unit Tests (pytest)"
    unit_tests_dir = os.path.join(PROJECT_DIR, "tests/unit/")
    logs_dir = os.path.join(PROJECT_DIR, "logs") # For JUnit XML report

    if not os.path.exists(unit_tests_dir):
        log_message(f"Unit tests directory not found: {unit_tests_dir}. Skipping pytest run.", level="WARN")
        add_test_result(category_name, "Pytest Setup", "WARN", f"Unit tests directory '{unit_tests_dir}' not found.")
        return

    # Ensure logs directory exists for the report
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
            log_message(f"Created logs directory: {logs_dir}", level="INFO")
        except Exception as e:
            log_message(f"Failed to create logs directory {logs_dir}: {e}. JUnit XML report may not be saved.", level="ERROR")
            # Proceed with test execution, but report might be lost or saved in PROJECT_DIR
            # Pytest might also fail if the path is not writable.

    xml_report_path = os.path.join(logs_dir, "pytest_unit_report.xml")
    # Ensure path is absolute for pytest if logs_dir creation failed and it's just a filename
    if not os.path.isabs(xml_report_path) and logs_dir == os.path.join(PROJECT_DIR,"logs"): # Check if it's the intended path
         xml_report_path = os.path.join(PROJECT_DIR, "pytest_unit_report.xml") # Fallback to PROJECT_DIR
         log_message(f"JUnit XML report will be saved to: {xml_report_path} (logs dir issue)", level="WARN")
    else:
         log_message(f"JUnit XML report will be saved to: {xml_report_path}", level="INFO")


    pytest_command = [
        sys.executable, "-m", "pytest",
        "tests/unit/", # Target directory relative to PROJECT_DIR
        f"--junitxml={xml_report_path}"
    ]

    log_message(f"Executing Pytest command: {' '.join(pytest_command)} in {PROJECT_DIR}", level="INFO")
    stdout, stderr, returncode = run_shell_command(pytest_command, cwd=PROJECT_DIR)

    if returncode not in [0, 1, 2, 5]: # 0=all pass, 1=tests failed, 2=interrupted, 5=no tests collected
        # Other error codes might indicate misuse or environment issues
        log_message(f"Pytest execution error. RC: {returncode}\nStdout: {stdout}\nStderr: {stderr}", level="ERROR")
        add_test_result(category_name, "Pytest Execution Status", "FAIL", f"Pytest command failed with RC {returncode}. Stderr: {stderr[:500]}")
        # Attempt to parse report anyway, as some tests might have run
    elif stderr and "INTERNALERROR" in stderr:
        log_message(f"Pytest internal error. RC: {returncode}\nStdout: {stdout}\nStderr: {stderr}", level="ERROR")
        add_test_result(category_name, "Pytest Execution Status", "FAIL", f"Pytest reported internal error. Stderr: {stderr[:500]}")

    if not os.path.exists(xml_report_path):
        log_message(f"Pytest JUnit XML report not found at {xml_report_path}.", level="ERROR")
        add_test_result(category_name, "Pytest Report Parsing", "FAIL", f"JUnit XML report not found: {xml_report_path}. Stdout from pytest: {stdout[:500]}")
        if returncode == 0 and not stderr : # If pytest claimed success but no report, it's odd
             add_test_result(category_name, "Pytest Execution Anomaly", "WARN", "Pytest exited 0 but no XML report found.")
        return

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_report_path)
        root = tree.getroot()
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        skipped_tests = 0

        for testsuite_node in root.findall("testsuite"):
            total_tests += int(testsuite_node.get("tests", 0))
            # Pytest often has one top-level testsuite.
            for testcase_node in testsuite_node.findall("testcase"):
                name = testcase_node.get("name")
                classname = testcase_node.get("classname", "UnknownClass")
                full_test_name = f"{classname}.{name}"
                details = []

                failure_node = testcase_node.find("failure")
                error_node = testcase_node.find("error")
                skipped_node = testcase_node.find("skipped")

                if failure_node is not None:
                    status = "FAIL"
                    failed_tests +=1
                    details.append(f"Failure: {failure_node.get('message', '')}\n{failure_node.text[:500] if failure_node.text else ''}")
                elif error_node is not None:
                    status = "FAIL" # Treat errors as failures for simplicity
                    error_tests +=1
                    details.append(f"Error: {error_node.get('message', '')}\n{error_node.text[:500] if error_node.text else ''}")
                elif skipped_node is not None:
                    status = "WARN" # Or "SKIPPED" - depends on preference
                    skipped_tests +=1
                    details.append(f"Skipped: {skipped_node.get('message', '')}")
                else:
                    status = "PASS"
                    passed_tests +=1

                add_test_result(category_name, full_test_name, status, "\n".join(details).strip())

        # If root is a testsuites element, it might contain multiple testsuite elements
        if root.tag == 'testsuites':
            for testsuite_node in root.findall('testsuite'):
                total_tests += int(testsuite_node.get('tests', 0))
                # passed_tests += (int(testsuite_node.get('tests', 0)) - int(testsuite_node.get('failures', 0)) - int(testsuite_node.get('errors', 0)) - int(testsuite_node.get('skipped', 0)))
                # The above is not quite right, better to sum from testcases.
                # The individual testcase parsing already handles counts.
        elif root.tag == 'testsuite' and not total_tests: # If only one testsuite, and we haven't summed it up
             total_tests = int(root.get("tests", 0))
             # Individual test cases already counted for pass/fail/skip.
             # This is mostly for the overall status.

        summary_status = "PASS"
        summary_details = f"Total: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}, Errors: {error_tests}, Skipped: {skipped_tests}."
        if failed_tests > 0 or error_tests > 0:
            summary_status = "FAIL"
        elif skipped_tests > 0 and passed_tests == 0 and failed_tests == 0 and error_tests == 0 : # All skipped
            summary_status = "WARN"
        elif total_tests == 0 : # Pytest return code 5 for no tests collected
             if returncode == 5:
                 summary_status = "WARN"
                 summary_details = "No tests collected by Pytest." + f" stdout: {stdout[:200]}"
             else: # No tests in XML but pytest didn't say "no tests collected"
                 summary_status = "WARN"
                 summary_details = "XML report parsed but no test cases found. " + summary_details

        add_test_result(category_name, "Pytest Unit Tests Run Summary", summary_status, summary_details, value=f"RC:{returncode}")
        log_message(f"Pytest results: {summary_details}", level="INFO" if summary_status == "PASS" else "WARN")

    except ET.ParseError as e:
        log_message(f"Error parsing Pytest XML report {xml_report_path}: {e}", level="ERROR")
        add_test_result(category_name, "Pytest Report Parsing", "FAIL", f"XML ParseError: {e}")
    except Exception as e:
        log_message(f"Unexpected error during Pytest report processing: {e}", level="CRITICAL")
        add_test_result(category_name, "Pytest Report Processing", "FAIL", f"Unexpected error: {e}")


# --- New Function: check_components_overview_consistency ---
def check_components_overview_consistency():
    log_message("Running COMPONENTS_OVERVIEW.md Consistency Check...")
    category_name = "Project Structure and Dependencies"
    overview_file_path = os.path.join(PROJECT_DIR, "COMPONENTS_OVERVIEW.md")

    if not os.path.exists(overview_file_path):
        # This case should ideally be caught before calling, but as a safeguard:
        add_test_result(category_name, "COMPONENTS_OVERVIEW.md Structure Check", "FAIL", "COMPONENTS_OVERVIEW.md not found.")
        return

    paths_in_overview = []
    # Regex to capture paths like: |-- path/to/file_or_dir/ # Optional comment
    # It tries to capture the path part, ignoring the tree structure prefixes and comments.
    # Adjusted to better handle various depths of tree structure.
    # Example lines:
    # |-- app.py # Main Streamlit application
    # |   |-- .streamlit/
    # |   |   |-- config.toml
    # |-- components/ # Reusable Streamlit UI components
    path_regex = re.compile(r"^\s*(?:\|[\s\-]*)*(?:`?([a-zA-Z0-9_\-\.\/]+(?:`|\b/?)))\s*(?:#.*)?")


    try:
        with open(overview_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line_stripped = line.strip()
                if not line_stripped: # Skip empty lines
                    continue

                match = path_regex.search(line_stripped)
                if match:
                    path_candidate = match.group(1).replace('`', '') # Remove backticks if any
                    # Further cleanups if needed, e.g. specific comment patterns not caught by #
                    if path_candidate and not path_candidate.startswith(('#', '<', '>')): # Avoid comments or HTML-like tags
                        paths_in_overview.append({"path": path_candidate, "line": line_num})

    except Exception as e:
        add_test_result(category_name, "COMPONENTS_OVERVIEW.md Read/Parse", "FAIL", f"Error reading or parsing file: {e}")
        return

    if not paths_in_overview:
        add_test_result(category_name, "COMPONENTS_OVERVIEW.md Path Extraction", "WARN", "No paths extracted from COMPONENTS_OVERVIEW.md. Regex might need adjustment or file is empty/malformed.")
        return

    all_paths_exist = True
    missing_paths_details = []
    for item in paths_in_overview:
        path_str = item["path"]
        full_path = os.path.join(PROJECT_DIR, path_str.strip('/')) # Normalize by removing trailing slash for os.path.exists if it's a dir check
        exists = os.path.exists(full_path)
        status_char = "✅" if exists else "❌"
        log_message(f"Path check: {status_char} {path_str} (from line {item['line']}) -> {full_path} (Exists: {exists})", level="DEBUG" if exists else "WARN")
        if not exists:
            all_paths_exist = False
            missing_paths_details.append(f"Missing: '{path_str}' (line {item['line']})")
            add_test_result(category_name, f"Overview Path: {path_str}", "FAIL", f"Path '{full_path}' listed in COMPONENTS_OVERVIEW.md (line {item['line']}) does not exist.")
        else:
            add_test_result(category_name, f"Overview Path: {path_str}", "PASS", f"Path '{full_path}' exists.")


    if all_paths_exist:
        add_test_result(category_name, "COMPONENTS_OVERVIEW.md Structure Consistency", "PASS", "All paths listed in COMPONENTS_OVERVIEW.md exist in the project.")
    else:
        add_test_result(category_name, "COMPONENTS_OVERVIEW.md Structure Consistency", "FAIL", f"Some paths listed in COMPONENTS_OVERVIEW.md do not exist. Details: {'; '.join(missing_paths_details)}")

# --- New Function: test_log_directory_write_permission ---
def test_log_directory_write_permission():
    log_message("Running Log Directory Write Permission Test...")
    # As per instruction, primary log directory to test is PROJECT_DIR/logs/
    # Category can be "Environment Setup" or "Project Structure and Dependencies"
    # Let's use "Project Structure and Dependencies" for now.
    category_name = "Project Structure and Dependencies"
    log_dir_relative = "logs/"
    log_dir_path = os.path.join(PROJECT_DIR, log_dir_relative)
    test_file_name = "temp_health_check_write_test.log"
    test_file_path = os.path.join(log_dir_path, test_file_name)
    test_content = f"Health check write test: {datetime.datetime.now().isoformat()}"

    # Step 1: Check/Create Log Directory
    if not os.path.exists(log_dir_path):
        log_message(f"Log directory '{log_dir_path}' does not exist. Attempting to create it for the test.", level="WARN")
        try:
            os.makedirs(log_dir_path)
            log_message(f"Successfully created log directory: {log_dir_path}", level="INFO")
            add_test_result(category_name, f"Log Directory Existence ({log_dir_relative})", "WARN", f"Directory did not exist but was successfully created for the test at {log_dir_path}.")
        except Exception as e:
            log_message(f"Failed to create log directory {log_dir_path}: {e}", level="ERROR")
            add_test_result(category_name, f"Log Directory Creation ({log_dir_relative})", "FAIL", f"Failed to create directory {log_dir_path}: {e}. Write test cannot continue.")
            return # Cannot proceed if directory cannot be created
    else:
        log_message(f"Log directory '{log_dir_path}' already exists.", level="INFO")
        add_test_result(category_name, f"Log Directory Existence ({log_dir_relative})", "PASS", f"Directory {log_dir_path} exists.")

    # Step 2: Attempt to create and write file
    try:
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        log_message(f"Successfully wrote to test file: {test_file_path}", level="INFO")
        add_test_result(category_name, f"Log File Write ({log_dir_relative})", "PASS", "Successfully wrote test file.")
    except Exception as e:
        log_message(f"Failed to write to test file {test_file_path}: {e}", level="ERROR")
        add_test_result(category_name, f"Log File Write ({log_dir_relative})", "FAIL", f"Failed to write to {test_file_path}: {e}")
        return # Cannot proceed if write fails

    # Step 3: Attempt to read and verify file content
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            read_content = f.read()
        if read_content == test_content:
            log_message(f"Successfully read and verified content of test file: {test_file_path}", level="INFO")
            add_test_result(category_name, f"Log File Read/Verify ({log_dir_relative})", "PASS", "Read content matches written content.")
        else:
            log_message(f"Content mismatch in test file {test_file_path}. Expected: '{test_content}', Got: '{read_content}'", level="ERROR")
            add_test_result(category_name, f"Log File Read/Verify ({log_dir_relative})", "FAIL", "Read content does not match written content.")
    except Exception as e:
        log_message(f"Failed to read or verify test file {test_file_path}: {e}", level="ERROR")
        add_test_result(category_name, f"Log File Read/Verify ({log_dir_relative})", "FAIL", f"Failed to read/verify {test_file_path}: {e}")

    # Step 4: Attempt to delete the temporary file
    try:
        os.remove(test_file_path)
        log_message(f"Successfully deleted test file: {test_file_path}", level="INFO")
        add_test_result(category_name, f"Log File Cleanup ({log_dir_relative})", "PASS", "Successfully deleted test file.")
    except Exception as e:
        log_message(f"Failed to delete test file {test_file_path}: {e}", level="ERROR")
        add_test_result(category_name, f"Log File Cleanup ({log_dir_relative})", "FAIL", f"Failed to delete {test_file_path}: {e}")


# --- New Function: test_api_key_reading ---
def test_api_key_reading():
    log_message("Running API Key Reading tests (Colab Secrets)...")
    category_name = "API Keys and Secrets"

    # Test Case 1: Key Exists
    log_message("Test Case 1: Colab Secret Read - Key Exists", level="DEBUG")
    setup_mock_userdata({"TEST_GEMINI_KEY_EXISTS": "fake_gemini_key_value"})
    try:
        key_value = userdata.get("TEST_GEMINI_KEY_EXISTS")
        if key_value == "fake_gemini_key_value":
            add_test_result(category_name, "Colab Secret Read - Key Exists", "PASS", "Successfully retrieved mock key.")
        else:
            add_test_result(category_name, "Colab Secret Read - Key Exists", "FAIL", f"Retrieved incorrect value: {key_value}")
    except Exception as e:
        add_test_result(category_name, "Colab Secret Read - Key Exists", "FAIL", f"Error getting key: {e}")

    # Test Case 2: Key Missing (causes SecretNotFoundError)
    log_message("Test Case 2: Colab Secret Read - Key Missing (Error Handling)", level="DEBUG")
    setup_mock_userdata({"TEST_GEMINI_KEY_MISSING": errors.SecretNotFoundError})
    try:
        # This call should raise errors.SecretNotFoundError (mocked version)
        userdata.get("TEST_GEMINI_KEY_MISSING")
        # If it doesn't raise, it's a fail for this test's expectation
        add_test_result(category_name, "Colab Secret Read - Key Missing (Error Handling)", "FAIL", "SecretNotFoundError was not raised as expected.")
    except errors.SecretNotFoundError:
        add_test_result(category_name, "Colab Secret Read - Key Missing (Error Handling)", "PASS", "Correctly caught SecretNotFoundError.")
    except Exception as e:
        add_test_result(category_name, "Colab Secret Read - Key Missing (Error Handling)", "FAIL", f"Caught unexpected error: {e}")

    # Test Case 3: Application's API Key Retrieval Logic (Simplified)
    log_message("Test Case 3: Application Key Logic - Key Missing Graceful Handling (Conceptual)", level="DEBUG")
    # This test is conceptual for this script. It checks if the application's key retrieval
    # (if it were called) would interact correctly with a missing key via the mocked userdata.
    # We simulate this by directly calling userdata.get with a config that would make a real app function
    # receive a None or raise an error.
    # For this subtask, we focus on the mock's behavior.
    # A more advanced test would try to import and call `app.core.config.get_gemini_api_key()`
    # after setting up the mock.

    setup_mock_userdata({"APP_GEMINI_KEY": errors.SecretNotFoundError}) # Simulate key not set in Colab
    app_key_value = None
    # app_error_caught = False # Not strictly needed with current structure
    try:
        # In a real scenario, this would be: app_key_value = some_app_config_function()
        # Here, we directly test the mock's behavior as if the app called it.
        app_key_value = userdata.get("APP_GEMINI_KEY", default=None) # Common pattern: provide a default
        if app_key_value is None and MOCK_SECRET_NOT_FOUND_ERROR_OCCURRED: # Check if our mock error was hit internally by userdata.get
             add_test_result(category_name, "App Logic - Key Missing (Simulated)", "PASS",
                            "userdata.get with default=None returned None for missing key, as expected for graceful app handling.")
        elif app_key_value is None: # Key was not in MOCK_COLAB_USERDATA_STORE, and default=None was used
             add_test_result(category_name, "App Logic - Key Missing (Simulated)", "PASS",
                            "userdata.get returned default None as expected (key not in mock store and no specific error configured).")
        else: # Key was found in store and was not an error, or some other default was returned.
            add_test_result(category_name, "App Logic - Key Missing (Simulated)", "FAIL",
                            f"userdata.get returned a value ('{app_key_value}') when None or error was expected for 'APP_GEMINI_KEY'.")

    except errors.SecretNotFoundError:
        # This path would be taken if the app's function didn't provide a default to userdata.get()
        # AND "APP_GEMINI_KEY" was configured to raise SecretNotFoundError explicitly
        add_test_result(category_name, "App Logic - Key Missing (Simulated)", "PASS",
                        "userdata.get raised SecretNotFoundError as expected (app function might propagate this or handle it).")
        # app_error_caught = True # For clarity in logging
    except Exception as e:
        add_test_result(category_name, "App Logic - Key Missing (Simulated)", "FAIL", f"Unexpected error: {e}")

    add_test_result(category_name, "Application Key Logic - Note", "INFO",
                    "This test simulates app's interaction with Colab secrets. True app-level graceful handling (e.g., returning defaults, custom errors) should be verified via app's own unit/integration tests or manual checks.")


# --- New Function: check_requirements_integrity ---
def check_requirements_integrity():
    log_message("Running Requirements Integrity Check...")
    category_name = "Dependency Integrity"
    project_app_dir = os.path.join(PROJECT_DIR, "app")
    project_components_dir = os.path.join(PROJECT_DIR, "components")
    py_files = []

    for dir_path in [project_app_dir, project_components_dir]:
        if not os.path.exists(dir_path):
            log_message(f"Directory not found: {dir_path}", level="WARN")
            add_test_result(category_name, f"Directory Scan: {os.path.basename(dir_path)}", "WARN", f"{dir_path} not found, skipping scan for this directory.")
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

    if not py_files:
        add_test_result(category_name, "Python File Scan", "WARN", "No Python files found in app/ or components/.")
        return

    # Standard library modules (a basic list, can be expanded)
    # NOTE: `ast` module recommends sys.stdlib_module_names (Python 3.10+)
    # For broader compatibility, a predefined list is used here.
    stdlib_modules = {
        "os", "sys", "json", "re", "datetime", "time", "subprocess", "shutil",
        "signal", "importlib", "collections", "itertools", "functools", "math",
        "logging", "pathlib", "typing", "abc", "argparse", "base64", "binascii",
        "calendar", "configparser", "contextlib", "copy", "csv", "ctypes",
        "dataclasses", "decimal", "difflib", "dis", "enum", "filecmp", "fileinput",
        "fnmatch", "fractions", "ftplib", "getopt", "getpass", "gettext", "glob",
        "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib", "inspect",
        "io", "ipaddress", "keyword", "locale", "lzma", "mailbox", "mimetypes",
        "multiprocessing", "netrc", "nntplib", "operator", "optparse", "pickle",
        "pickletools", "pkgutil", "platform", "plistlib", "poplib", "pprint",
        "profile", "pstats", "pty", "py_compile", "pyclbr", "pydoc", "queue",
        "quopri", "random", "readline", "reprlib", "resource", "rlcompleter",
        "sched", "secrets", "select", "selectors", "shelve", "shlex", "smtpd",
        "smtplib", "sndhdr", "socket", "socketserver", "sqlite3", "ssl", "stat",
        "statistics", "string", "stringprep", "struct", "symtable", "tarfile",
        "telnetlib", "tempfile", "termios", "textwrap", "threading", "tkinter",
        "token", "tokenize", "trace", "traceback", "tracemalloc", "tty", "turtle",
        "types", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "wsgiref", "xdrlib", "xml",
        "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
        # Project specific modules to ignore (if any, based on project structure)
        "app", "components", "services", "utils", "backend" # Assuming these are top-level project dirs/modules
    }


    imported_modules = set()
    # Regex to find imports: import library or from library import ...
    # This is a simplified regex and might not catch all import styles (e.g., import library.submodule as alias)
    import_regex = re.compile(r"^\s*(?:import\s+([a-zA-Z0-9_]+)|from\s+([a-zA-Z0-9_]+)\s+import)")

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line in f:
                    match = import_regex.match(line)
                    if match:
                        # Group 1 for "import X", Group 2 for "from X import Y"
                        module_name = match.group(1) or match.group(2)
                        if module_name and module_name not in stdlib_modules:
                            # Normalize: lowercase, treat underscore as hyphen for comparison (common in reqs.txt)
                            normalized_name = module_name.lower().replace("_", "-")
                            imported_modules.add(normalized_name)
        except Exception as e:
            log_message(f"Error reading/parsing {py_file}: {e}", level="ERROR")
            add_test_result(category_name, "File Parsing", "FAIL", f"Error processing {os.path.basename(py_file)}: {e}")

    if not imported_modules:
        add_test_result(category_name, "Imported Module Extraction", "WARN", "No third-party modules found or regex needs refinement.")
    else:
        add_test_result(category_name, "Imported Module Extraction", "INFO", f"Found potential third-party modules: {', '.join(sorted(list(imported_modules)))}")


    requirements_path = os.path.join(PROJECT_DIR, "requirements.txt")
    if not os.path.exists(requirements_path):
        add_test_result(category_name, "Requirements File Check", "FAIL", "requirements.txt not found.")
        return

    requirements_packages = set()
    try:
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Remove version specifiers (e.g., ==1.2.3, >=1.0) and comments
                package_name = re.split(r"[<>=!~;#]", line, 1)[0].strip()
                if package_name:
                    # Normalize: lowercase, treat underscore as hyphen
                    normalized_package = package_name.lower().replace("_", "-")
                    requirements_packages.add(normalized_package)
    except Exception as e:
        add_test_result(category_name, "Requirements File Read", "FAIL", f"Error reading requirements.txt: {e}")
        return

    if not requirements_packages:
        add_test_result(category_name, "Requirements Package Extraction", "WARN", "No packages found in requirements.txt.")
    else:
         add_test_result(category_name, "Requirements Package Extraction", "INFO", f"Found packages in requirements.txt: {', '.join(sorted(list(requirements_packages)))}")


    missing_in_requirements = imported_modules - requirements_packages
    # Unused_in_code = requirements_packages - imported_modules # Harder to be accurate, focus on missing

    if not missing_in_requirements and not imported_modules and not requirements_packages:
         add_test_result(category_name, "Requirements Integrity", "INFO", "No imports or requirements to compare.")
    elif not missing_in_requirements:
        add_test_result(category_name, "Requirements Integrity", "PASS", "All detected third-party imports seem to be in requirements.txt.")
    else:
        add_test_result(category_name, "Requirements Integrity", "WARN",
                        f"Modules imported but potentially missing from requirements.txt: {', '.join(sorted(list(missing_in_requirements)))}."
                        " (Note: This check is based on regex and may have false positives/negatives. Review manually.)")

    # Optional: Check for unused packages (less reliable)
    # if unused_in_code:
    #     add_test_result(category_name, "Potentially Unused Packages", "INFO",
    #                     f"Packages in requirements.txt not detected as imported: {', '.join(unused_in_code)}. "
    #                     "(Note: This check is heuristic and may not be fully accurate.)")

# --- New Function: verify_core_package_imports ---
def verify_core_package_imports():
    log_message("Running Core Package Import Verification...")
    category_name = "Dependency Integrity"
    core_packages = [
        "streamlit", "google.generativeai", "fastapi", "uvicorn",
        "pandas", "yfinance", "fredapi", "requests", "jose", "passlib"
    ]
    all_successful = True
    details = []

    # Ensure PROJECT_DIR is in path if project modules need to be resolved by core packages
    # (e.g. if a core package tries to import something from the project itself upon its own import)
    original_sys_path = list(sys.path)
    if PROJECT_DIR not in sys.path:
        sys.path.insert(0, PROJECT_DIR)
        path_modified = True
    else:
        path_modified = False

    for package_name in core_packages:
        try:
            importlib.import_module(package_name)
            log_message(f"Successfully imported core package: {package_name}", level="INFO")
            details.append(f"{package_name}: Import Success")
            add_test_result(category_name, f"Core Import: {package_name}", "PASS")
        except ImportError as e:
            log_message(f"Failed to import core package: {package_name}. Error: {e}", level="ERROR")
            details.append(f"{package_name}: Import FAIL ({e})")
            add_test_result(category_name, f"Core Import: {package_name}", "FAIL", details=str(e))
            all_successful = False
        except Exception as e_other: # Catch other potential errors during import
            log_message(f"Error importing core package {package_name}: {e_other}", level="ERROR")
            details.append(f"{package_name}: Import Error ({e_other})")
            add_test_result(category_name, f"Core Import: {package_name}", "FAIL", details=f"Other error: {e_other}")
            all_successful = False

    if path_modified: # Restore sys.path
        sys.path = original_sys_path

    overall_status = "PASS" if all_successful else "FAIL"
    add_test_result(category_name, "Overall Core Package Importability", overall_status, details=", ".join(details))


# --- Phase 2: Test Execution ---
def phase_2_tests(project_clone_successful):
    log_message("--- Phase 2: Test Execution ---")

    # Colab Environment Checks (condensed from v2)
    log_message("Running Colab Environment checks...")
    add_test_result("Colab Environment", "Python Version", "INFO", value=sys.version.replace("\n", ""))

    # Google Drive Accessibility Test
    test_google_drive_accessibility()

    # Note on run_in_colab.ipynb logic
    add_test_result("External Script Validations", "run_in_colab.ipynb Drive Logic", "INFO",
                    "The comprehensive Drive mount success/failure path switching logic within `run_in_colab.ipynb` "
                    "(including user interaction for auth and fallback to local paths) is best verified by manually "
                    "executing `run_in_colab.ipynb` under different conditions (e.g., accepting/rejecting Drive authorization).")

    try: # CPU
        stdout, _, rc = run_shell_command(["lscpu"])
        if rc==0: add_test_result("Colab Environment","CPU Info","INFO",value=f"Model: {re.search(r'Model name:\s*(.*)',stdout).group(1).strip() if re.search(r'Model name:\s*(.*)',stdout) else 'N/A'} | CPUs: {re.search(r'CPU\(s\):\s*(\d+)',stdout).group(1).strip() if re.search(r'CPU\(s\):\s*(\d+)',stdout) else 'N/A'}")
        else: add_test_result("Colab Environment","CPU Info","FAIL",details=f"lscpu failed (RC:{rc})")
    except Exception as e: add_test_result("Colab Environment","CPU Info","FAIL",details=str(e))
    try: # Memory
        stdout, _, rc = run_shell_command(["cat","/proc/meminfo"])
        if rc==0: add_test_result("Colab Environment","Memory Info","INFO",value=f"Total: {re.search(r'MemTotal:\s*(.*)',stdout).group(1).strip()} | Available: {re.search(r'MemAvailable:\s*(.*)',stdout).group(1).strip()}")
        else: add_test_result("Colab Environment","Memory Info","FAIL",details="cat /proc/meminfo failed")
    except Exception as e: add_test_result("Colab Environment","Memory Info","FAIL",details=str(e))
    try: # Disk
        stdout, _, rc = run_shell_command(["df","-h","/"])
        if rc==0 and len(stdout.strip().split("\n")) > 1: parts = stdout.strip().split("\n")[1].split(); add_test_result("Colab Environment","Disk Space (/)","INFO",value=f"Device: {parts[0]}, Total: {parts[1]}, Used: {parts[2]}, Avail: {parts[3]}")
        else: add_test_result("Colab Environment","Disk Space (/)","FAIL",details="df -h / failed or output unexpected")
    except Exception as e: add_test_result("Colab Environment","Disk Space (/)","FAIL",details=str(e))
    try: # GPU
        stdout, stderr, rc = run_shell_command(["nvidia-smi"])
        if rc==0: gpu_name = (re.search(r"Product Name:\s*([^\s|]+)",stdout) or re.search(r"\|\s+\d+\s+([^|]+?)\s+(On|Off)\s+",stdout)); gpu_name = gpu_name.group(1).strip() if gpu_name else "GPU Found"; vram = re.search(r"(\d+MiB)\s*/\s*(\d+MiB)",stdout); vram_info = f" (VRAM: {vram.group(1)}/{vram.group(2)})" if vram else ""; add_test_result("Colab Environment","GPU Status","INFO",value=f"{gpu_name}{vram_info}",details=stdout[:300])
        elif rc==127: add_test_result("Colab Environment","GPU Status","WARN",value="nvidia-smi not found")
        else: add_test_result("Colab Environment","GPU Status","INFO",value="No GPU or nvidia-smi error",details=f"RC:{rc}, Err:{stderr}")
    except Exception as e: add_test_result("Colab Environment","GPU Status","FAIL",details=str(e))

    if not project_clone_successful:
        log_message("Skipping tests that depend on project clone.", level="WARN")
        add_test_result("Project Structure and Dependencies", "Key File Checks", "N/A", "Project clone failed.")
        add_test_result("Frontend (Streamlit) Integrity", "All Checks", "N/A", "Project clone failed.")
        add_test_result("Backend (FastAPI) Server", "All Checks", "N/A", "Project clone failed.")
        return

    log_message("Running Project Structure and Dependencies checks (File/Dir existence)...")
    key_paths = ["app.py", "backend/main.py", "requirements.txt", "components/", "services/", "utils/", "style.css", "prompts.toml", ".streamlit/config.toml"]
    for path in key_paths:
        status = "PASS" if os.path.exists(os.path.join(PROJECT_DIR, path)) else "FAIL"
        add_test_result("Project Structure and Dependencies", f"Check Path: {path}", status, value=f"{path} {'exists' if status=='PASS' else 'NOT found'}")

    # Frontend (Streamlit) Integrity Checks
    log_message("Running Frontend (Streamlit) Integrity checks...")
    app_py_path = os.path.join(PROJECT_DIR, "app.py")
    app_py_syntax_ok = False
    if os.path.exists(app_py_path):
        try:
            with open(app_py_path, 'r', encoding='utf-8') as f: app_code = f.read()
            compile(app_code, 'app.py', 'exec')
            add_test_result("Frontend (Streamlit) Integrity", "app.py Syntax Check", "PASS")
            app_py_syntax_ok = True
        except SyntaxError as e:
            add_test_result("Frontend (Streamlit) Integrity", "app.py Syntax Check", "FAIL", details=f"SyntaxError: {e}")
        except Exception as e:
            add_test_result("Frontend (Streamlit) Integrity", "app.py Syntax Check", "FAIL", details=f"Error compiling app.py: {e}")
    else:
        add_test_result("Frontend (Streamlit) Integrity", "app.py Syntax Check", "FAIL", details="app.py not found.")

    if app_py_syntax_ok:
        log_message("Checking local module import paths from app.py...")
        # Simplified regex for top-level local imports
        # For a real check, AST parsing would be more robust.
        local_import_pattern = r"^\s*(?:from\s+([a-zA-Z0-9_]+)(?:\.[a-zA-Z0-9_]+)*\s+import|import\s+([a-zA-Z0-9_]+))"
        found_modules = set()
        try:
            with open(app_py_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = re.match(local_import_pattern, line)
                    if match:
                        # Match group 1 for "from X import Y", group 2 for "import X"
                        module_name = match.group(1) or match.group(2)
                        # Consider only likely project-local modules (heuristic)
                        if os.path.exists(os.path.join(PROJECT_DIR, module_name)) or \
                           os.path.exists(os.path.join(PROJECT_DIR, module_name + ".py")):
                            found_modules.add(module_name)

            if not found_modules:
                 add_test_result("Frontend (Streamlit) Integrity", "Local Module Import Paths", "WARN", "No obvious local module imports found or regex needs refinement.")
            else:
                sys.path.insert(0, PROJECT_DIR)
                all_found_spec = True
                details_list = []
                for module_name in found_modules:
                    try:
                        spec = importlib.util.find_spec(module_name)
                        if spec and spec.loader:
                            details_list.append(f"{module_name}: Found")
                        else:
                            all_found_spec = False
                            details_list.append(f"{module_name}: NOT Found by importlib")
                            log_message(f"Could not find spec for local module: {module_name}", level="WARN")
                    except ModuleNotFoundError:
                        all_found_spec = False
                        details_list.append(f"{module_name}: ModuleNotFoundError")
                        log_message(f"ModuleNotFoundError for local module: {module_name}", level="WARN")
                    except Exception as e_spec:
                        all_found_spec = False
                        details_list.append(f"{module_name}: Error ({e_spec})")
                        log_message(f"Error finding spec for {module_name}: {e_spec}", level="ERROR")

                sys.path.pop(0) # Clean up sys.path
                status = "PASS" if all_found_spec else "FAIL"
                add_test_result("Frontend (Streamlit) Integrity", "Local Module Import Paths", status, details=", ".join(details_list) if details_list else "No local modules parsed.")

        except Exception as e_parse:
            add_test_result("Frontend (Streamlit) Integrity", "Local Module Import Paths", "FAIL", details=f"Error parsing app.py for imports: {e_parse}")
            if PROJECT_DIR in sys.path: sys.path.pop(0) # Ensure cleanup
    else:
        add_test_result("Frontend (Streamlit) Integrity", "Local Module Import Paths", "SKIPPED", "app.py syntax check failed.")

    style_css_path = os.path.join(PROJECT_DIR, "style.css")
    status_css = "PASS" if os.path.exists(style_css_path) else "WARN" # style.css might be optional for basic functionality
    add_test_result("Frontend (Streamlit) Integrity", "style.css Existence", status_css, value="style.css found" if status_css=="PASS" else "style.css not found (may be optional)")


    # API Keys and External Connectivity (condensed from v2)
    log_message("Running API Keys and External Connectivity checks...")
    gemini_key = os.environ.get("COLAB_GOOGLE_API_KEY_FOR_TEST")
    if gemini_key:
        try: r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",timeout=10); add_test_result("API Keys and External Connectivity","Google Gemini API Key","PASS" if r.status_code==200 else "FAIL",f"Status:{r.status_code}")
        except Exception as e: add_test_result("API Keys and External Connectivity","Google Gemini API Key","FAIL",str(e))
    else: add_test_result("API Keys and External Connectivity","Google Gemini API Key","WARN","COLAB_GOOGLE_API_KEY_FOR_TEST not set.")
    fred_key = os.environ.get("COLAB_FRED_API_KEY_FOR_TEST")
    if fred_key:
        try: r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=GNPCA&api_key={fred_key}&file_type=json&limit=1",timeout=15); add_test_result("API Keys and External Connectivity","FRED API Key","PASS" if r.status_code==200 and "observations" in r.json() else "FAIL",f"Status:{r.status_code}, Valid JSON: {'observations' in r.json() if r.status_code==200 else 'N/A'}")
        except Exception as e: add_test_result("API Keys and External Connectivity","FRED API Key","FAIL",str(e))
    else: add_test_result("API Keys and External Connectivity","FRED API Key","WARN","COLAB_FRED_API_KEY_FOR_TEST not set.")
    for name,url in {"Google GenAI":"https://generativelanguage.googleapis.com","FRED API":"https://api.stlouisfed.org"}.items():
        try: r = requests.get(url,timeout=10); add_test_result("API Keys and External Connectivity",f"Connectivity: {name}","PASS" if r.status_code in [200,404] else "FAIL",f"Status:{r.status_code}")
        except Exception as e: add_test_result("API Keys and External Connectivity",f"Connectivity: {name}","FAIL",str(e))

    # Backend (FastAPI) Server Tests (condensed from v2)
    global fastapi_process, test_api_auth_token # Ensure global token is accessible
    api_category_name = "Backend API Endpoints"
    error_handling_category_name = "Error Handling"

    # --- Logic for temporary modification of health.py for error handling test ---
    health_router_path = os.path.join(PROJECT_DIR, "backend/app/routers/health.py")
    original_health_router_content = None
    modified_for_error_test = False

    if os.path.exists(health_router_path):
        try:
            log_message(f"Reading original content of {health_router_path} for error handling test setup.", level="DEBUG")
            with open(health_router_path, 'r', encoding='utf-8') as f:
                original_health_router_content = f.read()

            # Prepare modified content
            # Add Header import: from fastapi import APIRouter, Header
            # Modify signature: async def health_check(): -> async def health_check(x_test_trigger_error: str = Header(None)):
            # Add error trigger: if x_test_trigger_error == "true": raise Exception(...)

            temp_content = original_health_router_content
            if "from fastapi import APIRouter, Header" not in temp_content:
                 if "from fastapi import APIRouter" in temp_content:
                     temp_content = temp_content.replace("from fastapi import APIRouter", "from fastapi import APIRouter, Header", 1)
                 else: # Less likely, but as a fallback
                     temp_content = "from fastapi import Header\n" + temp_content

            # Make signature change more robust by targeting the line
            lines = temp_content.split('\n')
            new_lines = []
            injected_if = False
            signature_modified = False
            health_check_func_name = "async def health_check(" # Target this

            for i, line in enumerate(lines):
                if health_check_func_name in line and not signature_modified:
                    new_lines.append(line.replace("):", ", x_test_trigger_error: str = Header(None)):", 1))
                    signature_modified = True
                elif signature_modified and "return {" in line and not injected_if : # Assuming return is the last substantive line before modification
                    # Inject before the return statement
                    new_lines.append("    # Added by health check for error handling test")
                    new_lines.append("    if x_test_trigger_error == \"true\":")
                    new_lines.append("        raise Exception(\"Simulated unhandled error for health check testing\")")
                    new_lines.append(line)
                    injected_if = True
                else:
                    new_lines.append(line)

            if signature_modified and injected_if:
                modified_content = "\n".join(new_lines)
                log_message(f"Temporarily modifying {health_router_path} to enable error trigger.", level="INFO")
                with open(health_router_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                modified_for_error_test = True
                # log_message(f"Modified content for {health_router_path}:\n{modified_content}", level="DEBUG") # For verbose debugging
            else:
                log_message(f"Failed to prepare modified content for {health_router_path}. Signature or return line not found as expected. Skipping modification.", level="ERROR")
                add_test_result(error_handling_category_name, "FastAPI Global Error Handler Setup", "FAIL", "Could not modify health.py for test.")
                original_health_router_content = None # Ensure no revert if modification failed

        except Exception as e_modify:
            log_message(f"Error during pre-test modification of {health_router_path}: {e_modify}", level="ERROR")
            add_test_result(error_handling_category_name, "FastAPI Global Error Handler Setup", "FAIL", f"Error modifying health.py: {e_modify}")
            original_health_router_content = None # Ensure no revert
    else:
        log_message(f"{health_router_path} not found. Skipping global error handler test that requires its modification.", level="WARN")
        add_test_result(error_handling_category_name, "FastAPI Global Error Handler Setup", "SKIPPED", f"{os.path.basename(health_router_path)} not found.")


    # --- Start FastAPI Server (potentially with modified code) ---
    log_message("Running Backend (FastAPI) Server checks...")
    os.makedirs(os.path.dirname(FASTAPI_LOG_PATH), exist_ok=True)
    if os.path.exists(FASTAPI_LOG_PATH): os.remove(FASTAPI_LOG_PATH)

    fastapi_cmd_str = f"nohup {sys.executable} -m uvicorn backend.main:app --host 0.0.0.0 --port {FASTAPI_PORT} --app-dir {PROJECT_DIR} > {FASTAPI_LOG_PATH} 2>&1 &"
    server_started_ok = False
    try:
        log_message(f"Starting FastAPI server (Port: {FASTAPI_PORT})...")
        fastapi_process = subprocess.Popen(fastapi_cmd_str, shell=True, cwd=PROJECT_DIR)
        log_message(f"FastAPI shell process PID: {fastapi_process.pid}. Waiting 15s...")
        time.sleep(15)

        log_ok = os.path.exists(FASTAPI_LOG_PATH) and os.path.getsize(FASTAPI_LOG_PATH) > 0
        log_content_sample = ""
        if log_ok:
            with open(FASTAPI_LOG_PATH, 'r', encoding='utf-8') as f: log_content_sample = f.read(500)
            if "Uvicorn running on" in log_content_sample or "Application startup complete" in log_content_sample:
                server_started_ok = True
                add_test_result(api_category_name, "Server Startup (Log Check)", "PASS", "Startup message in log.", value=log_content_sample)
            else:
                add_test_result(api_category_name, "Server Startup (Log Check)", "FAIL", "Startup message NOT in log.", value=log_content_sample)
        else:
            add_test_result(api_category_name, "Server Startup (Log Check)", "FAIL", "Log file not found or empty.")

        if not server_started_ok:
            try:
                r = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=5)
                if r.status_code == 200:
                    server_started_ok = True
                    add_test_result(api_category_name, "Server Startup (Ping)", "PASS", "/api/health OK")
                else:
                    add_test_result(api_category_name, "Server Startup (Ping)", "FAIL", f"/api/health status: {r.status_code}")
            except requests.exceptions.ConnectionError:
                add_test_result(api_category_name, "Server Startup (Ping)", "FAIL", "Connection error to /api/health")

        if server_started_ok:
            add_test_result(api_category_name, "Overall Server Startup", "PASS")
            db_path = os.path.join(PROJECT_DIR, "AI_data/main_database.db")
            add_test_result(api_category_name, "Database Initialization Check", "PASS" if os.path.exists(db_path) else "WARN", f"DB at {db_path} {'found' if os.path.exists(db_path) else 'NOT found'}")

            # --- Basic Endpoint Tests (including the potentially modified /api/health) ---
            # Test /api/health normally (without trigger header)
            try:
                r_health_normal = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=10)
                if r_health_normal.status_code == 200 and "status" in r_health_normal.json() and r_health_normal.json()["status"] == "OK":
                    add_test_result(api_category_name, "Endpoint: /api/health (Normal)", "PASS", "Status 200, status OK.")
                else:
                    add_test_result(api_category_name, "Endpoint: /api/health (Normal)", "FAIL", f"Status: {r_health_normal.status_code}, Response: {r_health_normal.text[:100]}")
            except Exception as e_health_normal:
                add_test_result(api_category_name, "Endpoint: /api/health (Normal)", "FAIL", str(e_health_normal))

            # Test /api/config
            try:
                r_config = requests.get(f"{FASTAPI_BASE_URL}/api/config", timeout=10)
                if r_config.status_code == 200 and "PROJECT_NAME" in r_config.json():
                    add_test_result(api_category_name, "Endpoint: /api/config", "PASS", "Status 200, PROJECT_NAME found.")
                else:
                    add_test_result(api_category_name, "Endpoint: /api/config", "FAIL", f"Status: {r_config.status_code}, Response: {r_config.text[:100]}")
            except Exception as e_config:
                add_test_result(api_category_name, "Endpoint: /api/config", "FAIL", str(e_config))

            # --- Global Error Handler Test (if health.py was modified) ---
            if modified_for_error_test:
                log_message("Testing FastAPI Global Error Handler by triggering simulated error in /api/health...", level="INFO")
                try:
                    headers_trigger_error = {"X-Test-Trigger-Error": "true"}
                    r_error = requests.get(f"{FASTAPI_BASE_URL}/api/health", headers=headers_trigger_error, timeout=10)

                    # Expected: 500 status, JSON response with "detail":"Internal Server Error" or similar
                    # The exact detail message depends on the global exception handler in backend/app/core/middlewares.py
                    # For this test, we primarily check for 500 and any JSON body.
                    if r_error.status_code == 500:
                        try:
                            error_json = r_error.json()
                            # A simple check for any json response. More specific checks depend on the actual handler.
                            if error_json: # Check if JSON is not empty or null
                                add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "PASS",
                                                f"Status 500 and JSON error response received as expected. Detail: {error_json.get('detail', str(error_json))[:100]}")
                            else:
                                add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "WARN",
                                                f"Status 500 received, but JSON response was empty or null. Response text: {r_error.text[:200]}")
                        except ValueError: # Not JSON
                             add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "FAIL",
                                            f"Status 500 received, but response was not valid JSON. Response text: {r_error.text[:200]}")
                    else:
                        add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "FAIL",
                                        f"Expected status 500, but got {r_error.status_code}. Response: {r_error.text[:200]}")
                except Exception as e_global_error:
                    add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "FAIL",
                                    f"Request to trigger error failed: {e_global_error}")
            else:
                 add_test_result(error_handling_category_name, "FastAPI Global Error Handler - Unhandled Exception", "SKIPPED", "Skipped due to failure in modifying health.py or file not found.")


            # --- Continue with other API tests ---
            # (The existing tests for /api/auth/login, /api/chat/invoke, etc. follow here)
            # These should run correctly as long as they don't send the X-Test-Trigger-Error header.

            # --- FastAPI Process Check ---
            pgrep_fastapi_cmd = ["pgrep", "-f", f"uvicorn backend.main:app --port {FASTAPI_PORT}"]
            log_message(f"Checking for running FastAPI process: {' '.join(pgrep_fastapi_cmd)}", level="DEBUG")
            stdout_pg_fastapi, stderr_pg_fastapi, rc_pg_fastapi = run_shell_command(pgrep_fastapi_cmd)
            if rc_pg_fastapi == 0 and stdout_pg_fastapi.strip():
                add_test_result(api_category_name, "FastAPI Process Check - Background Running", "PASS", f"FastAPI process found (PID(s): {stdout_pg_fastapi.strip()}).")
            else:
                add_test_result(api_category_name, "FastAPI Process Check - Background Running", "WARN", f"FastAPI process NOT found via pgrep. RC:{rc_pg_fastapi}, STDOUT:'{stdout_pg_fastapi}', STDERR:'{stderr_pg_fastapi}'. Server might have exited prematurely despite log messages.")
                # This could be a more severe FAIL if previous log checks also indicated issues.

            # --- /api/auth/login Test (Enhanced) ---
            login_payload = {"apiKey": "test_colab_health_check_key_valid"} # Assuming this key is valid for tests
            log_message(f"Testing {FASTAPI_BASE_URL}/api/auth/login with payload: {login_payload}", level="DEBUG")
            try:
                r = requests.post(f"{FASTAPI_BASE_URL}/api/auth/login", json=login_payload, timeout=10)
                if r.status_code == 200 and "access_token" in r.json():
                    test_api_auth_token = r.json()["access_token"]
                    add_test_result(api_category_name, "/api/auth/login", "PASS", "Login OK, token received and stored.")
                    log_message(f"Auth token stored: {test_api_auth_token[:15]}...", level="INFO")
                else:
                    add_test_result(api_category_name, "/api/auth/login", "FAIL", f"Status {r.status_code}, token in response: {'access_token' in r.json() if r.status_code==200 else 'N/A'}. Response: {r.text[:100]}")
                    test_api_auth_token = None
            except Exception as e:
                add_test_result(api_category_name, "/api/auth/login", "FAIL", str(e))
                test_api_auth_token = None

            auth_headers = {}
            if test_api_auth_token:
                auth_headers = {"Authorization": f"Bearer {test_api_auth_token}"}
            else:
                log_message("No auth token obtained from login, authenticated endpoint tests will be skipped or may fail.", level="WARN")


            # --- /api/chat Test ---
            chat_endpoint_url = f"{FASTAPI_BASE_URL}/api/chat/invoke" # Adjusted based on typical structure
            if not test_api_auth_token:
                add_test_result(api_category_name, "Chat Endpoint - Normal Request", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "SKIPPED", "Auth token not available.")
            else:
                # Test Case: Normal Chat Request
                chat_payload_normal = {"user_message": "Hello, Wolf AI!", "chat_history": []}
                log_message(f"Testing {chat_endpoint_url} (Normal) with payload: {chat_payload_normal}", level="DEBUG")
                try:
                    r_chat_normal = requests.post(chat_endpoint_url, json=chat_payload_normal, headers=auth_headers, timeout=20)
                    if r_chat_normal.status_code == 200 and "reply" in r_chat_normal.json():
                        add_test_result(api_category_name, "Chat Endpoint - Normal Request", "PASS", "Status 200, 'reply' in response.", value=f"Reply snippet: {r_chat_normal.json()['reply'][:50]}...")
                    else:
                        add_test_result(api_category_name, "Chat Endpoint - Normal Request", "FAIL", f"Status: {r_chat_normal.status_code}, Response: {r_chat_normal.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Chat Endpoint - Normal Request", "FAIL", str(e))

                # Test Case: Invalid Chat Request
                chat_payload_invalid = {"chat_history": []} # Missing user_message
                log_message(f"Testing {chat_endpoint_url} (Invalid) with payload: {chat_payload_invalid}", level="DEBUG")
                try:
                    r_chat_invalid = requests.post(chat_endpoint_url, json=chat_payload_invalid, headers=auth_headers, timeout=10)
                    if r_chat_invalid.status_code == 422: # FastAPI default for validation errors
                        add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "PASS", "Status 422 (Unprocessable Entity) as expected for invalid payload.")
                    else:
                        add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "FAIL", f"Expected 422, Got Status: {r_chat_invalid.status_code}, Response: {r_chat_invalid.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "FAIL", str(e))


            # --- /api/data/fetch Test ---
            data_fetch_url = f"{FASTAPI_BASE_URL}/api/data/fetch"
            if not test_api_auth_token:
                add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "SKIPPED", "Auth token not available.")
            else:
                # Valid yfinance Ticker
                yf_payload_valid = {"source": "yfinance", "parameters": {"symbol": "AAPL", "period": "1d"}}
                log_message(f"Testing {data_fetch_url} (yfinance AAPL) with payload: {yf_payload_valid}", level="DEBUG")
                try:
                    r_yf_valid = requests.post(data_fetch_url, json=yf_payload_valid, headers=auth_headers, timeout=15)
                    if r_yf_valid.status_code == 200 and r_yf_valid.json().get("success") and not r_yf_valid.json().get("is_cached"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "PASS", "Status 200, success:true, is_cached:false.", value=f"Data sample: {str(r_yf_valid.json().get('data'))[:50]}...")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "FAIL", f"Status: {r_yf_valid.status_code}, Response: {r_yf_valid.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "FAIL", str(e))

                # yfinance Cache Check
                log_message(f"Testing {data_fetch_url} (yfinance AAPL Cache) with payload: {yf_payload_valid}", level="DEBUG")
                try:
                    r_yf_cache = requests.post(data_fetch_url, json=yf_payload_valid, headers=auth_headers, timeout=15)
                    if r_yf_cache.status_code == 200 and r_yf_cache.json().get("success") and r_yf_cache.json().get("is_cached"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "PASS", "Status 200, success:true, is_cached:true.")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "FAIL", f"Status: {r_yf_cache.status_code}, Response: {r_yf_cache.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "FAIL", str(e))

                # Invalid yfinance Ticker
                yf_payload_invalid = {"source": "yfinance", "parameters": {"symbol": "INVALIDTICKERXYZ", "period": "1d"}}
                log_message(f"Testing {data_fetch_url} (yfinance Invalid) with payload: {yf_payload_invalid}", level="DEBUG")
                try:
                    r_yf_invalid = requests.post(data_fetch_url, json=yf_payload_invalid, headers=auth_headers, timeout=15)
                    # Expecting success:false or some specific error structure within a 200, or a 4xx/5xx
                    if r_yf_invalid.status_code == 200 and not r_yf_invalid.json().get("success"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "PASS", "Status 200, success:false as expected for invalid ticker.")
                    elif r_yf_invalid.status_code >= 400: # Or if it returns a client/server error status
                         add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "PASS", f"Status {r_yf_invalid.status_code} as expected for invalid ticker.")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "FAIL", f"Status: {r_yf_invalid.status_code}, Response: {r_yf_invalid.text[:200]}. Expected success:false or error status.")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "FAIL", str(e))

            # --- Test FRED API data source via /api/data/fetch ---
            if not test_api_auth_token:
                add_test_result(api_category_name, "Data Fetch - FRED Valid Series (GNPCA)", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - FRED Invalid Series", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - FRED Cache Check (GNPCA)", "SKIPPED", "Auth token not available.")
            else:
                # Valid FRED Series
                fred_payload_valid = {"source": "fred", "parameters": {"series_id": "GNPCA", "limit": 5}} # Add limit for manageable response
                log_message(f"Testing {data_fetch_url} (FRED GNPCA) with payload: {fred_payload_valid}", level="DEBUG")
                try:
                    r_fred_valid = requests.post(data_fetch_url, json=fred_payload_valid, headers=auth_headers, timeout=20) # FRED can be slow
                    if r_fred_valid.status_code == 200 and r_fred_valid.json().get("success") and r_fred_valid.json().get("data") and not r_fred_valid.json().get("is_cached"):
                        # Add more specific check for data structure if possible, e.g., list of observations
                        data_sample = r_fred_valid.json().get("data")
                        data_looks_ok = isinstance(data_sample, list) and len(data_sample) > 0 and "date" in data_sample[0] and "value" in data_sample[0]
                        if data_looks_ok:
                            add_test_result(api_category_name, "Data Fetch - FRED Valid Series (GNPCA)", "PASS", "Status 200, success:true, data present, is_cached:false.", value=f"Data sample: {str(data_sample)[:70]}...")
                        else:
                            add_test_result(api_category_name, "Data Fetch - FRED Valid Series (GNPCA)", "WARN", "Status 200, success:true, but data format unexpected or empty.", value=f"Response: {r_fred_valid.text[:200]}")
                    else:
                        add_test_result(api_category_name, "Data Fetch - FRED Valid Series (GNPCA)", "FAIL", f"Status: {r_fred_valid.status_code}, Response: {r_fred_valid.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - FRED Valid Series (GNPCA)", "FAIL", str(e))

                # FRED Cache Check (GNPCA)
                log_message(f"Testing {data_fetch_url} (FRED GNPCA Cache) with payload: {fred_payload_valid}", level="DEBUG")
                try:
                    r_fred_cache = requests.post(data_fetch_url, json=fred_payload_valid, headers=auth_headers, timeout=20)
                    if r_fred_cache.status_code == 200 and r_fred_cache.json().get("success") and r_fred_cache.json().get("is_cached"):
                        add_test_result(api_category_name, "Data Fetch - FRED Cache Check (GNPCA)", "PASS", "Status 200, success:true, is_cached:true.")
                    else:
                        # If cache is not implemented for FRED, this might be an expected fail/warn.
                        # For now, assume cache SHOULD work if yfinance caching works.
                        add_test_result(api_category_name, "Data Fetch - FRED Cache Check (GNPCA)", "FAIL", f"Expected cached result. Status: {r_fred_cache.status_code}, Response: {r_fred_cache.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - FRED Cache Check (GNPCA)", "FAIL", str(e))

                # Invalid FRED Series
                fred_payload_invalid = {"source": "fred", "parameters": {"series_id": "INVALIDFREDIDXYZ"}}
                log_message(f"Testing {data_fetch_url} (FRED Invalid) with payload: {fred_payload_invalid}", level="DEBUG")
                try:
                    r_fred_invalid = requests.post(data_fetch_url, json=fred_payload_invalid, headers=auth_headers, timeout=20)
                    if r_fred_invalid.status_code == 200 and not r_fred_invalid.json().get("success"):
                        add_test_result(api_category_name, "Data Fetch - FRED Invalid Series", "PASS", "Status 200, success:false as expected for invalid series.")
                    elif r_fred_invalid.status_code >= 400 : # Or if it returns a client/server error status for invalid series
                         add_test_result(api_category_name, "Data Fetch - FRED Invalid Series", "PASS", f"Status {r_fred_invalid.status_code} (error) as expected for invalid series.")
                    else:
                        add_test_result(api_category_name, "Data Fetch - FRED Invalid Series", "FAIL", f"Status: {r_fred_invalid.status_code}, Response: {r_fred_invalid.text[:200]}. Expected success:false or error status.")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - FRED Invalid Series", "FAIL", str(e))

            # --- /api/files/upload Test ---
            file_upload_url = f"{FASTAPI_BASE_URL}/api/files/upload"
            dummy_file_content = "This is a health check dummy upload file."
            dummy_file_name = "health_check_upload_test.txt"
            # Ensure logs dir exists from pytest setup, or use PROJECT_DIR
            logs_dir_path = os.path.join(PROJECT_DIR, "logs")
            if not os.path.exists(logs_dir_path): os.makedirs(logs_dir_path, exist_ok=True) # Should exist from pytest, but ensure
            dummy_file_path = os.path.join(logs_dir_path, dummy_file_name)

            if not test_api_auth_token:
                add_test_result(api_category_name, "File Upload - Successful Upload", "SKIPPED", "Auth token not available.")
            else:
                try:
                    with open(dummy_file_path, "w") as f: f.write(dummy_file_content)
                    log_message(f"Testing {file_upload_url} with file: {dummy_file_path}", level="DEBUG")
                    with open(dummy_file_path, "rb") as f_rb:
                        files_payload = {'upload_file': (dummy_file_name, f_rb, 'text/plain')}
                        r_upload = requests.post(file_upload_url, files=files_payload, headers=auth_headers, timeout=15)

                    if r_upload.status_code == 200 and r_upload.json().get("success") and r_upload.json().get("file_id"):
                        add_test_result(api_category_name, "File Upload - Successful Upload", "PASS", "Status 200, success:true, file_id present.", value=f"File ID: {r_upload.json()['file_id']}")
                    else:
                        add_test_result(api_category_name, "File Upload - Successful Upload", "FAIL", f"Status: {r_upload.status_code}, Response: {r_upload.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "File Upload - Successful Upload", "FAIL", str(e))
                finally:
                    if os.path.exists(dummy_file_path): os.remove(dummy_file_path)


            # --- /api/db/backup Test ---
            db_backup_url = f"{FASTAPI_BASE_URL}/api/db/backup"
            if not test_api_auth_token:
                add_test_result(api_category_name, "Database Backup - Successful Backup", "SKIPPED", "Auth token not available.")
            else:
                backup_file_path_from_api = None
                try:
                    log_message(f"Testing {db_backup_url}", level="DEBUG")
                    r_backup = requests.post(db_backup_url, headers=auth_headers, timeout=20) # Backup can take time
                    if r_backup.status_code == 200 and r_backup.json().get("success") and r_backup.json().get("backup_path"):
                        backup_file_path_from_api = r_backup.json()["backup_path"]
                        # The path might be relative to PROJECT_DIR or absolute.
                        # For this test, let's assume it's relative to PROJECT_DIR if not absolute.
                        if not os.path.isabs(backup_file_path_from_api):
                            backup_file_full_path = os.path.join(PROJECT_DIR, backup_file_path_from_api)
                        else:
                            backup_file_full_path = backup_file_path_from_api

                        if os.path.exists(backup_file_full_path):
                            add_test_result(api_category_name, "Database Backup - Successful Backup", "PASS", "Status 200, success:true, backup file created.", value=f"Backup path: {backup_file_path_from_api}")
                        else:
                            add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", f"Status 200, success:true, but backup file NOT found at {backup_file_full_path}", value=f"API path: {backup_file_path_from_api}")
                    else:
                        add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", f"Status: {r_backup.status_code}, Response: {r_backup.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", str(e))
                finally:
                    if backup_file_path_from_api:
                        # Construct full path for cleanup similar to how it was checked
                        if not os.path.isabs(backup_file_path_from_api):
                            cleanup_path = os.path.join(PROJECT_DIR, backup_file_path_from_api)
                        else:
                            cleanup_path = backup_file_path_from_api
                        if os.path.exists(cleanup_path):
                            log_message(f"Cleaning up backup file: {cleanup_path}", level="DEBUG")
                            os.remove(cleanup_path)
        else:
            add_test_result(api_category_name, "Overall Server Startup", "FAIL", "Server did not start. Endpoint tests skipped.")
    finally:
        log_message("Attempting to shutdown FastAPI server...")
        # Using pkill is more robust for processes started with `nohup ... &`
        pkill_cmd = ["pkill", "-f", f"uvicorn backend.main:app --port {FASTAPI_PORT}"]
        log_message(f"Running: {' '.join(pkill_cmd)}")
        _, pkill_stderr, pkill_rc = run_shell_command(pkill_cmd)
        shutdown_status, shutdown_details = "N/A", "Attempted pkill."
        if pkill_rc == 0: # pkill found and signaled
            time.sleep(3) # Give it time to die
            try:
                requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=3)
                shutdown_status, shutdown_details = "FAIL", "Server still responding after pkill."
                log_message(shutdown_details, level="WARN")
            except requests.exceptions.ConnectionError:
                shutdown_status, shutdown_details = "PASS", "Server not responding after pkill (presumed stopped)."
                log_message(shutdown_details)
        elif "no processes found" in pkill_stderr.lower() or pkill_rc == 1:
            shutdown_status, shutdown_details = "PASS" if server_started_ok else "INFO", "No matching process found by pkill (already stopped or never started)."
            log_message(shutdown_details)
        else:
            shutdown_status, shutdown_details = "WARN", f"pkill command had issues. RC:{pkill_rc}, Err:{pkill_stderr}"
            log_message(shutdown_details, level="WARN")
        add_test_result(api_category_name, "Server Shutdown", shutdown_status, shutdown_details)
        # Keep FastAPI log for inspection: os.remove(FASTAPI_LOG_PATH)

        # --- Revert health.py modification ---
        if original_health_router_content and modified_for_error_test: # Only revert if successfully read and modified
            try:
                log_message(f"Reverting changes to {health_router_path}.", level="INFO")
                with open(health_router_path, 'w', encoding='utf-8') as f:
                    f.write(original_health_router_content)
                add_test_result(error_handling_category_name, "FastAPI Global Error Handler Cleanup", "PASS", f"Successfully reverted {os.path.basename(health_router_path)}.")
            except Exception as e_revert:
                log_message(f"CRITICAL: Failed to revert {health_router_path} to its original content: {e_revert}", level="CRITICAL")
                add_test_result(error_handling_category_name, "FastAPI Global Error Handler Cleanup", "FAIL", f"CRITICAL: Failed to revert {os.path.basename(health_router_path)}: {e_revert}")
        elif original_health_router_content and not modified_for_error_test:
            log_message(f"No modification was applied to {health_router_path}, so no reversion needed.", level="DEBUG")
        elif not original_health_router_content and os.path.exists(health_router_path) :
             log_message(f"Original content of {health_router_path} was not stored. Cannot revert. Manual check advised.", level="WARN")


    # --- Pytest Unit Tests ---
    # (Existing pytest call remains here)
    if pytest_install_status == "PASS":
        run_unit_tests_with_pytest()
    else:
        add_test_result("Unit Tests (pytest)", "Pytest Execution", "SKIPPED", "Pytest not installed.")

    # Streamlit application tests
    test_streamlit_startup_and_log_initialization()


    return clone_successful


# --- New Function: test_google_drive_accessibility ---
def test_google_drive_accessibility():
    log_message("Running Google Drive Accessibility Test...")
    category_name = "Colab Environment"
    gdrive_mount_path = "/content/drive/MyDrive"

    try:
        import google.colab.drive
        log_message("google.colab.drive imported successfully. Script is likely in a Colab environment.", level="INFO")

        if os.path.exists(gdrive_mount_path):
            log_message(f"Path '{gdrive_mount_path}' exists.", level="INFO")
            if os.access(gdrive_mount_path, os.W_OK):
                add_test_result(category_name, "Google Drive Path (/content/drive/MyDrive)", "PASS", f"Path '{gdrive_mount_path}' exists and is writable.")
                try:
                    # Attempt a very small, brief write/read/delete operation if safe
                    # This is a more definitive check but has minor side effects.
                    temp_file_path = os.path.join(gdrive_mount_path, ".health_check_gdrive_test.tmp")
                    with open(temp_file_path, "w") as f:
                        f.write("test")
                    with open(temp_file_path, "r") as f:
                        content = f.read()
                    os.remove(temp_file_path)
                    if content == "test":
                         add_test_result(category_name, "Google Drive Write/Read Test", "PASS", "Successfully performed a brief write/read/delete in /content/drive/MyDrive.")
                    else:
                         add_test_result(category_name, "Google Drive Write/Read Test", "WARN", "Brief write/read test in /content/drive/MyDrive failed verification. Content mismatch.")
                except Exception as e_io:
                    log_message(f"Google Drive brief I/O test failed: {e_io}", level="WARN")
                    add_test_result(category_name, "Google Drive Write/Read Test", "WARN", f"Brief I/O test in /content/drive/MyDrive failed: {e_io}. Path might be writable but operations are failing.")

            else:
                add_test_result(category_name, "Google Drive Path (/content/drive/MyDrive)", "WARN", f"Path '{gdrive_mount_path}' exists but is NOT writable. Check Drive permissions for the Colab user/notebook.")
        else:
            add_test_result(category_name, "Google Drive Path (/content/drive/MyDrive)", "INFO", f"Path '{gdrive_mount_path}' does NOT exist. Google Drive may not be mounted in this Colab session.")

    except ImportError:
        log_message("google.colab.drive import failed. Script is not running in a standard Colab environment with Drive utilities.", level="WARN")
        add_test_result(category_name, "Google Drive Accessibility", "SKIPPED", "Not running in a Colab environment with google.colab.drive.")
    except Exception as e:
        log_message(f"An unexpected error occurred during Google Drive accessibility test: {e}", level="ERROR")
        add_test_result(category_name, "Google Drive Accessibility", "FAIL", f"Unexpected error during test: {e}")


# --- New Function: test_streamlit_startup_and_log_initialization ---

def test_streamlit_url_acquisition_internal(category_name):
    log_message("Running Streamlit URL Acquisition tests (Internal)...")
    # This function is called while Streamlit process is expected to be running.

    try:
        from google.colab.output import eval_js
        log_message("google.colab.output.eval_js imported successfully.", level="DEBUG")

        eval_js_command = f'google.colab.kernel.proxyPort({STREAMLIT_TEST_PORT})'
        log_message(f"Attempting to get Streamlit URL via eval_js: {eval_js_command}", level="INFO")
        streamlit_url_eval_js = None
        try:
            streamlit_url_eval_js = eval_js(eval_js_command, timeout_sec=10) # Increased timeout slightly
            if streamlit_url_eval_js and (streamlit_url_eval_js.startswith("http://") or streamlit_url_eval_js.startswith("https://")):
                add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "PASS", f"Successfully obtained URL via eval_js: {streamlit_url_eval_js}")
                # Overall success if eval_js works
                add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "PASS", f"URL obtained via eval_js: {streamlit_url_eval_js}")
                return True # Indicates URL acquired
            else:
                add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "FAIL", f"eval_js did not return a valid URL. Received: '{streamlit_url_eval_js}'")
        except Exception as e_evaljs:
            log_message(f"google.colab.output.eval_js failed: {e_evaljs}", level="ERROR")
            add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "FAIL", f"eval_js call failed: {e_evaljs}")

    except ImportError:
        log_message("google.colab.output.eval_js not available. Skipping eval_js test for Streamlit URL.", level="WARN")
        add_test_result(category_name, "Streamlit URL Acquisition - eval_js Method", "SKIPPED", "Not in a Colab environment with google.colab.output.")
        # Fall through to cloudflared check if eval_js is not even available

    # Conceptual Cloudflared Fallback Check (if eval_js failed or was skipped)
    log_message("eval_js did not yield a URL or was skipped. Checking for cloudflared as a conceptual fallback.", level="INFO")
    cloudflared_check_details = "This check only verifies cloudflared presence, not actual tunnel functionality which is complex to automate here."
    stdout_cf, stderr_cf, rc_cf = run_shell_command(["cloudflared", "--version"])
    if rc_cf == 0:
        add_test_result(category_name, "Streamlit URL Acquisition - Cloudflared Check", "PASS", f"cloudflared is installed ({stdout_cf.strip()}). {cloudflared_check_details}")
        # Overall status is WARN because we have a fallback but didn't get URL from primary method
        add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "WARN", "eval_js failed/skipped, but cloudflared (fallback) is present. Actual URL not obtained by this script.")
    else:
        add_test_result(category_name, "Streamlit URL Acquisition - Cloudflared Check", "WARN", f"cloudflared not found or version check failed (RC:{rc_cf}). {cloudflared_check_details}", value=stderr_cf)
        # Overall status is FAIL because primary failed and fallback is not present
        add_test_result(category_name, "Streamlit URL Acquisition - Overall Status", "FAIL", "eval_js failed/skipped, and cloudflared (fallback) is not available.")

    return False # Indicates URL not acquired by primary method

def check_streamlit_application_log(category_name, streamlit_log_path):
    """Checks the application's own Streamlit log file."""
    log_message(f"Checking Streamlit application log: {streamlit_log_path}", level="INFO")
    if os.path.exists(streamlit_log_path):
        try:
            with open(streamlit_log_path, 'r', encoding='utf-8', errors='replace') as f_log:
                log_head = f_log.read(500) # Read first 500 chars
            if "streamlit" in log_head.lower() or "info" in log_head.lower() or "debug" in log_head.lower() or "logger" in log_head.lower():
                add_test_result(category_name, "Streamlit App Log Initialization", "PASS", f"App log '{os.path.basename(streamlit_log_path)}' exists and contains initial log patterns.", value=f"Log snippet: {log_head[:100]}...")
            else:
                add_test_result(category_name, "Streamlit App Log Initialization", "WARN", f"App log '{os.path.basename(streamlit_log_path)}' exists but expected patterns not found. Manual check advised.", value=f"Log snippet: {log_head[:100]}...")
        except Exception as e:
            add_test_result(category_name, "Streamlit App Log Initialization", "FAIL", f"Error reading app log {os.path.basename(streamlit_log_path)}: {e}")
    else:
        add_test_result(category_name, "Streamlit App Log Initialization", "WARN", f"App log file '{os.path.basename(streamlit_log_path)}' not found. App might not be configured to log here or did not start/log correctly.")


def test_streamlit_startup_and_log_initialization():
    log_message("Running Streamlit Startup, URL Acquisition, and Log Initialization tests...")
    category_name = "Frontend Application (Streamlit)"
    streamlit_app_path = os.path.join(PROJECT_DIR, "app.py")
    streamlit_log_dir = os.path.join(PROJECT_DIR, "logs")
    # App's own log, configured by the app itself:
    application_streamlit_log_path = os.path.join(streamlit_log_dir, "streamlit.log")
    # Log for the Streamlit process started by this health check:
    health_check_streamlit_process_log_path = os.path.join(streamlit_log_dir, "health_check_streamlit_process.log")

    if not os.path.exists(streamlit_app_path):
        add_test_result(category_name, "Streamlit App File Check", "FAIL", f"Streamlit app.py not found at {streamlit_app_path}.")
        # Add SKIPPED for all sub-tests if app.py is missing
        for test_name_suffix in ["App Startup", "URL Acquisition - Overall Status", "App Log Initialization"]:
            add_test_result(category_name, f"Streamlit {test_name_suffix}", "SKIPPED", "app.py not found.")
        return

    if not os.path.exists(streamlit_log_dir):
        try:
            os.makedirs(streamlit_log_dir)
            log_message(f"Created logs directory for Streamlit: {streamlit_log_dir}", level="INFO")
        except Exception as e:
            log_message(f"Failed to create Streamlit logs directory {streamlit_log_dir}: {e}", level="ERROR")
            add_test_result(category_name, "Streamlit Log Directory Setup", "FAIL", f"Failed to create {streamlit_log_dir}: {e}.")
            # Do not return; attempt startup anyway, but URL/log tests might be affected or save to different locations.

    cmd = [
        sys.executable, "-m", "streamlit", "run", streamlit_app_path,
        "--server.port", str(STREAMLIT_TEST_PORT), "--server.headless", "true",
        "--server.runOnSave", "false", "--server.fileWatcherType", "none"
    ]
    process = None
    startup_presumed_ok = False

    try:
        log_message(f"Executing Streamlit command: {' '.join(cmd)} for startup test.", level="DEBUG")
        with open(health_check_streamlit_process_log_path, 'wb') as proc_log_f:
            process = subprocess.Popen(cmd, cwd=PROJECT_DIR, stdout=proc_log_f, stderr=proc_log_f)

        log_message(f"Streamlit process (PID: {process.pid}) launched. Waiting ~15s for initial stability check.", level="INFO")
        try:
            process.wait(timeout=15)
            rc = process.returncode
            log_message(f"Streamlit process terminated early with RC: {rc}", level="WARN")
            add_test_result(category_name, "Streamlit App Startup", "FAIL" if rc != 0 else "WARN",
                            f"Process terminated early. RC: {rc}. Check '{os.path.basename(health_check_streamlit_process_log_path)}'.")
            startup_presumed_ok = False
        except subprocess.TimeoutExpired:
            log_message(f"Streamlit process (PID: {process.pid}) running after 15s. Presuming successful headless startup.", level="INFO")
            add_test_result(category_name, "Streamlit App Startup", "PASS", f"Process running after 15s (PID: {process.pid}). Headless startup presumed OK.")
            startup_presumed_ok = True

            # If startup is OK, attempt URL acquisition
            log_message("Proceeding to Streamlit URL acquisition tests while process is running...", level="INFO")
            test_streamlit_url_acquisition_internal(category_name) # Call the internal function

            # Allow a little more time if needed before forced termination, e.g. for eval_js to complete.
            # The URL acquisition has its own timeout for eval_js.
            time.sleep(2) # Brief pause before terminating.

    except Exception as e:
        log_message(f"Exception during Streamlit process management: {e}", level="ERROR")
        add_test_result(category_name, "Streamlit App Startup", "FAIL", f"Exception: {e}. Check '{os.path.basename(health_check_streamlit_process_log_path)}'.")
        startup_presumed_ok = False
    finally:
        if process:
            log_message(f"Ensuring Streamlit process (PID: {process.pid}) is terminated.", level="INFO")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log_message(f"Streamlit process (PID: {process.pid}) did not terminate gracefully, killing.", level="WARN")
                process.kill()
            except Exception as e_term: # Handle cases where process might already be dead
                log_message(f"Error during Streamlit process termination (PID: {process.pid if hasattr(process, 'pid') else 'N/A'}): {e_term}", level="ERROR")
            log_message(f"Streamlit process (PID: {process.pid if hasattr(process, 'pid') else 'N/A'}) cleanup finished.", level="INFO")

        if os.path.exists(health_check_streamlit_process_log_path):
            with open(health_check_streamlit_process_log_path, 'r', encoding='utf-8', errors='replace') as f_log_proc_read:
                log_content = f_log_proc_read.read()
            if not startup_presumed_ok and log_content:
                 add_test_result(category_name, "Streamlit Process Output (Health Check Log)", "INFO", f"Contents of '{os.path.basename(health_check_streamlit_process_log_path)}' (last 1000 chars): ...{log_content[-1000:]}")
            elif not log_content :
                 add_test_result(category_name, "Streamlit Process Output (Health Check Log)", "INFO", f"'{os.path.basename(health_check_streamlit_process_log_path)}' was empty.")


    # Check application's own log file AFTER Streamlit process has been handled
    # This part is independent of whether startup_presumed_ok is True, as the app might have logged errors before failing.
    # However, it makes more sense to check it if we believe the app at least tried to start.
    # For now, let's check it regardless, as it might contain useful diagnostic info even on failed startup.
    check_streamlit_application_log(category_name, application_streamlit_log_path)


# --- New Function: run_unit_tests_with_pytest ---
                try:
                    r = requests.get(f"{FASTAPI_BASE_URL}{ep}", timeout=10)
                    if r.status_code == 200:
                        response_json = r.json()
                        missing_keys = [k for k in checks["keys"] if k not in response_json]
                        if not missing_keys:
                            add_test_result(api_category_name, f"Endpoint: {ep}", "PASS", "Status 200, required keys OK.")
                        else:
                            add_test_result(api_category_name, f"Endpoint: {ep}", "WARN", f"Status 200, missing keys: {missing_keys}", value=str(response_json))
                    else:
                        add_test_result(api_category_name, f"Endpoint: {ep}", "FAIL", f"Status: {r.status_code}", value=r.text[:100])
                except Exception as e:
                    add_test_result(api_category_name, f"Endpoint: {ep}", "FAIL", str(e))

            # --- FastAPI Process Check ---
            pgrep_fastapi_cmd = ["pgrep", "-f", f"uvicorn backend.main:app --port {FASTAPI_PORT}"]
            log_message(f"Checking for running FastAPI process: {' '.join(pgrep_fastapi_cmd)}", level="DEBUG")
            stdout_pg_fastapi, stderr_pg_fastapi, rc_pg_fastapi = run_shell_command(pgrep_fastapi_cmd)
            if rc_pg_fastapi == 0 and stdout_pg_fastapi.strip():
                add_test_result(api_category_name, "FastAPI Process Check - Background Running", "PASS", f"FastAPI process found (PID(s): {stdout_pg_fastapi.strip()}).")
            else:
                add_test_result(api_category_name, "FastAPI Process Check - Background Running", "WARN", f"FastAPI process NOT found via pgrep. RC:{rc_pg_fastapi}, STDOUT:'{stdout_pg_fastapi}', STDERR:'{stderr_pg_fastapi}'. Server might have exited prematurely despite log messages.")
                # This could be a more severe FAIL if previous log checks also indicated issues.

            # --- /api/auth/login Test (Enhanced) ---
            login_payload = {"apiKey": "test_colab_health_check_key_valid"} # Assuming this key is valid for tests
            log_message(f"Testing {FASTAPI_BASE_URL}/api/auth/login with payload: {login_payload}", level="DEBUG")
            try:
                r = requests.post(f"{FASTAPI_BASE_URL}/api/auth/login", json=login_payload, timeout=10)
                if r.status_code == 200 and "access_token" in r.json():
                    test_api_auth_token = r.json()["access_token"]
                    add_test_result(api_category_name, "/api/auth/login", "PASS", "Login OK, token received and stored.")
                    log_message(f"Auth token stored: {test_api_auth_token[:15]}...", level="INFO")
                else:
                    add_test_result(api_category_name, "/api/auth/login", "FAIL", f"Status {r.status_code}, token in response: {'access_token' in r.json() if r.status_code==200 else 'N/A'}. Response: {r.text[:100]}")
                    test_api_auth_token = None
            except Exception as e:
                add_test_result(api_category_name, "/api/auth/login", "FAIL", str(e))
                test_api_auth_token = None

            auth_headers = {}
            if test_api_auth_token:
                auth_headers = {"Authorization": f"Bearer {test_api_auth_token}"}
            else:
                log_message("No auth token obtained from login, authenticated endpoint tests will be skipped or may fail.", level="WARN")


            # --- /api/chat Test ---
            chat_endpoint_url = f"{FASTAPI_BASE_URL}/api/chat/invoke" # Adjusted based on typical structure
            if not test_api_auth_token:
                add_test_result(api_category_name, "Chat Endpoint - Normal Request", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "SKIPPED", "Auth token not available.")
            else:
                # Test Case: Normal Chat Request
                chat_payload_normal = {"user_message": "Hello, Wolf AI!", "chat_history": []}
                log_message(f"Testing {chat_endpoint_url} (Normal) with payload: {chat_payload_normal}", level="DEBUG")
                try:
                    r_chat_normal = requests.post(chat_endpoint_url, json=chat_payload_normal, headers=auth_headers, timeout=20)
                    if r_chat_normal.status_code == 200 and "reply" in r_chat_normal.json():
                        add_test_result(api_category_name, "Chat Endpoint - Normal Request", "PASS", "Status 200, 'reply' in response.", value=f"Reply snippet: {r_chat_normal.json()['reply'][:50]}...")
                    else:
                        add_test_result(api_category_name, "Chat Endpoint - Normal Request", "FAIL", f"Status: {r_chat_normal.status_code}, Response: {r_chat_normal.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Chat Endpoint - Normal Request", "FAIL", str(e))

                # Test Case: Invalid Chat Request
                chat_payload_invalid = {"chat_history": []} # Missing user_message
                log_message(f"Testing {chat_endpoint_url} (Invalid) with payload: {chat_payload_invalid}", level="DEBUG")
                try:
                    r_chat_invalid = requests.post(chat_endpoint_url, json=chat_payload_invalid, headers=auth_headers, timeout=10)
                    if r_chat_invalid.status_code == 422: # FastAPI default for validation errors
                        add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "PASS", "Status 422 (Unprocessable Entity) as expected for invalid payload.")
                    else:
                        add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "FAIL", f"Expected 422, Got Status: {r_chat_invalid.status_code}, Response: {r_chat_invalid.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Chat Endpoint - Invalid Payload", "FAIL", str(e))


            # --- /api/data/fetch Test ---
            data_fetch_url = f"{FASTAPI_BASE_URL}/api/data/fetch"
            if not test_api_auth_token:
                add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "SKIPPED", "Auth token not available.")
                add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "SKIPPED", "Auth token not available.")
            else:
                # Valid yfinance Ticker
                yf_payload_valid = {"source": "yfinance", "parameters": {"symbol": "AAPL", "period": "1d"}}
                log_message(f"Testing {data_fetch_url} (yfinance AAPL) with payload: {yf_payload_valid}", level="DEBUG")
                try:
                    r_yf_valid = requests.post(data_fetch_url, json=yf_payload_valid, headers=auth_headers, timeout=15)
                    if r_yf_valid.status_code == 200 and r_yf_valid.json().get("success") and not r_yf_valid.json().get("is_cached"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "PASS", "Status 200, success:true, is_cached:false.", value=f"Data sample: {str(r_yf_valid.json().get('data'))[:50]}...")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "FAIL", f"Status: {r_yf_valid.status_code}, Response: {r_yf_valid.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Valid Ticker (AAPL)", "FAIL", str(e))

                # yfinance Cache Check
                log_message(f"Testing {data_fetch_url} (yfinance AAPL Cache) with payload: {yf_payload_valid}", level="DEBUG")
                try:
                    r_yf_cache = requests.post(data_fetch_url, json=yf_payload_valid, headers=auth_headers, timeout=15)
                    if r_yf_cache.status_code == 200 and r_yf_cache.json().get("success") and r_yf_cache.json().get("is_cached"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "PASS", "Status 200, success:true, is_cached:true.")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "FAIL", f"Status: {r_yf_cache.status_code}, Response: {r_yf_cache.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Cache Check (AAPL)", "FAIL", str(e))

                # Invalid yfinance Ticker
                yf_payload_invalid = {"source": "yfinance", "parameters": {"symbol": "INVALIDTICKERXYZ", "period": "1d"}}
                log_message(f"Testing {data_fetch_url} (yfinance Invalid) with payload: {yf_payload_invalid}", level="DEBUG")
                try:
                    r_yf_invalid = requests.post(data_fetch_url, json=yf_payload_invalid, headers=auth_headers, timeout=15)
                    # Expecting success:false or some specific error structure within a 200, or a 4xx/5xx
                    if r_yf_invalid.status_code == 200 and not r_yf_invalid.json().get("success"):
                        add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "PASS", "Status 200, success:false as expected for invalid ticker.")
                    elif r_yf_invalid.status_code >= 400: # Or if it returns a client/server error status
                         add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "PASS", f"Status {r_yf_invalid.status_code} as expected for invalid ticker.")
                    else:
                        add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "FAIL", f"Status: {r_yf_invalid.status_code}, Response: {r_yf_invalid.text[:200]}. Expected success:false or error status.")
                except Exception as e:
                    add_test_result(api_category_name, "Data Fetch - yfinance Invalid Ticker", "FAIL", str(e))

            # --- /api/files/upload Test ---
            file_upload_url = f"{FASTAPI_BASE_URL}/api/files/upload"
            dummy_file_content = "This is a health check dummy upload file."
            dummy_file_name = "health_check_upload_test.txt"
            # Ensure logs dir exists from pytest setup, or use PROJECT_DIR
            logs_dir_path = os.path.join(PROJECT_DIR, "logs")
            if not os.path.exists(logs_dir_path): os.makedirs(logs_dir_path, exist_ok=True) # Should exist from pytest, but ensure
            dummy_file_path = os.path.join(logs_dir_path, dummy_file_name)

            if not test_api_auth_token:
                add_test_result(api_category_name, "File Upload - Successful Upload", "SKIPPED", "Auth token not available.")
            else:
                try:
                    with open(dummy_file_path, "w") as f: f.write(dummy_file_content)
                    log_message(f"Testing {file_upload_url} with file: {dummy_file_path}", level="DEBUG")
                    with open(dummy_file_path, "rb") as f_rb:
                        files_payload = {'upload_file': (dummy_file_name, f_rb, 'text/plain')}
                        r_upload = requests.post(file_upload_url, files=files_payload, headers=auth_headers, timeout=15)

                    if r_upload.status_code == 200 and r_upload.json().get("success") and r_upload.json().get("file_id"):
                        add_test_result(api_category_name, "File Upload - Successful Upload", "PASS", "Status 200, success:true, file_id present.", value=f"File ID: {r_upload.json()['file_id']}")
                    else:
                        add_test_result(api_category_name, "File Upload - Successful Upload", "FAIL", f"Status: {r_upload.status_code}, Response: {r_upload.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "File Upload - Successful Upload", "FAIL", str(e))
                finally:
                    if os.path.exists(dummy_file_path): os.remove(dummy_file_path)


            # --- /api/db/backup Test ---
            db_backup_url = f"{FASTAPI_BASE_URL}/api/db/backup"
            if not test_api_auth_token:
                add_test_result(api_category_name, "Database Backup - Successful Backup", "SKIPPED", "Auth token not available.")
            else:
                backup_file_path_from_api = None
                try:
                    log_message(f"Testing {db_backup_url}", level="DEBUG")
                    r_backup = requests.post(db_backup_url, headers=auth_headers, timeout=20) # Backup can take time
                    if r_backup.status_code == 200 and r_backup.json().get("success") and r_backup.json().get("backup_path"):
                        backup_file_path_from_api = r_backup.json()["backup_path"]
                        # The path might be relative to PROJECT_DIR or absolute.
                        # For this test, let's assume it's relative to PROJECT_DIR if not absolute.
                        if not os.path.isabs(backup_file_path_from_api):
                            backup_file_full_path = os.path.join(PROJECT_DIR, backup_file_path_from_api)
                        else:
                            backup_file_full_path = backup_file_path_from_api

                        if os.path.exists(backup_file_full_path):
                            add_test_result(api_category_name, "Database Backup - Successful Backup", "PASS", "Status 200, success:true, backup file created.", value=f"Backup path: {backup_file_path_from_api}")
                        else:
                            add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", f"Status 200, success:true, but backup file NOT found at {backup_file_full_path}", value=f"API path: {backup_file_path_from_api}")
                    else:
                        add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", f"Status: {r_backup.status_code}, Response: {r_backup.text[:200]}")
                except Exception as e:
                    add_test_result(api_category_name, "Database Backup - Successful Backup", "FAIL", str(e))
                finally:
                    if backup_file_path_from_api:
                        # Construct full path for cleanup similar to how it was checked
                        if not os.path.isabs(backup_file_path_from_api):
                            cleanup_path = os.path.join(PROJECT_DIR, backup_file_path_from_api)
                        else:
                            cleanup_path = backup_file_path_from_api
                        if os.path.exists(cleanup_path):
                            log_message(f"Cleaning up backup file: {cleanup_path}", level="DEBUG")
                            os.remove(cleanup_path)
        else:
            add_test_result(api_category_name, "Overall Server Startup", "FAIL", "Server did not start. Endpoint tests skipped.")
    finally:
        log_message("Attempting to shutdown FastAPI server...")
        # Using pkill is more robust for processes started with `nohup ... &`
        pkill_cmd = ["pkill", "-f", f"uvicorn backend.main:app --port {FASTAPI_PORT}"]
        log_message(f"Running: {' '.join(pkill_cmd)}")
        _, pkill_stderr, pkill_rc = run_shell_command(pkill_cmd)
        shutdown_status, shutdown_details = "N/A", "Attempted pkill."
        if pkill_rc == 0: # pkill found and signaled
            time.sleep(3) # Give it time to die
            try:
                requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=3)
                shutdown_status, shutdown_details = "FAIL", "Server still responding after pkill."
                log_message(shutdown_details, level="WARN")
            except requests.exceptions.ConnectionError:
                shutdown_status, shutdown_details = "PASS", "Server not responding after pkill (presumed stopped)."
                log_message(shutdown_details)
        elif "no processes found" in pkill_stderr.lower() or pkill_rc == 1:
            shutdown_status, shutdown_details = "PASS" if server_started_ok else "INFO", "No matching process found by pkill (already stopped or never started)."
            log_message(shutdown_details)
        else:
            shutdown_status, shutdown_details = "WARN", f"pkill command had issues. RC:{pkill_rc}, Err:{pkill_stderr}"
            log_message(shutdown_details, level="WARN")
        add_test_result("Backend (FastAPI) Server", "Server Shutdown", shutdown_status, shutdown_details)
        # Keep FastAPI log for inspection: os.remove(FASTAPI_LOG_PATH)

# --- Phase 3: HTML Report Generation ---
def phase_3_generate_report():
    log_message("--- Phase 3: Report Generation ---")

    html_parts = []
    html_parts.append("""
    <html><head><title>Ai_wolf 綜合健康度檢測報告</title><meta charset="UTF-8">
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        h1, h2, h3 { color: #444; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background-color: #fff; box-shadow: 0 2px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #e9e9e9; }
        .status-PASS { color: green; font-weight: bold; }
        .status-FAIL { color: red; font-weight: bold; }
        .status-WARN { color: orange; font-weight: bold; }
        .status-INFO { color: blue; }
        .status-N_A, .status-SKIPPED { color: grey; }
        .summary { border: 1px solid #ccc; padding: 15px; margin-bottom: 20px; background-color: #fff; }
        .category-title { margin-top: 30px; border-bottom: 2px solid #666; padding-bottom: 5px; }
        .details, .value { max-width: 400px; word-wrap: break-word; font-size: 0.9em; }
        .timestamp { font-size: 0.8em; color: #777; }
        #log_messages_toggle { cursor: pointer; color: blue; text-decoration: underline; margin-bottom: 10px; display: block; }
        #log_messages_content { display: none; border: 1px solid #ccc; padding: 10px; background: #f9f9f9; max-height: 400px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; }
    </style>
    </head><body>
    """)
    html_parts.append(f"<h1>Ai_wolf 綜合健康度檢測報告</h1>")
    html_parts.append(f"<p>報告生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

    # Overall Summary
    num_pass, num_fail, num_warn, num_info, num_total = 0, 0, 0, 0, 0
    for category in RESULTS_DATA["categories"]:
        for test in category["tests"]:
            num_total += 1
            if test["status"] == "PASS": num_pass += 1
            elif test["status"] == "FAIL": num_fail += 1
            elif test["status"] == "WARN": num_warn += 1
            elif test["status"] == "INFO": num_info += 1

    overall_status_text = "✅ 所有主要檢測通過"
    if num_fail > 0: overall_status_text = "❌ 發現嚴重問題，請檢查紅色標記的項目！"
    elif num_warn > 0: overall_status_text = "⚠️ 部分項目需要注意，請檢查橙色標記的項目。"

    html_parts.append("<div class='summary'><h2>總體狀況</h2>")
    html_parts.append(f"<p style='font-size:1.2em;'><strong>{overall_status_text}</strong></p>")
    html_parts.append(f"<p><span class='status-PASS'>PASS: {num_pass}</span> | ")
    html_parts.append(f"<span class='status-FAIL'>FAIL: {num_fail}</span> | ")
    html_parts.append(f"<span class='status-WARN'>WARN: {num_warn}</span> | ")
    html_parts.append(f"<span class='status-INFO'>INFO: {num_info}</span> || Total Tests: {num_total}</p></div>")

    for category in RESULTS_DATA["categories"]:
        html_parts.append(f"<h3 class='category-title'>{category['name']}</h3><table>")
        html_parts.append("<tr><th>測試項目</th><th>狀態</th><th>詳細資訊</th><th>數值</th><th>時間戳</th></tr>")
        for test in category["tests"]:
            status_class = f"status-{test['status'].replace('_','-')}" # Handle N_A -> N-A
            html_parts.append(f"""
            <tr>
                <td>{test['name']}</td>
                <td class='{status_class}'>{test['status']}</td>
                <td class='details'>{test['details']}</td>
                <td class='value'>{test['value']}</td>
                <td class='timestamp'>{test['timestamp']}</td>
            </tr>
            """)
        html_parts.append("</table>")

    html_parts.append("<h3 class='category-title'>執行日誌</h3>")
    html_parts.append("<div id='log_messages_toggle' onclick='document.getElementById(\"log_messages_content\").style.display = (document.getElementById(\"log_messages_content\").style.display === \"none\" ? \"block\" : \"none\");'>點此展開/收合詳細日誌</div>")
    html_parts.append("<div id='log_messages_content'><pre>")
    for msg in LOG_MESSAGES:
        # Basic HTML escaping for log messages
        msg_safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_parts.append(msg_safe + "\n")
    html_parts.append("</pre></div>")

    html_parts.append("</body></html>")
    return "".join(html_parts)

# --- New Test Function: AI Market Review with Specific Date (Simulating Initial Analysis) ---
def test_ai_market_review_with_specific_date():
    category_name = "AI 功能與資料整合測試"
    log_message("Running AI Market Review with Specific Date (simulating initial_analysis flow) test...", level="INFO")

    temp_dir_name = "temp_test_files"
    temp_files_dir_path = os.path.join(PROJECT_DIR, temp_dir_name)
    temp_doc_name = "temp_dated_doc.txt"
    temp_doc_path = os.path.join(temp_files_dir_path, temp_doc_name)
    specific_date_str = "2023-10-26" # Used for validation and date range
    file_text_content = f"""這是關於市場的一些初步想法。
主要關注日期：{specific_date_str}
我們認為基於{specific_date_str}的數據，市場情緒謹慎。
"""
    global test_api_auth_token # Ensure we use the globally stored token
    auth_headers = {"Authorization": f"Bearer {test_api_auth_token}"}

    if not test_api_auth_token:
        log_message("Auth token not available, skipping AI initial_analysis flow test.", level="WARN")
        add_test_result(category_name, "Initial Analysis - Setup", "SKIPPED", "Auth token not available.")
        return

    external_market_data = None
    pre_fetch_success = False

    try:
        # 1. Prepare test file and directory
        log_message(f"Creating temporary directory: {temp_files_dir_path}", level="DEBUG")
        os.makedirs(temp_files_dir_path, exist_ok=True)
        # add_test_result(category_name, "Initial Analysis - Temp Dir Creation", "PASS", f"Ensured {temp_files_dir_path} exists.") # Less critical sub-step for reporting

        log_message(f"Creating temporary dated document: {temp_doc_path}", level="DEBUG")
        with open(temp_doc_path, "w", encoding="utf-8") as f:
            f.write(file_text_content)
        # add_test_result(category_name, "Initial Analysis - Temp Doc Creation", "PASS", f"Created {temp_doc_name} with date {specific_date_str}.")

        read_doc_content_for_ai = ""
        with open(temp_doc_path, "r", encoding="utf-8") as f:
            read_doc_content_for_ai = f.read()

        if not read_doc_content_for_ai:
            add_test_result(category_name, "Initial Analysis - Temp Document Read", "FAIL", f"Failed to read content from {temp_doc_name}.")
            return # Cannot proceed without file content

        # 2. (New Step) Pre-fetch market data for 'AAPL' around the specific_date_str
        data_fetch_url = f"{FASTAPI_BASE_URL}/api/data/fetch"
        # Define a period that robustly includes specific_date_str. E.g., the whole month of October 2023.
        # Assuming yfinance takes start/end. If it takes period like '1mo' and an end_date, that's also an option.
        # For '2023-10-26', let's fetch data for October 2023.
        # Note: yfinance might need end_date to be exclusive or inclusive depending on library version or backend logic.
        # Let's try a range that safely covers a week around the date.
        # specific_datetime = datetime.datetime.strptime(specific_date_str, "%Y-%m-%d")
        # start_date_fetch = (specific_datetime - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        # end_date_fetch = (specific_datetime + datetime.timedelta(days=1)).strftime("%Y-%m-%d") # Fetch up to and including the day

        # Simpler: Assume the backend's /api/data/fetch can handle a "period" relative to a "date" or similar.
        # Or, as per instructions, try to get data for "AAPL" "around" the date.
        # If the API expects specific start/end, this is a guess.
        # A common pattern for "1wk" data might be the 7 days ending on the given date.
        # Let's use a common symbol like 'AAPL' and a period like '1mo' to increase chance of getting data.
        # The actual date relevance of this fetched data to the AI's output for "2023-10-26" is complex to assert strongly.
        market_data_payload = {
            "source": "yfinance",
            "parameters": {"symbol": "AAPL", "period": "1mo"} # Fetch 1 month of data for AAPL, hoping it covers the date.
            # "parameters": {"symbol": "AAPL", "start_date": "2023-10-01", "end_date": "2023-10-31"} # More specific if API supports
        }
        log_message(f"Pre-fetching market data from {data_fetch_url} for AAPL (1mo period). Payload: {market_data_payload}", level="INFO")
        try:
            r_market_data = requests.post(data_fetch_url, json=market_data_payload, headers=auth_headers, timeout=20)
            if r_market_data.status_code == 200 and r_market_data.json().get("success"):
                external_market_data = r_market_data.json().get("data")
                if external_market_data:
                    log_message("Successfully pre-fetched market data for AAPL.", level="INFO")
                    add_test_result(category_name, "Initial Analysis - Market Data Pre-fetch (AAPL)", "PASS", "Successfully fetched external market data.")
                    pre_fetch_success = True
                else:
                    log_message("Market data pre-fetch for AAPL was successful but data field is empty/null.", levelWARN")
                    add_test_result(category_name, "Initial Analysis - Market Data Pre-fetch (AAPL)", "WARN", "API success, but no data returned.", value=r_market_data.text[:150])
            else:
                log_message(f"Failed to pre-fetch market data for AAPL. Status: {r_market_data.status_code}, Response: {r_market_data.text[:150]}", level="WARN")
                add_test_result(category_name, "Initial Analysis - Market Data Pre-fetch (AAPL)", "FAIL", f"Status: {r_market_data.status_code}", value=r_market_data.text[:150])
        except Exception as e_fetch:
            log_message(f"Error during market data pre-fetch for AAPL: {e_fetch}", level="ERROR")
            add_test_result(category_name, "Initial Analysis - Market Data Pre-fetch (AAPL)", "FAIL", f"Exception: {str(e_fetch)[:150]}")

        # 3. Construct payload for /api/chat/invoke with trigger_action = "initial_analysis"
        chat_endpoint_url = f"{FASTAPI_BASE_URL}/api/chat/invoke"
        # Using 'invoke' as per previous structure, assuming it routes based on context.trigger_action

        initial_analysis_payload = {
            "user_message": "", # No direct user message for this action
            "chat_history": [],
            "context": {
                "trigger_action": "initial_analysis",
                "file_content": read_doc_content_for_ai,
                "date_range_for_analysis": specific_date_str, # e.g., "2023-10-26"
                "external_data": external_market_data if pre_fetch_success else None # Pass fetched data
            }
        }

        log_message(f"Posting to {chat_endpoint_url} for 'initial_analysis'. Date: {specific_date_str}. Payload (external_data excerpt): {str(initial_analysis_payload)[:200]}... (Full external_data may be large)", level="INFO")
        response = requests.post(chat_endpoint_url, json=initial_analysis_payload, headers=auth_headers, timeout=45) # Increased timeout for more complex AI task

        # 4. Validate AI response
        if response.status_code == 200:
            log_message(f"Initial Analysis AI endpoint returned 200. Response: {str(response.text)[:300]}...", level="DEBUG")
            try:
                response_json = response.json()
                ai_reply_markdown = response_json.get("reply", "")

                if not ai_reply_markdown.strip():
                    add_test_result(category_name, "Initial Analysis - AI Reply Content", "FAIL", "AI reply is empty or whitespace.")
                    return # No further validation possible

                # Primary Validation: "A. 週次與日期範圍:"
                # Regex to find "A. 週次與日期範圍:" followed by the date. Case-insensitive for "A." vs "a."
                # Making it flexible for potential markdown bolding like **A. 週次與日期範圍:**
                # Also, allowing for slight variations in whitespace.
                date_range_pattern = re.compile(r"(?i)\*\*?A\.\s*週次與日期範圍:\s*\*\*?\s*(.*" + re.escape(specific_date_str) + r".*)", re.MULTILINE)
                date_match = date_range_pattern.search(ai_reply_markdown)

                if date_match:
                    add_test_result(category_name, "Initial Analysis - Section A Date Validation", "PASS", f"Correct date '{specific_date_str}' found in 'A. 週次與日期範圍:'.", value=f"Matched line: {date_match.group(1)[:100]}...")
                else:
                    add_test_result(category_name, "Initial Analysis - Section A Date Validation", "FAIL", f"Specific date '{specific_date_str}' NOT found or pattern mismatch in 'A. 週次與日期範圍:'.", value=f"AI Reply (first 300 chars): {ai_reply_markdown[:300]}...")

                # Secondary Validation: "C. 當週市場重點回顧:" content related to external_data (AAPL)
                if pre_fetch_success and external_market_data:
                    # Regex for "C. 當週市場重點回顧:"
                    market_review_pattern = re.compile(r"(?i)\*\*?C\.\s*當週市場重點回顧:\s*\*\*?\s*([\s\S]*?)(?=\n\s*\*\*?[D]\.|Z\.)", re.MULTILINE) # Try to capture content until next section or end
                    review_match = market_review_pattern.search(ai_reply_markdown)
                    if review_match:
                        review_text = review_match.group(1)
                        if "AAPL" in review_text or "Apple" in review_text.capitalize(): # Check for ticker or company name
                            add_test_result(category_name, "Initial Analysis - Section C Content (AAPL)", "PASS", "Mention of 'AAPL' or 'Apple' found in market review section.", value=f"Review snippet: {review_text[:150]}...")
                        else:
                            add_test_result(category_name, "Initial Analysis - Section C Content (AAPL)", "WARN", "Mention of 'AAPL' or 'Apple' NOT found in market review. Data might not have been used or mentioned.", value=f"Review snippet: {review_text[:150]}...")
                        # A more advanced check would be to look for numerical data points from external_market_data,
                        # but this is complex due to formatting and AI paraphrasing.
                    else:
                        add_test_result(category_name, "Initial Analysis - Section C Content (AAPL)", "WARN", "Could not locate 'C. 當週市場重點回顧:' section clearly for AAPL check.", value=f"AI Reply (first 300 chars): {ai_reply_markdown[:300]}...")
                elif pre_fetch_success and not external_market_data:
                    add_test_result(category_name, "Initial Analysis - Section C Content (AAPL)", "INFO", "Market data pre-fetch was successful but data was empty, Section C check skipped.")
                else: # Pre-fetch failed or no data
                    add_test_result(category_name, "Initial Analysis - Section C Content (AAPL)", "SKIPPED", "Market data pre-fetch failed or no data, Section C check skipped.")

            except ValueError: # Not JSON
                add_test_result(category_name, "Initial Analysis - AI Response Parsing", "FAIL", f"AI endpoint response was not valid JSON. Status: {response.status_code}.", value=response.text[:200])
            except Exception as e_parse:
                add_test_result(category_name, "Initial Analysis - AI Response Parsing", "FAIL", f"Error parsing AI response: {e_parse}. Response text: {response.text[:200]}")
        else:
            log_message(f"Initial Analysis AI endpoint returned error. Status: {response.status_code}, Response: {response.text[:300]}", level="ERROR")
            add_test_result(category_name, "Initial Analysis - AI API Call", "FAIL", f"AI endpoint returned status {response.status_code}.", value=response.text[:200])

    except requests.exceptions.Timeout:
        log_message(f"Request to AI endpoint for Initial Analysis timed out.", level="ERROR")
        add_test_result(category_name, "Initial Analysis - AI API Call", "FAIL", "Request timed out.")
    except Exception as e:
        log_message(f"An unexpected error occurred in test_ai_market_review_with_specific_date (initial_analysis): {e}", level="CRITICAL")
        add_test_result(category_name, "Initial Analysis - Overall Test Execution", "FAIL", f"Unexpected error: {e}")
    finally:
        # 5. Cleanup temporary files and directory
        try:
            if os.path.exists(temp_doc_path):
                os.remove(temp_doc_path)
                # log_message(f"Cleaned up temporary document: {temp_doc_path}", level="DEBUG")
            if os.path.exists(temp_files_dir_path):
                shutil.rmtree(temp_files_dir_path) # Use rmtree for robustness as dir may not be empty
                # log_message(f"Cleaned up temporary directory: {temp_files_dir_path}", level="DEBUG")
            # add_test_result(category_name, "Initial Analysis - Cleanup", "PASS", "Cleanup attempted for temp files/dir.") # Less critical for reporting
        except Exception as e_cleanup:
            log_message(f"Error during cleanup in initial_analysis test: {e_cleanup}", level="ERROR")
            # add_test_result(category_name, "Initial Analysis - Cleanup", "FAIL", f"Error during cleanup: {e_cleanup}")


# --- Phase 4: Display Report and Cleanup ---
def phase_4_display_and_cleanup(html_report_str):
    log_message("--- Phase 4: Display Report and Cleanup ---")
    clear_output(wait=True) # Clear previous print outputs from Colab cell
    display(HTML(html_report_str))
    # FastAPI server shutdown is handled in its own try/finally block in phase_2_tests
    log_message("Cleanup of other resources if any would go here.")

# --- Main Execution ---
if __name__ == "__main__":
    # Ensure display can work by checking if in IPython environment
    try:
        get_ipython()
        IN_IPYTHON = True
    except NameError:
        IN_IPYTHON = False
        log_message("Not running in an IPython environment. HTML display will be skipped.", level="WARN")

    log_message("=== Ai_wolf Comprehensive Health Check Script (Final Version) Started ===")

    project_clone_ok = phase_1_environment_setup()
    phase_2_tests(project_clone_ok) # Pass clone status

    html_report = phase_3_generate_report()

    if IN_IPYTHON:
        phase_4_display_and_cleanup(html_report)
    else:
        # Fallback for non-IPython environments: print report to console or save to file
        log_message("Non-IPython environment: HTML report content will be printed below.", level="INFO")
        # print("\n--- HTML Report Content ---\n") # This might be too verbose for console
        # print(html_report)
        report_file = "health_check_report.html"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html_report)
            log_message(f"HTML report saved to: {os.path.abspath(report_file)}", level="INFO")
        except Exception as e_save:
            log_message(f"Error saving HTML report to file: {e_save}", level="ERROR")


    log_message(f"Total log messages collected: {len(LOG_MESSAGES)}")
    log_message("=== Ai_wolf Comprehensive Health Check Script (Final Version) Finished ===")
    if os.path.exists(FASTAPI_LOG_PATH):
        log_message(f"FastAPI test log available at: {FASTAPI_LOG_PATH}")

    verify_all_test_processes_terminated()

# --- Final Process Verification Function ---
def verify_all_test_processes_terminated():
    log_message("--- Final Verification: Checking for leftover test processes ---", level="INFO")

    # Check for FastAPI test process
    # Ensure the pattern matches exactly how it's launched, especially if --app-dir is part of the unique identifier
    # The original FastAPI launch string: f"nohup {sys.executable} -m uvicorn backend.main:app --host 0.0.0.0 --port {FASTAPI_PORT} --app-dir {PROJECT_DIR} > {FASTAPI_LOG_PATH} 2>&1 &"
    # pkill uses: f"uvicorn backend.main:app --port {FASTAPI_PORT}"
    # For pgrep, we should be specific enough.
    fastapi_pgrep_pattern = f"uvicorn backend.main:app --host 0.0.0.0 --port {FASTAPI_PORT} --app-dir {PROJECT_DIR}"
    # Simpler pattern if the above is too specific due to shell expansion or nohup:
    # fastapi_pgrep_pattern = f"uvicorn backend.main:app --port {FASTAPI_PORT}"

    pgrep_fastapi_cmd = ["pgrep", "-f", fastapi_pgrep_pattern]
    log_message(f"Final check for FastAPI process: {' '.join(pgrep_fastapi_cmd)}", level="DEBUG")
    stdout_pg_fastapi, _, rc_pg_fastapi = run_shell_command(pgrep_fastapi_cmd)
    if rc_pg_fastapi == 0 and stdout_pg_fastapi.strip():
        log_message(f"WARNING: FastAPI test process (port {FASTAPI_PORT}, pattern: '{fastapi_pgrep_pattern}') may still be running (PIDs: {stdout_pg_fastapi.strip()}).", level="WARN")
    elif rc_pg_fastapi == 1: # pgrep returns 1 if no processes matched
        log_message(f"INFO: FastAPI test process (port {FASTAPI_PORT}) confirmed terminated.", level="INFO")
    else: # Other return codes might indicate an issue with pgrep itself
        log_message(f"INFO: pgrep check for FastAPI had RC:{rc_pg_fastapi}. Unable to confirm termination status definitively.", level="INFO")


    # Check for Streamlit test process
    # Original launch command: [sys.executable, "-m", "streamlit", "run", streamlit_app_path, "--server.port", str(STREAMLIT_TEST_PORT), ...]
    # Need to ensure streamlit_app_path is resolved correctly if PROJECT_DIR is not absolute from the start.
    # However, PROJECT_DIR is defined as "/content/wolfAI", which is absolute.
    streamlit_app_path_for_pgrep = os.path.join(PROJECT_DIR, "app.py")
    streamlit_pgrep_pattern = f"streamlit run {streamlit_app_path_for_pgrep} --server.port {STREAMLIT_TEST_PORT}"

    pgrep_streamlit_cmd = ["pgrep", "-f", streamlit_pgrep_pattern]
    log_message(f"Final check for Streamlit process: {' '.join(pgrep_streamlit_cmd)}", level="DEBUG")
    stdout_pg_streamlit, _, rc_pg_streamlit = run_shell_command(pgrep_streamlit_cmd)
    if rc_pg_streamlit == 0 and stdout_pg_streamlit.strip():
        log_message(f"WARNING: Streamlit test process (port {STREAMLIT_TEST_PORT}, pattern: '{streamlit_pgrep_pattern}') may still be running (PIDs: {stdout_pg_streamlit.strip()}).", level="WARN")
    elif rc_pg_streamlit == 1:
        log_message(f"INFO: Streamlit test process (port {STREAMLIT_TEST_PORT}) confirmed terminated.", level="INFO")
    else:
        log_message(f"INFO: pgrep check for Streamlit had RC:{rc_pg_streamlit}. Unable to confirm termination status definitively.", level="INFO")

```
