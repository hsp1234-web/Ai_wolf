# services/gemini_service.py
import streamlit as st
import google.generativeai as genai
import google.api_core.exceptions
import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from config.app_settings import TOKEN_SAFETY_FACTOR # Import specific setting

logger = logging.getLogger(__name__)

def call_gemini_api(
    prompt_parts: List[str],
    api_keys_list: List[str],
    selected_model: str,
    global_rpm: int,
    global_tpm: int, # TPM is not directly used in this version of call_gemini_api but kept for future
    generation_config_dict: Optional[Dict[str, Any]] = None,
    cached_content_name: Optional[str] = None
) -> Tuple[str, bool]: # Modified return type
    """
    呼叫 Gemini API 以生成內容。日誌記錄已添加。

    Args:
        prompt_parts: 提示詞的各部分組成的列表。
        api_keys_list: 可用的 Gemini API 金鑰列表。 (實際使用的金鑰將從 session_state 中基於索引選擇)
        selected_model: 要使用的 Gemini 模型名稱。
        global_rpm: 每分鐘允許的請求數上限。 (針對單一金鑰)
        global_tpm: 每分鐘允許的詞元數上限 (當前未使用，但保留參數)。
        generation_config_dict: Gemini 生成配置字典。
        cached_content_name: 要使用的已快取內容的名稱。

    Returns:
        Tuple[str, bool]: Gemini API 返回的文本結果 (或錯誤訊息) 和一個布林值指示是否發生了截斷。
    """
    logger.info(f"開始執行 call_gemini_api。模型: {selected_model}, 是否使用快取: {'是' if cached_content_name else '否'}, 提示詞部分數量: {len(prompt_parts)}")
    logger.debug(f"詳細參數 - global_rpm: {global_rpm}, global_tpm: {global_tpm}, generation_config: {generation_config_dict}, cached_content_name: {cached_content_name}")

    # Initialize was_truncated early, default to False for early exits or pre-truncation errors
    was_truncated = False

    if not api_keys_list:
        logger.error("Gemini API 呼叫中止：原始 API 金鑰列表為空。")
        return "錯誤：未提供有效的 Gemini API 金鑰。", was_truncated

    # 過濾掉暫時無效的金鑰
    temporarily_invalid_keys = st.session_state.get('temporarily_invalid_gemini_keys', [])
    available_keys = [key for key in api_keys_list if key not in temporarily_invalid_keys]
    logger.debug(f"原始 API 金鑰數量: {len(api_keys_list)}, 暫時無效金鑰數量: {len(temporarily_invalid_keys)}, 可用金鑰數量: {len(available_keys)}")

    if not available_keys:
        logger.error("Gemini API 呼叫中止：所有提供的 API 金鑰均已在本會話中被標記為無效。")
        return "錯誤：所有可用的 Gemini API 金鑰均已在本會話中被標記為無效或權限不足。", was_truncated

    # API 金鑰輪換和速率限制邏輯 (基於 available_keys)
    active_key_index = st.session_state.get('active_gemini_key_index', 0)
    # 確保 active_key_index 在 available_keys 的有效範圍內
    if active_key_index >= len(available_keys):
        active_key_index = 0
        logger.warning(f"active_gemini_key_index ({st.session_state.get('active_gemini_key_index')}) 超出可用金鑰列表範圍 (長度 {len(available_keys)})，已重置為 0。")
    st.session_state.active_gemini_key_index = active_key_index # 更新 session_state 中的索引

    current_api_key = available_keys[active_key_index]
    logger.info(f"選定可用 API 金鑰索引: {active_key_index} (金鑰尾號: ...{current_api_key[-4:] if current_api_key else 'N/A'})")

    now = time.time()
    # 初始化 API 金鑰使用情況追蹤 (如果尚未存在)
    if 'gemini_api_key_usage' not in st.session_state:
        st.session_state.gemini_api_key_usage = {}
        logger.debug("已初始化 session_state.gemini_api_key_usage。")

    # 為當前金鑰初始化使用追蹤（如果需要）
    if current_api_key not in st.session_state.gemini_api_key_usage:
        st.session_state.gemini_api_key_usage[current_api_key] = {'requests': [], 'tokens': []}
        logger.debug(f"已為金鑰 ...{current_api_key[-4:]} 初始化使用追蹤。")

    # 過濾掉60秒之前的請求記錄 (RPM 計算窗口)
    st.session_state.gemini_api_key_usage[current_api_key]['requests'] = [
        ts for ts in st.session_state.gemini_api_key_usage[current_api_key].get('requests', []) if now - ts < 60
    ]
    current_requests_count = len(st.session_state.gemini_api_key_usage[current_api_key]['requests'])
    logger.info(f"金鑰 ...{current_api_key[-4:]} 在過去60秒內的請求計數: {current_requests_count} (RPM 上限: {global_rpm})")

    if current_requests_count >= global_rpm:
        original_key_index_in_available = active_key_index
        # 輪換到下一個可用金鑰
        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(available_keys)
        next_api_key_candidate = available_keys[st.session_state.active_gemini_key_index]
        logger.warning(f"API 金鑰 ...{current_api_key[-4:]} (在可用列表中的索引 {original_key_index_in_available}) RPM 已達上限。嘗試切換到下一個可用金鑰索引 {st.session_state.active_gemini_key_index} (尾號: ...{next_api_key_candidate[-4:]})。")
        return f"錯誤：API 金鑰 ...{current_api_key[-4:]} RPM 達到上限 ({global_rpm})。已自動輪換金鑰，請重試。", was_truncated # was_truncated is False here

    try:
        logger.info(f"正在使用 API 金鑰 ...{current_api_key[-4:]} 配置 Gemini (模型: {selected_model})...")
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(model_name=selected_model)
        logger.debug(f"Gemini 模型實例化完成: {model}")

        # --- Token Counting and Truncation Logic (using helper function) ---
        final_contents_for_api_call = [str(p) for p in prompt_parts] # Default to original if truncation fails or not needed

        try:
            model_token_limit = model.input_token_limit
            # safety_factor = 0.90 # Replaced by app_settings.TOKEN_SAFETY_FACTOR
            effective_token_limit = int(model_token_limit * app_settings.TOKEN_SAFETY_FACTOR)
            logger.info(f"call_gemini_api: 模型 '{selected_model}' 輸入 Token 上限: {model_token_limit}, 安全計算閾值 (x{app_settings.TOKEN_SAFETY_FACTOR}): {effective_token_limit}")

            final_contents_for_api_call, was_truncated = _truncate_prompt_parts(
                prompt_parts, model, effective_token_limit, logger
            )
            if was_truncated:
                logger.info("call_gemini_api: 提示詞因Token超限已被截斷。")

        except Exception as e_trunc_setup:
            logger.error(f"call_gemini_api: 準備截斷或執行截斷時發生錯誤: {e_trunc_setup}. 將使用原始提示。", exc_info=True)
            final_contents_for_api_call = [str(p) for p in prompt_parts] # Ensure original parts are used
            was_truncated = False # Explicitly set to false as truncation process had an issue
        # --- End of Token Counting and Truncation ---

        generation_config_obj = genai.types.GenerationConfig(**generation_config_dict) if generation_config_dict else None
        logger.debug(f"Gemini 生成配置: {generation_config_obj}")

        # final_prompt_content = "\n---\n".join(map(str, contents_for_api_call)) # Using the potentially truncated list
        # The generate_content API expects a list of parts (which can be strings)
        # No need to join them into a single string here if the API handles List[str]

        logger.debug(f"最終發送到 Gemini 的內容部分數量: {len(final_contents_for_api_call)}")
        if final_contents_for_api_call:
            logger.debug(f"  首部分 (前100字符): {str(final_contents_for_api_call[0])[:100]}...")
            if len(final_contents_for_api_call) > 1:
                 logger.debug(f"  末部分 (前100字符): {str(final_contents_for_api_call[-1])[:100]}...")


        logger.info(f"正在調用 Gemini API (model.generate_content)... 使用快取: {cached_content_name if cached_content_name else '無'}")
        response = model.generate_content(
            final_contents_for_api_call, # Pass the list of content parts
            generation_config=generation_config_obj,
            safety_settings=None, # Default safety settings
            tools=None,
            tool_config=None,
            cached_content=cached_content_name
        )
        logger.info(f"Gemini API 呼叫成功 (金鑰 ...{current_api_key[-4:]}, 模型 {selected_model})。")

        st.session_state.gemini_api_key_usage[current_api_key]['requests'].append(now)
        if response.usage_metadata and response.usage_metadata.total_token_count:
            token_count = response.usage_metadata.total_token_count
            st.session_state.gemini_api_key_usage[current_api_key]['tokens'].append((now, token_count))
            logger.info(f"Gemini 使用元數據: {response.usage_metadata} (Tokens: {token_count})")
        else:
            logger.warning("Gemini API 響應中未找到使用元數據或 token 計數。")

        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(api_keys_list)
        logger.info(f"請求成功，API 金鑰索引為下一次呼叫輪換至: {st.session_state.active_gemini_key_index}")

        response_text = "".join(part.text for part in response.parts if hasattr(part, 'text')) if response.parts else ""
        if not response_text and hasattr(response, 'text') and response.text:
             response_text = response.text

        logger.info(f"從 Gemini API 獲取回應文本，長度: {len(response_text)}")
        if not response_text:
            logger.warning("Gemini API 返回的響應中沒有文本內容 (parts 或 text 均為空或無效)。")
            return "錯誤：模型未返回任何文字內容。", was_truncated

        logger.debug(f"Gemini API 原始回應 (前100字符): {response_text[:100]}...")
        return response_text, was_truncated

    except genai.types.BlockedPromptException as bpe:
        logger.error(f"Gemini API 錯誤 (BlockedPromptException) 使用金鑰 ...{current_api_key[-4:]}，模型 {selected_model}: {bpe}", exc_info=True)
        return f"錯誤：提示詞被 Gemini API 封鎖。原因: {bpe}", was_truncated # Error after truncation attempt
    except genai.types.generation_types.StopCandidateException as sce:
        logger.error(f"Gemini API 錯誤 (StopCandidateException) 使用金鑰 ...{current_api_key[-4:]}，模型 {selected_model}: {sce}", exc_info=True)
        return f"錯誤：內容生成因安全原因或其他限制而停止。原因: {sce}", was_truncated # Error after truncation attempt
    except google.api_core.exceptions.PermissionDenied as e:
        logger.error(f"Gemini API 錯誤 (PermissionDenied) 使用金鑰 ...{current_api_key[-4:]} (模型 {selected_model}): {str(e)}。該金鑰將被標記為暫時不可用。", exc_info=True)
        # 確保 'temporarily_invalid_gemini_keys' 列表存在於 session_state 中
        st.session_state.setdefault('temporarily_invalid_gemini_keys', [])
        if current_api_key not in st.session_state.temporarily_invalid_gemini_keys:
            st.session_state.temporarily_invalid_gemini_keys.append(current_api_key)
            logger.info(f"金鑰 ...{current_api_key[-4:]} 已添加到暫時無效列表。")
        # 更新 active_gemini_key_index 以便下次嘗試不同的 (如果有的話) 或相同的 (如果只有一個壞鍵)
        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(available_keys) if len(available_keys) > 0 else 0

        return f"錯誤：API 金鑰 ...{current_api_key[-4:]} 權限不足或已過期，已被標記為暫時不可用。請嘗試重新發送請求，系統將嘗試使用下一個可用金鑰。", False # Error before this call's content processing
    except google.api_core.exceptions.InvalidArgument as e:
        logger.error(f"Gemini API 錯誤 (InvalidArgument) 使用金鑰 ...{current_api_key[-4:]}，模型 {selected_model}: {str(e)}", exc_info=True)
        return f"錯誤：呼叫 Gemini API 時參數無效 (例如模型名稱 '{selected_model}' 不正確或內容不當)。詳細資訊: {str(e)}", was_truncated # Error after truncation attempt
    except google.api_core.exceptions.ResourceExhausted as re: # RPM/TPM 錯誤
        logger.error(f"Gemini API 錯誤 (ResourceExhausted) 使用金鑰 ...{current_api_key[-4:]}，模型 {selected_model}: {str(re)}", exc_info=True)
        # 這種情況下，我們也應該輪換金鑰，類似於 RPM 檢查後的輪換
        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(available_keys) if len(available_keys) > 0 else 0
        return f"錯誤：Gemini API 資源耗盡 (金鑰 ...{current_api_key[-4:]} 可能達到 RPM/TPM 上限)。已嘗試輪換金鑰，請重試。詳細資訊: {str(re)}", False # Error before this call's content processing
    except Exception as e:
        logger.error(f"呼叫 Gemini API 時發生非預期錯誤 (金鑰 ...{current_api_key[-4:]}，模型 {selected_model}): {type(e).__name__} - {str(e)}", exc_info=True)
        return f"呼叫 Gemini API 時發生非預期錯誤: {type(e).__name__} - {str(e)}", was_truncated # Error could be after truncation attempt


