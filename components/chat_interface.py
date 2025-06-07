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
# Removed: from services.gemini_service import call_gemini_api
# Removed: from services.prompt_builder import build_gemini_request_contents
# Removed: from config.api_keys_config import api_keys_info
import requests # Added
import json # Added
# from config import app_settings # No longer importing the whole module directly if settings come from ui_settings
# from config.app_settings import DEFAULT_CHAT_CONTAINER_HEIGHT # This will come from ui_settings

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
    Internal function to process the last user message in chat_history and get AI's response via backend.
    This function assumes st.session_state.gemini_processing is already True.
    """
    logger.info("聊天介面 (_trigger_gemini_response_processing)：開始準備並調用後端 API。")
    with st.spinner("AI 正在思考中，請稍候..."):
        model_response_text = ""
        is_error_response = False

        try:
            # 1. Collect necessary data
            user_input = st.session_state.chat_history[-1]["parts"][0] # Get the latest user input

            # Prepare chat_history for backend (ensure it's serializable and matches backend format)
            # Assuming backend expects [{"role": "user", "parts": ["text"]}, {"role": "model", "parts": ["text"]}]
            chat_history_for_backend = []
            for msg in st.session_state.chat_history[:-1]: # Exclude the current user input
                role = msg.get("role")
                parts = msg.get("parts")
                if role and parts: # Ensure essential fields are present
                    chat_history_for_backend.append({"role": role, "parts": parts})

            ui_settings = st.session_state.get("ui_settings", {})
            default_prompt_from_settings = ui_settings.get("default_main_gemini_prompt", "Fallback: Provide analysis.")
            system_prompt = st.session_state.get("main_gemini_prompt", default_prompt_from_settings)

            context_documents = []
            # Priority to selected_core_documents
            selected_core_docs_paths = st.session_state.get("selected_core_documents", [])
            wolf_data_file_map = st.session_state.get("wolf_data_file_map", {})
            uploaded_files_content_map = st.session_state.get("uploaded_file_contents", {})

            processed_doc_names = set()

            if selected_core_docs_paths:
                logger.info(f"處理 {len(selected_core_docs_paths)} 個選定的核心文件。")
                for rel_path in selected_core_docs_paths:
                    doc_display_name = os.path.basename(rel_path)
                    content = "[Content not available]"
                    core_doc_full_path = wolf_data_file_map.get(rel_path)
                    if core_doc_full_path and os.path.exists(core_doc_full_path):
                        try:
                            if core_doc_full_path.endswith((".txt", ".md")):
                                with open(core_doc_full_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                            else: # Placeholder for other types, or could be an error/skip
                                content = f"[Unsupported core file type: {doc_display_name}]"
                        except Exception as e:
                            content = f"[Error reading core file {doc_display_name}: {str(e)}]"
                    elif rel_path in uploaded_files_content_map: # Check if it's a generally uploaded file selected as core
                         content = uploaded_files_content_map[rel_path]

                    context_documents.append({"filename": doc_display_name, "content": content})
                    processed_doc_names.add(doc_display_name)

            # Add other uploaded files if "Include all uploaded files" is active (or similar logic)
            # For now, let's assume only selected_core_documents are primary context.
            # If general uploaded files are also to be included by default, add them here, avoiding duplicates.
            # This example assumes only selected_core_documents for simplicity of change.
            # If you have a separate toggle for "include all uploaded files" it would be checked here.
            # For example, to add all OTHER uploaded files not already added as core docs:
            # for filename, content in uploaded_files_content_map.items():
            #    if filename not in processed_doc_names: # Avoid duplication
            #        context_documents.append({"filename": filename, "content": content})


            external_data_summary = ""
            fetched_data_preview = st.session_state.get("fetched_data_preview", {})
            if fetched_data_preview:
                summary_parts = []
                for source, data in fetched_data_preview.items():
                    if isinstance(data, pd.DataFrame):
                        summary_parts.append(f"Summary for {source}:\n{data.head().to_string()}\n...")
                    else:
                        summary_parts.append(f"Data from {source}: {str(data)[:200]}...")
                external_data_summary = "\n".join(summary_parts)

            # 2. Construct payload
            payload = {
                "user_input": user_input,
                "chat_history": chat_history_for_backend,
                "system_prompt": system_prompt,
                "context_documents": context_documents,
                "external_data_summary": external_data_summary
                # Add any other fields expected by the backend, e.g., model_name, generation_config
                # "model_name": st.session_state.get("selected_model_name"),
                # "generation_config": st.session_state.get("generation_config", DEFAULT_GENERATION_CONFIG)
            }
            logger.debug(f"發送到後端的請求體 (部分內容): user_input='{payload['user_input'][:50]}...', history_len={len(payload['chat_history'])}, system_prompt_len={len(payload['system_prompt'])}, docs_count={len(payload['context_documents'])}")

            # 3. Send HTTP POST request
            backend_url = "http://localhost:8000/api/chat/invoke" # As per assumption

            response = requests.post(backend_url, json=payload, timeout=180) # Increased timeout
            response.raise_for_status() # Raises HTTPError for 4xx/5xx status codes

            api_response_json = response.json()
            model_response_text = api_response_json.get("response")

            if model_response_text is None: # Check if 'response' key exists and has a value
                logger.error(f"後端 API 回應中缺少 'response' 欄位或其值為 None。回應: {api_response_json}")
                model_response_text = "錯誤：AI服務返回的數據格式不正確 (缺少 'response' 內容)。"
                is_error_response = True
            # Any specific error handling based on backend's error structure could be added here
            # For example, if backend returns a specific error code or message structure for partial success / truncation

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"後端 API HTTP 錯誤: {http_err.response.status_code} - {http_err.response.text}", exc_info=True)
            try:
                error_detail = http_err.response.json().get("detail", http_err.response.text)
            except json.JSONDecodeError:
                error_detail = http_err.response.text
            model_response_text = f"AI服務錯誤 ({http_err.response.status_code}): {error_detail}"
            is_error_response = True
        except requests.exceptions.RequestException as req_err:
            logger.error(f"後端服務通訊失敗: {req_err}", exc_info=True)
            model_response_text = f"錯誤：無法連接到AI服務或服務無回應 ({req_err})。"
            is_error_response = True
        except json.JSONDecodeError as json_err:
            logger.error(f"無法解析後端服務的回應: {json_err}", exc_info=True)
            model_response_text = "錯誤：AI服務回應格式不正確。"
            is_error_response = True
        except Exception as e:
            logger.error(f"處理AI請求時發生未知錯誤: {type(e).__name__} - {str(e)}", exc_info=True)
            model_response_text = f"錯誤：處理您的請求時發生了意外問題 ({type(e).__name__} - {str(e)})。"
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
    ui_settings = st.session_state.get("ui_settings", {}) # Get ui_settings

    st.header("💬 步驟三：與 Gemini 進行分析與討論")

    default_chat_height_from_settings = ui_settings.get("default_chat_container_height", 400) # Fallback value
    chat_container_height = st.session_state.get("chat_container_height", default_chat_height_from_settings)
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
