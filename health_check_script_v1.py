import os
import sys
import subprocess
import shutil
import datetime
import json
import re

# --- Global Variables/Setup ---
PROJECT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
PROJECT_DIR = "/content/wolfAI"
RESULTS_DATA = {"categories": []}
LOG_MESSAGES = []

# --- Helper Functions ---
def log_message(message, level="INFO"):
    """Appends a formatted message to LOG_MESSAGES and also prints it."""
    timestamp = datetime.datetime.now().isoformat()
    formatted_message = f"[{timestamp}] [{level}] {message}"
    LOG_MESSAGES.append(formatted_message)
    print(formatted_message)

def run_shell_command(command_list):
    """Executes a shell command, captures output and error, returns (stdout, stderr, returncode)."""
    log_message(f"Running command: {' '.join(command_list)}", level="DEBUG")
    try:
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=60) # 60-second timeout
        returncode = process.returncode
        # log_message(f"Command stdout: {stdout}", level="DEBUG")
        # if stderr:
        #     log_message(f"Command stderr: {stderr}", level="DEBUG")
        return stdout, stderr, returncode
    except subprocess.TimeoutExpired:
        log_message(f"Command timed out: {' '.join(command_list)}", level="ERROR")
        process.kill()
        stdout, stderr = process.communicate()
        return stdout, stderr, -1 # Indicate timeout with a specific return code
    except Exception as e:
        log_message(f"Error running command {' '.join(command_list)}: {e}", level="ERROR")
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

    # Clean up old project
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

    # Clone project
    log_message(f"Cloning project from {PROJECT_REPO_URL} into {PROJECT_DIR}...")
    stdout, stderr, returncode = run_shell_command(["git", "clone", "--depth", "1", PROJECT_REPO_URL, PROJECT_DIR])
    if returncode == 0:
        log_message("Project cloned successfully.")
        add_test_result("Environment Setup", "Clone Project Repository", "PASS", f"Cloned from {PROJECT_REPO_URL}")
        # Store this for Phase 2 check
        add_test_result("Project Structure and Dependencies", "Git Clone Success", "PASS", f"Cloned from {PROJECT_REPO_URL}")
    else:
        log_message(f"Failed to clone project. Return code: {returncode}\nStdout: {stdout}\nStderr: {stderr}", level="ERROR")
        add_test_result("Environment Setup", "Clone Project Repository", "FAIL", f"Return code: {returncode}. Error: {stderr or stdout}")
        add_test_result("Project Structure and Dependencies", "Git Clone Success", "FAIL", f"Return code: {returncode}. Error: {stderr or stdout}")
        # If clone fails, many subsequent tests are pointless. Consider early exit or flagging.

    # Install dependencies
    log_message("Installing dependencies from requirements.txt...")
    requirements_path = os.path.join(PROJECT_DIR, "requirements.txt")
    dep_status = "N/A"
    dep_details = "Project clone failed, skipping dependency installation."

    if returncode == 0: # Only proceed if clone was successful
        if os.path.exists(requirements_path):
            stdout, stderr, pip_returncode = run_shell_command([sys.executable, "-m", "pip", "install", "-q", "-r", requirements_path])
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
    # Store this for Phase 2 check
    add_test_result("Project Structure and Dependencies", "Dependency Install Success", dep_status, dep_details)


