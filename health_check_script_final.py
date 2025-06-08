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
PROJECT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
PROJECT_DIR = "/content/wolfAI"
RESULTS_DATA = {"categories": []}
LOG_MESSAGES = []

FASTAPI_PORT = 8008 # Using a non-default port for testing
FASTAPI_BASE_URL = f"http://127.0.0.1:{FASTAPI_PORT}"
FASTAPI_LOG_PATH = "/content/temp_fastapi_health_check.log" # Will be kept for inspection
fastapi_process = None # To store the FastAPI server process

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
    return clone_successful

# --- Phase 2: Test Execution ---
def phase_2_tests(project_clone_successful):
    log_message("--- Phase 2: Test Execution ---")

    # Colab Environment Checks (condensed from v2)
    log_message("Running Colab Environment checks...")
    add_test_result("Colab Environment", "Python Version", "INFO", value=sys.version.replace("\n", ""))
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
    global fastapi_process
    log_message("Running Backend (FastAPI) Server checks...")
    os.makedirs(os.path.dirname(FASTAPI_LOG_PATH), exist_ok=True)
    if os.path.exists(FASTAPI_LOG_PATH): os.remove(FASTAPI_LOG_PATH)

    # Use shell=True for nohup & backgrounding. This is less robust.
    # Consider replacing with a library or more direct process control if issues arise.
    fastapi_cmd_str = f"nohup {sys.executable} -m uvicorn backend.main:app --host 0.0.0.0 --port {FASTAPI_PORT} --app-dir {PROJECT_DIR} > {FASTAPI_LOG_PATH} 2>&1 &"
    server_started_ok = False
    try:
        log_message(f"Starting FastAPI server (Port: {FASTAPI_PORT})...")
        # For shell=True, Popen needs a string command.
        fastapi_process = subprocess.Popen(fastapi_cmd_str, shell=True, cwd=PROJECT_DIR)
        log_message(f"FastAPI shell process PID: {fastapi_process.pid}. Waiting 15s...")
        time.sleep(15)

        log_ok = os.path.exists(FASTAPI_LOG_PATH) and os.path.getsize(FASTAPI_LOG_PATH) > 0
        log_content_sample = ""
        if log_ok:
            with open(FASTAPI_LOG_PATH, 'r', encoding='utf-8') as f: log_content_sample = f.read(500)
            if "Uvicorn running on" in log_content_sample or "Application startup complete" in log_content_sample:
                server_started_ok = True
                add_test_result("Backend (FastAPI) Server", "Server Startup (Log Check)", "PASS", "Startup message in log.", value=log_content_sample)
            else:
                add_test_result("Backend (FastAPI) Server", "Server Startup (Log Check)", "FAIL", "Startup message NOT in log.", value=log_content_sample)
        else:
            add_test_result("Backend (FastAPI) Server", "Server Startup (Log Check)", "FAIL", "Log file not found or empty.")

        if not server_started_ok: # Try ping if log check failed
            try:
                r = requests.get(f"{FASTAPI_BASE_URL}/api/health", timeout=5)
                if r.status_code == 200: server_started_ok = True; add_test_result("Backend (FastAPI) Server", "Server Startup (Ping)", "PASS", "/api/health OK")
                else: add_test_result("Backend (FastAPI) Server", "Server Startup (Ping)", "FAIL", f"/api/health status: {r.status_code}")
            except requests.exceptions.ConnectionError: add_test_result("Backend (FastAPI) Server", "Server Startup (Ping)", "FAIL", "Connection error to /api/health")

        if server_started_ok:
            add_test_result("Backend (FastAPI) Server", "Overall Server Startup", "PASS")
            db_path = os.path.join(PROJECT_DIR, "AI_data/main_database.db") # Adjust if needed
            add_test_result("Backend (FastAPI) Server", "Database Initialization", "PASS" if os.path.exists(db_path) else "WARN", f"DB at {db_path} {'found' if os.path.exists(db_path) else 'NOT found'}")
            # Test /api/health and /api/config
            for ep, checks in {"/api/health":{"keys":["status","version"]}, "/api/config":{"keys":["PROJECT_NAME"]}}.items():
                try:
                    r = requests.get(f"{FASTAPI_BASE_URL}{ep}", timeout=10)
                    if r.status_code == 200:
                        missing_keys = [k for k in checks["keys"] if k not in r.json()]
                        if not missing_keys: add_test_result("Backend (FastAPI) Server", f"Endpoint: {ep}", "PASS", f"Status 200, keys OK.")
                        else: add_test_result("Backend (FastAPI) Server", f"Endpoint: {ep}", "WARN", f"Status 200, missing keys: {missing_keys}", value=str(r.json()))
                    else: add_test_result("Backend (FastAPI) Server", f"Endpoint: {ep}", "FAIL", f"Status: {r.status_code}",value=r.text[:100])
                except Exception as e: add_test_result("Backend (FastAPI) Server", f"Endpoint: {ep}", "FAIL", str(e))
            # Test /api/auth/login
            try:
                r = requests.post(f"{FASTAPI_BASE_URL}/api/auth/login", json={"apiKey":"test_colab_health_check_key_valid"}, timeout=10)
                if r.status_code == 200 and "access_token" in r.json(): add_test_result("Backend (FastAPI) Server", "/api/auth/login", "PASS", "Login OK, token received.")
                else: add_test_result("Backend (FastAPI) Server", "/api/auth/login", "FAIL", f"Status {r.status_code}, token in response: {'access_token' in r.json() if r.status_code==200 else 'N/A'}")
            except Exception as e: add_test_result("Backend (FastAPI) Server", "/api/auth/login", "FAIL", str(e))
        else:
            add_test_result("Backend (FastAPI) Server", "Overall Server Startup", "FAIL", "Server did not start. Endpoint tests skipped.")
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

```
