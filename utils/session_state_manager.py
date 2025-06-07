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

    # API 金鑰相關 - REMOVED
    # API keys are now managed by the backend.
    # The frontend will no longer attempt to load them from Colab secrets or store them in session_state directly.
    # for key_name in api_keys_info.values():
    #     if key_name not in st.session_state:
    #         st.session_state[key_name] = "" # Initialize to empty string

    # if IS_COLAB:
    #     logger.info("在 Colab 環境中，嘗試從 userdata 加載 API 金鑰。")
    #     try:
    #         # 檢查 userdata 是否可用且具有 'get' 方法
    #         if hasattr(userdata, 'get'):
    #             google_api_key_colab = userdata.get('GOOGLE_API_KEY')
    #             if google_api_key_colab:
    #                 # This assumes api_keys_info['Google Gemini API Key 1'] is the correct key name string
    #                 # st.session_state[api_keys_info['Google Gemini API Key 1']] = google_api_key_colab
    #                 logger.info("已從 Colab userdata 讀取 GOOGLE_API_KEY (不再儲存到 session_state)。")
    #             else:
    #                 logger.info("在 Colab userdata 中未找到 GOOGLE_API_KEY。")

    #             fred_api_key_colab = userdata.get('FRED_API_KEY')
    #             if fred_api_key_colab:
    #                 # st.session_state[api_keys_info['FRED API Key']] = fred_api_key_colab
    #                 logger.info("已從 Colab userdata 讀取 FRED_API_KEY (不再儲存到 session_state)。")
    #             else:
    #                 logger.info("在 Colab userdata 中未找到 FRED_API_KEY。")
    #         else:
    #             logger.warning("Colab userdata 物件似乎不可用或不完整 (缺少 'get' 方法)。跳過從 userdata 加載 API 金鑰。")
    #     except Exception as e:
    #         logger.error(f"從 Colab userdata 加載 API 金鑰時發生錯誤: {e}")
    # else:
    #     logger.info("不在 Colab 環境中或 google.colab.userdata 無法導入，跳過從 userdata 加載 API 金鑰。")

    logger.info("API 金鑰相關的 session_state 初始化步驟已更新 (不再從前端加載金鑰)。")

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
    logger.info("Session_state 基本鍵初始化完成。")

    # --- Fetch UI settings from backend ---
    if 'ui_settings' not in st.session_state:
        logger.info("嘗試從後端獲取 UI 設定...")
        try:
            # Assuming backend URL is available, e.g., from an environment variable or a common config
            # For this example, let's use a placeholder. This should ideally come from a robust config mechanism.
            # In a real setup, app_settings.FASTAPI_BACKEND_URL would be defined.
            # backend_url = getattr(st.session_state.get("app_settings_module", {}), "FASTAPI_BACKEND_URL", "http://localhost:8000")
            # Temporarily hardcode for this step, assuming app_settings might not be fully available yet or to avoid circular deps
            backend_base_url = "http://localhost:8000" # TODO: Replace with proper config access

            # Dynamically import app_settings if not already available in a structured way
            # This is a bit of a workaround if session_state_manager runs before app.py fully sets up app_settings in session_state
            app_s = None
            if "app_settings_module" in st.session_state:
                app_s = st.session_state.app_settings_module
            else:
                try:
                    from config import app_settings as app_s_direct
                    app_s = app_s_direct
                except ImportError:
                    logger.error("無法直接導入 config.app_settings for backend URL.")


            if app_s and hasattr(app_s, 'FASTAPI_BACKEND_URL'):
                backend_base_url = app_s.FASTAPI_BACKEND_URL
            else:
                logger.warning(f"FASTAPI_BACKEND_URL 未在 app_settings 中配置或無法訪問，將使用預設值: {backend_base_url}")

            settings_url = f"{backend_base_url}/api/config/ui_settings"
            response = requests.get(settings_url, timeout=10)
            response.raise_for_status()
            st.session_state.ui_settings = response.json()
            logger.info(f"成功從後端獲取 UI 設定: {st.session_state.ui_settings}")
        except requests.exceptions.RequestException as e:
            logger.error(f"無法從後端 ({settings_url}) 獲取UI設定: {e}. 將使用備用預設值。")
            # Provide fallback default values
            st.session_state.ui_settings = {
                "app_name": app_s.APP_NAME if app_s else "Wolf_V5 (Fallback)",
                "default_gemini_rpm_limit": app_s.DEFAULT_GEMINI_RPM_LIMIT if app_s else 3,
                "default_gemini_tpm_limit": app_s.DEFAULT_GEMINI_TPM_LIMIT if app_s else 100000,
                "default_generation_config": app_s.DEFAULT_GENERATION_CONFIG if app_s else {"temperature": 0.7, "top_p": 0.9, "top_k": 32, "max_output_tokens": 8192},
                "default_main_gemini_prompt": app_s.DEFAULT_MAIN_GEMINI_PROMPT if app_s else "Fallback default prompt",
                "ny_fed_dataset_names": [item["name"] for item in (app_s.NY_FED_POSITIONS_URLS if app_s else [])],
                "yfinance_interval_options": app_s.YFINANCE_INTERVAL_OPTIONS if app_s else {"1 Day": "1d"},
                "allowed_upload_file_types": app_s.ALLOWED_UPLOAD_FILE_TYPES if app_s else ["txt", "csv"],
                "default_yfinance_tickers": app_s.DEFAULT_YFINANCE_TICKERS if app_s else "SPY",
                "default_fred_series_ids": app_s.DEFAULT_FRED_SERIES_IDS if app_s else "GDP",
                "default_yfinance_interval_label": app_s.DEFAULT_YFINANCE_INTERVAL_LABEL if app_s else "1 Day",
                # Add other UI-specific fallbacks that were in app_settings.py
                "default_theme": app_s.DEFAULT_THEME if app_s else "Light",
                "default_font_size_name": app_s.DEFAULT_FONT_SIZE_NAME if app_s else "Medium",
                "font_size_css_map": app_s.FONT_SIZE_CSS_MAP if app_s else {"Small": "font-small", "Medium": "font-medium", "Large": "font-large"},
                "text_preview_max_chars": app_s.TEXT_PREVIEW_MAX_CHARS if app_s else 500,
                "log_display_height": app_s.LOG_DISPLAY_HEIGHT if app_s else 300,
                "max_ui_log_entries": app_s.MAX_UI_LOG_ENTRIES if app_s else 300,
                "default_chat_container_height": app_s.DEFAULT_CHAT_CONTAINER_HEIGHT if app_s else 400,
                "agent_buttons_per_row": app_s.AGENT_BUTTONS_PER_ROW if app_s else 3,
                "prompts_dir": app_s.PROMPTS_DIR if app_s else "prompts" # Needed for agent buttons
            }
            logger.info(f"已應用備用 UI 設定: {st.session_state.ui_settings}")
        except Exception as e_other: # Catch any other unexpected error during UI settings fetch
            logger.error(f"獲取UI設定時發生非預期錯誤: {e_other}", exc_info=True)
            st.session_state.ui_settings = {} # Empty dict to avoid errors, app might be partially functional
            st.error("無法加載應用程式設定，某些功能可能無法正常運作。")

    logger.info("Session_state 初始化 (包括 UI 設定) 完成。")

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