def _truncate_prompt_parts(prompt_parts: List[str], model: Any, effective_token_limit: int, logger_object: logging.Logger) -> Tuple[List[str], bool]:
    """
    智能截斷提示詞列表以符合 Token 限制。

    Args:
        prompt_parts: 原始提示詞部分列表。
        model: Gemini 模型對象 (用於 count_tokens)。
        effective_token_limit: 經安全係數調整後的有效 Token 上限。
        logger_object: 用於日誌記錄的 logger 實例。

    Returns:
        Tuple[List[str], bool]: 截斷後的提示詞列表和一個布林值 (True 表示發生了截斷)。
    """
    was_truncated = False
    contents_for_token_count = [str(p) for p in prompt_parts]

    try:
        token_count_response = model.count_tokens(contents_for_token_count)
        current_tokens = token_count_response.total_tokens
        logger_object.info(f"_truncate_prompt_parts: 初始 Token 數量: {current_tokens}, 限制: {effective_token_limit}")
    except Exception as e_count_tokens:
        logger_object.error(f"_truncate_prompt_parts: 計算 Token 數量時出錯: {e_count_tokens}. 無法執行截斷。", exc_info=True)
        return prompt_parts, False # 返回原始parts，未截斷

    if current_tokens > effective_token_limit:
        logger_object.warning(f"_truncate_prompt_parts: Token 數量 {current_tokens} 超過安全閾值 {effective_token_limit}。開始截斷...")
        was_truncated = True
        num_parts_original = len(contents_for_token_count)

        if num_parts_original <= 2:
            logger_object.warning(f"_truncate_prompt_parts: 無法進一步截斷，只有 {num_parts_original} 部分。")
            return contents_for_token_count, was_truncated # 雖然標記為 truncated，但實際未改變

        system_prompt_part = [prompt_parts[0]] if len(prompt_parts) > 0 else []
        user_question_part = [prompt_parts[-1]] if len(prompt_parts) > 1 else []
        middle_parts_to_truncate = list(prompt_parts[len(system_prompt_part):-len(user_question_part)])

        while current_tokens > effective_token_limit and middle_parts_to_truncate:
            middle_parts_to_truncate.pop(0) # 移除最早的中間部分
            temp_contents = system_prompt_part + middle_parts_to_truncate + user_question_part

            try:
                token_count_response = model.count_tokens(temp_contents)
                current_tokens = token_count_response.total_tokens
                logger_object.info(f"_truncate_prompt_parts: 截斷後，重新計算的 Token 數量: {current_tokens}")
            except Exception as e_recount:
                logger_object.error(f"_truncate_prompt_parts: 截斷後重新計算 Token 時出錯: {e_recount}. 停止截斷。", exc_info=True)
                # 返回當前已截斷的狀態，即使計數失敗
                return temp_contents, was_truncated

        contents_for_token_count = system_prompt_part + middle_parts_to_truncate + user_question_part
        if current_tokens > effective_token_limit:
            logger_object.warning(f"_truncate_prompt_parts: 即使截斷後，Token 數量 ({current_tokens}) 仍可能過高。")
    else:
        logger_object.info(f"_truncate_prompt_parts: Token 數量 {current_tokens} 在限制內，無需截斷。")

    return contents_for_token_count, was_truncated

