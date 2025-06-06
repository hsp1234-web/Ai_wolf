# components/chat_interface.py
import streamlit as st
import logging
import pandas as pd # For constructing prompt parts with DataFrame summaries
from services.gemini_service import call_gemini_api
from config.api_keys_config import api_keys_info # To get Gemini key names

logger = logging.getLogger(__name__)

def render_chat():
    """
    渲染聊天介面。
    顯示聊天歷史、處理用戶輸入，並調用 Gemini API 生成回應。
    """
    logger.info("聊天介面：開始渲染 (render_chat)。")

    st.header("💬 步驟三：與 Gemini 進行分析與討論")

    # 聊天訊息容器
    chat_container_height = st.session_state.get("chat_container_height", 400)
    chat_container = st.container(height=chat_container_height)
    logger.debug(f"聊天介面：聊天容器高度設置為 {chat_container_height}px。")

    with chat_container:
        # session_state.chat_history 應由 session_state_manager 初始化
        if "chat_history" not in st.session_state or not isinstance(st.session_state.chat_history, list):
            logger.warning("聊天介面：'chat_history' 未在 session_state 中正確初始化，將其重置為空列表。")
            st.session_state.chat_history = []

        for i, message in enumerate(st.session_state.chat_history):
            role = message.get("role", "model")
            avatar_icon = "👤" if role == "user" else "✨"
            with st.chat_message(role, avatar=avatar_icon):
                if message.get("is_error", False):
                    st.error(message["parts"][0])
                else:
                    st.markdown(message["parts"][0]) # Markdown可以更好地顯示格式化的AI回應

    user_input = st.chat_input("向 Gemini 提問或給出指令：", key="chat_user_input")

    if user_input:
        logger.info(f"聊天介面：收到用戶輸入 (長度: {len(user_input)}): '{user_input[:70]}...'")
        st.session_state.chat_history.append({"role": "user", "parts": [user_input]})
        st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user" and not st.session_state.get("gemini_processing", False):
        st.session_state.gemini_processing = True
        logger.info("聊天介面：檢測到新的用戶訊息，開始準備並調用 Gemini API。")

        with st.spinner("Gemini 正在思考中，請稍候..."):
            model_response_text = ""
            is_error_response = False

            try:
                logger.debug("聊天介面：開始構建 Gemini API 的提示詞列表 (prompt_parts)。")
                full_prompt_parts = []
                prompt_context_summary = [] # 用於記錄提示詞包含哪些上下文

                if st.session_state.get("main_gemini_prompt"):
                    full_prompt_parts.append(f"**主要指示 (System Prompt):**\n{st.session_state.main_gemini_prompt}")
                    prompt_context_summary.append("系統提示詞")

                if st.session_state.get("uploaded_file_contents") and isinstance(st.session_state.uploaded_file_contents, dict):
                    num_uploaded_files = len(st.session_state.uploaded_file_contents)
                    if num_uploaded_files > 0:
                        uploaded_texts_str = "**已上傳文件內容摘要:**\n"
                        for fn, content in st.session_state.uploaded_file_contents.items():
                            if isinstance(content, str):
                                uploaded_texts_str += f"檔名: {fn}\n內容片段 (前1000字符):\n{content[:1000]}...\n\n"
                            elif isinstance(content, pd.DataFrame):
                                 uploaded_texts_str += f"檔名: {fn} (表格數據)\n欄位: {', '.join(content.columns)}\n前3行:\n{content.head(3).to_string()}\n\n"
                            else: # 其他類型，如 bytes
                                uploaded_texts_str += f"檔名: {fn} (二進制或其他格式，無法直接預覽)\n\n"
                        full_prompt_parts.append(uploaded_texts_str)
                        prompt_context_summary.append(f"{num_uploaded_files}個已上傳檔案")

                if st.session_state.get("fetched_data_preview") and isinstance(st.session_state.fetched_data_preview, dict):
                    num_data_sources = len(st.session_state.fetched_data_preview)
                    if num_data_sources > 0:
                        external_data_str = "**已引入的外部市場與總經數據摘要:**\n"
                        for source, data_items in st.session_state.fetched_data_preview.items():
                            external_data_str += f"\n來源: {source.upper()}\n"
                            if isinstance(data_items, dict):
                                for item_name, df_item in data_items.items():
                                    if isinstance(df_item, pd.DataFrame):
                                        external_data_str += f"  {item_name} (最近3筆):\n{df_item.tail(3).to_string(index=False)}\n" # index=False 更簡潔
                            elif isinstance(data_items, pd.DataFrame):
                                external_data_str += f"  {source}數據 (最近3筆):\n{data_items.tail(3).to_string(index=False)}\n"
                        full_prompt_parts.append(external_data_str)
                        prompt_context_summary.append(f"{num_data_sources}個外部數據源")

                last_user_input = st.session_state.chat_history[-1]["parts"][0]
                full_prompt_parts.append(f"**使用者當前問題/指令:**\n{last_user_input}")
                prompt_context_summary.append("用戶當前問題")
                logger.info(f"聊天介面：Gemini 提示詞上下文包含: {', '.join(prompt_context_summary)}。")

                valid_gemini_api_keys = [
                    st.session_state.get(key_name, "")
                    for key_name in api_keys_info.values()
                    if "gemini" in key_name.lower() and st.session_state.get(key_name, "") # 確保比較時大小寫不敏感
                ]

                selected_model_name = st.session_state.get("selected_model_name")
                # 確保 generation_config 是從 session_state 獲取，如果不存在則使用預設值
                generation_config = st.session_state.get("generation_config", {"temperature": 0.7, "top_p": 0.9, "top_k": 32, "max_output_tokens": 8192})
                selected_cache_name_for_api = st.session_state.get("selected_cache_for_generation")

                if not valid_gemini_api_keys:
                    model_response_text = "錯誤：請在側邊欄設定至少一個有效的 Gemini API 金鑰。"
                    is_error_response = True
                    logger.error("聊天介面：無有效 Gemini API 金鑰，無法調用 API。")
                elif not selected_model_name:
                    model_response_text = "錯誤：請在側邊欄選擇一個 Gemini 模型。"
                    is_error_response = True
                    logger.error("聊天介面：未選擇 Gemini 模型，無法調用 API。")
                else:
                    logger.info(f"聊天介面：準備調用 call_gemini_api。模型: '{selected_model_name}', 有效金鑰數量: {len(valid_gemini_api_keys)}, 使用快取: '{selected_cache_name_for_api if selected_cache_name_for_api else '否'}'")
                    logger.debug(f"聊天介面：傳遞給 call_gemini_api 的 generation_config: {generation_config}")

                    model_response_text = call_gemini_api(
                        prompt_parts=full_prompt_parts,
                        api_keys_list=valid_gemini_api_keys,
                        selected_model=selected_model_name,
                        global_rpm=st.session_state.get("global_rpm_limit", 3),
                        global_tpm=st.session_state.get("global_tpm_limit", 100000),
                        generation_config_dict=generation_config,
                        cached_content_name=selected_cache_name_for_api
                    )

                    if model_response_text.startswith("錯誤："):
                        is_error_response = True
                        logger.warning(f"聊天介面：Gemini API 調用返回業務錯誤訊息: {model_response_text[:200]}...") #記錄部分錯誤信息
                    else:
                        logger.info(f"聊天介面：Gemini API 成功返回響應。響應長度: {len(model_response_text)}。")
                        logger.debug(f"聊天介面：Gemini API 響應 (前100字符): {model_response_text[:100]}...")


            except Exception as e:
                logger.error(f"聊天介面：在準備或調用 Gemini API 時發生意外錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
                model_response_text = f"處理您的請求時發生未預期的錯誤： {type(e).__name__} - {str(e)}"
                is_error_response = True

            logger.debug(f"聊天介面：將模型回應添加到聊天歷史。是否為錯誤: {is_error_response}。")
            st.session_state.chat_history.append({
                "role": "model",
                "parts": [model_response_text],
                "is_error": is_error_response
            })
            st.session_state.gemini_processing = False
            logger.info("聊天介面：Gemini API 處理完畢，準備刷新頁面顯示結果。")
            st.rerun()

    logger.info("聊天介面：渲染結束 (render_chat)。")

if __name__ == "__main__":
    # 為了能在本地運行和測試此組件，需要模擬 Streamlit 和 session_state
    # 以及相關的服務和配置。
    # 這通常比較複雜，更適合在集成到主應用後進行端到端測試。
    # 以下是一個非常基礎的模擬示例：

    # class MockSessionState:
    #     def __init__(self, initial_state=None):
    #         self._state = initial_state if initial_state else {}
    #     def get(self, key, default=None): return self._state.get(key, default)
    #     def __setitem__(self, key, value): self._state[key] = value
    #     def __getitem__(self, key): return self._state[key]
    #     def __contains__(self, key): return key in self._state
    #     def update(self, d): self._state.update(d)

    # st.session_state = MockSessionState({
    #     "chat_history": [],
    #     "main_gemini_prompt": "Test prompt",
    #     "uploaded_file_contents": {"test.txt": "File content"},
    #     "fetched_data_preview": {"yfinance": {"AAPL": pd.DataFrame({'Close': [150, 151]})}},
    #     "gemini_api_key_1": "FAKE_KEY", # 需要真實或模擬的 API key 才能完整測試
    #     "selected_model_name": "gemini-1.0-pro",
    #     "global_rpm_limit": 3,
    #     "global_tpm_limit": 100000,
    #     "active_gemini_key_index": 0,
    #     "gemini_api_key_usage": {},
    #     "api_keys_info": {"Gemini API Key 1": "gemini_api_key_1"}
    # })

    # 模擬 Streamlit UI 元素
    # st.header = print
    # st.container = lambda height: MockContainer() # 簡易模擬
    # st.chat_message = lambda role, avatar: MockChatMessage(role, avatar) # 簡易模擬
    # st.markdown = print
    # st.error = print
    # st.chat_input = lambda label, key: input(label) # 簡易模擬
    # st.spinner = lambda text: MockSpinner(text) # 簡易模擬
    # st.rerun = lambda: print("--- ST.RERUN CALLED ---")

    # class MockContainer:
    #     def __enter__(self): return self
    #     def __exit__(self, type, value, traceback): pass

    # class MockChatMessage:
    #     def __init__(self, role, avatar): self.role = role; self.avatar = avatar
    #     def __enter__(self): print(f"Entering chat message: {self.role}, Avatar: {self.avatar}"); return self
    #     def __exit__(self, type, value, traceback): print(f"Exiting chat message: {self.role}")

    # class MockSpinner:
    #     def __init__(self, text): self.text = text
    #     def __enter__(self): print(f"Spinner started: {self.text}"); return self
    #     def __exit__(self, type, value, traceback): print("Spinner finished.")

    # render_chat()
    pass
