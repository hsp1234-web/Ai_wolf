import logging
import os
from typing import Optional, List

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel, Field

from app.config.settings import AI_DATA_PATH
from app.services import file_service # Assuming file_service.py is in app/services/

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class FileUploadResponse(BaseModel):
    file_id: str = Field(..., description="唯一的檔案識別碼 (UUID)")
    file_name: str = Field(..., description="上傳的原始檔案名稱")
    message: str = Field("檔案上傳成功", description="操作結果訊息")
    content_type: Optional[str] = Field(None, description="檔案的 Content-Type")
    size: Optional[int] = Field(None, description="檔案大小 (bytes)")

class FileInfo(BaseModel):
    file_id: str
    file_name: str
    content_type: Optional[str]
    size: Optional[int]

class MultipleFileUploadResponse(BaseModel):
    successful_uploads: List[FileUploadResponse] = Field(default_factory=list)
    failed_uploads: List[dict] = Field(default_factory=list) # Store filename and error message

@router.post("/upload", response_model=FileUploadResponse)
async def upload_single_file(file: UploadFile = File(...)):
    """
    上傳單個檔案。檔案將儲存在伺服器的 `AI_data/uploads/<file_id>/<original_filename>` 路徑下。
    """
    if not file.filename:
        logger.error("File upload attempt with no filename.")
        raise HTTPException(status_code=400, detail="上傳的檔案沒有檔案名稱。")

    logger.info(f"API CALL: POST /api/files/upload - Received file: '{file.filename}', Content-Type: {file.content_type}, Size: {file.size}")

    try:
        # AI_DATA_PATH is the base for all AI-related data, including uploads
        file_id, saved_filename, content_type, size = await file_service.save_uploaded_file(
            file=file,
            base_upload_dir=AI_DATA_PATH
        )

        logger.info(f"File '{saved_filename}' (ID: {file_id}) processed successfully by file_service.")

        return FileUploadResponse(
            file_id=file_id,
            file_name=saved_filename,
            content_type=content_type,
            size=size,
            message=f"檔案 '{saved_filename}' 上傳成功。"
        )
    except IOError as e:
        logger.error(f"IOError during file upload of '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"儲存檔案 '{file.filename}' 時發生錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during file upload of '{file.filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"處理檔案 '{file.filename}' 時發生未預期的伺服器錯誤。")


@router.post("/upload_multiple", response_model=MultipleFileUploadResponse)
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """
    上傳多個檔案。每個檔案將儲存在伺服器的 `AI_data/uploads/<file_id>/<original_filename>` 路徑下。
    """
    logger.info(f"API CALL: POST /api/files/upload_multiple - Received {len(files)} files.")

    successful_uploads: List[FileUploadResponse] = []
    failed_uploads: List[dict] = []

    for file in files:
        if not file.filename:
            logger.warning("Skipping a file in multiple upload because it has no filename.")
            failed_uploads.append({"file_name": "N/A", "error": "檔案沒有檔案名稱。"})
            continue

        logger.info(f"Processing file in multiple upload: '{file.filename}', Content-Type: {file.content_type}")
        try:
            file_id, saved_filename, content_type, size = await file_service.save_uploaded_file(
                file=file,
                base_upload_dir=AI_DATA_PATH
            )
            successful_uploads.append(FileUploadResponse(
                file_id=file_id,
                file_name=saved_filename,
                content_type=content_type,
                size=size,
                message=f"檔案 '{saved_filename}' 上傳成功。"
            ))
            logger.info(f"Successfully uploaded '{saved_filename}' (ID: {file_id}) in multiple upload.")
        except IOError as e:
            logger.error(f"IOError during multiple file upload of '{file.filename}': {e}", exc_info=True)
            failed_uploads.append({"file_name": file.filename, "error": f"儲存檔案時發生錯誤: {str(e)}"})
        except Exception as e:
            logger.error(f"Unexpected error during multiple file upload of '{file.filename}': {e}", exc_info=True)
            failed_uploads.append({"file_name": file.filename, "error": f"處理檔案時發生未預期的伺服器錯誤。"})

    logger.info(f"Multiple file upload process finished. Successful: {len(successful_uploads)}, Failed: {len(failed_uploads)}")
    return MultipleFileUploadResponse(successful_uploads=successful_uploads, failed_uploads=failed_uploads)

# Future: Add endpoints for listing, downloading, deleting files if needed.
# Example:
# @router.get("/{file_id}/{file_name}")
# async def download_file(file_id: str, file_name: str):
#     file_path = file_service.get_uploaded_file_path(file_id, file_name, AI_DATA_PATH)
#     if not file_path:
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(file_path, media_type='application/octet-stream', filename=file_name)
