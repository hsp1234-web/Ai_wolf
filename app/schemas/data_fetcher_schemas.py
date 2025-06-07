from pydantic import BaseModel, Field, validator
from typing import Any, Dict

class DataFetchRequest(BaseModel):
    source: str = Field(..., description='The data source to fetch from, e.g., "fred"')
    parameters: Dict[str, Any] = Field(..., description='Parameters specific to the data source, e.g., {"symbol": "CPIAUCSL"}')

    @validator('source')
    def source_must_be_supported(cls, value: str) -> str:
        # Example validation, can be expanded
        if value.lower() not in ['fred']: # Add other supported sources here
            raise ValueError(f"Unsupported data source: {value}. Supported sources: ['fred']")
        return value.lower() # Normalize to lowercase

class DataFetchResponse(BaseModel):
    success: bool = Field(True, description="Indicates if the data fetch (including cache interaction) was successful from the service's perspective.")
    source: str = Field(..., description="The data source from which data was fetched or attempted.")
    parameters: Dict[str, Any] = Field(..., description="The parameters used for the data fetch request.")
    data: Any | None = Field(None, description="The fetched data, can be JSON, list of records, etc. Null if no data was retrieved or an error occurred before data retrieval.")
    message: str | None = Field(None, description="Optional message, e.g., 'Data retrieved from cache', or an error message if success is false but handled gracefully.")
    is_cached: bool = Field(False, description="Indicates if the returned data was served from the cache.")
