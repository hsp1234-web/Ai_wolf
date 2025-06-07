import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Any

# Assuming model_catalog.py or settings.py provides getting model list
# Corrected import paths relative to 'app' directory
from app.services import model_catalog
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

class ModelInfo(BaseModel):
    name: str
    displayName: str
    # Optional fields, can be added if model_catalog provides them
    # description: Optional[str] = None
    # input_token_limit: Optional[int] = None
    # output_token_limit: Optional[int] = None

class AppConfigResponse(BaseModel):
    appName: str = Field(..., description="應用程式名稱")
    appVersion: str = Field(..., description="應用程式版本")
    availableModels: List[ModelInfo] = Field(..., description="可用的 AI 模型列表")
    defaultModelName: str = Field(..., description="預設選中的模型名稱")
    # Example of other configs if needed:
    # defaultGenerationConfig: Dict[str, Any] = Field({}, description="預設生成配置")


# Dependency to get an API key (example, might not be needed if get_available_models handles it)
# def get_api_key():
#     if not settings.AVAILABLE_GEMINI_API_KEYS:
#         raise HTTPException(status_code=503, detail="No API keys configured for fetching models.")
#     return settings.AVAILABLE_GEMINI_API_KEYS[0] # Use the first one

@router.get("/config", response_model=AppConfigResponse)
async def get_app_config(): # Removed api_key: str = Depends(get_api_key) for now as get_available_models handles it
    '''
    獲取應用程式的前端動態配置，例如可用的模型列表。
    '''
    logger.info("API CALL: GET /api/config")
    try:
        # get_available_models now attempts to use a key from settings if none provided
        raw_models_data = model_catalog.get_available_models()

        available_models_pydantic = []
        if raw_models_data:
            for model_obj in raw_models_data:
                # model_catalog.get_available_models returns list of Model objects from genai
                # These objects have .name and .display_name attributes
                available_models_pydantic.append(ModelInfo(
                    name=getattr(model_obj, 'name', 'Unknown Name'),
                    displayName=getattr(model_obj, 'display_name', getattr(model_obj, 'name', 'Unknown Display Name'))
                ))
        else:
            logger.warning("/api/config - get_available_models returned empty or None. Check model_catalog service and API key validity.")
            # Decide if an empty model list is an error or acceptable
            # For now, returning empty list if that's what the service provides.

        default_model_name = model_catalog.get_default_model()

        return AppConfigResponse(
            appName=settings.APP_NAME,
            appVersion=settings.APP_VERSION,
            availableModels=available_models_pydantic,
            defaultModelName=default_model_name
            # defaultGenerationConfig=settings.DEFAULT_GENERATION_CONFIG # Example if needed
        )
    except Exception as e:
        logger.error(f"獲取 /api/config 時發生錯誤: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"無法獲取應用程式配置: {str(e)}")
