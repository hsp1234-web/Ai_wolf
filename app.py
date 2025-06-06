# app.py (新的主應用程式檔案)
import streamlit as st
import logging
import sys

# --- 模組化導入 ---
from utils.log_utils import StreamlitLogHandler, setup_logging # StreamlitLogHandler is imported but instance is created in setup_logging
from utils.session_state_manager import initialize_session_state
from utils.css_utils import load_custom_css # Removed inject_dynamic_theme_css, inject_font_size_css as they are handled differently now

from components.sidebar import render_sidebar
from components.main_page import render_main_page_content
from components.chat_interface import render_chat
from components.log_display import render_log_viewer

# --- 定義日誌檔案路徑 (Colab 環境) ---
# 這個路徑需要在 Colab Cell 1 中通過 !mkdir -p GDRIVE_PROJECT_DIR/logs 創建
# GDRIVE_PROJECT_DIR 通常是 /content/drive/MyDrive/wolfAI
COLAB_LOG_FILE_PATH = "/content/drive/MyDrive/wolfAI/logs/streamlit.log"

# --- 全局日誌記錄器 ---
logger = logging.getLogger(__name__)

def main():
    """
    應用程式主函數。
    """
    # 1. 設定頁面配置 (必須是第一個 Streamlit 命令)
    st.set_page_config(
        page_title="金融分析與洞察助理 (Gemini Pro驅動)",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/LinWolf/Gemini_Financial_Analysis_Assistant/issues',
            'Report a bug': "https://github.com/LinWolf/Gemini_Financial_Analysis_Assistant/issues",
            'About': """
            ## 金融分析與洞察助理 (Gemini Pro 驅動)
            版本 2.1 (日誌系統增強)
            此應用程式使用 Google Gemini API 進行高級金融數據分析和生成洞察。
            由 LinWolf (https://github.com/LinWolf) 開發。
            """
        }
    )

    # 2. 初始化 Session State (包含 ui_logs 的初始化)
    # 這次先調用 initialize_session_state，確保 'ui_logs' 鍵在 setup_logging 之前已存在且為列表。
    # StreamlitLogHandler 的 __init__ 也會嘗試初始化，但先做更保險。
    initialize_session_state()
    # logger.info("主應用：Session state 初始化完畢。") # 日誌系統此時可能還未完全配置好

    # 3. 初始化日誌系統
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
