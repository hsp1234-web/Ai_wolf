# components/chat_interface.py
import streamlit as st
import logging
import pandas as pd # For constructing prompt parts with DataFrame summaries
import os # Needed for os.path.basename
import re # For finding python-plot blocks
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import numpy as np # For exec context
from services.gemini_service import call_gemini_api
from services.prompt_builder import build_gemini_request_contents
from config.api_keys_config import api_keys_info # To get Gemini key names
from config import app_settings # Import app_settings for DEFAULT_MAIN_GEMINI_PROMPT
from config.app_settings import DEFAULT_GENERATION_CONFIG, DEFAULT_CHAT_CONTAINER_HEIGHT # Import specific settings

logger = logging.getLogger(__name__)

# Helper function to process and display model responses that might contain plots
def process_and_display_model_response_with_plots(response_text: str):
    """
    Processes the model's response text, displaying markdown for text parts
    and attempting to execute and render python-plot code blocks.
    """
    logger.debug(f"Processing model response for plot display. Response length: {len(response_text)}")
    # Pattern to find ```python-plot ... ``` blocks
    pattern = re.compile(r"```python-plot\n(.*?)\n```", re.DOTALL)
    parts = pattern.split(response_text)

    # Globals dict for exec, pre-populate with common libraries
    execution_globals = {
        'plt': plt,
        'go': go,
        'px': px,
        'pd': pd,
        'np': np,
        # 'st': st # Optionally, provide st if Gemini might generate st.write etc. For plots, usually not needed.
    }

    for i, part_content in enumerate(parts): # Renamed 'part' to 'part_content' to avoid conflict with pd.DataFrame.part
        if i % 2 == 0: # This is a text part
            if part_content.strip(): # Avoid rendering empty markdown parts
                st.markdown(part_content)
        else: # This is a plot code part
            plot_code = part_content.strip()
            if plot_code:
                logger.info(f"Executing python-plot code block:\n{plot_code[:300]}...") # Log snippet
                try:
                    # Using a fresh local scope for each execution
                    execution_locals = {}
                    exec(plot_code, execution_globals, execution_locals)

                    # Attempt to display Matplotlib plot
                    fig_mpl = execution_locals.get('fig', plt.gcf()) # Common practice to name the fig 'fig'

                    # Check if fig_mpl is a Matplotlib Figure and has axes (i.e., something was plotted)
                    if isinstance(fig_mpl, plt.Figure) and fig_mpl.get_axes():
                        logger.info("Displaying Matplotlib plot.")
                        st.pyplot(fig_mpl)
                    elif not isinstance(fig_mpl, plt.Figure): # If fig was something else, clear plt state
                        pass # Not a matplotlib figure from 'fig' variable or gcf() did not return one with axes

                    plt.clf() # Always clear the current figure state of plt
                    plt.close('all') # Close all figures plt might be tracking to free memory

                    # Attempt to display Plotly plot
                    # Check common names for Plotly figures in the executed code's locals
                    fig_plotly = None
                    if 'fig_plotly' in execution_locals:
                        fig_plotly = execution_locals['fig_plotly']
                    elif 'fig' in execution_locals and isinstance(execution_locals['fig'], go.Figure): # if 'fig' was used for plotly
                        fig_plotly = execution_locals['fig']

                    if fig_plotly and isinstance(fig_plotly, go.Figure):
                        logger.info("Displaying Plotly plot.")
                        st.plotly_chart(fig_plotly)
                    # else:
                        # logger.debug("No identifiable Plotly figure object found in execution locals.")

                except Exception as e_exec:
                    error_message = f"執行繪圖代碼時出錯 (Error executing plot code): {e_exec}"
                    logger.error(error_message, exc_info=True)
                    st.error(error_message)
                    st.code(plot_code, language="python") # Show the problematic code

