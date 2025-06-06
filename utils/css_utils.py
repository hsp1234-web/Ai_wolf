# utils/css_utils.py
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def load_custom_css(css_file_path: str = "style.css") -> None:
    """
    從指定路徑讀取 CSS 檔案並在 Streamlit 應用中應用它。

    Args:
        css_file_path (str): CSS 檔案的路徑。默認為 "style.css"。
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
        logger.error(f"CSS工具：加載 CSS 檔案 '{css_file_path}' 時發生錯誤: {type(e).__name__} - {str(e)}", exc_info=True)

def inject_dynamic_theme_css() -> None:
    """
    根據 session_state 中的 active_theme 注入包含主題類別的 div。
    這允許 CSS 根據主題動態更改應用程序的外觀。
    """
    active_theme = st.session_state.get("active_theme", "Light") # 默認為 Light 主題
    theme_class = "theme-light" if active_theme == "Light" else "theme-dark"

    # 使用 st.markdown 創建一個帶有動態類名的頂層 div
    # 這個 div 會包圍 Streamlit 應用的主要內容區域
    # 注意：Streamlit 的 HTML 結構可能會變化，這種方法依賴於當前的結構
    # 更穩健的方法可能是直接修改 body 的 class，但 Streamlit 不直接支持

    # 這裡我們注入一個隱藏的 div 來攜帶 class，然後 CSS 可以使用它
    # 例如: .theme-dark .stApp { background-color: #333; }
    # 或者直接應用於 st.markdown 自身，如果 CSS 是這樣設計的
    st.markdown(f"<div id='theme-injector' class='{theme_class}'></div>", unsafe_allow_html=True)

    # 為了讓CSS能全局應用，我們可能需要更複雜的注入，或者讓用戶的 style.css 直接包含這些主題類
    # 例如 style.css 包含:
    # .theme-light { --primary-color: #FFFFFF; --text-color: #000000; }
    # .theme-dark { --primary-color: #000000; --text-color: #FFFFFF; }
    # body { background-color: var(--primary-color); color: var(--text-color); }
    # st.markdown 會將樣式應用於其自身所在的塊，對於全局主題，CSS文件本身需要處理好選擇器
    logger.info(f"CSS工具：已注入動態主題 CSS 類別 '{theme_class}' (基於 session_state.active_theme='{active_theme}')。")


def inject_font_size_css() -> None:
    """
    根據 session_state 中的 font_size_name 注入對應的 CSS 類到一個 HTML 容器中。
    這允許 CSS 根據選擇的字體大小動態調整應用程序特定元素的字體。
    """
    font_size_name = st.session_state.get("font_size_name", "Medium") # 默認為 Medium
    # 從 config/app_settings.py 導入 font_size_css_map
    # 由於這是一個 util 函數，避免直接導入以減少循環依賴風險
    # 更好的做法是將 font_size_css_map 作為參數傳遞或從 st.session_state 獲取 (如果已存儲)

    # 假設 font_size_css_map 已在 app.py 中加載到 session_state
    font_size_css_map = st.session_state.get("font_size_css_map", {
        "Small": "font-small",
        "Medium": "font-medium",
        "Large": "font-large",
    })

    font_class = font_size_css_map.get(font_size_name, "font-medium")

    # 與主題注入類似，我們注入一個帶有類別的 div
    # CSS 中應定義如 .font-small, .font-medium, .font-large 樣式
    st.markdown(f"<div id='font-size-injector' class='{font_class}'></div>", unsafe_allow_html=True)
    logger.info(f"CSS工具：已注入動態字體大小 CSS 類別 '{font_class}' (基於 session_state.font_size_name='{font_size_name}')。")

# 注意:
# inject_dynamic_theme_css 和 inject_font_size_css 的有效性
# 高度依賴於 style.css 文件中如何定義這些類別 (如 .theme-dark, .font-large)
# 以及這些類別如何影響 Streamlit 生成的 HTML 元素。
# 例如，style.css 可能需要如下規則：
#
# body.theme-dark {
#   background-color: #2e2e2e;
#   color: #ffffff;
# }
# .font-large .stTextInput input, .font-large .stTextArea textarea {
#   font-size: 1.2em;
# }
#
# Streamlit 的 st.markdown("<style>...", unsafe_allow_html=True) 是添加全局樣式的標準方法。
# 上述函數通過 markdown 注入帶 class 的 div，是為了讓 CSS 可以基於這些 class 應用樣式。
# 如果 style.css 本身就能根據 Streamlit 的內建結構或 st.session_state (如果CSS能訪問) 來調整，
# 則這些注入函數可能需要調整。
# 目前的實現是提供一個可供CSS選擇器使用的目標。
