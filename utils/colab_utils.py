# utils/colab_utils.py
import streamlit as st
import logging
import os
from utils.session_state_manager import IS_COLAB # Assuming this is the best source for IS_COLAB

logger = logging.getLogger(__name__)

def ensure_colab_drive_mount_if_needed(path_to_check: str) -> bool:
    """
    Checks if a given path, potentially on Google Drive in Colab, exists.
    If it's a Colab environment and the Drive path doesn't exist,
    it sets session_state flags to prompt the user to mount their Drive.

    Args:
        path_to_check (str): The path to check.

    Returns:
        bool: True if the path exists or not in a relevant Colab/Drive scenario,
              False if in Colab, it's a Drive path, and it doesn't exist (prompt will be set).
    """
    logger.debug(f"Ensuring path: {path_to_check}. IS_COLAB: {IS_COLAB}")
    if IS_COLAB and path_to_check.startswith("/content/drive/"):
        if not os.path.exists(path_to_check):
            logger.warning(f"Colab Drive path '{path_to_check}' not found. Setting prompt flags.")
            # Ensure session_state keys are initialized before setting them
            if "show_drive_mount_prompt" not in st.session_state:
                st.session_state.show_drive_mount_prompt = False
            if "drive_path_requested" not in st.session_state:
                st.session_state.drive_path_requested = ""

            st.session_state.show_drive_mount_prompt = True
            st.session_state.drive_path_requested = path_to_check
            return False
        else:
            logger.debug(f"Colab Drive path '{path_to_check}' exists.")
            # Ensure prompt is not shown if path now exists
            if st.session_state.get("drive_path_requested") == path_to_check and st.session_state.get("show_drive_mount_prompt"):
                 st.session_state.show_drive_mount_prompt = False
                 logger.info(f"Path '{path_to_check}' now exists, clearing show_drive_mount_prompt.")
            return True
    # Not in Colab, or not a /content/drive/ path, or path exists.
    return True
