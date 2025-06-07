# components/main_page.py
import streamlit as st
import logging
import pandas as pd # For displaying DataFrame previews
import os # Ensure os is imported for path operations
# Import the new helper function
from components.chat_interface import add_message_and_process
# Import for Colab Drive path checking
from services.file_processors import handle_file_uploads, ensure_colab_drive_mount_if_needed
import os
import sys
from services.data_fetchers import (
    fetch_yfinance_data,
    fetch_fred_data,
    fetch_ny_fed_data
)
from config.api_keys_config import api_keys_info # For checking Gemini keys
from config import app_settings # Import the whole module for constants

logger = logging.getLogger(__name__)

def _are_gemini_keys_set() -> bool:
    """檢查 session_state 中是否設置了任何 Gemini API 金鑰。"""
    for key_label, key_name in api_keys_info.items():
        if "gemini" in key_label.lower() and st.session_state.get(key_name):
            return True
    return False

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
    # prompts_dir = "prompts" # Replaced by app_settings.PROMPTS_DIR
    agent_prompt_files = []
    if os.path.exists(app_settings.PROMPTS_DIR) and os.path.isdir(app_settings.PROMPTS_DIR):
        try:
            agent_prompt_files = sorted([
                f for f in os.listdir(app_settings.PROMPTS_DIR)
                if f.startswith("agent_") and f.endswith(".txt")
            ]) # Sort for consistent order
        except Exception as e:
            logger.error(f"主頁面：讀取 prompts 目錄 '{app_settings.PROMPTS_DIR}' 時發生錯誤: {e}")
            st.error(f"無法讀取 Agent 任務列表: {e}")

    if not agent_prompt_files:
        st.info(f"目前沒有可用的 Agent 快捷任務。請在 '{app_settings.PROMPTS_DIR}' 文件夾下添加 'agent_*.txt' 文件。")
    else:
        # Determine number of columns, e.g., 3 or 4 per row
        num_cols = min(len(agent_prompt_files), 3) # Max 3 buttons per row, or fewer if less files
        cols = st.columns(num_cols)
        for i, prompt_file in enumerate(agent_prompt_files):
            button_label = prompt_file.replace("agent_", "").replace(".txt", "").replace("_", " ").title()
            # Use session state to manage button clicks to avoid issues with st.rerun if called from elsewhere
            button_key = f"agent_button_{prompt_file}"

            if cols[i % num_cols].button(button_label, key=button_key):
                logger.info(f"主頁面：Agent 按鈕 '{button_label}' 被點擊。")
                try:
                    with open(os.path.join(app_settings.PROMPTS_DIR, prompt_file), "r", encoding="utf-8") as f:
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

    # --- API 金鑰缺失警告 ---
    if not _are_gemini_keys_set():
        st.warning(
            "⚠️ **核心功能需要 Gemini API 金鑰**\n\n"
            "此應用程式的核心分析功能由 Google Gemini 提供技術支援。請在左側邊欄「🔑 API 金鑰管理」部分設定您的 Gemini API 金鑰以啟用完整功能。\n\n"
            "如果您還沒有金鑰，可以點擊以下連結獲取： "
            "[點此獲取 Gemini API 金鑰](https://aistudio.google.com/app/apikey)",
            icon="🔑"
        )
        with st.expander("🔧 如何設定 API 金鑰？(中文教學)", expanded=False): # 默認不展開
            st.markdown("""
                ### 如何設定及使用 API 金鑰：
                1.  **獲取金鑰**：前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 網站，創建並複製API金鑰。
                2.  **在應用程式中設定**：在本應用程式的左側邊欄「🔑 API 金鑰管理」部分，將金鑰貼入任一 Gemini API Key 輸入框中。
                3.  **開始使用**：金鑰設定完成後，應用程式的 Gemini 分析功能即可使用。
                **重要提示**：請妥善保管您的 API 金鑰。
            """)
        logger.info("因缺少 Gemini API 金鑰，已在主頁顯示警告和設定指南。")

    # --- 步驟一：上傳文件 ---
    st.header("📄 步驟一：上傳與檢視文件")
    st.caption("請上傳您需要分析的文字檔案、CSV 或 Excel 檔案到當前會話。")
    logger.debug("主頁面：渲染文件上傳區域。")

    uploaded_files_from_widget = st.file_uploader(
        "上傳新文件到當前會話 (可多選):",
        type=["txt", "csv", "xls", "xlsx", "md", "py", "json", "xml", "html", "css", "js"],
        accept_multiple_files=True,
        key="main_file_uploader_widget",
        help="此處上傳的文件將可用於下方選擇進行 All-in-One 分析，或用於其他獨立分析功能。"
    )

    if uploaded_files_from_widget: # Check if list is not empty
        logger.info(f"主頁面：用戶上傳了 {len(uploaded_files_from_widget)} 個檔案。調用 handle_file_uploads 處理。")
        handle_file_uploads(uploaded_files_from_widget)
        # handle_file_uploads 內部有詳細日誌，此處僅記錄用戶操作和調用。

    if st.session_state.get("uploaded_files_list"):
        logger.debug(f"主頁面：顯示已上傳文件預覽。共 {len(st.session_state.uploaded_files_list)} 個文件。")
        st.subheader("已上傳文件預覽:")
        if not st.session_state.get("uploaded_file_contents"):
            logger.warning("主頁面：已上傳文件列表不為空，但文件內容為空。")
            st.warning("所有上傳的檔案都無法成功讀取內容，或尚未處理。請檢查檔案格式或內容。")

        for file_name in st.session_state.uploaded_files_list:
            content_or_df = st.session_state.uploaded_file_contents.get(file_name)
            with st.expander(f"檔名: {file_name} (點擊展開/收起預覽)", expanded=False):
                if isinstance(content_or_df, str):
                    st.text(content_or_df[:500] + "..." if len(content_or_df) > 500 else content_or_df)
                elif isinstance(content_or_df, pd.DataFrame):
                    st.dataframe(content_or_df.head())
                elif content_or_df is None and file_name in st.session_state.uploaded_files_list: # 文件名在列表中但內容為空
                    logger.warning(f"主頁面：預覽文件 '{file_name}' 時發現其內容為空或處理失敗。")
                    st.warning(f"檔案 '{file_name}' 的內容尚未處理或處理失敗。")
                elif content_or_df is not None:
                    logger.debug(f"主頁面：文件 '{file_name}' 為無法直接預覽的類型 (例如字節)。大小: {len(content_or_df)} 字節。")
                    st.text(f"無法直接預覽此檔案類型 (大小: {len(content_or_df)} 字節)。")
    else:
        logger.debug("主頁面：當前沒有已上傳的檔案。顯示提示信息。")
        st.info("請通過上方的「上傳新文件到當前會話」按鈕上傳文件。")
    st.markdown("---")

    # --- 步驟二：選擇核心分析文件 (用於 All-in-One 報告) ---
    st.header("🎯 步驟二：選擇核心分析文件 (用於 All-in-One 報告)")
    st.caption("從 `Wolf_Data/source_documents/` 或已上傳的文件中選擇核心文檔。")
    logger.debug("主頁面：渲染核心分析文件選擇區域。")

    # --- Wolf_Data/source_documents/ 文件掃描邏輯 ---
    IN_COLAB_MAIN_PAGE = 'google.colab' in sys.modules # Local check for Colab

    # Construct paths using constants from app_settings
    if IN_COLAB_MAIN_PAGE:
        wolf_data_source_path_to_scan = os.path.join(
            app_settings.COLAB_DRIVE_BASE_PATH,
            app_settings.BASE_DATA_DIR_NAME,
            app_settings.SOURCE_DOCUMENTS_DIR_NAME
        )
    else:
        wolf_data_source_path_to_scan = os.path.join(
            os.path.expanduser(app_settings.USER_HOME_DIR),
            app_settings.BASE_DATA_DIR_NAME,
            app_settings.SOURCE_DOCUMENTS_DIR_NAME
        )

    can_scan_wolf_data = True
    if IN_COLAB_MAIN_PAGE: # Only call ensure_colab_drive_mount_if_needed if in Colab and path is for Colab
        # ensure_colab_drive_mount_if_needed expects the specific path to check,
        # which is wolf_data_source_path_to_scan when in Colab.
        if not ensure_colab_drive_mount_if_needed(wolf_data_source_path_to_scan):
            can_scan_wolf_data = False
            logger.info(f"主頁面：ensure_colab_drive_mount_if_needed 返回 False for '{wolf_data_source_path_to_scan}'. 跳過掃描。")
            # The prompt will be shown at the top of the page.
            # We should ensure wolf_data_file_map is empty if we can't scan.
            st.session_state.wolf_data_file_map = {}


    display_name_to_path = {}
    # Only proceed with scanning if the path is considered valid (or not a Colab path needing mount)
    if can_scan_wolf_data and os.path.exists(wolf_data_source_path_to_scan):
        logger.info(f"主頁面：開始掃描 Wolf_Data 目錄: {wolf_data_source_path_to_scan}")
        for root, _, files in os.walk(wolf_data_source_path_to_scan):
            for file in files:
                if file.endswith((".txt", ".md")):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, wolf_data_source_path_to_scan)
                    display_name_to_path[relative_path] = full_path
        st.session_state.wolf_data_file_map = display_name_to_path
        logger.info(f"主頁面：掃描到 {len(display_name_to_path)} 個文件從 Wolf_Data。")
    elif can_scan_wolf_data and not os.path.exists(wolf_data_source_path_to_scan):
        # This case handles if not IN_COLAB_MAIN_PAGE and local path doesn't exist,
        # or if ensure_colab_drive_mount_if_needed passed but path still somehow not found (less likely for Colab)
        logger.warning(f"主頁面：Wolf_Data 目錄 '{wolf_data_source_path_to_scan}' 不存在 (can_scan_wolf_data was True)。")
        st.session_state.wolf_data_file_map = {}
    # If can_scan_wolf_data is False, wolf_data_file_map is already set to {} above.

    multiselect_options_wolf = list(st.session_state.get("wolf_data_file_map", {}).keys())

    # --- 已上傳文件列表 (作為備選或補充) ---
    # 保持 uploaded_files_list 的可用性，但優先顯示 Wolf_Data 的文件
    # 如果 Wolf_Data 為空，可以考慮使用 uploaded_files_list 作為備選

    final_multiselect_options = multiselect_options_wolf
    info_message = ""

    if not final_multiselect_options:
        info_message = f"提示：在 '{wolf_data_source_path_to_scan}' 中未找到 .txt 或 .md 文件。您也可以使用上方「步驟一」上傳臨時文件。"
        # Fallback to uploaded files if Wolf_Data is empty and uploaded_files_list is not
        # For now, let's keep it simple and prioritize Wolf_Data. If Wolf_Data is empty, user sees that.
        # Fallback can be added later if needed.
        # options_for_multiselect = st.session_state.get("uploaded_files_list", [])
        # if options_for_multiselect:
        #     info_message += " 您可以從已上傳的文件中選擇："
        # else:
        #     options_for_multiselect = ["示例-無可用文件.txt"] # Placeholder if everything is empty
        #     info_message += " 也沒有已上傳的文件。"
        st.info(info_message)
        # If final_multiselect_options is empty, ensure multiselect doesn't break
        if not final_multiselect_options: final_multiselect_options = ["目前無可選文件"]


    else:
        st.info(f"請從 '{os.path.basename(wolf_data_source_path_to_scan.rstrip(os.sep))}' 目錄 (或其子目錄) 中選擇文件。")

    # 使用 relative paths (keys of wolf_data_file_map) for selection
    # st.session_state.selected_core_documents should store these relative paths
    selected_relative_paths = st.multiselect(
        "選擇要進行 All-in-One 綜合分析的文件 (可複選):",
        options=sorted(final_multiselect_options), # Sort for better UX
        default=st.session_state.selected_core_documents,
        key="main_selected_core_documents_multiselect"
    )

    if selected_relative_paths != st.session_state.selected_core_documents:
        st.session_state.selected_core_documents = selected_relative_paths
        logger.info(f"主頁面：用戶選擇的核心分析文件 (相對路徑) 已更新: {selected_relative_paths}")

    if st.session_state.selected_core_documents:
        st.markdown("##### 已選定核心文件 (相對路徑):")
        for rel_path_doc_name in st.session_state.selected_core_documents:
            st.markdown(f"- {rel_path_doc_name}")
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
                old_yf_tickers = st.session_state.get("yfinance_tickers", "")
                new_yf_tickers = st.text_input("yfinance Tickers (逗號分隔):", value=old_yf_tickers, key="main_yfinance_tickers")
                if new_yf_tickers != old_yf_tickers:
                    st.session_state.yfinance_tickers = new_yf_tickers
                    logger.debug(f"主頁面：yfinance tickers 更改為 '{new_yf_tickers}'")

                old_yf_interval = st.session_state.get("yfinance_interval_label", "1 Day")
                new_yf_interval = st.selectbox(
                    "yfinance 數據週期:",
                    options=list(app_settings.YFINANCE_INTERVAL_OPTIONS.keys()),
                    index=list(app_settings.YFINANCE_INTERVAL_OPTIONS.keys()).index(old_yf_interval) if old_yf_interval in app_settings.YFINANCE_INTERVAL_OPTIONS else 0,
                    key="main_yfinance_interval"
                )
                if new_yf_interval != old_yf_interval:
                    st.session_state.yfinance_interval_label = new_yf_interval
                    logger.debug(f"主頁面：yfinance interval 更改為 '{new_yf_interval}'")
        with param_col2:
            if st.session_state.get("select_fred"):
                old_fred_ids = st.session_state.get("fred_series_ids", app_settings.DEFAULT_FRED_SERIES_IDS) # Use default from settings
                new_fred_ids = st.text_input("FRED Series IDs (逗號分隔):", value=old_fred_ids, key="main_fred_ids")
                if new_fred_ids != old_fred_ids:
                    st.session_state.fred_series_ids = new_fred_ids
                    logger.debug(f"主頁面：FRED Series IDs 更改為 '{new_fred_ids}'")

        if st.button("🔍 獲取並預覽選定數據", key="main_fetch_data_button"):
            logger.info("主頁面：用戶點擊 '獲取並預覽選定數據' 按鈕。")
            st.session_state.fetch_data_button_clicked = True
            st.session_state.fetched_data_preview = {}
            st.session_state.fetch_errors = {}

            if not (st.session_state.get("select_yfinance") or st.session_state.get("select_fred") or st.session_state.get("select_ny_fed")):
                logger.warning("主頁面：用戶點擊獲取數據但未選擇任何數據源。")
                st.warning("請至少選擇一個數據源。")
                st.session_state.fetch_data_button_clicked = False
            else:
                with st.spinner("正在獲取外部數據...請稍候..."):
                    st.toast("⏳ 正在從外部源獲取數據，請耐心等候...", icon="⏳")
                    logger.debug("主頁面：開始獲取所選外部數據。")
                    if st.session_state.get("select_yfinance"):
                        actual_yf_interval = app_settings.YFINANCE_INTERVAL_OPTIONS[st.session_state.yfinance_interval_label]
                        current_yf_tickers = st.session_state.get("yfinance_tickers", app_settings.DEFAULT_YFINANCE_TICKERS) # Use default
                        logger.info(f"主頁面：準備調用 fetch_yfinance_data。Tickers: {current_yf_tickers}, Start: {st.session_state.data_start_date}, End: {st.session_state.data_end_date}, Interval: {actual_yf_interval}")
                        yf_data, yf_errs = fetch_yfinance_data(
                            current_yf_tickers, st.session_state.data_start_date,
                            st.session_state.data_end_date, actual_yf_interval
                        )
                        if yf_data: st.session_state.fetched_data_preview["yfinance"] = yf_data
                        if yf_errs: st.session_state.fetch_errors["yfinance"] = yf_errs
                        logger.info(f"主頁面：fetch_yfinance_data 調用完畢。獲取 {len(yf_data)} 組數據，{len(yf_errs)} 個錯誤。")

                    if st.session_state.get("select_fred"):
                        fred_api_key_val = ""
                        fred_key_name_in_session = next((k_name for k_label, k_name in api_keys_info.items() if "fred" in k_label.lower()), None)
                        if fred_key_name_in_session:
                            fred_api_key_val = st.session_state.get(fred_key_name_in_session, "")

                        if not fred_api_key_val:
                            logger.error("主頁面：FRED API 金鑰未設定，無法獲取 FRED 數據。")
                            st.session_state.fetch_errors["fred"] = ["錯誤：FRED API 金鑰未在側邊欄的 API 金鑰管理中設定。"]
                        else:
                            logger.info(f"主頁面：準備調用 fetch_fred_data。Series IDs: {st.session_state.fred_series_ids}, Start: {st.session_state.data_start_date}, End: {st.session_state.data_end_date}, Key_Present: {bool(fred_api_key_val)}")
                            fred_data, fred_errs = fetch_fred_data(
                                st.session_state.fred_series_ids, st.session_state.data_start_date,
                                st.session_state.data_end_date, fred_api_key_val
                            )
                            if fred_data: st.session_state.fetched_data_preview["fred"] = fred_data
                            if fred_errs: st.session_state.fetch_errors["fred"] = fred_errs
                            logger.info(f"主頁面：fetch_fred_data 調用完畢。獲取 {len(fred_data)} 組數據，{len(fred_errs)} 個錯誤。")

                    if st.session_state.get("select_ny_fed"):
                        logger.info("主頁面：準備調用 fetch_ny_fed_data。")
                        nyfed_df, nyfed_errs = fetch_ny_fed_data()
                        if nyfed_df is not None: st.session_state.fetched_data_preview["ny_fed"] = nyfed_df
                        if nyfed_errs: st.session_state.fetch_errors["ny_fed"] = nyfed_errs
                        logger.info(f"主頁面：fetch_ny_fed_data 調用完畢。獲取數據: {'是' if nyfed_df is not None else '否'}，{len(nyfed_errs)} 個錯誤。")

                if not st.session_state.get("fetch_errors") and st.session_state.get("fetched_data_preview"):
                    logger.info("主頁面：外部數據已成功獲取且無錯誤報告。")
                    st.success("外部數據已成功獲取。")
                elif not st.session_state.get("fetched_data_preview") and not st.session_state.get("fetch_errors"):
                     logger.info("主頁面：未獲取到任何外部數據，且無錯誤報告。")
                     st.info("未獲取到任何外部數據。請檢查您的輸入或數據源是否在該時段有數據。")
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

            if "ny_fed" in st.session_state.fetched_data_preview and st.session_state.fetched_data_preview["ny_fed"] is not None and not st.session_state.fetched_data_preview["ny_fed"].empty:
                st.markdown("#### NY Fed 一級交易商數據:")
                df_nyfed = st.session_state.fetched_data_preview["ny_fed"]
                with st.expander(f"NY Fed 總持有量 (共 {len(df_nyfed)} 行)", expanded=False): st.dataframe(df_nyfed.head())
            logger.debug("主頁面：已獲取數據預覽渲染完畢。")

    st.markdown("---")
    logger.info("主頁面：主要內容渲染結束 (render_main_page_content)。")

if __name__ == "__main__":
    # 模擬測試 (需要 Streamlit 環境和 session_state)
    # st.session_state.update({ ... 初始化 main_page 需要的鍵 ...})
    # render_main_page_content()
    pass