# --- Phase 2: Test Execution (Colab Environment & Project Basics) ---
def phase_2_tests():
    log_message("--- Phase 2: Test Execution ---")

    # Category: "Colab Environment"
    log_message("Running Colab Environment checks...")
    python_version = sys.version.replace("\n", "")
    add_test_result("Colab Environment", "Python Version", "INFO", value=python_version)

    # CPU Info
    try:
        stdout, stderr, returncode = run_shell_command(["lscpu"])
        if returncode == 0:
            model_name = re.search(r"Model name:\s*(.*)", stdout)
            cpus = re.search(r"CPU\(s\):\s*(\d+)", stdout)
            cpu_info_value = ""
            if model_name:
                cpu_info_value += f"Model: {model_name.group(1).strip()}"
            if cpus:
                cpu_info_value += f" | CPUs: {cpus.group(1).strip()}"
            add_test_result("Colab Environment", "CPU Info", "INFO", value=cpu_info_value if cpu_info_value else stdout)
        else:
            add_test_result("Colab Environment", "CPU Info", "FAIL", details=f"lscpu failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e:
        log_message(f"Error parsing CPU info: {e}", level="ERROR")
        add_test_result("Colab Environment", "CPU Info", "FAIL", details=f"Exception during lscpu parsing: {e}")

    # Memory Info
    try:
        stdout, stderr, returncode = run_shell_command(["cat", "/proc/meminfo"])
        if returncode == 0:
            mem_total = re.search(r"MemTotal:\s*(.*)", stdout)
            mem_available = re.search(r"MemAvailable:\s*(.*)", stdout) # More relevant than MemFree
            mem_info_value = ""
            if mem_total:
                mem_info_value += f"Total: {mem_total.group(1).strip()}"
            if mem_available:
                mem_info_value += f" | Available: {mem_available.group(1).strip()}"
            add_test_result("Colab Environment", "Memory Info", "INFO", value=mem_info_value if mem_info_value else stdout)
        else:
            add_test_result("Colab Environment", "Memory Info", "FAIL", details=f"cat /proc/meminfo failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e:
        log_message(f"Error parsing Memory info: {e}", level="ERROR")
        add_test_result("Colab Environment", "Memory Info", "FAIL", details=f"Exception during memory info parsing: {e}")

    # Disk Space
    try:
        stdout, stderr, returncode = run_shell_command(["df", "-h", "/"])
        if returncode == 0:
            lines = stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split() # Filesystem Size Used Avail Use% Mounted on
                disk_info_value = f"Device: {parts[0]}, Total Size: {parts[1]}, Used: {parts[2]}, Available: {parts[3]}, Use%: {parts[4]}"
                add_test_result("Colab Environment", "Disk Space (/)", "INFO", value=disk_info_value)
            else:
                add_test_result("Colab Environment", "Disk Space (/)", "WARN", details="df output format unexpected.", value=stdout)
        else:
            add_test_result("Colab Environment", "Disk Space (/)", "FAIL", details=f"df -h / failed. RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e:
        log_message(f"Error parsing Disk Space info: {e}", level="ERROR")
        add_test_result("Colab Environment", "Disk Space (/)", "FAIL", details=f"Exception during disk space parsing: {e}")

    # GPU Status
    try:
        stdout, stderr, returncode = run_shell_command(["nvidia-smi"])
        if returncode == 0:
            gpu_name_match = re.search(r"Product Name:\s*([^\s|]+)", stdout) # Attempt to find a common product name pattern
            if not gpu_name_match: # Fallback for different nvidia-smi versions
                 gpu_name_match = re.search(r"\|\s+\d+\s+([^|]+?)\s+(On|Off)\s+", stdout) # General pattern for GPU name in the table

            gpu_name = "GPU Found (Details in log)"
            if gpu_name_match:
                gpu_name = gpu_name_match.group(1).strip()

            # Try to get VRAM
            vram_match = re.search(r"(\d+MiB)\s*/\s*(\d+MiB)", stdout) # e.g., "15109MiB / 15360MiB"
            vram_info = ""
            if vram_match:
                vram_info = f" (VRAM: {vram_match.group(1)} / {vram_match.group(2)})"

            add_test_result("Colab Environment", "GPU Status", "INFO", value=f"{gpu_name}{vram_info}", details=stdout[:500]) # Store part of nvidia-smi output
        elif returncode == 127: # command not found
             add_test_result("Colab Environment", "GPU Status", "WARN", value="nvidia-smi not found", details="nvidia-smi command was not found. This usually means no NVIDIA GPU is present or drivers are not installed.")
        else:
            add_test_result("Colab Environment", "GPU Status", "INFO", value="No GPU allocated or nvidia-smi error", details=f"nvidia-smi RC: {returncode}. Error: {stderr or stdout}")
    except Exception as e:
        log_message(f"Error running/parsing nvidia-smi: {e}", level="ERROR")
        add_test_result("Colab Environment", "GPU Status", "FAIL", details=f"Exception during nvidia-smi execution/parsing: {e}")

    # Category: "Project Structure and Dependencies"
    log_message("Running Project Structure and Dependencies checks...")
    # Git Clone Success and Dependency Install Success are already added in Phase 1
    # but are part of this logical category.

    key_paths_to_check = [
        "app.py",
        "backend/main.py",
        "requirements.txt",
        "components/",
        "services/",
        "utils/",
        "style.css",
        "prompts.toml", # Added as per user feedback in other contexts
        ".streamlit/config.toml" # Added as per user feedback in other contexts
    ]

    # Only check paths if project dir exists (clone was successful)
    project_clone_successful = any(
        test["name"] == "Clone Project Repository" and test["status"] == "PASS"
        for cat in RESULTS_DATA["categories"] if cat["name"] == "Environment Setup"
        for test in cat["tests"]
    )

    if project_clone_successful:
        for path in key_paths_to_check:
            full_path = os.path.join(PROJECT_DIR, path)
            if os.path.exists(full_path):
                add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "PASS", value=f"{path} exists")
            else:
                add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "FAIL", value=f"{path} NOT found")
    else:
        log_message("Skipping key file/directory checks because project clone failed.", level="WARN")
        for path in key_paths_to_check:
            add_test_result("Project Structure and Dependencies", f"Check Path: {path}", "N/A", value="Project clone failed")


# --- Main Execution ---
if __name__ == "__main__":
    log_message("=== Comprehensive Health Check Script v1 Started ===")

    phase_1_environment_setup()
    phase_2_tests()

    log_message("--- Preliminary Test Data Collected ---")
    # Using ensure_ascii=False for proper display of CJK characters if any in future
    results_json = json.dumps(RESULTS_DATA, indent=2, ensure_ascii=False)
    log_message(results_json)
    # Also print to stdout directly for easier capture if needed, without timestamp/level
    print("\n--- RESULTS_JSON_START ---")
    print(results_json)
    print("--- RESULTS_JSON_END ---")

    log_message("\n--- Raw Log Messages Collected ---")
    # for msg in LOG_MESSAGES: # Already printed by log_message
    #     print(msg)
    if LOG_MESSAGES: # Print a count for verification
        log_message(f"Total log messages collected: {len(LOG_MESSAGES)}")

    log_message("=== Comprehensive Health Check Script v1 Finished ===")

```
