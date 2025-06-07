# app.py (替換整個檔案)
import streamlit as st
import logging
import sys
import os # 引入 os 以便處理路徑

# --- 模組化導入 ---
from utils.log_utils import setup_logging
from utils.session_state_manager import initialize_session_state
from utils.css_utils import load_custom_css, apply_dynamic_css # 導入新的函數

from components.sidebar import render_sidebar
from components.main_page import render_main_page_content
from components.chat_interface import render_chat
from components.log_display import render_log_viewer
from config import app_settings # Import app_settings

# --- 定義日誌檔案路徑 ---
IN_COLAB = 'google.colab' in sys.modules
if IN_COLAB:
    # For Colab, construct path using COLAB_DRIVE_BASE_PATH and BASE_DATA_DIR_NAME
    BASE_DATA_DIR = os.path.join(
        app_settings.COLAB_DRIVE_BASE_PATH,
        app_settings.BASE_DATA_DIR_NAME
    )
else:
    # For local, construct path using USER_HOME_DIR and BASE_DATA_DIR_NAME
    BASE_DATA_DIR = os.path.join(
        os.path.expanduser(app_settings.USER_HOME_DIR),
        app_settings.BASE_DATA_DIR_NAME
    )

APP_LOG_DIR = os.path.join(BASE_DATA_DIR, app_settings.APP_LOG_DIR_NAME)
APP_LOG_FILE_PATH = os.path.join(APP_LOG_DIR, "streamlit.log") # Filename can also be a constant

# --- 全局日誌記錄器 ---
logger = logging.getLogger(__name__)

def main():
    """
    應用程式主函數。
    """
    # 1. 設定頁面配置
    st.set_page_config(page_title=app_settings.APP_NAME, layout="wide")

    # 2. 初始化 Session State (包括 API 金鑰的 Colab Secrets 讀取邏輯)
    initialize_session_state()

    # 2.1 確保日誌目錄存在
    if not os.path.exists(APP_LOG_DIR):
        try:
            os.makedirs(APP_LOG_DIR, exist_ok=True)
            # 使用 logging 記錄此信息，而不是 print
            # logger.info(f"日誌目錄 {APP_LOG_DIR} 已創建。") # 注意：此時 logger 可能還未完全配置 FileHandler
        except Exception as e:
            # logger.error(f"創建日誌目錄 {APP_LOG_DIR} 失敗: {e}") # 同上
            # 打印到 stderr 以便在啟動早期階段可見
            print(f"Warning: Failed to create log directory {APP_LOG_DIR}: {str(e)}", file=sys.stderr)


    # 3. 初始化日誌系統
    if 'log_handler' not in st.session_state or st.session_state.log_handler is None:
        log_handler_instance = setup_logging(
            log_level=logging.INFO,
            log_file_path=APP_LOG_FILE_PATH,
            streamlit_ui_log_key='ui_logs'
        )
        st.session_state.log_handler = log_handler_instance
        logging.getLogger(__name__).info(f"主應用: 日誌系統初始化完成. 日誌將寫入至 {APP_LOG_FILE_PATH}")
    else:
        logging.getLogger(__name__).debug("主應用: 日誌系統已存在於 session_state.")

    # 4. 加載和應用 CSS
    load_custom_css("style.css")
    apply_dynamic_css()

    # --- 導入引導頁面渲染函數 ---
    from components.onboarding_page import render_onboarding_page

    # --- 引導流程 ---
    if not st.session_state.get("setup_complete", False):
        render_onboarding_page()
    else:
        # --- 渲染核心組件 ---
        try:
            render_sidebar()
            render_main_page_content()
            render_chat()
            render_log_viewer()
        except Exception as e:
            logger.error(f"渲染核心組件時發生嚴重錯誤: {str(e)}", exc_info=True)
        st.error(f"應用程式在渲染核心UI組件時遇到問題: {str(e)}")
        st.error("請嘗試刷新頁面. 如果問題持續, 請檢查日誌或聯繫開發者.")

    logger.info("主應用: 主要渲染流程結束.")

if __name__ == "__main__":
    bootstrap_logger = logging.getLogger("__bootstrap__")
    if not bootstrap_logger.hasHandlers():
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - [%(funcName)s:%(lineno)d] - %(message)s'))
        bootstrap_logger.addHandler(ch)
        bootstrap_logger.setLevel(logging.INFO)

    try:
        bootstrap_logger.info("應用程式啟動中 (執行 main())...")
        main()
    except Exception as e:
        bootstrap_logger.critical(f"應用程式啟動失敗 (在 __main__ 中捕獲到頂層異常): {str(e)}", exc_info=True)
        try:
            st.error(f"""
            應用程式啟動時發生嚴重錯誤.

            抱歉, 應用程式在初始化階段遇到了一個無法恢復的問題, 導致無法啟動.
            請檢查應用程式的後端日誌 (如果配置了檔案日誌, 則檢查日誌檔案) 或 Colab 的輸出以獲取詳細的錯誤訊息.

            錯誤概要:
            類型: {type(e).__name__}
            訊息: {str(e)}

            如果問題持續, 請聯繫技術支援.
            """)
        except Exception as st_render_error:
            bootstrap_logger.error(f"在顯示頂層錯誤訊息時, Streamlit 本身也發生錯誤: {str(st_render_error)}", exc_info=True)
            print(f"CRITICAL ERROR during app startup (captured in __main__): {str(e)}", file=sys.stderr)
            print(f"ADDITIONAL CRITICAL ERROR trying to display error in Streamlit: {str(st_render_error)}", file=sys.stderr)
    finally:
        bootstrap_logger.info("應用程式執行完畢或已終止.")
