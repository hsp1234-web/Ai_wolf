# app.py (新的主應用程式檔案)
import streamlit as st
import logging
import sys

# --- 模組化導入 ---
try:
    from google.colab import userdata
    IS_COLAB_ENVIRONMENT = True
    # print("DEBUG: google.colab.userdata imported successfully.") # 臨時調試
except ImportError:
    IS_COLAB_ENVIRONMENT = False
    # print("DEBUG: Failed to import google.colab.userdata. Assuming not in Colab.") # 臨時調試
    # 創建一個模擬的 userdata 物件
    class MockUserdata:
        def __init__(self):
            self._data = {} # 可以預設一些測試值
            # print("DEBUG: MockUserdata initialized.") # 臨時調試
        def get(self, key: str):
            # print(f"DEBUG: MockUserdata.get called for key: {key}") # 臨時調試
            return self._data.get(key, None) # 返回 None 如果鍵不存在
        # 可選: 模仿 SecretNotFoundError
        class SecretNotFoundError(Exception):
            pass
    userdata = MockUserdata()

from utils.log_utils import StreamlitLogHandler, setup_logging # StreamlitLogHandler is imported but instance is created in setup_logging
from utils.session_state_manager import initialize_session_state
from utils.css_utils import load_custom_css # Removed inject_dynamic_theme_css, inject_font_size_css as they are handled differently now

from components.sidebar import render_sidebar
from components.main_page import render_main_page_content
from components.chat_interface import render_chat
from components.log_display import render_log_viewer

# --- 定義日誌檔案路徑 (Colab 環境) ---
import os # 新增導入 os 模組

# 這個路徑需要在 Colab Cell 1 中通過 !mkdir -p GDRIVE_PROJECT_DIR/logs 創建
# GDRIVE_PROJECT_DIR 通常是 /content/drive/MyDrive/wolfAI
# COLAB_LOG_FILE_PATH = "/content/drive/MyDrive/wolfAI/logs/streamlit.log" # 舊路徑
COLAB_LOG_FILE_PATH = "/content/drive/MyDrive/MyWolfData/logs/streamlit.log" # 新路徑

# --- 全局日誌記錄器 ---
logger = logging.getLogger(__name__)

