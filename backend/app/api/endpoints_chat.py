import logging
import random # For basic API key rotation
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from app.services import prompt_builder, gemini_service, model_catalog, file_service # Added file_service
from app.config import settings
from app.config.settings import AI_DATA_PATH # Added AI_DATA_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="訊息角色 ('user' 或 'model')")
    parts: List[str] = Field(..., description="訊息內容的多個部分")

# Removed UploadedFile model as it's replaced by uploadedFileInfo

class ChatRequest(BaseModel):
    userInput: str
    chatHistory: Optional[List[ChatMessage]] = None
    # uploadedFileContents: Optional[List[UploadedFile]] = None # Replaced
    uploadedFileInfo: Optional[List[Dict[str,str]]] = Field(None, description="上傳檔案的資訊列表，格式: [{'file_id': '...', 'file_name': '...'}, ...]")
    externalDataSummaries: Optional[Dict[str, Any]] = Field(None, description="客戶端已獲取並摘要的外部數據")
    selectedModelName: Optional[str] = None
    systemPromptOverride: Optional[str] = None
    generationConfig: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    isError: bool = False
    errorDetail: Optional[str] = None
    # modelUsed: Optional[str] = None
    # tokensUsed: Optional[int] = None
    # wasTruncated: Optional[bool] = None

@router.post("/chat", response_model=ChatResponse)
async def handle_chat_request(request: ChatRequest = Body(...)):
    '''
    處理聊天請求，與 Gemini 模型互動並返回結果。
    '''
    logger.info(f"API CALL: POST /api/chat with userInput: '{request.userInput[:50]}...'")

    try:
        # 1. Select API Key
        if not settings.AVAILABLE_GEMINI_API_KEYS:
            logger.error("沒有可用的 Gemini API 金鑰設定。")
            raise HTTPException(status_code=500, detail="後端 Gemini API 金鑰未設定。")

        current_api_key = random.choice(settings.AVAILABLE_GEMINI_API_KEYS)
        logger.info(f"使用 Gemini API 金鑰 (隨機選擇尾號 ...{current_api_key[-4:]})。")

        # 2. Determine Model
        model_to_use = request.selectedModelName or model_catalog.get_default_model()
        logger.info(f"使用模型: {model_to_use}")

        # 3. Determine System Prompt
        system_prompt_to_use = request.systemPromptOverride or settings.DEFAULT_MAIN_GEMINI_PROMPT
        plot_instruction = "\n如果需要生成圖表，請嚴格以 Plotly JSON schema 格式提供圖表數據。不要生成 Python 繪圖代碼。\n"
        if "Plotly JSON schema" not in system_prompt_to_use:
             system_prompt_to_use += plot_instruction
        logger.debug(f"使用的系統提示詞 (前100字符): {system_prompt_to_use[:100]}...")

        # 4. Prepare uploaded file contents
        core_docs_for_builder = [] # Initialize as empty list
        if request.uploadedFileInfo:
            logger.info(f"Processing {len(request.uploadedFileInfo)} uploaded file(s) information.")
            for file_info in request.uploadedFileInfo:
                file_id = file_info.get("file_id")
                file_name = file_info.get("file_name")

                if not file_id or not file_name:
                    logger.warning(f"Skipping a file due to missing file_id or file_name in uploadedFileInfo: {file_info}")
                    # Optionally, communicate this back to the user if possible/needed
                    continue

                try:
                    logger.debug(f"Attempting to read content for file_id: {file_id}, file_name: {file_name}")
                    # Assuming file content should be read as text (UTF-8)
                    content_str = await file_service.get_uploaded_file_content(
                        file_id=file_id,
                        file_name=file_name,
                        base_upload_dir=AI_DATA_PATH,
                        mode='r' # Read as text
                    )
                    if content_str is not None:
                        core_docs_for_builder.append({"name": file_name, "content": content_str})
                        logger.info(f"Successfully read and added content for: {file_name} (ID: {file_id})")
                    else:
                        logger.warning(f"Failed to read content for file: {file_name} (ID: {file_id}). File not found or empty.")
                        # Optionally, add a notice to the user or error log that a file was not processed
                except Exception as e:
                    logger.error(f"Error reading file {file_name} (ID: {file_id}): {e}", exc_info=True)
                    # Optionally, add a notice to the user

            if not core_docs_for_builder: # If list is empty after processing
                 logger.info("No file contents were successfully processed from uploadedFileInfo.")
                 # core_docs_for_builder will be an empty list, which is fine for prompt_builder

        # 5. Prepare chat history
        chat_history_for_builder = None
        if request.chatHistory:
            chat_history_for_builder = [msg.model_dump() for msg in request.chatHistory]
            logger.info(f"包含 {len(chat_history_for_builder)} 條聊天歷史。")

        # 6. Build prompt parts
        logger.info("正在建構提示詞...")
        prompt_parts = prompt_builder.build_gemini_request_contents(
            main_system_prompt=system_prompt_to_use,
            core_docs_contents=core_docs_for_builder,
            external_data_summaries=request.externalDataSummaries,
            chat_history_for_prompt=chat_history_for_builder,
            current_user_input=request.userInput
        )

        # 7. Call Gemini API
        generation_config_to_use = request.generationConfig or settings.DEFAULT_GENERATION_CONFIG
        logger.info(f"正在調用 Gemini API。模型: {model_to_use}")

        # call_gemini_api is synchronous, FastAPI will run it in a threadpool
        api_response_text, was_truncated = gemini_service.call_gemini_api(
            prompt_parts=prompt_parts,
            current_api_key=current_api_key,
            selected_model=model_to_use,
            generation_config_dict=generation_config_to_use,
            logger_object=logger
        )

        # Optionally include was_truncated in the response if needed by client
        # For now, just logging it.
        if was_truncated:
            logger.info("Gemini API 調用時提示詞被截斷。")

        if api_response_text.startswith("錯誤：") or "Error:" in api_response_text : # Broader check
            logger.error(f"Gemini API 返回錯誤: {api_response_text}")
            # Consider if all errors from gemini_service should be 500, or if some are client-related (4xx)
            return ChatResponse(response=api_response_text, isError=True, errorDetail=api_response_text)

        logger.info(f"Gemini API 成功返回。回應長度: {len(api_response_text)}")
        return ChatResponse(response=api_response_text)

    except HTTPException as http_exc:
        logger.error(f"HTTPException in /api/chat: {http_exc.detail}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"處理 /api/chat 請求時發生未預期錯誤: {e}", exc_info=True)
        # Return a generic error response to the client
        return ChatResponse(response="處理您的請求時發生意外的內部錯誤。", isError=True, errorDetail=str(e))
