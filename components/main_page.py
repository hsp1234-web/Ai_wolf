# components/main_page.py
import streamlit as st
import logging
import pandas as pd # For displaying DataFrame previews
import os # Ensure os is imported for path operations
# Import the new helper function
from components.chat_interface import add_message_and_process
# Import for Colab Drive path checking
from utils.colab_utils import ensure_colab_drive_mount_if_needed # Changed import path
import os
import sys
import requests # Added for API calls
# from utils.path_manager import SOURCE_DOCS_DIR, IN_COLAB # Already imported via file_processors or similar, ensure it's available
from utils.path_manager import SOURCE_DOCS_DIR, IN_COLAB # Explicitly ensure it's here if direct use
# Removed old data_fetchers
# from services.data_fetchers import (
#     fetch_yfinance_data,
#     fetch_fred_data,
#     fetch_ny_fed_data
# )
# from config.api_keys_config import api_keys_info # For checking Gemini keys - This check might change or be removed
from config import app_settings # Import app_settings primarily for FASTAPI_BACKEND_URL if not sourced otherwise
# Specific constant imports below will be removed or changed to use st.session_state.ui_settings
# from config.app_settings import ALLOWED_UPLOAD_FILE_TYPES, TEXT_PREVIEW_MAX_CHARS, CORE_DOC_SCAN_EXTENSIONS, AGENT_BUTTONS_PER_ROW

logger = logging.getLogger(__name__)

# def _are_gemini_keys_set() -> bool: # This function might be deprecated if key handling is fully backend
#     """檢查 session_state 中是否設置了任何 Gemini API 金鑰。"""
#     # This check is less relevant now as keys are backend managed.
#     # For now, we can assume if backend is up, it's configured.
#     # Or, this could be replaced by a backend health check / config check endpoint.
#     # For this refactor, we'll remove its direct usage in restricting UI elements,
#     # as functionality now depends on backend calls.
#     # from config.api_keys_config import api_keys_info
#     # for key_label, key_name in api_keys_info.items():
#     #     if "gemini" in key_label.lower() and st.session_state.get(key_name): # This assumes keys were in session_state
#     #         return True
#     return True # Assume backend is configured for now, or this check is removed.

