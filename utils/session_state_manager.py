# utils/session_state_manager.py
import streamlit as st
import logging
from config.api_keys_config import api_keys_info
try:
    from google.colab import userdata
    IS_COLAB = True
except ImportError:
    IS_COLAB = False
from config.app_settings import (
    DEFAULT_MAIN_GEMINI_PROMPT,
    FONT_SIZE_CSS_MAP, # Updated name
    DEFAULT_GEMINI_RPM_LIMIT,
    DEFAULT_GEMINI_TPM_LIMIT,
    DEFAULT_YFINANCE_TICKERS,
    DEFAULT_FRED_SERIES_IDS,
    DEFAULT_YFINANCE_INTERVAL_LABEL,
    DEFAULT_CACHE_TTL_SECONDS # For cache_ttl_seconds_input
)

logger = logging.getLogger(__name__)

def initialize_session_state():
    """
    初始化 Streamlit 應用程式所需的所有 session_state 鍵。
    這樣可以確保所有鍵在應用程式的任何地方被訪問之前都已存在。
    """
    if "initialized_keys" in st.session_state:
        logger.info("Session state 已初始化。")
        return

    logger.info("開始初始化 session_state...")

    # API 金鑰相關
    for key_name in api_keys_info.values():
        if key_name not in st.session_state:
            st.session_state[key_name] = ""

    if IS_COLAB:
        logger.info("在 Colab 環境中，嘗試從 userdata 加載 API 金鑰。")
        try:
            # 檢查 userdata 是否可用且具有 'get' 方法
            if hasattr(userdata, 'get'):
                google_api_key_colab = userdata.get('GOOGLE_API_KEY')
                if google_api_key_colab:
                    st.session_state[api_keys_info['Google Gemini API Key 1']] = google_api_key_colab
                    logger.info("已從 Colab userdata 加載 GOOGLE_API_KEY。")
                else:
                    logger.info("在 Colab userdata 中未找到 GOOGLE_API_KEY。")

                fred_api_key_colab = userdata.get('FRED_API_KEY')
                if fred_api_key_colab:
                    st.session_state[api_keys_info['FRED API Key']] = fred_api_key_colab
                    logger.info("已從 Colab userdata 加載 FRED_API_KEY。")
                else:
                    logger.info("在 Colab userdata 中未找到 FRED_API_KEY。")
            else:
                logger.warning("Colab userdata 物件似乎不可用或不完整 (缺少 'get' 方法)。跳過從 userdata 加載 API 金鑰。")
        except Exception as e:
            logger.error(f"從 Colab userdata 加載 API 金鑰時發生錯誤: {e}")
    else:
        logger.info("不在 Colab 環境中或 google.colab.userdata 無法導入，跳過從 userdata 加載 API 金鑰。")

    logger.info("API 金鑰 session_state 初始化完畢。")

    # Gemini 模型設定
    if "initialized_model_settings" not in st.session_state:
        st.session_state.selected_model_name = None # Will be populated dynamically
        st.session_state.global_rpm_limit = DEFAULT_GEMINI_RPM_LIMIT
        st.session_state.global_tpm_limit = DEFAULT_GEMINI_TPM_LIMIT
        st.session_state.initialized_model_settings = True
    logger.info("Gemini 模型設定 session_state 初始化完畢 (selected_model_name is None initially)。")

    # 主要提示詞設定
    if "initialized_prompt_settings" not in st.session_state:
        st.session_state.main_gemini_prompt = DEFAULT_MAIN_GEMINI_PROMPT
        st.session_state.initialized_prompt_settings = True
    logger.info("主要提示詞設定 session_state 初始化完畢。")

    # 檔案上傳設定
    if "initialized_file_upload_settings" not in st.session_state:
        st.session_state.uploaded_files_list = []
        st.session_state.uploaded_file_contents = {}  # {filename: content}
        st.session_state.initialized_file_upload_settings = True
    logger.info("檔案上傳設定 session_state 初始化完畢。")

    # 數據源設定
    if "initialized_data_source_settings" not in st.session_state:
        st.session_state.select_yfinance = True
        st.session_state.select_fred = False
        st.session_state.select_ny_fed = False
        st.session_state.select_all_sources = False # 新增一個全選/全不選的狀態
        st.session_state.data_start_date = None # 由用戶選擇
        st.session_state.data_end_date = None # 由用戶選擇
        st.session_state.yfinance_tickers = DEFAULT_YFINANCE_TICKERS
        st.session_state.yfinance_interval_label = DEFAULT_YFINANCE_INTERVAL_LABEL
        st.session_state.fred_series_ids = DEFAULT_FRED_SERIES_IDS
        st.session_state.fetched_data_preview = {} # {source_name: pd.DataFrame}
        st.session_state.fetch_errors = {} # {source_name: error_message}
        st.session_state.fetch_data_button_clicked = False
        st.session_state.initialized_data_source_settings = True
    logger.info("數據源設定 session_state 初始化完畢。")

    # Gemini 互動設定
    if "initialized_gemini_interaction_settings" not in st.session_state:
        st.session_state.chat_history = [] # [{"role": "user/model", "parts": ["text"]}]
        st.session_state.active_gemini_key_index = 0 # 當前使用的 API key 索引
        st.session_state.gemini_api_key_usage = {key: 0 for key in api_keys_info.values()} # 跟蹤每個key的使用次數
        st.session_state.gemini_caches_list = [] # 存儲 (DisplayName, Name) 的元組列表
        st.session_state.selected_cache_for_generation = None # 用戶選擇用於生成的快取名稱
        st.session_state.temporarily_invalid_gemini_keys = [] # 用於追蹤本會話中驗證無效的Gemini金鑰
        st.session_state.initialized_gemini_interaction_settings = True
    logger.info("Gemini 互動設定 session_state 初始化完畢 (包括 temporarily_invalid_gemini_keys)。")

    # 主題設定
    if "initialized_theme_settings" not in st.session_state:
        st.session_state.active_theme = "Light"  # "Light" 或 "Dark"
        st.session_state.initialized_theme_settings = True
    logger.info("主題設定 session_state 初始化完畢。")

    # 字體大小設定
    if "initialized_font_settings" not in st.session_state:
        st.session_state.font_size_name = "Medium" # Default size name
        st.session_state.font_size_css_map = FONT_SIZE_CSS_MAP # Use the constant
        st.session_state.initialized_font_settings = True
    logger.info("字體大小設定 session_state 初始化完畢。")

    # 日誌處理程序 (將在主 app.py 中設置)
    if "log_handler" not in st.session_state:
        st.session_state.log_handler = None # 將由 setup_logging 返回並存儲於此
    logger.info("日誌處理程序 session_state 鍵已創建。")

    # 前端UI日誌列表
    if "ui_logs" not in st.session_state:
        st.session_state.ui_logs = []
        logger.info("UI 日誌列表 (ui_logs) 已在 session_state 中初始化。")

    # Gemini 內容快取管理相關的輸入字段
    if "cache_display_name_input" not in st.session_state:
        st.session_state.cache_display_name_input = ""
    if "cache_content_input" not in st.session_state:
        st.session_state.cache_content_input = ""
    if "cache_ttl_seconds_input" not in st.session_state:
        st.session_state.cache_ttl_seconds_input = DEFAULT_CACHE_TTL_SECONDS # 使用常數
    if "cache_name_to_delete_input" not in st.session_state:
        st.session_state.cache_name_to_delete_input = ""
    logger.info("Gemini 內容快取管理輸入字段 session_state 初始化完畢。")

    if "setup_complete" not in st.session_state:
        st.session_state.setup_complete = False
        logger.info("使用者引導狀態 (setup_complete) 已初始化為 False。")

    if "current_agent_prompt" not in st.session_state:
        st.session_state.current_agent_prompt = ""
        logger.info("Agent 提示詞狀態 (current_agent_prompt) 已初始化。")

    # Colab Drive 掛載提示相關
    if "show_drive_mount_prompt" not in st.session_state:
        st.session_state.show_drive_mount_prompt = False
        logger.info("Colab Drive 掛載提示 (show_drive_mount_prompt) 已初始化為 False。")
    if "drive_path_requested" not in st.session_state:
        st.session_state.drive_path_requested = ""
        logger.info("Colab Drive 掛載路徑請求 (drive_path_requested) 已初始化為空字串。")

    st.session_state.initialized_keys = True
    logger.info("Session_state 初始化完成。")

if __name__ == "__main__":
    # 這個函數通常在 Streamlit 應用的主腳本頂部被調用
    # 為了測試，你可以模擬 Streamlit 的 session_state
    class MockSessionState:
        def __init__(self):
            self._state = {}
        def __setitem__(self, key, value):
            self._state[key] = value
        def __getitem__(self, key):
            return self._state[key]
        def __contains__(self, key):
            return key in self._state
        def get(self, key, default=None):
            return self._state.get(key, default)

    # st.session_state = MockSessionState() # 取消註釋以在本地運行此腳本進行測試
    # initialize_session_state()
    # print(st.session_state._state)
    pass