def _trigger_gemini_response_processing():
    """
    Internal function to process the last user message in chat_history and get Gemini's response.
    This function assumes st.session_state.gemini_processing is already True.
    """
    logger.info("聊天介面 (_trigger_gemini_response_processing)：開始準備並調用 Gemini API。")
    with st.spinner("Gemini 正在思考中，請稍候..."):
        model_response_text = ""
        is_error_response = False
        try:
            logger.debug("聊天介面：開始構建 Gemini API 的提示詞列表 (prompt_parts) using prompt_builder.")

            # Retrieve data for prompt builder
            system_prompt_to_use = st.session_state.get("main_gemini_prompt", app_settings.DEFAULT_MAIN_GEMINI_PROMPT)

            # Prepare core_docs_contents for the builder
            # This will be List[Dict[str, str]] or None
            core_docs_for_builder = []
            selected_core_doc_relative_paths = st.session_state.get("selected_core_documents", [])
            wolf_data_file_map = st.session_state.get("wolf_data_file_map", {})
            uploaded_files_content_map = st.session_state.get("uploaded_file_contents", {})

            if selected_core_doc_relative_paths:
                logger.info(f"聊天介面：處理 {len(selected_core_doc_relative_paths)} 個選定的核心文件以用於 prompt_builder。")
                for rel_path in selected_core_doc_relative_paths:
                    doc_display_name = os.path.basename(rel_path)
                    content_to_add = None
                    core_doc_full_path = wolf_data_file_map.get(rel_path)

                    if core_doc_full_path and os.path.exists(core_doc_full_path):
                        try:
                            if core_doc_full_path.endswith((".txt", ".md")):
                                with open(core_doc_full_path, "r", encoding="utf-8") as f:
                                    content_to_add = f.read()
                            # For DataFrames or other types from Wolf_Data, they'd need specific handling here
                            # Assuming for now Wolf_Data primarily contains text files for core_docs
                            else:
                                content_to_add = f"[Unsupported file type from Wolf_Data: {doc_display_name}]"
                        except Exception as e:
                            content_to_add = f"[Error reading file {doc_display_name}: {str(e)}]"
                    elif rel_path in uploaded_files_content_map: # Check general uploaded files if selected as core
                        content_to_add = uploaded_files_content_map[rel_path]
                    else:
                        content_to_add = "[Content not available]"

                    core_docs_for_builder.append({"name": doc_display_name, "content": content_to_add})

            # Fallback: if no core docs selected, check if general uploaded files should be used (as per old logic)
            # The prompt_builder's `core_docs_contents` can handle general uploaded files too if formatted as List[Dict]
            # For simplicity and to match the new builder's design, we'll only pass selected_core_documents here.
            # If general uploaded files need to be included when no core docs are selected,
            # that logic could be added here to populate core_docs_for_builder from uploaded_files_content_map.
            # For now, sticking to selected_core_documents for `core_docs_contents`.
            # If `core_docs_for_builder` is empty, it will be passed as None or empty list to builder.

            external_data_for_prompt = st.session_state.get("fetched_data_preview") # This is Dict[str, Any]
            last_user_input = st.session_state.chat_history[-1]["parts"][0]

            # chat_history_for_prompt: Passing None as per subtask instructions for initial refactoring.
            # If chat history needs to be passed, it would be st.session_state.chat_history (after potential formatting)
            chat_history_for_builder = None

            logger.info(f"聊天介面：調用 build_gemini_request_contents。系統提示: {'是' if system_prompt_to_use else '否'}, 核心文件數: {len(core_docs_for_builder)}, 外部數據: {'是' if external_data_for_prompt else '否'}")

            full_prompt_parts = build_gemini_request_contents(
                main_system_prompt=system_prompt_to_use,
                core_docs_contents=core_docs_for_builder if core_docs_for_builder else None,
                external_data_summaries=external_data_for_prompt if external_data_for_prompt else None,
                chat_history_for_prompt=chat_history_for_builder,
                current_user_input=last_user_input
            )

            # Logging the context summary is now handled by the builder itself.
            # final_prompt_length = sum(len(str(p)) for p in full_prompt_parts) # Optional: log length if needed
            # logger.info(f"聊天介面：從 prompt_builder 獲得 {len(full_prompt_parts)} 個提示部分。")


            valid_gemini_api_keys = [st.session_state.get(key_name, "") for key_name in api_keys_info.values() if "gemini" in key_name.lower() and st.session_state.get(key_name, "")]
            selected_model_name = st.session_state.get("selected_model_name")
            # Use DEFAULT_GENERATION_CONFIG from app_settings
            generation_config = st.session_state.get("generation_config", app_settings.DEFAULT_GENERATION_CONFIG)
            selected_cache_name_for_api = st.session_state.get("selected_cache_for_generation")

            if not valid_gemini_api_keys:
                model_response_text = "錯誤：請在側邊欄設定至少一個有效的 Gemini API 金鑰。"
                is_error_response = True
            elif not selected_model_name:
                model_response_text = "錯誤：請在側邊欄選擇一個 Gemini 模型。"
                is_error_response = True
            else:
                # Modified call to unpack two return values
                model_response_text, was_truncated = call_gemini_api(
                    prompt_parts=full_prompt_parts, # This should be the list of strings
                    api_keys_list=valid_gemini_api_keys,
                    selected_model=selected_model_name,
                    global_rpm=st.session_state.get("global_rpm_limit", 3),
                    global_tpm=st.session_state.get("global_tpm_limit", 100000),
                    generation_config_dict=generation_config,
                    cached_content_name=selected_cache_name_for_api
                )
                if was_truncated:
                    st.toast("⚠️ 為符合模型限制，部分較早的對話或文件上下文已被移除。", icon="⚠️")

                if model_response_text.startswith("錯誤："): is_error_response = True
        except Exception as e:
            logger.error(f"聊天介面：在準備或調用 Gemini API 時發生意外錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
            model_response_text = f"處理您的請求時發生未預期的錯誤： {type(e).__name__} - {str(e)}"
            is_error_response = True

        st.session_state.chat_history.append({"role": "model", "parts": [model_response_text], "is_error": is_error_response})
        st.session_state.gemini_processing = False
        logger.info("聊天介面：Gemini API 處理完畢，準備刷新頁面顯示結果。")
        st.rerun()

def add_message_and_process(user_prompt_content: str, from_agent: bool = False):
    """
    Adds a user message to the chat history and triggers the Gemini processing flow via st.rerun().
    If 'from_agent' is True, it implies st.session_state.current_agent_prompt was set and might be cleared here or after processing.
    """
    logger.info(f"聊天介面 (add_message_and_process)：收到新的用戶提示 (來自 Agent: {from_agent})。長度: {len(user_prompt_content)}")
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.append({"role": "user", "parts": [user_prompt_content]})

    if from_agent:
        # Clear the current_agent_prompt as it's now been transferred to chat_history
        st.session_state.current_agent_prompt = ""
        logger.debug("聊天介面 (add_message_and_process)：已清除 current_agent_prompt (因 from_agent=True)。")

    # The actual processing will be picked up by render_chat after st.rerun()
    st.rerun()


def render_chat():
    """
    渲染聊天介面。
    顯示聊天歷史、處理用戶輸入，並調用 Gemini API 生成回應。
    """
    logger.info("聊天介面：開始渲染 (render_chat)。")

    st.header("💬 步驟三：與 Gemini 進行分析與討論")

    # Use DEFAULT_CHAT_CONTAINER_HEIGHT from app_settings
    chat_container_height = st.session_state.get("chat_container_height", app_settings.DEFAULT_CHAT_CONTAINER_HEIGHT)
    chat_container = st.container(height=chat_container_height)
    logger.debug(f"聊天介面：聊天容器高度設置為 {chat_container_height}px。")

    with chat_container:
        if "chat_history" not in st.session_state or not isinstance(st.session_state.chat_history, list):
            logger.warning("聊天介面：'chat_history' 未在 session_state 中正確初始化，將其重置為空列表。")
            st.session_state.chat_history = []

        for i, message in enumerate(st.session_state.chat_history):
            role = message.get("role", "model")
            avatar_icon = "👤" if role == "user" else "✨"
            with st.chat_message(role, avatar=avatar_icon):
                response_content = message["parts"][0]
                if message.get("is_error", False):
                    st.error(response_content)
                elif role == "model" and "```python-plot" in response_content:
                    process_and_display_model_response_with_plots(response_content)
                else:
                    st.markdown(response_content)

    user_input = st.chat_input("向 Gemini 提問或給出指令：", key="chat_user_input")

    if user_input:
        # Instead of directly appending and rerunning, call the new helper
        add_message_and_process(user_input, from_agent=False)

    # This block will now call the refactored processing function
    if st.session_state.chat_history and \
       st.session_state.chat_history[-1]["role"] == "user" and \
       not st.session_state.get("gemini_processing", False):
        st.session_state.gemini_processing = True # Mark as processing
        _trigger_gemini_response_processing() # Call the refactored internal function

    # logger.info("聊天介面：渲染結束 (render_chat)。") # Moved to the start of the function for this turn


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
