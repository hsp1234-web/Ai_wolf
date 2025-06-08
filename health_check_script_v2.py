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

# --- Global Variables/Setup ---
PROJECT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
PROJECT_DIR = "/content/wolfAI"
RESULTS_DATA = {"categories": []}
LOG_MESSAGES = []

FASTAPI_PORT = 8008 # Using a non-default port for testing
FASTAPI_BASE_URL = f"http://127.0.0.1:{FASTAPI_PORT}"
FASTAPI_LOG_PATH = "/content/temp_fastapi_health_check.log"
fastapi_process = None # To store the FastAPI server process

# --- Helper Functions ---
def log_message(message, level="INFO"):
    """Appends a formatted message to LOG_MESSAGES and also prints it."""
    timestamp = datetime.datetime.now().isoformat()
    formatted_message = f"[{timestamp}] [{level}] {message}"
    LOG_MESSAGES.append(formatted_message)
    print(formatted_message)

def run_shell_command(command_list, cwd=None, use_shell=False, pass_through_env=False):
    """Executes a shell command, captures output and error, returns (stdout, stderr, returncode)."""
    log_message(f"Running command: {' '.join(command_list) if not use_shell else command_list}", level="DEBUG")
    env = os.environ.copy() if pass_through_env else None
    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            shell=use_shell, # Use shell=True cautiously
            preexec_fn=os.setsid if not use_shell else None, # Create new process group if not using shell
            env=env
        )
        stdout, stderr = process.communicate(timeout=60) # 60-second timeout
        returncode = process.returncode
        return stdout, stderr, returncode
    except subprocess.TimeoutExpired:
        log_message(f"Command timed out: {' '.join(command_list) if not use_shell else command_list}", level="ERROR")
        if not use_shell and process.pgid: # process.pgid might not be set if shell=True
             os.killpg(process.pgid, signal.SIGKILL)
        elif use_shell: # Cannot reliably kill process group if shell=True without more complex PID tracking
             process.kill() # Try to kill the shell process at least
        # stdout, stderr = process.communicate() # This might hang if process.kill() was used
        return "", "TimeoutExpired", -1 # Indicate timeout
    except Exception as e:
        log_message(f"Error running command {' '.join(command_list) if not use_shell else command_list}: {e}", level="ERROR")
        return "", str(e), -2 # Indicate other exception

def add_test_result(category_name, test_name, status, details="", value=""):
    """Adds a test result to RESULTS_DATA."""
    category = next((cat for cat in RESULTS_DATA["categories"] if cat["name"] == category_name), None)
    if not category:
        category = {"name": category_name, "tests": []}
        RESULTS_DATA["categories"].append(category)

    category["tests"].append({
        "name": test_name,
        "status": status,
        "details": details,
        "value": value,
        "timestamp": datetime.datetime.now().isoformat()
    })