def render_main_page_content():
    """
    渲染主頁面的UI內容。
    包括標題、文件上傳、外部數據源選擇和獲取、數據預覽和錯誤顯示等。
    """
    logger.info("主頁面：開始渲染主要內容 (render_main_page_content)。")

    # --- Handle Colab Drive Mount Prompt ---
    # This should be near the top to potentially block other rendering or inform user early.
    if st.session_state.get("show_drive_mount_prompt", False):
        path_requested = st.session_state.get("drive_path_requested", "指定的路徑")
        st.warning(
            f"⚠️ **Google Drive 路徑未掛載或不可用**\n\n"
            f"應用程式需要存取 Google Drive 上的路徑 '{path_requested}'，但該路徑目前無法訪問。\n\n"
            "如果您正在 Colab 環境中運行此應用程式，請執行筆記本中的 Google Drive 掛載儲存格，然後點擊下方的「重試檔案存取」按鈕。",
            icon="📁"
        )
        if st.button("🔄 重試檔案存取", key="drive_retry_button"):
            st.session_state.show_drive_mount_prompt = False # Clear the flag
            # We don't need to set drive_path_requested to "" here,
            # ensure_colab_drive_mount_if_needed will re-check and re-set if still not mounted.
            logger.info("用戶點擊 '重試檔案存取' 按鈕。重新運行頁面。")
            st.rerun()
        # Optionally, you might want to stop further rendering of components that depend on this path
        # For now, the check before os.walk will handle not trying to access it.

    # --- Initialize session state for this page if not already done ---
    if "selected_core_documents" not in st.session_state:
        st.session_state.selected_core_documents = []
        logger.debug("主頁面：'selected_core_documents' 初始化為空列表。")
    if "wolf_data_file_map" not in st.session_state: # For storing relative_path -> full_path
        st.session_state.wolf_data_file_map = {}
        logger.debug("主頁面：'wolf_data_file_map' 初始化為空字典。")

    st.title("金融分析與洞察助理 (由 Gemini 驅動)")

    # --- Agent 快捷任務 ---
    st.subheader("🤖 Agent 快捷任務")
    ui_settings = st.session_state.get("ui_settings", {})
    prompts_dir = ui_settings.get("prompts_dir", "prompts") # Fallback to "prompts"
    agent_buttons_per_row = ui_settings.get("agent_buttons_per_row", 3)

    agent_prompt_files = []
    if os.path.exists(prompts_dir) and os.path.isdir(prompts_dir):
        try:
            agent_prompt_files = sorted([
                f for f in os.listdir(prompts_dir)
                if f.startswith("agent_") and f.endswith(".txt")
            ]) # Sort for consistent order
        except Exception as e:
            logger.error(f"主頁面：讀取 prompts 目錄 '{prompts_dir}' 時發生錯誤: {e}")
            st.error(f"無法讀取 Agent 任務列表: {e}")

    if not agent_prompt_files:
        st.info(f"目前沒有可用的 Agent 快捷任務。請在 '{prompts_dir}' 文件夾下添加 'agent_*.txt' 文件。")
    else:
        # Determine number of columns, e.g., 3 or 4 per row
        num_cols = min(len(agent_prompt_files), agent_buttons_per_row) # Max buttons per row from settings
        cols = st.columns(num_cols)
        for i, prompt_file in enumerate(agent_prompt_files):
            button_label = prompt_file.replace("agent_", "").replace(".txt", "").replace("_", " ").title()
            # Use session state to manage button clicks to avoid issues with st.rerun if called from elsewhere
            button_key = f"agent_button_{prompt_file}"

            if cols[i % num_cols].button(button_label, key=button_key):
                logger.info(f"主頁面：Agent 按鈕 '{button_label}' 被點擊。")
                try:
                    with open(os.path.join(prompts_dir, prompt_file), "r", encoding="utf-8") as f:
                        prompt_content = f.read()

                    # Store the raw prompt. It will be cleared by add_message_and_process if from_agent is True.
                    st.session_state.current_agent_prompt = prompt_content

                    logger.info(f"Agent 任務 '{button_label}' 的提示詞已載入。調用 add_message_and_process。")

                    # Call the helper function from chat_interface.py
                    add_message_and_process(prompt_content, from_agent=True)

                    # Toast is good, st.rerun() is handled by add_message_and_process
                    st.toast(f"Agent 任務 '{button_label}' 已觸發。", icon="🤖")

                except Exception as e:
                    st.error(f"載入 Agent 提示詞 '{prompt_file}' 失敗: {e}")
                    logger.error(f"載入 Agent 提示詞 '{prompt_file}' 失敗: {e}")
    st.markdown("---") # 分隔線

    # --- API 金鑰缺失警告 (REMOVED as keys are backend managed) ---
    # if not _are_gemini_keys_set(): # This function is also a candidate for removal
    #     st.warning(
    #         "⚠️ **核心功能依賴後端 API 金鑰配置**\n\n"
    #         "此應用程式的核心分析功能由 Google Gemini 提供技術支援。請確保後端服務已正確配置 API 金鑰以啟用完整功能。\n\n"
    #         "API 金鑰不再通過前端界面管理。",
    #         icon="🔑"
    #     )
    #     logger.info("主頁面：顯示 API 金鑰由後端管理的信息。")

    # --- 步驟一：上傳文件 ---
    st.header("📄 步驟一：上傳與檢視文件")
    st.caption("請上傳您需要分析的文字檔案、CSV 或 Excel 檔案到後端服務。") # Caption updated
    logger.debug("主頁面：渲染文件上傳區域。")
    ui_settings = st.session_state.get("ui_settings", {}) # Ensure ui_settings is available
    allowed_upload_types_fallback = ["txt", "csv", "md", "py", "json", "xml", "html", "css", "js", "xls", "xlsx"] # More comprehensive static fallback
    allowed_upload_file_types_from_settings = ui_settings.get("allowed_upload_file_types", allowed_upload_types_fallback)

    uploaded_files_from_widget = st.file_uploader(
        "上傳新文件到後端服務 (可多選):", # Label updated
        type=allowed_upload_file_types_from_settings,
        accept_multiple_files=True,
        key="main_file_uploader_widget",
        help="此處上傳的文件將發送到後端進行處理和存儲。" # Help updated
    )

    if uploaded_files_from_widget: # User has selected files in the widget
        logger.info(f"主頁面：用戶在 file_uploader 中選擇了 {len(uploaded_files_from_widget)} 個檔案。")

        # Prepare files for multipart/form-data upload
        files_for_api_upload = []
        for up_file in uploaded_files_from_widget:
            files_for_api_upload.append(('files', (up_file.name, up_file.getvalue(), up_file.type)))

        if files_for_api_upload:
            backend_upload_url = f"{app_settings.FASTAPI_BACKEND_URL}/api/files/upload"
            st.info(f"正在上傳 {len(files_for_api_upload)} 個文件到後端服務...")
            try:
                api_response = requests.post(backend_upload_url, files=files_for_api_upload, timeout=180) # Increased timeout for potentially large files
                api_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                response_json = api_response.json()

                if response_json.get("success"):
                    st.success(response_json.get("message", f"成功上傳 {len(files_for_api_upload)} 個文件到後端。"))

                    # Replace old session state vars for uploaded file contents
                    st.session_state.pop("uploaded_files_list", None)
                    st.session_state.pop("uploaded_file_contents", None)

                    # Store new backend-provided file info
                    # It's better to append to or update an existing list to handle multiple upload batches.
                    if "uploaded_documents_info" not in st.session_state:
                        st.session_state.uploaded_documents_info = []

                    new_files_info = response_json.get("uploaded_files_info", [])
                    # Simple append for now. A more robust way would be to update by file_id if files can be re-uploaded.
                    st.session_state.uploaded_documents_info.extend(new_files_info)

                    logger.info(f"後端文件上傳成功。收到 {len(new_files_info)} 個文件的信息。")
                    # Rerun to clear the file_uploader and reflect new state
                    st.rerun()
                else:
                    error_msg = response_json.get("error", "後端處理文件上傳失敗，但未提供明確錯誤訊息。")
                    st.error(f"後端錯誤: {error_msg}")
                    logger.error(f"後端文件上傳API返回失敗: {error_msg}")

            except requests.exceptions.RequestException as e:
                st.error(f"上傳文件到後端失敗: {e}")
                logger.error(f"上傳文件到後端失敗: {e}", exc_info=True)
            except Exception as e:
                st.error(f"處理文件上傳時發生未知錯誤: {e}")
                logger.error(f"處理文件上傳時發生未知錯誤: {e}", exc_info=True)
        # It's important to clear the file uploader widget after an upload attempt (success or failure)
        # to prevent re-uploading the same files on next script run if not handled carefully.
        # A common way is st.rerun(), or manually resetting the key of file_uploader if possible,
        # or managing a flag. st.rerun() is used on success. If error, files remain in widget.

    # Display files based on new session state variable `st.session_state.uploaded_documents_info`
    if st.session_state.get("uploaded_documents_info"):
        st.subheader("已上傳到後端的文件:")
        # Create a set of filenames for efficient duplicate checking if backend doesn't ensure uniqueness
        # For now, assuming backend returns a clean list per upload batch, and we extend.
        # If backend ensures global uniqueness by file_id, list directly.

        displayed_files = st.session_state.uploaded_documents_info
        if not displayed_files:
             st.caption("目前沒有文件信息。")

        for doc_info in displayed_files:
            file_id = doc_info.get("file_id", "N/A")
            filename = doc_info.get("filename", "N/A")
            summary = doc_info.get("summary", "後端未提供預覽。")
            content_type = doc_info.get("content_type", "N/A")
            size_kb = doc_info.get("size", 0) / 1024

            expander_title = f"文件名: {filename} (ID: ...{file_id[-6:] if file_id != 'N/A' else 'N/A'}, 类型: {content_type}, 大小: {size_kb:.2f} KB)"
            with st.expander(expander_title, expanded=False):
                st.markdown(f"**後端提供的摘要/預覽:**")
                st.text(summary)
                # TODO: Add a button or mechanism to remove/manage individual files if backend supports it
                # e.g., if st.button(f"從後端移除 {filename}", key=f"del_{file_id}"): call_backend_delete_api(file_id)
    else:
        st.info("尚未上傳任何文件到後端服務。請使用上方的上傳工具。") # Updated message
    st.markdown("---")

    # --- 步驟二：選擇核心分析文件 (用於 All-in-One 報告) ---
    st.header("🎯 步驟二：選擇核心分析文件 (用於 All-in-One 報告)")
    st.caption("從 `Wolf_Data/source_documents/` (本地掃描) 或已上傳到後端的文件中選擇核心文檔。") # Caption updated
    logger.debug("主頁面：渲染核心分析文件選擇區域。")

    # --- Wolf_Data/source_documents/ 文件掃描邏輯 (Frontend local scan) ---
    # This part remains largely the same if SOURCE_DOCS_DIR is a locally accessible path by the frontend.
    # The `ensure_colab_drive_mount_if_needed` is still relevant for this local scanning part.
    can_scan_wolf_data = True
    if IN_COLAB:
        if not ensure_colab_drive_mount_if_needed(SOURCE_DOCS_DIR):
            can_scan_wolf_data = False
            logger.info(f"主頁面：ensure_colab_drive_mount_if_needed 返回 False for '{SOURCE_DOCS_DIR}'. 跳過掃描。")
            st.session_state.wolf_data_file_map = {} # Ensure it's empty if scan is skipped

    local_wolf_data_files_map = {} # Stores display_name -> {type, identifier, display_name}
    core_doc_scan_extensions_fallback = (".txt", ".md")
    core_doc_scan_extensions_from_settings = ui_settings.get("core_doc_scan_extensions", core_doc_scan_extensions_fallback)

    if can_scan_wolf_data and os.path.exists(SOURCE_DOCS_DIR):
        logger.info(f"主頁面：開始掃描本地 Wolf_Data 目錄: {SOURCE_DOCS_DIR}")
        for root, _, files in os.walk(SOURCE_DOCS_DIR):
            for file in files:
                if file.endswith(core_doc_scan_extensions_from_settings):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, SOURCE_DOCS_DIR)
                    display_name = f"[本地] {relative_path}"
                    local_wolf_data_files_map[display_name] = {"path_type": "local_wolf_data", "identifier": full_path, "display_name": display_name}
        logger.info(f"主頁面：掃描到 {len(local_wolf_data_files_map)} 個文件從本地 Wolf_Data。")
    elif can_scan_wolf_data and not os.path.exists(SOURCE_DOCS_DIR): # Path doesn't exist, but tried to scan (e.g. local non-Colab)
        logger.warning(f"主頁面：本地 Wolf_Data 目錄 '{SOURCE_DOCS_DIR}' 不存在。")
        # st.session_state.wolf_data_file_map might not be the right variable to clear here if it's specific to previous structure

    # --- Files uploaded to backend ---
    backend_uploaded_files_map = {} # Stores display_name -> {type, identifier, display_name}
    if st.session_state.get("uploaded_documents_info"):
        for doc_info in st.session_state.uploaded_documents_info:
            filename = doc_info.get('filename', 'N/A')
            file_id = doc_info.get('file_id', 'N/A')
            display_name = f"[後端] {filename} (ID: ...{file_id[-6:] if file_id != 'N/A' else 'N/A'})"
            backend_uploaded_files_map[display_name] = {"path_type": "backend_file_id", "identifier": file_id, "display_name": display_name, "filename": filename}

    # Combine options for multiselect
    # The keys of this map will be the display names shown in the multiselect widget
    combined_options_map = {**local_wolf_data_files_map, **backend_uploaded_files_map}
    multiselect_display_options = sorted(list(combined_options_map.keys()))

    if not multiselect_display_options:
        st.info(f"提示：在 '{SOURCE_DOCS_DIR}' (本地) 中未找到符合條件的文件，且後端無已上傳文件。請使用「步驟一」上傳文件。")
        # Provide a dummy option if empty to prevent multiselect error, though it's better if multiselect handles empty options list gracefully.
        # For now, assuming st.multiselect handles empty list fine, or user sees the info message.
    else:
        st.info(f"請從掃描到的本地 '{os.path.basename(SOURCE_DOCS_DIR.rstrip(os.sep))}' 目錄或已上傳到後端的文件中選擇。")

    # `selected_core_documents` in session_state will now store the list of selected *display names*.
    # We will then use `combined_options_map` to get the actual identifier and type when needed (e.g., for building context).

    # Get current selections from session state (these are display names)
    # Default selection logic needs to be robust if "selected_core_documents" previously stored different kind of values
    # For this refactor, let's assume selected_core_documents will store the display names.
    # If it's the first run or structure changed, it might be empty or need conversion.

    # Ensure st.session_state.selected_core_documents holds display names compatible with current options
    current_default_selection = []
    if "selected_core_documents" in st.session_state:
        if isinstance(st.session_state.selected_core_documents, list):
            # Filter to ensure only valid display names are part of default
            current_default_selection = [name for name in st.session_state.selected_core_documents if name in multiselect_display_options]
        else: # If it was not a list, reset it
            st.session_state.selected_core_documents = []


    selected_display_names_from_widget = st.multiselect(
        "選擇要進行 All-in-One 綜合分析的文件 (可複選):",
        options=multiselect_display_options, # List of display names
        default=current_default_selection,
        key="main_selected_core_documents_multiselect_new" # New key to avoid state conflicts if old one existed with different data type
    )

    if selected_display_names_from_widget != st.session_state.get("selected_core_documents"):
        st.session_state.selected_core_documents = selected_display_names_from_widget # Store the selected display names
        logger.info(f"主頁面：用戶選擇的核心分析文件 (顯示名稱) 已更新: {selected_display_names_from_widget}")

    if st.session_state.get("selected_core_documents"):
        st.markdown("##### 已選定核心文件:")
        for display_name in st.session_state.selected_core_documents:
            # Retrieve the full info for logging or more detailed display if needed
            doc_detail = combined_options_map.get(display_name)
            if doc_detail:
                 st.markdown(f"- {doc_detail['display_name']} (來源: {doc_detail['path_type']})")
            else: # Should not happen if default filtering is correct
                 st.markdown(f"- {display_name} (詳細資訊未知)")
    else:
        st.caption("尚未選定任何核心文件。")

    st.markdown("---")


    # --- 步驟三：引入外部數據 ---
    st.header("📊 步驟三：引入外部數據 (可選)")
    logger.debug("主頁面：渲染外部數據源選擇區域。")
    with st.expander("📊 設定並載入外部數據 (點擊展開/收起)", expanded=False):
        st.caption("選擇 yfinance, FRED, NY Fed 等外部市場與總經數據源，設定參數並載入數據。")

        # 確保相關 session_state 鍵已由 session_state_manager 初始化
        # 此處不再重複初始化，以依賴 manager 的統一管理

        col_sel1, col_sel2, col_sel3, col_sel4 = st.columns(4)
        with col_sel1:
            old_select_all = st.session_state.get("select_all_sources", False)
            new_select_all = st.checkbox("🌍 全選數據源", value=old_select_all, key="main_select_all_cb")
            if new_select_all != old_select_all:
                st.session_state.select_all_sources = new_select_all
                st.session_state.select_yfinance = new_select_all
                st.session_state.select_fred = new_select_all
                st.session_state.select_ny_fed = new_select_all
                logger.info(f"主頁面：用戶更改'全選數據源'為 {new_select_all}。")
                st.rerun()
        with col_sel2:
            old_yf = st.session_state.get("select_yfinance", False)
            new_yf = st.checkbox("📈 yfinance", value=old_yf, key="main_select_yfinance_cb")
            if new_yf != old_yf:
                st.session_state.select_yfinance = new_yf
                logger.info(f"主頁面：用戶更改'yfinance'選擇為 {new_yf}。")
        with col_sel3:
            old_fred = st.session_state.get("select_fred", False)
            new_fred = st.checkbox("🏦 FRED", value=old_fred, key="main_select_fred_cb")
            if new_fred != old_fred:
                st.session_state.select_fred = new_fred
                logger.info(f"主頁面：用戶更改'FRED'選擇為 {new_fred}。")
        with col_sel4:
            old_nyf = st.session_state.get("select_ny_fed", False)
            new_nyf = st.checkbox("🇺🇸 NY Fed", value=old_nyf, key="main_select_nyfed_cb")
            if new_nyf != old_nyf:
                st.session_state.select_ny_fed = new_nyf
                logger.info(f"主頁面：用戶更改'NY Fed'選擇為 {new_nyf}。")


        date_col1, date_col2 = st.columns(2)
        with date_col1:
            old_start_date = st.session_state.get("data_start_date", "")
            new_start_date = st.text_input("開始日期 (YYYYMMDD):", value=old_start_date, key="main_data_start_date")
            if new_start_date != old_start_date:
                st.session_state.data_start_date = new_start_date
                logger.debug(f"主頁面：數據開始日期更改為 {new_start_date}")
        with date_col2:
            old_end_date = st.session_state.get("data_end_date", "")
            new_end_date = st.text_input("結束日期 (YYYYMMDD):", value=old_end_date, key="main_data_end_date")
            if new_end_date != old_end_date:
                st.session_state.data_end_date = new_end_date
                logger.debug(f"主頁面：數據結束日期更改為 {new_end_date}")

        param_col1, param_col2 = st.columns(2)
        with param_col1:
            if st.session_state.get("select_yfinance"):
                default_yf_tickers = ui_settings.get("default_yfinance_tickers", "SPY,QQQ")
                old_yf_tickers = st.session_state.get("yfinance_tickers", default_yf_tickers)
                new_yf_tickers = st.text_input("yfinance Tickers (逗號分隔):", value=old_yf_tickers, key="main_yfinance_tickers")
                if new_yf_tickers != old_yf_tickers:
                    st.session_state.yfinance_tickers = new_yf_tickers
                    logger.debug(f"主頁面：yfinance tickers 更改為 '{new_yf_tickers}'")

                yfinance_interval_options_fallback = {"1 Day": "1d", "1 Week": "1wk"}
                yfinance_interval_options_from_settings = ui_settings.get("yfinance_interval_options", yfinance_interval_options_fallback)
                default_yfinance_interval_label_from_settings = ui_settings.get("default_yfinance_interval_label", "1 Day")

                old_yf_interval_label = st.session_state.get("yfinance_interval_label", default_yfinance_interval_label_from_settings)
                new_yf_interval_label = st.selectbox(
                    "yfinance 數據週期:",
                    options=list(yfinance_interval_options_from_settings.keys()),
                    index=list(yfinance_interval_options_from_settings.keys()).index(old_yf_interval_label) if old_yf_interval_label in yfinance_interval_options_from_settings else 0,
                    key="main_yfinance_interval"
                )
                if new_yf_interval_label != old_yf_interval_label:
                    st.session_state.yfinance_interval_label = new_yf_interval_label
                    logger.debug(f"主頁面：yfinance interval 更改為 '{new_yf_interval_label}'")
        with param_col2:
            if st.session_state.get("select_fred"):
                default_fred_ids = ui_settings.get("default_fred_series_ids", "GDP,CPIAUCSL")
                old_fred_ids = st.session_state.get("fred_series_ids", default_fred_ids)
                new_fred_ids = st.text_input("FRED Series IDs (逗號分隔):", value=old_fred_ids, key="main_fred_ids")
                if new_fred_ids != old_fred_ids:
                    st.session_state.fred_series_ids = new_fred_ids
                    logger.debug(f"主頁面：FRED Series IDs 更改為 '{new_fred_ids}'")

        if st.button("🔍 獲取並預覽選定數據", key="main_fetch_data_button"):
            logger.info("主頁面：用戶點擊 '獲取並預覽選定數據' 按鈕。")
            st.session_state.fetch_data_button_clicked = True # Mark as clicked to persist state across reruns if needed
            st.session_state.fetched_data_preview = {} # Clear previous previews
            st.session_state.fetch_errors = {} # Clear previous errors

            if not (st.session_state.get("select_yfinance") or st.session_state.get("select_fred") or st.session_state.get("select_ny_fed")):
                logger.warning("主頁面：用戶點擊獲取數據但未選擇任何數據源。")
                st.warning("請至少選擇一個數據源。")
                st.session_state.fetch_data_button_clicked = False # Reset if no action taken
            else:
                with st.spinner("正在獲取外部數據...請稍候..."):
                    st.toast("⏳ 正在從外部源獲取數據，請耐心等候...", icon="⏳")
                    logger.debug("主頁面：開始獲取所選外部數據。")
                    if st.session_state.get("select_yfinance"):
                        yfinance_interval_options_from_settings = ui_settings.get("yfinance_interval_options", {"1 Day": "1d"}) # Fallback
                        actual_yf_interval = yfinance_interval_options_from_settings.get(st.session_state.yfinance_interval_label, "1d") # Fallback interval value
                        current_yf_tickers = st.session_state.get("yfinance_tickers", ui_settings.get("default_yfinance_tickers", "SPY"))
                        logger.info(f"主頁面：準備調用後端 YFinance API。Tickers: {current_yf_tickers}, Start: {st.session_state.data_start_date}, End: {st.session_state.data_end_date}, Interval: {actual_yf_interval}")

                        yfinance_payload = {
                            "tickers": [t.strip() for t in current_yf_tickers.split(",")],
                            "start_date": st.session_state.data_start_date,
                            "end_date": st.session_state.data_end_date,
                            "interval": actual_yf_interval
                        }
                        try:
                            response = requests.post(f"{app_settings.FASTAPI_BACKEND_URL}/api/data/yfinance", json=yfinance_payload, timeout=60)
                            response.raise_for_status()
                            yf_response_json = response.json()
                            if yf_response_json.get("success"):
                                yf_data_json = yf_response_json.get("data", {})
                                yf_data_dfs = {ticker: pd.read_json(pds_json, orient='split') for ticker, pds_json in yf_data_json.items()}
                                if yf_data_dfs: st.session_state.fetched_data_preview["yfinance"] = yf_data_dfs
                                logger.info(f"後端 YFinance API 調用成功。獲取 {len(yf_data_dfs)} 組數據。")
                                # Handle plots if backend provides them
                                # if "plots" in yf_response_json: ...
                            else:
                                err_msg = yf_response_json.get("error", "YFinance 後端 API 返回失敗但未提供錯誤訊息。")
                                st.session_state.fetch_errors["yfinance"] = [err_msg]
                                logger.error(f"後端 YFinance API 返回失敗: {err_msg}")
                        except requests.exceptions.RequestException as e:
                            st.session_state.fetch_errors["yfinance"] = [f"調用 YFinance 後端 API 失敗: {e}"]
                            logger.error(f"調用 YFinance 後端 API 失敗: {e}", exc_info=True)

                    if st.session_state.get("select_fred"):
                        current_fred_ids = st.session_state.get("fred_series_ids", ui_settings.get("default_fred_series_ids", "GDP"))
                        logger.info(f"主頁面：準備調用後端 FRED API。Series IDs: {current_fred_ids}, Start: {st.session_state.data_start_date}, End: {st.session_state.data_end_date}")
                        fred_payload = {
                            "series_ids": [s.strip() for s in current_fred_ids.split(",")],
                            "start_date": st.session_state.data_start_date,
                            "end_date": st.session_state.data_end_date
                        }
                        try:
                            response = requests.post(f"{app_settings.FASTAPI_BACKEND_URL}/api/data/fred", json=fred_payload, timeout=60)
                            response.raise_for_status()
                            fred_response_json = response.json()
                            if fred_response_json.get("success"):
                                fred_data_json = fred_response_json.get("data", {})
                                fred_data_dfs = {sid: pd.read_json(s_json, orient='split') for sid, s_json in fred_data_json.items()}
                                if fred_data_dfs: st.session_state.fetched_data_preview["fred"] = fred_data_dfs
                                logger.info(f"後端 FRED API 調用成功。獲取 {len(fred_data_dfs)} 組數據。")
                            else:
                                err_msg = fred_response_json.get("error", "FRED 後端 API 返回失敗但未提供錯誤訊息。")
                                st.session_state.fetch_errors["fred"] = [err_msg]
                                logger.error(f"後端 FRED API 返回失敗: {err_msg}")
                        except requests.exceptions.RequestException as e:
                            st.session_state.fetch_errors["fred"] = [f"調用 FRED 後端 API 失敗: {e}"]
                            logger.error(f"調用 FRED 後端 API 失敗: {e}", exc_info=True)

                    if st.session_state.get("select_ny_fed"):
                        logger.info("主頁面：準備調用後端 NY Fed (fetch_web_content) API。")
                        # This URL might need to be made configurable or passed differently if it changes often
                        ny_fed_target_url = "https://www.newyorkfed.org/markets/desk-operations/ambs" # Example, assuming this is what was fetched
                        nyfed_payload = {"url": ny_fed_target_url, "source_type": "ny_fed_ambs"} # Added source_type for backend
                        try:
                            response = requests.post(f"{app_settings.FASTAPI_BACKEND_URL}/api/data/fetch_web_content", json=nyfed_payload, timeout=60)
                            response.raise_for_status()
                            nyfed_response_json = response.json()
                            if nyfed_response_json.get("success"):
                                # Assuming backend returns DataFrame as JSON string if it was processed to DataFrame
                                # Or raw content if that's what the backend provides
                                if nyfed_response_json.get("content_type") == "application/json_dataframe": # Custom type for DF
                                     nyfed_df = pd.read_json(nyfed_response_json.get("data"), orient='split')
                                     st.session_state.fetched_data_preview["ny_fed"] = nyfed_df
                                     logger.info(f"後端 NY Fed API 調用成功。獲取 DataFrame。")
                                else: # Handle as plain text or other content
                                     st.session_state.fetched_data_preview["ny_fed_content"] = nyfed_response_json.get("data","")
                                     logger.info(f"後端 NY Fed API 調用成功。獲取 Content-Type: {nyfed_response_json.get('content_type')}")
                            else:
                                err_msg = nyfed_response_json.get("error", "NY Fed 後端 API 返回失敗但未提供錯誤訊息。")
                                st.session_state.fetch_errors["ny_fed"] = [err_msg]
                                logger.error(f"後端 NY Fed API 返回失敗: {err_msg}")
                        except requests.exceptions.RequestException as e:
                            st.session_state.fetch_errors["ny_fed"] = [f"調用 NY Fed 後端 API 失敗: {e}"]
                            logger.error(f"調用 NY Fed 後端 API 失敗: {e}", exc_info=True)

                if not st.session_state.get("fetch_errors") and st.session_state.get("fetched_data_preview"):
                    logger.info("主頁面：外部數據已成功獲取 (通過後端 API) 且無錯誤報告。")
                    st.success("外部數據已成功獲取 (通過後端)。")
                elif not st.session_state.get("fetched_data_preview") and not st.session_state.get("fetch_errors") and not st.session_state.get("fetched_data_preview",{}).get("ny_fed_content"):
                     logger.info("主頁面：未獲取到任何外部數據 (通過後端 API)，且無錯誤報告。")
                     st.info("未獲取到任何外部數據。請檢查您的輸入、數據源，或後端服務日誌。")
                # 如果有錯誤，會在下面顯示

        if st.session_state.get("fetch_errors"):
            logger.warning(f"主頁面：數據獲取過程中發生錯誤: {st.session_state.fetch_errors}")
            st.subheader("數據獲取錯誤:")
            for source, errors_list in st.session_state.fetch_errors.items():
                st.error(f"來源 {source.upper()}:")
                for err_msg in errors_list:
                    st.markdown(f"- {err_msg}")

        if st.session_state.get("fetched_data_preview"):
            logger.debug("主頁面：開始渲染已獲取數據的預覽。")
            st.subheader("已獲取數據預覽:")
            if "yfinance" in st.session_state.fetched_data_preview:
                st.markdown("#### yfinance 數據:")
                for ticker, df_yf in st.session_state.fetched_data_preview["yfinance"].items():
                    with st.expander(f"Ticker: {ticker} (共 {len(df_yf)} 行)", expanded=False): st.dataframe(df_yf.head())

            if "fred" in st.session_state.fetched_data_preview:
                st.markdown("#### FRED 數據:")
                for series_id, df_fred in st.session_state.fetched_data_preview["fred"].items():
                    with st.expander(f"Series ID: {series_id} (共 {len(df_fred)} 行)", expanded=False): st.dataframe(df_fred.head())

            if "ny_fed" in st.session_state.fetched_data_preview and isinstance(st.session_state.fetched_data_preview["ny_fed"], pd.DataFrame) and not st.session_state.fetched_data_preview["ny_fed"].empty:
                st.markdown("#### NY Fed 一級交易商數據 (DataFrame):")
                df_nyfed = st.session_state.fetched_data_preview["ny_fed"]
                with st.expander(f"NY Fed 總持有量 (共 {len(df_nyfed)} 行)", expanded=False): st.dataframe(df_nyfed.head())
            elif "ny_fed_content" in st.session_state.fetched_data_preview and st.session_state.fetched_data_preview["ny_fed_content"]:
                st.markdown("#### NY Fed 數據 (原始內容):")
                with st.expander("原始網頁內容預覽 (前500字符)", expanded=False):
                    st.text(st.session_state.fetched_data_preview["ny_fed_content"][:500] + "...")
            logger.debug("主頁面：已獲取數據預覽渲染完畢 (通過後端 API)。")

    st.markdown("---")
    logger.info("主頁面：主要內容渲染結束 (render_main_page_content)。")

if __name__ == "__main__":
    # 模擬測試 (需要 Streamlit 環境和 session_state)
    # st.session_state.update({ ... 初始化 main_page 需要的鍵 ...})
    # render_main_page_content()
    pass
