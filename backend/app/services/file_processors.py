# services/file_processors.py
# import streamlit as st # Removed Streamlit import
import logging
import pandas as pd
from io import StringIO, BytesIO
import os
# from utils.session_state_manager import IS_COLAB # Removed IS_COLAB import, ensure_colab_drive_mount_if_needed will be removed/commented

logger = logging.getLogger(__name__)

# The ensure_colab_drive_mount_if_needed function is heavily tied to Streamlit's session_state
# and a UI flow for Colab. It's not suitable for a backend service.
# If path validation is needed in the backend, it should be context-agnostic.
# For now, this function will be commented out.
# def ensure_colab_drive_mount_if_needed(path_to_check: str) -> bool:
#     """
#     Checks if a given path, potentially on Google Drive in Colab, exists.
#     If it's a Colab environment and the Drive path doesn't exist,
#     it sets session_state flags to prompt the user to mount their Drive.
#
#     Args:
#         path_to_check (str): The path to check.
#
#     Returns:
#         bool: True if the path exists or not in a relevant Colab/Drive scenario,
#               False if in Colab, it's a Drive path, and it doesn't exist (prompt will be set).
#     """
#     logger.debug(f"Ensuring path: {path_to_check}. IS_COLAB: {IS_COLAB}")
#     if IS_COLAB and path_to_check.startswith("/content/drive/"):
#         if not os.path.exists(path_to_check):
#             logger.warning(f"Colab Drive path '{path_to_check}' not found. Setting prompt flags.")
#             # st.session_state.show_drive_mount_prompt = True # Removed
#             # st.session_state.drive_path_requested = path_to_check # Removed
#             return False
#         else:
#             logger.debug(f"Colab Drive path '{path_to_check}' exists.")
#             # Ensure prompt is not shown if path now exists
#             # if st.session_state.get("drive_path_requested") == path_to_check and st.session_state.get("show_drive_mount_prompt"): # Removed
#             #      st.session_state.show_drive_mount_prompt = False # Removed
#             #      logger.info(f"Path '{path_to_check}' now exists, clearing show_drive_mount_prompt.") # Removed
#             return True
#     return True

def process_uploaded_files(files_data: list[dict]) -> dict:
    """
    Processes a list of file data (filename and bytes).
    Returns a dictionary with filenames as keys and processed contents (text, DataFrame, or bytes) as values.

    Args:
        files_data: A list of dictionaries, where each dictionary has:
                    {'filename': str, 'file_bytes': bytes, 'size': int, 'type': str (optional MIME type)}
    Returns:
        dict: A dictionary where keys are filenames and values are the processed file contents.
              Content can be str, pd.DataFrame, or bytes (if decoding/parsing fails).
    """
    logger.info(f"Starting process_uploaded_files. Received {len(files_data) if files_data else 0} files.")

    if not files_data:
        logger.info("No files provided for processing.")
        return {}

    processed_file_contents = {}

    for file_data in files_data:
        filename = file_data.get("filename")
        content_bytes = file_data.get("file_bytes")
        file_size = file_data.get("size", len(content_bytes) if content_bytes else 0)
        file_mime_type = file_data.get("type", "application/octet-stream") # Default MIME type

        if not filename or content_bytes is None:
            logger.warning(f"Skipping a file entry due to missing filename or content_bytes. Provided: {file_data}")
            continue

        logger.info(f"Processing file: '{filename}' (Size: {file_size} bytes, Type: {file_mime_type})")

        content = None
        file_type_processed = "Unknown"

        # Buffer for multiple read attempts if necessary (e.g. for pandas after text attempt)
        # For raw bytes, this is straightforward. If it were a stream, BytesIO would be needed.

        try:
            # --- Priority for table-like structures ---
            if filename.endswith((".csv")):
                file_type_processed = "CSV (DataFrame Attempt)"
                logger.debug(f"File '{filename}' identified as CSV. Attempting pandas read...")
                try:
                    # For raw bytes, pandas can read directly from BytesIO
                    df = pd.read_csv(BytesIO(content_bytes))
                    content = df
                    logger.info(f"Successfully read CSV file '{filename}' into DataFrame. Shape: {df.shape}")
                except Exception as e_csv_pandas:
                    logger.error(f"Pandas failed to read CSV file '{filename}': {e_csv_pandas}. Falling back to text.", exc_info=True)
                    # Fallback to text decoding for CSV
                    try:
                        content = content_bytes.decode("utf-8")
                        logger.info(f"Fallback: Successfully decoded CSV '{filename}' as UTF-8 text.")
                        file_type_processed = "Text (CSV Fallback UTF-8)"
                    except UnicodeDecodeError:
                        logger.warning(f"Fallback: UTF-8 decoding failed for CSV '{filename}'. Attempting latin-1...")
                        try:
                            content = content_bytes.decode("latin-1")
                            logger.info(f"Fallback: Successfully decoded CSV '{filename}' as latin-1 text.")
                            file_type_processed = "Text (CSV Fallback latin-1)"
                        except UnicodeDecodeError:
                            logger.error(f"Fallback: latin-1 decoding also failed for CSV '{filename}'. Storing as raw bytes.")
                            content = content_bytes
                            file_type_processed = "Bytes (CSV Text Fallback Failed)"

            elif filename.endswith((".xls", ".xlsx")):
                file_type_processed = "Excel (DataFrame Attempt)"
                logger.debug(f"File '{filename}' identified as Excel. Attempting pandas read...")
                try:
                    df = pd.read_excel(BytesIO(content_bytes), engine=None) # Auto-select engine
                    content = df
                    logger.info(f"Successfully read Excel file '{filename}' into DataFrame. Shape: {df.shape}")
                except Exception as e_excel:
                    logger.error(f"Pandas failed to read Excel file '{filename}': {e_excel}. Storing as raw bytes.", exc_info=True)
                    content = content_bytes
                    file_type_processed = "Bytes (Excel Read Failed)"

            # --- General text file processing (if not already processed as DataFrame) ---
            elif content is None and filename.endswith((".txt", ".py", ".json", ".md", ".log", ".xml", ".html", ".css", ".js")):
                file_type_processed = "Text (Generic)"
                logger.debug(f"File '{filename}' identified as generic text. Attempting UTF-8 decode...")
                try:
                    content = content_bytes.decode("utf-8")
                    logger.info(f"Successfully decoded '{filename}' as UTF-8 text. Length: {len(content)} chars.")
                except UnicodeDecodeError:
                    logger.warning(f"UTF-8 decoding failed for '{filename}'. Attempting latin-1...")
                    try:
                        content = content_bytes.decode("latin-1")
                        logger.info(f"Successfully decoded '{filename}' as latin-1 text. Length: {len(content)} chars.")
                    except UnicodeDecodeError:
                        logger.error(f"latin-1 decoding also failed for '{filename}'. Storing as raw bytes.")
                        content = content_bytes
                        file_type_processed = "Bytes (Text Decode Failed)"
                except Exception as e_text_generic:
                    logger.error(f"Unknown error reading/decoding '{filename}' as text: {e_text_generic}. Storing as raw bytes.", exc_info=True)
                    content = content_bytes
                    file_type_processed = "Bytes (Text Read/Decode Unknown Error)"

            # --- Fallback for any other file type or if content is still None ---
            elif content is None:
                logger.info(f"File '{filename}' did not match specific handlers or failed previous attempts. Storing as raw bytes.")
                content = content_bytes
                file_type_processed = "Bytes (Fallback)"

            processed_file_contents[filename] = content
            logger.debug(f"File '{filename}' processed. Stored type: {type(content).__name__}, Processing method: {file_type_processed}")

        except Exception as e_outer:
            logger.error(f"Top-level error while processing file '{filename}': {type(e_outer).__name__} - {str(e_outer)}", exc_info=True)
            # In a backend, we might raise an exception or return an error status for this file
            processed_file_contents[filename] = f"Error processing file: {str(e_outer)}"


    logger.info(f"All files processed. Total processed contents: {len(processed_file_contents)}")
    logger.debug(f"Processed file names: {list(processed_file_contents.keys())}")
    return processed_file_contents

