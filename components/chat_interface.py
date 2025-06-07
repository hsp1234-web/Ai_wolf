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
from services.prompt_builder import build_gemini_request_contents # Import the new prompt builder
from config.api_keys_config import api_keys_info # To get Gemini key names
# from config import app_settings # Might be needed if prompt_builder uses some settings directly

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
                response_content = message["parts"][0]
                if message.get("is_error", False):
                    st.error(response_content)
                elif role == "model" and "```python-plot" in response_content:
                    # This message contains plot code, process it with the helper
                    process_and_display_model_response_with_plots(response_content)
                else:
                    # Standard markdown display for user messages or simple model responses
                    st.markdown(response_content)

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

                # --- 核心分析文件處理 (來自 Wolf_Data 或已上傳文件) ---
                selected_core_doc_relative_paths = st.session_state.get("selected_core_documents", [])
                wolf_data_file_map = st.session_state.get("wolf_data_file_map", {})
                # uploaded_content_map remains for files uploaded via st.file_uploader, if we decide to allow mixing
                # For now, the logic in main_page.py prioritizes Wolf_Data for selection if available.
                # This chat_interface part will now prioritize resolving selected_core_doc_relative_paths using wolf_data_file_map.

                if selected_core_doc_relative_paths:
                    logger.info(f"聊天介面：檢測到 {len(selected_core_doc_relative_paths)} 個核心文件被選中。")
                    core_docs_content_parts = ["\n**核心分析文件內容 (Core Analysis Documents Content):**\n"]
                    files_actually_included = 0

                    for rel_path in selected_core_doc_relative_paths:
                        core_doc_full_path = wolf_data_file_map.get(rel_path)
                        doc_display_name = os.path.basename(rel_path) # Use relative path for display name initially

                        if core_doc_full_path and os.path.exists(core_doc_full_path):
                            doc_display_name = os.path.basename(core_doc_full_path) # Update to actual basename if path resolved
                            try:
                                if core_doc_full_path.endswith((".txt", ".md")):
                                    with open(core_doc_full_path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                    core_docs_content_parts.append(f"--- Document Start: {doc_display_name} ---\n{content}\n--- Document End: {doc_display_name} ---\n\n")
                                    logger.debug(f"聊天介面：已從 '{core_doc_full_path}' 添加核心文件 '{doc_display_name}' (文本) 到提示詞。長度: {len(content)}")
                                    files_actually_included +=1
                                else:
                                    core_docs_content_parts.append(f"--- Document: {doc_display_name} (Unsupported file type for direct inclusion from Wolf_Data: {core_doc_full_path}) ---\n")
                                    logger.warning(f"聊天介面：核心文件 '{doc_display_name}' ({core_doc_full_path}) 類型不受支持，無法直接包含。")
                            except FileNotFoundError:
                                core_docs_content_parts.append(f"--- Document: {doc_display_name} (File not found at path: {core_doc_full_path}) ---\n")
                                logger.error(f"聊天介面：核心文件 '{doc_display_name}' 路徑 '{core_doc_full_path}' 未找到。")
                            except Exception as e:
                                core_docs_content_parts.append(f"--- Document: {doc_display_name} (Error reading file at path: {core_doc_full_path}) ---\nError: {str(e)}\n")
                                logger.error(f"聊天介面：讀取核心文件 '{doc_display_name}' ({core_doc_full_path}) 時發生錯誤: {e}", exc_info=True)
                        elif rel_path in st.session_state.get("uploaded_file_contents", {}): # Fallback: Check if it's a name from uploaded_files_list
                            content = st.session_state.uploaded_file_contents[rel_path]
                            doc_display_name = rel_path # Use the key from uploaded_files_list
                            if isinstance(content, str):
                                core_docs_content_parts.append(f"--- Document Start (Uploaded): {doc_display_name} ---\n{content}\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                                logger.debug(f"聊天介面：已添加來自 st.file_uploader 的核心文件 '{doc_display_name}' (文本) 到提示詞。長度: {len(content)}")
                            elif isinstance(content, pd.DataFrame):
                                core_docs_content_parts.append(f"--- Document Start (Uploaded): {doc_display_name} (表格數據) ---\n欄位: {', '.join(content.columns)}\n數據 (前5行):\n{content.head(5).to_string()}\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                                logger.debug(f"聊天介面：已添加來自 st.file_uploader 的核心文件 '{doc_display_name}' (表格) 到提示詞。Shape: {content.shape}")
                            else:
                                core_docs_content_parts.append(f"--- Document (Uploaded): {doc_display_name} (二進制或其他格式，無法直接預覽) ---\n[Content not directly previewable, length: {len(content)} bytes]\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                                logger.debug(f"聊天介面：已添加來自 st.file_uploader 的核心文件 '{doc_display_name}' (二進制) 到提示詞。長度: {len(content)}")
                            files_actually_included += 1
                        else:
                            # This handles cases where rel_path is neither in wolf_data_file_map nor in uploaded_file_contents (e.g. mock name if main_page uses it)
                            core_docs_content_parts.append(f"--- Document: {rel_path} (Content not available from Wolf_Data or session uploads) ---\n")
                            logger.warning(f"聊天介面：核心文件 '{rel_path}' 在 selected_core_documents 中，但在 wolf_data_file_map 或 uploaded_file_contents 中未找到其內容。")

                    if files_actually_included > 0:
                        full_prompt_parts.append("".join(core_docs_content_parts))
                        prompt_context_summary.append(f"{files_actually_included}個核心分析文件")

                    logger.info("聊天介面：核心分析文件處理完畢。")
                    # Decision: If selected_core_documents is not empty, we ONLY use those.
                    # So, we skip the general uploaded_file_contents iteration.
                    logger.info("聊天介面：由於已選定核心分析文件，將跳過自動包含所有其他 '已上傳文件列表(uploaded_file_contents)' 的步驟。")

                else: # No selected_core_doc_relative_paths, use general uploaded_file_contents if any
                    uploaded_content_map_general = st.session_state.get("uploaded_file_contents", {})
                    if uploaded_content_map_general:
                        logger.info("聊天介面：未選定核心分析文件，將檢查並包含所有 '已上傳文件列表(uploaded_file_contents)' 中的文件。")
                        num_general_uploaded_files = len(uploaded_content_map_general)
                        uploaded_texts_str = "**已上傳文件內容摘要 (All Uploaded Files Summary):**\n"
                        for fn, content in uploaded_content_map_general.items():
                            if isinstance(content, str):
                                uploaded_texts_str += f"檔名: {fn}\n內容片段 (前1000字符):\n{content[:1000]}...\n\n"
                            elif isinstance(content, pd.DataFrame):
                                 uploaded_texts_str += f"檔名: {fn} (表格數據)\n欄位: {', '.join(content.columns)}\n前3行:\n{content.head(3).to_string()}\n\n"
                            else: # 其他類型，如 bytes
                                uploaded_texts_str += f"檔名: {fn} (二進制或其他格式，無法直接預覽)\n\n"
                        full_prompt_parts.append(uploaded_texts_str)
                        prompt_context_summary.append(f"{num_general_uploaded_files}個已上傳檔案 (通用)")

                # --- 外部數據處理 (不變) ---
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

                final_prompt_for_api = "\n---\n".join(map(str, full_prompt_parts))
                final_prompt_length = len(final_prompt_for_api)
                logger.info(f"聊天介面：Gemini 提示詞上下文包含: {', '.join(prompt_context_summary)}。最終提示詞長度: {final_prompt_length} 字元。")
                if final_prompt_length > 100000: # Example threshold for very long prompt
                    logger.warning(f"聊天介面：最終提示詞長度 ({final_prompt_length} 字元) 非常長，可能影響 API 性能或成本。")

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

                    # Note: call_gemini_api expects a list of parts, not a single pre-joined string.
                    # However, our current structure of full_prompt_parts already builds it as a list of strings.
                    # If call_gemini_api was more nuanced about parts, this might need adjustment.
                    # For now, it implies call_gemini_api internally joins them or handles a list of strings.
                    # Let's assume call_gemini_api joins the list elements with newlines if necessary.
                    # The prompt_parts argument in call_gemini_api should indeed be a list of strings.
                    model_response_text = call_gemini_api(
                        prompt_parts=full_prompt_parts, # Passing the list of strings
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
            logger.debug("聊天介面：開始構建 Gemini API 的提示詞列表 (prompt_parts)。")
            full_prompt_parts = []
            prompt_context_summary = []

            if st.session_state.get("main_gemini_prompt"):
                full_prompt_parts.append(f"**主要指示 (System Prompt):**\n{st.session_state.main_gemini_prompt}")
                prompt_context_summary.append("系統提示詞")

            selected_core_doc_relative_paths = st.session_state.get("selected_core_documents", [])
            wolf_data_file_map = st.session_state.get("wolf_data_file_map", {})

            if selected_core_doc_relative_paths:
                logger.info(f"聊天介面：檢測到 {len(selected_core_doc_relative_paths)} 個核心文件被選中。")
                core_docs_content_parts = ["\n**核心分析文件內容 (Core Analysis Documents Content):**\n"]
                files_actually_included = 0
                for rel_path in selected_core_doc_relative_paths:
                    core_doc_full_path = wolf_data_file_map.get(rel_path)
                    doc_display_name = os.path.basename(rel_path)
                    if core_doc_full_path and os.path.exists(core_doc_full_path):
                        doc_display_name = os.path.basename(core_doc_full_path)
                        try:
                            if core_doc_full_path.endswith((".txt", ".md")):
                                with open(core_doc_full_path, "r", encoding="utf-8") as f: content = f.read()
                                core_docs_content_parts.append(f"--- Document Start: {doc_display_name} ---\n{content}\n--- Document End: {doc_display_name} ---\n\n")
                                files_actually_included +=1
                            else:
                                core_docs_content_parts.append(f"--- Document: {doc_display_name} (Unsupported file type from Wolf_Data: {core_doc_full_path}) ---\n")
                        except Exception as e:
                            core_docs_content_parts.append(f"--- Document: {doc_display_name} (Error reading file: {core_doc_full_path}) ---\nError: {str(e)}\n")
                    elif rel_path in st.session_state.get("uploaded_file_contents", {}):
                        content = st.session_state.uploaded_file_contents[rel_path]
                        doc_display_name = rel_path
                        if isinstance(content, str):
                            core_docs_content_parts.append(f"--- Document Start (Uploaded): {doc_display_name} ---\n{content}\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                        elif isinstance(content, pd.DataFrame):
                            core_docs_content_parts.append(f"--- Document Start (Uploaded): {doc_display_name} (表格數據) ---\n欄位: {', '.join(content.columns)}\n數據 (前5行):\n{content.head(5).to_string()}\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                        else:
                            core_docs_content_parts.append(f"--- Document (Uploaded): {doc_display_name} (二進制或其他格式) ---\n[Content not directly previewable, length: {len(content)} bytes]\n--- Document End (Uploaded): {doc_display_name} ---\n\n")
                        files_actually_included += 1
                    else:
                        core_docs_content_parts.append(f"--- Document: {rel_path} (Content not available) ---\n")
                if files_actually_included > 0:
                    full_prompt_parts.append("".join(core_docs_content_parts))
                    prompt_context_summary.append(f"{files_actually_included}個核心分析文件")
                logger.info("聊天介面：核心分析文件處理完畢。")
            else:
                uploaded_content_map_general = st.session_state.get("uploaded_file_contents", {})
                if uploaded_content_map_general:
                    num_general_uploaded_files = len(uploaded_content_map_general)
                    uploaded_texts_str = "**已上傳文件內容摘要 (All Uploaded Files Summary):**\n"
                    for fn, content in uploaded_content_map_general.items():
                        if isinstance(content, str): uploaded_texts_str += f"檔名: {fn}\n內容片段 (前1000字符):\n{content[:1000]}...\n\n"
                        elif isinstance(content, pd.DataFrame): uploaded_texts_str += f"檔名: {fn} (表格數據)\n欄位: {', '.join(content.columns)}\n前3行:\n{content.head(3).to_string()}\n\n"
                        else: uploaded_texts_str += f"檔名: {fn} (二進制或其他格式)\n\n"
                    full_prompt_parts.append(uploaded_texts_str)
                    prompt_context_summary.append(f"{num_general_uploaded_files}個已上傳檔案 (通用)")

            if st.session_state.get("fetched_data_preview") and isinstance(st.session_state.fetched_data_preview, dict):
                num_data_sources = len(st.session_state.fetched_data_preview)
                if num_data_sources > 0:
                    external_data_str = "**已引入的外部市場與總經數據摘要:**\n"
                    for source, data_items in st.session_state.fetched_data_preview.items():
                        external_data_str += f"\n來源: {source.upper()}\n"
                        if isinstance(data_items, dict):
                            for item_name, df_item in data_items.items():
                                if isinstance(df_item, pd.DataFrame): external_data_str += f"  {item_name} (最近3筆):\n{df_item.tail(3).to_string(index=False)}\n"
                        elif isinstance(data_items, pd.DataFrame): external_data_str += f"  {source}數據 (最近3筆):\n{data_items.tail(3).to_string(index=False)}\n"
                    full_prompt_parts.append(external_data_str)
                    prompt_context_summary.append(f"{num_data_sources}個外部數據源")

            last_user_input = st.session_state.chat_history[-1]["parts"][0]
            full_prompt_parts.append(f"**使用者當前問題/指令:**\n{last_user_input}")
            prompt_context_summary.append("用戶當前問題")

            # final_prompt_for_api = "\n---\n".join(map(str, full_prompt_parts)) # This was for single string prompt
            # The call_gemini_api expects a list of parts.
            # Ensure full_prompt_parts is a list of strings/parts suitable for the API.

            final_prompt_length = sum(len(str(p)) for p in full_prompt_parts)
            logger.info(f"聊天介面：Gemini 提示詞上下文包含: {', '.join(prompt_context_summary)}。最終提示詞長度: {final_prompt_length} 字元。")

            valid_gemini_api_keys = [st.session_state.get(key_name, "") for key_name in api_keys_info.values() if "gemini" in key_name.lower() and st.session_state.get(key_name, "")]
            selected_model_name = st.session_state.get("selected_model_name")
            generation_config = st.session_state.get("generation_config", {"temperature": 0.7, "top_p": 0.9, "top_k": 32, "max_output_tokens": 8192})
            selected_cache_name_for_api = st.session_state.get("selected_cache_for_generation")

            if not valid_gemini_api_keys:
                model_response_text = "錯誤：請在側邊欄設定至少一個有效的 Gemini API 金鑰。"
                is_error_response = True
            elif not selected_model_name:
                model_response_text = "錯誤：請在側邊欄選擇一個 Gemini 模型。"
                is_error_response = True
            else:
                model_response_text = call_gemini_api(
                    prompt_parts=full_prompt_parts, # This should be the list of strings
                    api_keys_list=valid_gemini_api_keys,
                    selected_model=selected_model_name,
                    global_rpm=st.session_state.get("global_rpm_limit", 3),
                    global_tpm=st.session_state.get("global_tpm_limit", 100000),
                    generation_config_dict=generation_config,
                    cached_content_name=selected_cache_name_for_api
                )
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

    chat_container_height = st.session_state.get("chat_container_height", 400)
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
