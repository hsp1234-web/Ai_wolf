# utils/log_utils.py
import logging
# import streamlit as st # Removed Streamlit import
# from io import StringIO # StringIO not used after removing StreamlitLogHandler
import os
import sys
# from config.app_settings import MAX_UI_LOG_ENTRIES # Removed, was for StreamlitLogHandler

# StreamlitLogHandler class is removed as it's UI specific.

def setup_logging(
    log_level: int = logging.INFO,
    log_file_path: str = None
    # streamlit_ui_log_key parameter removed
) -> None: # Returns None as StreamlitLogHandler instance is no longer returned
    """
    Sets up root logging for a backend application.
    Configures console and optional file logging.

    Args:
        log_level (int): Logging level, e.g., logging.INFO, logging.DEBUG.
        log_file_path (str, optional): If provided, logs will also be written to this file.
    """
    log_format_str = "%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(log_format_str)

    handlers = []

    # 1. StreamHandler (Console)
    # Ensure console handler uses stdout or stderr consistently.
    # For many server apps, logging to stdout is common for containerization/orchestration.
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # 2. FileHandler
    if log_file_path:
        try:
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                 os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            # Use print for this critical bootstrap error, as logging might not be fully set up.
            print(f"Logging setup error: Failed to configure file log handler to '{log_file_path}': {e}", flush=True)

    # Configure root logger
    # Remove existing handlers and add new ones.
    # This is crucial in environments where logging might have been pre-configured (e.g. some PaaS).
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]: # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close()

    root_logger.setLevel(log_level)
    for handler in handlers:
        root_logger.addHandler(handler)

    initial_log_message = (
        f"Logging system configured. Level: {logging.getLevelName(log_level)}. "
        f"Handlers count: {len(handlers)}."
    )
    if log_file_path and any(isinstance(h, logging.FileHandler) for h in handlers):
        initial_log_message += f" Log file path: '{log_file_path}'."

    logging.info(initial_log_message)
    # No longer returns the handler instance

# if __name__ == "__main__":
    # This testing block was for the Streamlit-specific version.
    # A new testing block for the backend version would look different.
    # print("--- Backend Logging Util Test ---")

    # LOG_FILE_BACKEND = "backend_test_app.log"
    # if os.path.exists(LOG_FILE_BACKEND):
    #     os.remove(LOG_FILE_BACKEND)

    # print("\n[Test 1: INFO level, with file logging]")
    # setup_logging(log_level=logging.INFO, log_file_path=LOG_FILE_BACKEND)
    # logging.debug("This is a backend DEBUG log - should not appear.")
    # logging.info("This is a backend INFO log - should appear in console and file.")
    # logging.warning("This is a backend WARNING log.")

    # if os.path.exists(LOG_FILE_BACKEND):
    #     with open(LOG_FILE_BACKEND, 'r', encoding='utf-8') as f:
    #         print(f"\nContents of {LOG_FILE_BACKEND}:\n{f.read()}")
    # else:
    #     print(f"\nLog file {LOG_FILE_BACKEND} was not created.")

    # print("\n[Test 2: DEBUG level, console only]")
    # setup_logging(log_level=logging.DEBUG) # Should reconfigure root logger
    # logging.debug("This is another backend DEBUG log - should appear now.")
    # logging.info("This is another backend INFO log.")

    # print("\n--- Backend Logging Util Test Complete ---")
    # pass