# --- Phase 1: Environment Setup ---
def phase_1_environment_setup():
    log_message("--- Phase 1: Environment Setup ---")
    # (Identical to v1 - reusing the logic)
    log_message(f"Cleaning up old project directory: {PROJECT_DIR}...")
    cleanup_status = "PASS"
    cleanup_details = f"Directory {PROJECT_DIR} did not exist or was successfully removed."
    if os.path.exists(PROJECT_DIR):
        try:
            shutil.rmtree(PROJECT_DIR)
            log_message(f"Successfully removed {PROJECT_DIR}.")
        except Exception as e:
            log_message(f"Failed to remove {PROJECT_DIR}: {e}", level="ERROR")
            cleanup_status = "FAIL"
            cleanup_details = f"Failed to remove {PROJECT_DIR}: {e}"
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
        log_message(f"Failed to clone project. Return code: {returncode}\nStdout: {stdout}\nStderr: {stderr}", level="ERROR")
        add_test_result("Environment Setup", "Clone Project Repository", "FAIL", f"Return code: {returncode}. Error: {stderr or stdout}")
        add_test_result("Project Structure and Dependencies", "Git Clone Success", "FAIL", f"Return code: {returncode}. Error: {stderr or stdout}")
        # Exit early if clone fails as other steps depend on it
        log_message("Project clone failed. Subsequent tests depending on project files will be skipped or fail.", level="CRITICAL")
        return False # Indicate failure

    log_message("Installing dependencies from requirements.txt...")
    requirements_path = os.path.join(PROJECT_DIR, "requirements.txt")
    dep_status = "N/A"
    dep_details = "Project clone failed, skipping dependency installation."

    if clone_successful:
        if os.path.exists(requirements_path):
            # Pass through existing environment variables, as pip might need them (e.g. for private repos, proxies)
            stdout, stderr, pip_returncode = run_shell_command(
                [sys.executable, "-m", "pip", "install", "-q", "-r", requirements_path],
                cwd=PROJECT_DIR, # Run pip install from the project directory
                pass_through_env=True
            )
            if pip_returncode == 0:
                log_message("Dependencies installed successfully.")
                dep_status = "PASS"
                dep_details = "Successfully installed dependencies from requirements.txt"
            else:
                log_message(f"Failed to install dependencies. Return code: {pip_returncode}\nStdout: {stdout}\nStderr: {stderr}", level="ERROR")
                dep_status = "FAIL"
                dep_details = f"pip install failed. RC: {pip_returncode}. Error: {stderr or stdout}"
        else:
            log_message(f"requirements.txt not found at {requirements_path}.", level="WARN")
            dep_status = "WARN"
            dep_details = f"requirements.txt not found at {requirements_path}."

    add_test_result("Environment Setup", "Install Dependencies", dep_status, dep_details)
    add_test_result("Project Structure and Dependencies", "Dependency Install Success", dep_status, dep_details)
    return clone_successful

