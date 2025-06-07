# utils/css_utils.py (替換整個檔案)
import streamlit as st
import logging
from config.app_settings import DEFAULT_CSS_FILE, DEFAULT_THEME, DEFAULT_FONT_SIZE_NAME # Import specific settings

logger = logging.getLogger(__name__)

def load_custom_css(css_file_path: str = app_settings.DEFAULT_CSS_FILE) -> None:
    """
    從指定路徑讀取 CSS 檔案並在 Streamlit 應用中應用它。
    """
    logger.info(f"CSS工具：開始加載自定義 CSS 檔案: '{css_file_path}'。")
    try:
        with open(css_file_path) as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        logger.info(f"CSS工具：成功加載並應用了自定義 CSS 檔案: '{css_file_path}'。")
    except FileNotFoundError:
        logger.warning(f"CSS工具：CSS 檔案 '{css_file_path}' 未找到。將跳過自定義 CSS 加載。")
    except Exception as e:
        logger.error(f"CSS工具：加載 CSS 檔案 '{css_file_path}' 時發生錯誤: {e}", exc_info=True)


def apply_dynamic_css() -> None:
    """
    根據 session_state 注入動態 CSS，以控制主題和字體大小。
    這是透過直接注入 <style> 標籤來修改 body 的 class 來實現的，更為穩健。
    """
    active_theme = st.session_state.get("active_theme", app_settings.DEFAULT_THEME)
    font_size_name = st.session_state.get("font_size_name", app_settings.DEFAULT_FONT_SIZE_NAME)
    font_size_css_map = st.session_state.get("font_size_css_map", {}) # Assuming FONT_SIZE_CSS_MAP is already in session_state from initializer
    font_class = font_size_css_map.get(font_size_name, "font-medium") # Fallback class if name not in map
    theme_class = "theme-dark" if active_theme == "Dark" else "theme-light"

    # 使用 JavaScript 動態地為 body 添加或刪除 class
    # 這是比注入 div 更可靠的方式
    js_code = f"""
    <script>
    document.body.classList.remove('theme-light', 'theme-dark', 'font-small', 'font-medium', 'font-large');
    document.body.classList.add('{theme_class}');
    document.body.classList.add('{font_class}');
    </script>
    """
    st.components.v1.html(js_code, height=0)
    logger.info(f"CSS工具：已應用動態主題 '{theme_class}' 和字體 '{font_class}'。")
