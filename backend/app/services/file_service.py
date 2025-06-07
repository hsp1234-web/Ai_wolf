import os
import uuid
import logging
from typing import Tuple, Optional, IO, AsyncGenerator

import aiofiles # For async file operations
from fastapi import UploadFile

logger = logging.getLogger(__name__)

# Define a chunk size for reading/writing files, e.g., 1MB
CHUNK_SIZE = 1024 * 1024

async def save_uploaded_file(
    file: UploadFile,
    base_upload_dir: str
) -> Tuple[str, str, Optional[str], int]:
    """
    Saves an uploaded file to a unique directory and returns file metadata.

    Args:
        file: The UploadFile object from FastAPI.
        base_upload_dir: The base directory where 'uploads' will be created.

    Returns:
        A tuple containing (file_id, original_filename, content_type, file_size).
    Raises:
        IOError: If file saving fails.
    """
    file_id = uuid.uuid4().hex
    # Sanitize filename to prevent directory traversal or other security issues
    original_filename = os.path.basename(str(file.filename)) # Ensure filename is just the name
    if not original_filename: # Handle empty filename case
        original_filename = "unnamed_file"

    upload_path_for_file_id = os.path.join(base_upload_dir, "uploads", file_id)

    try:
        os.makedirs(upload_path_for_file_id, exist_ok=True)
        logger.info(f"Upload directory created/ensured: {upload_path_for_file_id}")
    except OSError as e:
        logger.error(f"Error creating upload directory {upload_path_for_file_id}: {e}")
        raise IOError(f"Could not create upload directory for file ID {file_id}") from e

    file_path = os.path.join(upload_path_for_file_id, original_filename)

    file_size = 0
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(CHUNK_SIZE):
                await out_file.write(content)
                file_size += len(content)
        logger.info(f"File '{original_filename}' (ID: {file_id}) saved successfully to '{file_path}', Size: {file_size} bytes.")
    except Exception as e:
        logger.error(f"Error saving file '{original_filename}' (ID: {file_id}) to '{file_path}': {e}", exc_info=True)
        # Attempt to clean up partially saved file or directory if error occurs
        if os.path.exists(file_path):
            os.remove(file_path)
        # If the directory is empty after removing the file, try removing it.
        if os.path.exists(upload_path_for_file_id) and not os.listdir(upload_path_for_file_id):
            os.rmdir(upload_path_for_file_id)
        raise IOError(f"Could not save file {original_filename}") from e

    # file.size is Optional[int], so handle if it's None (though usually set for UploadFile)
    # The manual calculation of file_size during write is more reliable.
    actual_size = file_size
    if file.size is not None and file.size != actual_size :
        logger.warning(f"Reported file size {file.size} differs from actual written size {actual_size} for {original_filename} (ID: {file_id}). Using actual size.")

    return file_id, original_filename, file.content_type, actual_size


def get_uploaded_file_path(
    file_id: str,
    file_name: str,
    base_upload_dir: str
) -> Optional[str]:
    """
    Constructs the path to an uploaded file given its ID and original name.
    Checks if the file exists.

    Args:
        file_id: The unique ID of the file.
        file_name: The original name of the file.
        base_upload_dir: The base directory where 'uploads' are stored.

    Returns:
        The full path to the file if it exists, otherwise None.
    """
    # Sanitize file_name again
    sane_file_name = os.path.basename(file_name)
    file_path = os.path.join(base_upload_dir, "uploads", file_id, sane_file_name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return file_path
    logger.warning(f"File not found at expected path: {file_path} (ID: {file_id}, Name: {sane_file_name})")
    return None

async def get_uploaded_file_content(
    file_id: str,
    file_name: str,
    base_upload_dir: str,
    mode: str = 'r' # 'r' for text, 'rb' for bytes
) -> Optional[str | bytes]:
    """
    Asynchronously reads the content of an uploaded file.

    Args:
        file_id: The unique ID of the file.
        file_name: The original name of the file.
        base_upload_dir: The base directory where 'uploads' are stored.
        mode: 'r' for text content (default), 'rb' for binary content.

    Returns:
        The file content as a string (for text mode) or bytes (for binary mode),
        or None if the file cannot be read.
    """
    file_path = get_uploaded_file_path(file_id, file_name, base_upload_dir)
    if not file_path:
        return None

    try:
        async with aiofiles.open(file_path, mode) as f:
            content = await f.read()
        return content
    except Exception as e:
        logger.error(f"Error reading file content for '{file_name}' (ID: {file_id}) from '{file_path}': {e}", exc_info=True)
        return None

async def get_uploaded_file_stream(
    file_id: str,
    file_name: str,
    base_upload_dir: str
) -> AsyncGenerator[bytes, None]:
    """
    Provides an async generator to stream the content of an uploaded file.
    Useful for large files to avoid loading entire content into memory.

    Args:
        file_id: The unique ID of the file.
        file_name: The original name of the file.
        base_upload_dir: The base directory where 'uploads' are stored.

    Yields:
        Chunks of the file content as bytes.

    Raises:
        FileNotFoundError: If the file does not exist at the constructed path.
        IOError: If there's an issue reading the file.
    """
    file_path = get_uploaded_file_path(file_id, file_name, base_upload_dir)
    if not file_path:
        logger.error(f"Stream: File not found for ID {file_id}, name {file_name}")
        raise FileNotFoundError(f"File {file_name} (ID: {file_id}) not found.")

    try:
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(CHUNK_SIZE):
                yield chunk
    except Exception as e:
        logger.error(f"Error streaming file content for '{file_name}' (ID: {file_id}) from '{file_path}': {e}", exc_info=True)
        raise IOError(f"Could not stream file {file_name} (ID: {file_id}).") from e

# Placeholder for future cleanup logic
async def cleanup_old_files(base_upload_dir: str, max_age_days: int):
    """
    Conceptual function to remove old uploaded files.
    Actual implementation would require tracking file ages (e.g., from directory mtime or a database).
    """
    logger.info(f"Conceptual cleanup: Would scan {os.path.join(base_upload_dir, 'uploads')} for files older than {max_age_days} days.")
    # This would involve:
    # 1. Listing all file_id directories in 'uploads'.
    # 2. For each directory, checking its creation/modification time.
    # 3. If older than max_age_days, remove the directory and its contents.
    # This needs careful implementation to avoid race conditions or errors.
    pass