# --- Phase 2: Test Execution ---
def phase_2_tests(project_clone_successful):
    log_message("--- Phase 2: Test Execution ---")

    # Category: "Colab Environment" (Identical to v1)
    log_message("Running Colab Environment checks...")
    python_version = sys.version.replace("\n", "")
    add_test_result("Colab Environment", "Python Version", "INFO", value=python_version)
    try:
        stdout, stderr, returncode = run_shell_command(["lscpu"])
        if returncode == 0:
            model_name = re.search(r"Model name:\s*(.*)", stdout)
            cpus = re.search(r"CPU\(s\):\s*(\d+)", stdout)
            cpu_info_value = ""
            if model_name: cpu_info_value += f"Model: {model_name.group(1).strip()}"
            if cpus: cpu_info_value += f" | CPUs: {cpus.group(1).strip()}"
            add_test_result("Colab Environment", "CPU Info", "INFO", value=cpu_info_value if cpu_info_value else stdout)
        else: add_test_result("Colab Environment", "CPU Info", "FAIL", details=f"lscpu failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e: add_test_result("Colab Environment", "CPU Info", "FAIL", details=f"Exception: {e}")
    try:
        stdout, stderr, returncode = run_shell_command(["cat", "/proc/meminfo"])
        if returncode == 0:
            mem_total = re.search(r"MemTotal:\s*(.*)", stdout)
            mem_available = re.search(r"MemAvailable:\s*(.*)", stdout)
            mem_info_value = ""
            if mem_total: mem_info_value += f"Total: {mem_total.group(1).strip()}"
            if mem_available: mem_info_value += f" | Available: {mem_available.group(1).strip()}"
            add_test_result("Colab Environment", "Memory Info", "INFO", value=mem_info_value if mem_info_value else stdout)
        else: add_test_result("Colab Environment", "Memory Info", "FAIL", details=f"cat /proc/meminfo failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e: add_test_result("Colab Environment", "Memory Info", "FAIL", details=f"Exception: {e}")
    try:
        stdout, stderr, returncode = run_shell_command(["df", "-h", "/"])
        if returncode == 0:
            lines = stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                add_test_result("Colab Environment", "Disk Space (/)", "INFO", value=f"Device: {parts[0]}, Total: {parts[1]}, Used: {parts[2]}, Avail: {parts[3]}")
            else: add_test_result("Colab Environment", "Disk Space (/)", "WARN", details="df output format unexpected.", value=stdout)
        else: add_test_result("Colab Environment", "Disk Space (/)", "FAIL", details=f"df -h / failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e: add_test_result("Colab Environment", "Disk Space (/)", "FAIL", details=f"Exception: {e}")
    try:
        stdout, stderr, returncode = run_shell_command(["nvidia-smi"])
        if returncode == 0:
            gpu_name_match = re.search(r"Product Name:\s*([^\s|]+)", stdout) or re.search(r"\|\s+\d+\s+([^|]+?)\s+(On|Off)\s+", stdout)
            gpu_name = gpu_name_match.group(1).strip() if gpu_name_match else "GPU Found (Details in log)"
            vram_match = re.search(r"(\d+MiB)\s*/\s*(\d+MiB)", stdout)
            vram_info = f" (VRAM: {vram_match.group(1)} / {vram_match.group(2)})" if vram_match else ""
            add_test_result("Colab Environment", "GPU Status", "INFO", value=f"{gpu_name}{vram_info}", details=stdout[:500])
        elif returncode == 127 : add_test_result("Colab Environment", "GPU Status", "WARN", value="nvidia-smi not found")
        else: add_test_result("Colab Environment", "GPU Status", "INFO", value="No GPU or nvidia-smi error", details=f"RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e: add_test_result("Colab Environment", "GPU Status", "FAIL", details=f"Exception: {e}")

    # Category: "Project Structure and Dependencies" (Key file check part)
    if project_clone_successful:
        log_message("Running Project Structure and Dependencies checks (File/Dir existence)...")
        key_paths_to_check = ["app.py", "backend/main.py", "requirements.txt", "components/", "services/", "utils/", "style.css", "prompts.toml", ".streamlit/config.toml"]
        for path in key_paths_to_check:
            full_path = os.path.join(PROJECT_DIR, path)
            if os.path.exists(full_path): add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "PASS", value=f"{path} exists")
            else: add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "FAIL", value=f"{path} NOT found")
    else:
        log_message("Skipping Project Structure file/directory checks as project clone failed.", level="WARN")
        for path in ["app.py", "backend/main.py", "requirements.txt"]: # Sample a few key ones
             add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "N/A", value="Project clone failed")


    # --- New Sub-Phase: API Keys and External Connectivity ---
    log_message("Running API Keys and External Connectivity checks...")

    # Gemini API Key Check
    gemini_api_key = os.environ.get("COLAB_GOOGLE_API_KEY_FOR_TEST")
    if gemini_api_key:
        log_message("COLAB_GOOGLE_API_KEY_FOR_TEST found. Testing connectivity to Gemini API...")
        try:
            response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key}", timeout=10)
            if response.status_code == 200:
                add_test_result("API Keys and External Connectivity", "Google Gemini API Key", "PASS", "Successfully connected and listed models.")
            else:
                add_test_result("API Keys and External Connectivity", "Google Gemini API Key", "FAIL", f"Failed. Status: {response.status_code}, Response: {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            add_test_result("API Keys and External Connectivity", "Google Gemini API Key", "FAIL", f"Connection error: {e}")
    else:
        add_test_result("API Keys and External Connectivity", "Google Gemini API Key", "WARN", "COLAB_GOOGLE_API_KEY_FOR_TEST environment variable not set. Skipped.")

    # FRED API Key Check
    fred_api_key = os.environ.get("COLAB_FRED_API_KEY_FOR_TEST")
    if fred_api_key:
        log_message("COLAB_FRED_API_KEY_FOR_TEST found. Testing connectivity to FRED API...")
        try:
            # GNPCA is a common series ID. Using a small count to minimize data transfer.
            response = requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id=GNPCA&api_key={fred_api_key}&file_type=json&limit=1", timeout=15)
            if response.status_code == 200:
                # Check if 'observations' in response as a basic validation of content
                if "observations" in response.json():
                     add_test_result("API Keys and External Connectivity", "FRED API Key", "PASS", "Successfully connected and fetched sample data.")
                else:
                     add_test_result("API Keys and External Connectivity", "FRED API Key", "FAIL", f"Connected, but response format unexpected. Status: {response.status_code}, Response: {response.text[:150]}")
            else:
                add_test_result("API Keys and External Connectivity", "FRED API Key", "FAIL", f"Failed. Status: {response.status_code}, Response: {response.text[:150]}")
        except requests.exceptions.RequestException as e:
            add_test_result("API Keys and External Connectivity", "FRED API Key", "FAIL", f"Connection error: {e}")
    else:
        add_test_result("API Keys and External Connectivity", "FRED API Key", "WARN", "COLAB_FRED_API_KEY_FOR_TEST environment variable not set. Skipped.")

    # External API Service Root Connectivity
    external_services = {
        "Google Generative Language API": "https://generativelanguage.googleapis.com",
        "FRED API": "https://api.stlouisfed.org"
    }
    for service_name, service_url in external_services.items():
        log_message(f"Testing root connectivity to {service_name} ({service_url})...")
        try:
            response = requests.get(service_url, timeout=10)
            if response.status_code == 200 or response.status_code == 404 : # Some services might return 404 at root but are up
                add_test_result("API Keys and External Connectivity", f"Connectivity: {service_name}", "PASS", f"Connected. Status: {response.status_code}")
            else:
                add_test_result("API Keys and External Connectivity", f"Connectivity: {service_name}", "FAIL", f"Failed. Status: {response.status_code}, Response: {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            add_test_result("API Keys and External Connectivity", f"Connectivity: {service_name}", "FAIL", f"Connection error: {e}")

    # --- New Sub-Phase: Backend (FastAPI) Server Tests ---
    if not project_clone_successful:
        log_message("Skipping Backend (FastAPI) Server tests as project clone failed.", level="WARN")
        add_test_result("Backend (FastAPI) Server", "Server Startup", "N/A", "Project clone failed.")
        return # Cannot proceed with backend tests

    global fastapi_process
    log_message("Running Backend (FastAPI) Server checks...")

    # Ensure log directory exists for FastAPI log
    os.makedirs(os.path.dirname(FASTAPI_LOG_PATH), exist_ok=True)
    if os.path.exists(FASTAPI_LOG_PATH): # Clean up old log
        os.remove(FASTAPI_LOG_PATH)

    # Using shell=True for nohup and & is generally tricky for Popen.
    # A more robust way is to manage daemonization in Python or use supervisor.
    # For this script, we'll use shell=True and rely on os.killpg with the shell's PID.
    # Note: This means fastapi_process.pid will be the shell's PID.
    # Proper termination of uvicorn started this way can be unreliable.

    # Command as a string for shell=True
    fastapi_command_str = f"nohup {sys.executable} -m uvicorn backend.main:app --host 0.0.0.0 --port {FASTAPI_PORT} --app-dir {PROJECT_DIR} > {FASTAPI_LOG_PATH} 2>&1 &"

    server_started_successfully = False
    try:
        log_message(f"Attempting to start FastAPI server in background on port {FASTAPI_PORT}...")
        # Use Popen with shell=True for `nohup ... &`
        # This is less ideal than shell=False and managing daemonization, but simpler for script
        # For shell=True, pass command as a string. No preexec_fn needed typically.
        fastapi_process = subprocess.Popen(fastapi_command_str, shell=True, cwd=PROJECT_DIR)

        log_message(f"FastAPI server process initiated (Shell PID: {fastapi_process.pid}). Waiting 15s for initialization...")
        time.sleep(15) # Wait for server to initialize

        # For processes started with 'nohup ... &', Popen's poll() might not reflect the actual server status.
        # We'll check the log file and try to connect.

        if os.path.exists(FASTAPI_LOG_PATH) and os.path.getsize(FASTAPI_LOG_PATH) > 0:
            log_message("FastAPI log file created and not empty.")
            add_test_result("Backend (FastAPI) Server", "FastAPI Log Creation", "PASS", f"Log file {FASTAPI_LOG_PATH} created and has content.")
            # A more robust check would be to scan the log for "Uvicorn running on..."
            with open(FASTAPI_LOG_PATH, 'r') as f_log:
                log_content_sample = f_log.read(500)
            if "Uvicorn running on" in log_content_sample or "Application startup complete" in log_content_sample:
                 log_message("FastAPI server seems to have started (based on log).")
                 server_started_successfully = True
                 add_test_result("Backend (FastAPI) Server", "Server Startup Check (Log)", "PASS", "Server startup message found in log.", value=log_content_sample)
            else:
                 add_test_result("Backend (FastAPI) Server", "Server Startup Check (Log)", "FAIL", "Server startup message NOT found in log.", value=log_content_sample)
                 server_started_successfully = False # Re-evaluate based on log
        else:
            log_message("FastAPI log file not created or empty.", level="WARN")
            add_test_result("Backend (FastAPI) Server", "FastAPI Log Creation", "FAIL", f"Log file {FASTAPI_LOG_PATH} not found or empty.")
            server_started_successfully = False

        # Try a health check even if log check was iffy
        if not server_started_successfully: # Try a ping if log check wasn't definitive
            try:
                health_response = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=5)
                if health_response.status_code == 200:
                    log_message("FastAPI server responded to /api/health. Assuming started.")
                    server_started_successfully = True
                    add_test_result("Backend (FastAPI) Server", "Server Startup Check (Ping)", "PASS", "/api/health responded 200.")
                else:
                    add_test_result("Backend (FastAPI) Server", "Server Startup Check (Ping)", "FAIL", f"/api/health status: {health_response.status_code}")
            except requests.exceptions.ConnectionError:
                 add_test_result("Backend (FastAPI) Server", "Server Startup Check (Ping)", "FAIL", "Connection error to /api/health.")


        if server_started_successfully:
            add_test_result("Backend (FastAPI) Server", "Overall Server Startup", "PASS", "Server appears to be running.")
            # Database Initialization Test
            db_path = os.path.join(PROJECT_DIR, "AI_data/main_database.db") # Adjust if path is different
            if os.path.exists(db_path):
                add_test_result("Backend (FastAPI) Server", "Database Initialization", "PASS", f"Database file found at {db_path}")
            else:
                add_test_result("Backend (FastAPI) Server", "Database Initialization", "WARN", f"Database file NOT found at {db_path}")

            # Core API Endpoint Tests
            endpoints_to_test = {
                "/api/health": {"expected_status": 200, "check_json_keys": ["status", "version"]},
                "/api/config": {"expected_status": 200, "check_json_keys": ["PROJECT_NAME", "PROJECT_VERSION"]},
            }
            for endpoint, params in endpoints_to_test.items():
                try:
                    response = requests.get(f"{FASTAPI_BASE_URL}{endpoint}", timeout=10)
                    if response.status_code == params["expected_status"]:
                        try:
                            res_json = response.json()
                            keys_missing = [k for k in params.get("check_json_keys", []) if k not in res_json]
                            if not keys_missing:
                                add_test_result("Backend (FastAPI) Server", f"Endpoint Test: {endpoint}", "PASS", f"Status {response.status_code}, expected keys found.")
                            else:
                                add_test_result("Backend (FastAPI) Server", f"Endpoint Test: {endpoint}", "WARN", f"Status {response.status_code}, but missing keys: {keys_missing}", value=str(res_json))
                        except ValueError:
                            add_test_result("Backend (FastAPI) Server", f"Endpoint Test: {endpoint}", "FAIL", f"Status {response.status_code}, but response is not valid JSON.")
                    else:
                        add_test_result("Backend (FastAPI) Server", f"Endpoint Test: {endpoint}", "FAIL", f"Expected status {params['expected_status']}, got {response.status_code}. Response: {response.text[:100]}")
                except requests.exceptions.RequestException as e:
                    add_test_result("Backend (FastAPI) Server", f"Endpoint Test: {endpoint}", "FAIL", f"Connection error: {e}")

            # Auth Endpoint Test
            auth_payload = {"apiKey": "test_colab_health_check_key_valid"} # This key is expected to be in backend's temp auth for testing
            try:
                response = requests.post(f"{FASTAPI_BASE_URL}/api/auth/login", json=auth_payload, timeout=10)
                if response.status_code == 200:
                    if "access_token" in response.json():
                        add_test_result("Backend (FastAPI) Server", "Auth Endpoint Test (/api/auth/login)", "PASS", "Login successful, access_token received.")
                    else:
                        add_test_result("Backend (FastAPI) Server", "Auth Endpoint Test (/api/auth/login)", "FAIL", "Status 200, but 'access_token' not in response.")
                else:
                    add_test_result("Backend (FastAPI) Server", "Auth Endpoint Test (/api/auth/login)", "FAIL", f"Expected status 200, got {response.status_code}. Response: {response.text[:100]}")
            except requests.exceptions.RequestException as e:
                add_test_result("Backend (FastAPI) Server", "Auth Endpoint Test (/api/auth/login)", "FAIL", f"Connection error: {e}")
        else: # Server not started
            add_test_result("Backend (FastAPI) Server", "Overall Server Startup", "FAIL", "Server did not start successfully. Skipping endpoint tests.")

    finally:
        log_message("Attempting to shutdown FastAPI server...")
        # Since we used `nohup ... &` with `shell=True`, fastapi_process.pid is the shell's PID.
        # Killing this shell PID might not kill the actual uvicorn server reliably.
        # A more robust way is to find the uvicorn process listening on the port.
        # Example: `pkill -f "uvicorn backend.main:app --port {FASTAPI_PORT}"`

        shutdown_status = "N/A"
        shutdown_details = "FastAPI process not found or not started via this script."

        # Attempt to find and kill the process by port (more reliable for `nohup ... &`)
        pkill_command = ["pkill", "-f", f"uvicorn backend.main:app --port {FASTAPI_PORT}"]
        log_message(f"Trying to kill server using: {' '.join(pkill_command)}")
        _, pkill_stderr, pkill_rc = run_shell_command(pkill_command)

        if pkill_rc == 0: # pkill found and signaled process(es)
            log_message(f"pkill command succeeded for port {FASTAPI_PORT}. Server likely stopped.")
            time.sleep(5) # Give time for processes to terminate
            # Verify by trying to connect again
            try:
                requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=3)
                log_message(f"Server on port {FASTAPI_PORT} still responding after pkill. Shutdown may have failed.", level="WARN")
                shutdown_status = "FAIL"
                shutdown_details = f"Server on port {FASTAPI_PORT} still responding after pkill."
            except requests.exceptions.ConnectionError:
                log_message(f"Server on port {FASTAPI_PORT} is not responding. Shutdown successful.")
                shutdown_status = "PASS"
                shutdown_details = f"Server on port {FASTAPI_PORT} stopped successfully after pkill."
        elif "no processes found" in pkill_stderr.lower() or pkill_rc == 1: # pkill found no processes
            log_message(f"pkill: No uvicorn process found running on port {FASTAPI_PORT}. It might have already stopped or failed to start.")
            # If server_started_successfully was True, this is a PASS for shutdown. Otherwise, it was already stopped.
            shutdown_status = "PASS" if server_started_successfully else "INFO"
            shutdown_details = "No uvicorn process found by pkill; assumed stopped or never fully started."
        else: # pkill command failed for other reasons
            log_message(f"pkill command failed or had issues. Stderr: {pkill_stderr}", level="WARN")
            shutdown_status = "WARN"
            shutdown_details = f"pkill command for port {FASTAPI_PORT} had issues. Stderr: {pkill_stderr}"

        add_test_result("Backend (FastAPI) Server", "Server Shutdown", shutdown_status, shutdown_details)

        # Cleanup log file
        if os.path.exists(FASTAPI_LOG_PATH):
            log_message(f"Removing temp FastAPI log: {FASTAPI_LOG_PATH}")
            # Optional: Add log content to main report before removing
            try:
                with open(FASTAPI_LOG_PATH, 'r') as f_log_final:
                    final_log_content = f_log_final.read()
                add_test_result("Backend (FastAPI) Server", "FastAPI Full Log", "INFO", details="Log attached", value=final_log_content[:2000]) # Attach a snippet
            except Exception as e_log:
                log_message(f"Could not read FastAPI log before deleting: {e_log}", level="WARN")
            # os.remove(FASTAPI_LOG_PATH) # Keep log for inspection for now

# --- Main Execution ---
if __name__ == "__main__":
    log_message("=== Comprehensive Health Check Script v2 Started ===")

    # Phase 1 returns True if clone was successful
    project_ready = phase_1_environment_setup()

    # Pass clone status to Phase 2
    phase_2_tests(project_ready)

    log_message("--- All Test Data Collected ---")
    results_json = json.dumps(RESULTS_DATA, indent=2, ensure_ascii=False)
    log_message(results_json)

    print("\n--- RESULTS_JSON_START ---")
    print(results_json)
    print("--- RESULTS_JSON_END ---")

    if LOG_MESSAGES:
        log_message(f"Total log messages collected: {len(LOG_MESSAGES)}")

    log_message("=== Comprehensive Health Check Script v2 Finished ===")
```
