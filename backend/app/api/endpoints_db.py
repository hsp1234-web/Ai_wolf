import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import db_service # Assuming db_service.py is in app/services/

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class DBBackupResponse(BaseModel):
    success: bool = Field(..., description="是否成功執行備份操作")
    message: str = Field(..., description="操作結果的詳細訊息")
    backup_file_name: Optional[str] = Field(None, description="成功備份時的檔案名稱")

@router.post("/backup", response_model=DBBackupResponse)
async def backup_database_endpoint():
    """
    觸發資料庫備份操作。
    實際的備份過程是同步的，但 FastPI 會在線程池中執行它。
    """
    logger.info("API CALL: POST /api/db/backup - Request to backup database received.")

    try:
        # db_service.backup_database is a synchronous function.
        # FastAPI runs synchronous route handlers in a separate thread pool by default,
        # so we don't need to explicitly wrap it with run_in_threadpool here.
        success, message, backup_file = db_service.backup_database()

        if success:
            logger.info(f"Database backup successful: {message}")
            return DBBackupResponse(
                success=True,
                message=message,
                backup_file_name=backup_file
            )
        else:
            logger.error(f"Database backup failed: {message}")
            # For client errors (e.g. source DB not found, config issue),
            # it might be more appropriate to return a 4xx status code.
            # However, if it's a server-side issue (e.g., cannot write backup), 500 is okay.
            # Let's use 500 for any failure from the service for simplicity here.
            raise HTTPException(
                status_code=500,
                detail=f"資料庫備份失敗: {message}"
            )
    except Exception as e:
        # This catches unexpected errors either in the service call itself
        # or in the endpoint logic.
        logger.error(f"Unexpected error during database backup process: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"處理資料庫備份請求時發生未預期的伺服器錯誤: {str(e)}"
        )

# Example of how to test this endpoint using curl:
# curl -X POST http://localhost:8000/api/db/backup
# (Assuming your FastAPI app is running on port 8000)