def create_gemini_cache(
    api_key: str,
    model_name: str,
    cache_display_name: str,
    system_instruction: str,
    ttl_seconds: int
) -> Tuple[Optional[Any], Optional[str]]:
    """
    創建或更新 Gemini 內容快取。日誌記錄已添加。

    Args:
        api_key: 用於操作的 Gemini API 金鑰。
        model_name: 用於快取的模型名稱 (例如 "gemini-1.5-pro-latest")。
        cache_display_name: 快取的顯示名稱。
        system_instruction: 要快取的系統指令/內容。
        ttl_seconds: 快取的存活時間 (秒)。

    Returns:
        Tuple[Optional[genai.CachedContent], Optional[str]]:
            - genai.CachedContent 對象 (如果成功)。
            - 錯誤訊息字符串 (如果失敗)。
    """
    logger.info(f"開始創建/更新內容快取。顯示名稱: '{cache_display_name}', 模型: '{model_name}', TTL: {ttl_seconds}s")
    logger.debug(f"API 金鑰尾號: ...{api_key[-4:] if api_key else 'N/A'}, 系統指令長度: {len(system_instruction)}")

    if not all([api_key, model_name, cache_display_name, system_instruction]):
        msg = "創建快取失敗：API 金鑰、模型名稱、快取顯示名稱和內容均不能為空。"
        logger.error(msg) # 改為 error 級別
        return None, msg

    try:
        logger.debug(f"正在使用 API 金鑰 ...{api_key[-4:]} 配置 genai 以進行快取操作。")
        genai.configure(api_key=api_key)
        ttl_str = f"{ttl_seconds}s"

        model_for_caching_api = f"models/{model_name}" if not model_name.startswith("models/") else model_name
        logger.debug(f"用於快取的模型 API 名稱: {model_for_caching_api}")

        logger.info(f"正在調用 genai.create_cached_content API。顯示名稱: '{cache_display_name}'")
        cached_content = genai.create_cached_content(
            model=model_for_caching_api,
            display_name=cache_display_name,
            system_instruction=system_instruction, # 在 Gemini API v1beta 中，此參數可能為 contents=[system_instruction] 或特定字段
            ttl=ttl_str
        )
        logger.info(f"成功創建/更新快取。顯示名稱: '{cached_content.display_name}', 完整名稱: {cached_content.name}, 有效期至: {cached_content.expire_time}")
        logger.debug(f"快取對象詳情: {cached_content}")
        return cached_content, None
    except Exception as e:
        logger.error(f"創建/更新快取 '{cache_display_name}' (模型: {model_name}) 時發生錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
        return None, f"創建/更新快取失敗 (模型: {model_name}): {type(e).__name__} - {str(e)}"


def list_gemini_caches(api_key: str) -> Tuple[List[Any], Optional[str]]:
    """
    列出可用的 Gemini 內容快取。日誌記錄已添加。

    Args:
        api_key: 用於操作的 Gemini API 金鑰。

    Returns:
        Tuple[List[genai.CachedContent], Optional[str]]:
            - genai.CachedContent 對象列表。
            - 錯誤訊息字符串 (如果失敗)。
    """
    logger.info(f"開始列出 Gemini 內容快取。API 金鑰尾號: ...{api_key[-4:] if api_key else 'N/A'}")
    if not api_key:
        msg = "列出快取失敗：API 金鑰不能為空。"
        logger.error(msg) # 改為 error 級別
        return [], msg
    try:
        logger.debug(f"正在使用 API 金鑰 ...{api_key[-4:]} 配置 genai 以列出快取。")
        genai.configure(api_key=api_key)
        caches = list(genai.list_cached_contents()) # list_cached_contents() 返回迭代器
        logger.info(f"成功列出 {len(caches)} 個內容快取。")
        if caches:
            for i, c in enumerate(caches):
                logger.debug(f"  快取 {i+1}: DisplayName='{c.display_name}', Name='{c.name}', Model='{c.model}', CreateTime='{c.create_time}', ExpireTime='{c.expire_time}'")
        return caches, None
    except Exception as e:
        logger.error(f"列出內容快取時發生錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
        return [], f"列出快取失敗: {type(e).__name__} - {str(e)}"

def delete_gemini_cache(api_key: str, cache_name: str) -> Tuple[bool, Optional[str]]:
    """
    刪除指定的 Gemini 內容快取。日誌記錄已添加。

    Args:
        api_key: 用於操作的 Gemini API 金鑰。
        cache_name: 要刪除的快取的完整名稱 (例如 "cachedContents/...")。

    Returns:
        Tuple[bool, Optional[str]]:
            - True 如果成功刪除。
            - 錯誤訊息字符串 (如果失敗)。
    """
    logger.info(f"開始刪除 Gemini 內容快取。快取名稱: '{cache_name}', API 金鑰尾號: ...{api_key[-4:] if api_key else 'N/A'}")
    if not api_key or not cache_name:
        msg = "刪除快取失敗：API 金鑰和快取名稱均不能為空。"
        logger.error(msg) # 改為 error 級別
        return False, msg
    try:
        logger.debug(f"正在使用 API 金鑰 ...{api_key[-4:]} 配置 genai 以刪除快取 '{cache_name}'。")
        genai.configure(api_key=api_key)
        genai.delete_cached_content(name=cache_name)
        logger.info(f"成功刪除內容快取: {cache_name}")
        return True, None
    except google.api_core.exceptions.NotFound:
        logger.warning(f"試圖刪除的快取未找到: {cache_name}")
        return False, f"刪除失敗：快取 '{cache_name}' 未找到。"
    except Exception as e:
        logger.error(f"刪除內容快取 '{cache_name}' 時發生錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
        return False, f"刪除快取 '{cache_name}' 失敗: {type(e).__name__} - {str(e)}"

if __name__ == "__main__":
    # 簡易測試 (需要 Streamlit 環境和有效的 API Key / 網路連接)。
    # 這裡的測試代碼主要用於展示，實際執行需要配置好模擬的 st.session_state 和 API 金鑰。
    # 假設 st.session_state 已被適當初始化 (例如 API keys, active_gemini_key_index)

    # 模擬 st.session_state
    class MockSessionState:
        def __init__(self):
            self._state = {
                "active_gemini_key_index": 0,
                "gemini_api_key_usage": {}
                # "gemini_api_key_1": "YOUR_GEMINI_KEY_1", # 填入你的key
                # "gemini_api_key_2": "YOUR_GEMINI_KEY_2"  # 填入你的key
            }
        def get(self, key, default=None):
            return self._state.get(key, default)
        def __setitem__(self, key, value):
            self._state[key] = value
        def __contains__(self, key):
            return key in self._state

    # st.session_state = MockSessionState()
    # gemini_keys = [st.session_state.get("gemini_api_key_1",""), st.session_state.get("gemini_api_key_2","")]
    # valid_keys = [k for k in gemini_keys if k]

    # if valid_keys:
    #     logger.info("--- 測試 call_gemini_api ---")
    #     response = call_gemini_api(
    #         prompt_parts=["你好，Gemini！請介紹你自己。"],
    #         api_keys_list=valid_keys,
    #         selected_model="gemini-1.0-pro", # 或 "gemini-1.5-flash-latest"
    #         global_rpm=5,
    #         global_tpm=100000,
    #         generation_config_dict={"temperature": 0.7}
    #     )
    #     print("Gemini API Response:", response)

    #     logger.info("--- 測試快取管理 (需要一個有效的 API 金鑰) ---")
    #     test_api_key = valid_keys[0]
    #     cache_model = "gemini-1.0-pro" # 快取通常與特定模型類型關聯

        # logger.info("--- 測試創建快取 ---")
        # new_cache, err = create_gemini_cache(test_api_key, cache_model, "my_test_cache_01", "這是快取測試內容", 3600)
        # if err: print("Create Cache Error:", err)
        # if new_cache: print("Created Cache:", new_cache.name, new_cache.display_name)

        # logger.info("--- 測試列出快取 ---")
        # caches, err = list_gemini_caches(test_api_key)
        # if err: print("List Caches Error:", err)
        # if caches:
        #     print(f"Found {len(caches)} caches:")
        #     for c in caches: print(f"- {c.display_name} ({c.name}), Model: {c.model}")

        # logger.info("--- 測試刪除快取 ---")
        # 如果創建了快取並且知道其名稱，可以在此測試刪除
        # cache_to_delete_name = new_cache.name if new_cache else None
        # if cache_to_delete_name:
        #     success, err = delete_gemini_cache(test_api_key, cache_to_delete_name)
        #     if err: print("Delete Cache Error:", err)
        #     if success: print(f"Cache {cache_to_delete_name} deleted successfully.")
        # else:
        #     print("Skipping delete test as no cache was created or name is unknown.")
    # else:
    #     print("請在 MockSessionState 中設置有效的 Gemini API 金鑰以進行測試。")
    pass