def main():
    """
    應用程式主函數。
    """
    # 1. 設定頁面配置 (必須是第一個 Streamlit 命令)
    st.set_page_config(
        page_title="Wolf_V5",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/LinWolf/Gemini_Financial_Analysis_Assistant/issues',
            'Report a bug': "https://github.com/LinWolf/Gemini_Financial_Analysis_Assistant/issues",
            'About': """
            ## Wolf_V5
            版本 2.1 (日誌系統增強)
            此應用程式使用 Google Gemini API 進行高級金融數據分析和生成洞察。
            由 LinWolf (https://github.com/LinWolf) 開發。
            """
        }
    )

    # 2. 初始化 Session State (包含 ui_logs 的初始化)
    # 這次先調用 initialize_session_state，確保 'ui_logs' 鍵在 setup_logging 之前已存在且為列表。
    # StreamlitLogHandler 的 __init__ 也會嘗試初始化，但先做更保險。
    initialize_session_state() # 這會初始化 session_state 中的 api_keys_info 等
    # logger.info("主應用：Session state 初始化完畢。") # 日誌系統此時可能還未完全配置好

    # 2.5. 嘗試從 Colab Userdata 加載 API 金鑰 (在日誌系統初始化之前或之後均可，但需在 sidebar 渲染前)
    # logger is not fully configured yet here if we place it before log setup.
    # Using print for initial debug if needed, then switch to logger.
    # print("DEBUG: Attempting to load API keys from userdata...") # 臨時調試
    try:
        google_api_key = userdata.get('GOOGLE_API_KEY')
        fred_api_key = userdata.get('FRED_API_KEY')

        if google_api_key:
            st.session_state.gemini_api_key = google_api_key
            # print(f"DEBUG: Loaded GOOGLE_API_KEY from userdata (length: {len(google_api_key)}).") # 臨時調試
        else:
            # print("DEBUG: GOOGLE_API_KEY not found in userdata.") # 臨時調試
            pass # 保留 session_state 中可能已有的值或手動輸入的值

        if fred_api_key:
            st.session_state.fred_api_key = fred_api_key
            # print(f"DEBUG: Loaded FRED_API_KEY from userdata (length: {len(fred_api_key)}).") # 臨時調試
        else:
            # print("DEBUG: FRED_API_KEY not found in userdata.") # 臨時調試
            pass

    except Exception as e:
        # If userdata.get itself fails (e.g. if MockUserdata.SecretNotFoundError was raised and not caught by get)
        # print(f"DEBUG: Error accessing userdata: {e}") # 臨時調試
        st.warning(f"讀取 Colab Secrets 時發生錯誤: {e}")


    # 3. 初始化日誌系統
    # 在設定日誌之前，確保日誌目錄存在
    try:
        log_dir = os.path.dirname(COLAB_LOG_FILE_PATH)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            logging.info(f"主應用：日誌目錄 {log_dir} 已創建。")
    except Exception as e:
        # 即使創建目錄失敗，也嘗試繼續，logging 模組自身可能處理或拋出錯誤
        logging.error(f"主應用：創建日誌目錄 {log_dir} 失敗: {e}", exc_info=True)
        st.warning(f"無法自動創建日誌目錄 {log_dir}。如果日誌無法寫入，請手動創建該目錄。")

    # setup_logging 會返回 StreamlitLogHandler 的實例
    # streamlit_ui_log_key='ui_logs' 是預設值，這裡明確傳遞以保持清晰
    if 'log_handler' not in st.session_state or st.session_state.log_handler is None:
        # 傳遞日誌檔案路徑和 UI 日誌鍵給 setup_logging
        log_handler_instance = setup_logging(
            log_level=logging.INFO, # 可以根據需要調整應用級別的日誌級別
            log_file_path=COLAB_LOG_FILE_PATH,
            streamlit_ui_log_key='ui_logs'
        )
        st.session_state.log_handler = log_handler_instance
        # 日誌系統配置完成後的第一條日誌
        logging.getLogger(__name__).info("主應用：日誌系統和 StreamlitLogHandler 初始化完成。")
    else:
        # 如果 log_handler 已存在，通常意味著是在 rerun，不需要重新配置
        logging.getLogger(__name__).debug("主應用：日誌系統已存在於 session_state。")


    # 4. 加載和應用 CSS
    load_custom_css("style.css")

    active_theme_class = st.session_state.get("active_theme", "Light").lower()
    font_size_name = st.session_state.get("font_size_name", "Medium")
    font_size_css_map = st.session_state.get("font_size_css_map", {})
    font_class = font_size_css_map.get(font_size_name, "font-medium")

    st.markdown(f"<div class='theme-{active_theme_class} {font_class}'>", unsafe_allow_html=True)
    logger.debug(f"主應用：已應用主題 '{active_theme_class}' 和字體大小 '{font_class}' ({font_size_name}) 的包裹 div。")

    # --- 渲染核心組件 ---
    try:
        render_sidebar()
        render_main_page_content()
        render_chat()
        render_log_viewer() # log_viewer 現在從 st.session_state.ui_logs 讀取
    except Exception as e:
        logger.error(f"渲染核心組件時發生嚴重錯誤: {e}", exc_info=True)
        st.error(f"應用程式在渲染核心UI組件時遇到問題：{e}")
        st.error("請嘗試刷新頁面。如果問題持續，請檢查日誌或聯繫開發者。")

    st.markdown("</div>", unsafe_allow_html=True) # 關閉包裹 div
    logger.info("主應用：主要渲染流程結束。")


if __name__ == "__main__":
    # 獲取一個在 main() 之外的記錄器，用於捕獲 main() 本身的啟動錯誤
    # 這樣即使 setup_logging 失敗，我們仍有機會記錄到控制台
    bootstrap_logger = logging.getLogger("__bootstrap__")
    bootstrap_logger.setLevel(logging.INFO) # 確保能打印 INFO 級別的消息
    # 給 bootstrap_logger 添加一個基本的控制台處理器，以防 setup_logging 未成功執行
    if not bootstrap_logger.hasHandlers():
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
        bootstrap_logger.addHandler(ch)

    try:
        bootstrap_logger.info("應用程式啟動中 (執行 main())...")
        main()
    except Exception as e:
        bootstrap_logger.critical(f"應用程式啟動失敗 (在 __main__ 中捕獲到頂層異常): {e}", exc_info=True)
        try:
            st.error(f"""
            😞 應用程式啟動時發生嚴重錯誤 😞

            抱歉，應用程式在初始化階段遇到了一個無法恢復的問題，導致無法啟動。
            請檢查應用程式的後端日誌 (如果配置了檔案日誌，則檢查日誌檔案) 以獲取詳細的錯誤訊息。

            **錯誤概要:**
            類型: {type(e).__name__}
            訊息: {str(e)}

            如果問題持續，請聯繫技術支援。
            """)
        except Exception as st_render_error:
            bootstrap_logger.error(f"在顯示頂層錯誤訊息時，Streamlit 本身也發生錯誤: {st_render_error}", exc_info=True)
            print(f"CRITICAL ERROR during app startup (captured in __main__): {e}", file=sys.stderr)
            print(f"ADDITIONAL CRITICAL ERROR trying to display error in Streamlit: {st_render_error}", file=sys.stderr)
    finally:
        bootstrap_logger.info("應用程式執行完畢或已終止。")
