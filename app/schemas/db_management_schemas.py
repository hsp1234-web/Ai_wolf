from pydantic import BaseModel, Field
from typing import Optional

class BackupResponse(BaseModel):
    success: bool = Field(..., description="Indicates whether the backup operation was successful.")
    message: str = Field(..., description="A message detailing the outcome of the backup operation.")
    backup_path: Optional[str] = Field(None, description="The absolute or relative path to the created backup file, if successful.")