# if __name__ == "__main__":
    # Mock data for testing the backend version
    # class MockFile:
    #     def __init__(self, name, content_bytes, size=None, type="application/octet-stream"):
    #         self.filename = name
    #         self.file_bytes = content_bytes
    #         self.size = size if size is not None else len(content_bytes)
    #         self.type = type

    # test_files_data = [
    #     {"filename": "test.txt", "file_bytes": b"This is a test file in UTF-8."},
    #     {"filename": "data.csv", "file_bytes": b"col1,col2\n1,alpha\n3,beta"},
    #     {"filename": "image.jpg", "file_bytes": b"\xff\xd8\xff\xe0\x00\x10JFIF"}, # Some image bytes
    #     {"filename": "invalid_utf8.txt", "file_bytes": b'\xff\xfeA\x00B\x00'} # Invalid UTF-8
    # ]

    # # Example with an Excel file (requires openpyxl or other engine for pandas)
    # try:
    #     from openpyxl import Workbook
    #     wb = Workbook()
    #     sheet = wb.active
    #     sheet['A1'] = "Header1"
    #     sheet['B1'] = "Header2"
    #     sheet['A2'] = 10
    #     sheet['B2'] = 20
    #     excel_bytes_io = BytesIO()
    #     wb.save(excel_bytes_io)
    #     excel_bytes = excel_bytes_io.getvalue()
    #     test_files_data.append({"filename": "test.xlsx", "file_bytes": excel_bytes})
    # except ImportError:
    #     print("openpyxl not installed, skipping Excel file test.")


    # processed_contents = process_uploaded_files(test_files_data)

    # print("\n--- Processed File Contents ---")
    # for name, content_item in processed_contents.items():
    #     if isinstance(content_item, pd.DataFrame):
    #         print(f"Content of {name}: DataFrame with shape {content_item.shape}")
    #         # print(content_item.head())
    #     elif isinstance(content_item, bytes):
    #          print(f"Content of {name}: Bytes with length {len(content_item)}")
    #     elif isinstance(content_item, str):
    #         print(f"Content of {name} (String, first 100 chars): {content_item[:100]}...")
    #     else:
    #         print(f"Content of {name}: Type {type(content_item).__name__}, {str(content_item)[:100]}...")
    # pass
