# components/sidebar.py
import streamlit as st
import logging
import os
from config.api_keys_config import api_keys_info
from config import app_settings # Import app_settings
from config.app_settings import DEFAULT_THEME, DEFAULT_FONT_SIZE_NAME, DEFAULT_CACHE_DISPLAY_NAME # Import specific settings
from services.model_catalog import get_available_models, format_model_display_name
from services.gemini_service import (
    create_gemini_cache,
    list_gemini_caches,
    delete_gemini_cache
)

logger = logging.getLogger(__name__)

def _render_appearance_section():
    st.sidebar.header("🎨 外觀主題與字體")
    active_theme = st.session_state.get("active_theme", app_settings.DEFAULT_THEME)
    toggle_label = f"切換到 {'亮色模式' if active_theme == 'Dark' else '暗色模式'}"
    original_theme = st.session_state.active_theme

    new_toggle_state_is_dark = st.sidebar.toggle(
        toggle_label,
        value=(active_theme == "Dark"),
        key="theme_toggle_widget",
        help="點擊切換亮暗主題"
    )

    theme_changed = False
    if new_toggle_state_is_dark and original_theme == "Light":
        st.session_state.active_theme = "Dark"
        theme_changed = True
    elif not new_toggle_state_is_dark and original_theme == "Dark":
        st.session_state.active_theme = "Light"
        theme_changed = True

    if theme_changed:
        logger.info(f"主題已切換。原主題: {original_theme}, 新主題: {st.session_state.active_theme}")
        st.rerun()

    st.sidebar.caption(f"目前主題: {st.session_state.active_theme}")

    st.sidebar.markdown("##### 選擇字體大小:")
    font_size_options = list(st.session_state.get("font_size_css_map", app_settings.FONT_SIZE_CSS_MAP).keys())
    current_font_size_name = st.session_state.get("font_size_name", app_settings.DEFAULT_FONT_SIZE_NAME)

    selected_font_size_name = st.sidebar.radio(
        "字體大小:",
        options=font_size_options,
        index=font_size_options.index(current_font_size_name) if current_font_size_name in font_size_options else 1,
        key="font_size_radio",
        horizontal=True
    )
    if selected_font_size_name != current_font_size_name:
        st.session_state.font_size_name = selected_font_size_name
        logger.info(f"側邊欄：用戶更改字體大小為 '{selected_font_size_name}'。")
        st.rerun()
    st.sidebar.caption(f"目前字體: {st.session_state.font_size_name}")
    st.sidebar.markdown("---")

def _render_api_keys_section():
    st.sidebar.header("🔑 API 金鑰管理")
    st.sidebar.caption("請在此處管理您的 API 金鑰。")
    has_valid_gemini_key = any(
        st.session_state.get(key_name, "") for key_name in api_keys_info.values() if "gemini" in key_name.lower()
    )
    if not has_valid_gemini_key:
        logger.warning("側邊欄：未檢測到有效的 Gemini API 金鑰。")
        st.sidebar.warning("警告：至少需要一個有效的 Gemini API 金鑰才能使用 Gemini 分析功能。")

    keys_updated_in_sidebar = False
    for key_label, key_name_snake_case in api_keys_info.items():
        old_value = st.session_state.get(key_name_snake_case, "")
        new_value = st.sidebar.text_input(
            key_label, type="password", value=old_value, key=f"sidebar_{key_name_snake_case}_input"
        )
        if new_value != old_value:
            st.session_state[key_name_snake_case] = new_value
            logger.info(f"側邊欄：API 金鑰 '{key_label}' ({key_name_snake_case}) 已更新。新值長度: {len(new_value)} (0表示清空)")
            keys_updated_in_sidebar = True
            if "gemini" in key_name_snake_case.lower() and not new_value:
                 logger.warning(f"側邊欄：Gemini API 金鑰 '{key_label}' 已被清空。")
            elif "gemini" in key_name_snake_case.lower() and new_value:
                 logger.info(f"側邊欄：Gemini API 金鑰 '{key_label}' 已設定。")

    if keys_updated_in_sidebar:
        logger.info("側邊欄：至少一個 API 金鑰被更新，顯示成功訊息。")
        st.sidebar.success("API 金鑰已更新並儲存在會話中。")

def _render_gemini_model_settings_section():
    st.sidebar.header("🤖 Gemini 模型設定")
    st.sidebar.caption("選擇並配置要使用的 Gemini 模型。")

    primary_gemini_key_label = api_keys_info.get('Google Gemini API Key 1', 'GOOGLE_API_KEY_PRIMARY')
    current_api_key = st.session_state.get(primary_gemini_key_label, "")

    options_for_model_selector = []
    current_selected_model_object = None
    can_fetch_models = st.session_state.get("setup_complete", False) and current_api_key

    if can_fetch_models:
        with st.spinner("正在獲取可用模型列表..."):
            dynamic_models = get_available_models(api_key=current_api_key)
        if dynamic_models:
            options_for_model_selector = dynamic_models
            current_model_name_in_session = st.session_state.get("selected_model_name")
            if current_model_name_in_session:
                for model_obj in dynamic_models:
                    if model_obj.name == current_model_name_in_session:
                        current_selected_model_object = model_obj
                        break
            if not current_selected_model_object and dynamic_models:
                current_selected_model_object = dynamic_models[0]
                if st.session_state.get("selected_model_name") != current_selected_model_object.name:
                    st.session_state.selected_model_name = current_selected_model_object.name
                    logger.info(f"側邊欄：預設/回退模型設定為: '{current_selected_model_object.name}'")
        elif current_api_key:
            st.sidebar.warning("未能從 API 獲取模型列表。請檢查金鑰權限或稍後重試。")
    else:
        if not st.session_state.get("setup_complete", False):
            st.sidebar.info("請先完成初始設定以載入模型列表。")
        elif not current_api_key:
            st.sidebar.warning("需要有效的 Gemini API Key 才能載入模型列表。")

    selected_model_object_from_sb = st.sidebar.selectbox(
        "選擇 Gemini 模型:",
        options=options_for_model_selector,
        format_func=format_model_display_name,
        index=options_for_model_selector.index(current_selected_model_object) if current_selected_model_object and options_for_model_selector and current_selected_model_object in options_for_model_selector else 0,
        key="sidebar_selected_model_object_selector",
        disabled=not bool(options_for_model_selector)
    )

    if selected_model_object_from_sb and \
       st.session_state.get("selected_model_name") != selected_model_object_from_sb.name:
        st.session_state.selected_model_name = selected_model_object_from_sb.name
        logger.info(f"側邊欄：用戶選擇的 Gemini 模型更改為: '{selected_model_object_from_sb.name}'")

    old_rpm = st.session_state.get("global_rpm_limit", app_settings.DEFAULT_GEMINI_RPM_LIMIT)
    new_rpm = st.sidebar.number_input(
        "全域 RPM (每分鐘請求數):", min_value=1, value=old_rpm, step=1, key="sidebar_global_rpm_limit_input"
    )
    if new_rpm != old_rpm:
        st.session_state.global_rpm_limit = new_rpm
        logger.info(f"側邊欄：全域 RPM 上限更改為: {new_rpm}")

    old_tpm = st.session_state.get("global_tpm_limit", app_settings.DEFAULT_GEMINI_TPM_LIMIT)
    new_tpm = st.sidebar.number_input(
        "全域 TPM (每分鐘詞元數):", min_value=1000, value=old_tpm, step=10000, key="sidebar_global_tpm_limit_input"
    )
    if new_tpm != old_tpm:
        st.session_state.global_tpm_limit = new_tpm
        logger.info(f"側邊欄：全域 TPM 上限更改為: {new_tpm}")
    st.sidebar.caption("注意：請參考 Gemini 官方文件了解不同模型的具體 RPM/TPM 限制。")

def _render_main_prompt_section():
    st.sidebar.header("📝 主要提示詞")
    st.sidebar.caption("設定用於指導 Gemini 分析的主要提示詞。")
    old_prompt = st.session_state.get("main_gemini_prompt", app_settings.DEFAULT_MAIN_GEMINI_PROMPT)
    new_prompt_text_area = st.sidebar.text_area(
        "主要分析提示詞 (System Prompt):", value=old_prompt, height=250, key="sidebar_main_gemini_prompt_input"
    )
    if new_prompt_text_area != old_prompt:
        st.session_state.main_gemini_prompt = new_prompt_text_area
        logger.info(f"側邊欄：主要 Gemini 提示詞已通過文本區域更新。新提示詞長度: {len(new_prompt_text_area)}")

def _render_quick_prompts_section():
    st.sidebar.header("🚀 快捷提示詞載入")
    st.sidebar.caption(f"從 '{app_settings.PROMPTS_DIR}' 文件夾快速載入預設提示詞模板。")
    prompt_files = []
    try:
        if os.path.exists(app_settings.PROMPTS_DIR) and os.path.isdir(app_settings.PROMPTS_DIR):
            prompt_files = [
                f for f in os.listdir(app_settings.PROMPTS_DIR)
                if f.endswith(".txt") and not f.startswith("agent_")
            ]
            if not prompt_files:
                 prompt_files = [f for f in os.listdir(app_settings.PROMPTS_DIR) if f.endswith(".txt")]
        else:
            logger.warning(f"側邊欄：快捷提示詞目錄 '{app_settings.PROMPTS_DIR}' 不存在。")
    except Exception as e:
        logger.error(f"側邊欄：讀取快捷提示詞目錄 '{app_settings.PROMPTS_DIR}' 時出錯: {e}")
        st.sidebar.error(f"讀取提示詞目錄失敗: {e}")

    if not prompt_files:
        st.sidebar.info(f"在 '{app_settings.PROMPTS_DIR}' 目錄下未找到 .txt 格式的提示詞模板。")
    else:
        if "selected_prompt_template" not in st.session_state:
            st.session_state.selected_prompt_template = prompt_files[0] if prompt_files else None
        selected_template = st.sidebar.selectbox(
            "選擇提示詞範本:", options=prompt_files,
            index=prompt_files.index(st.session_state.selected_prompt_template) if st.session_state.selected_prompt_template in prompt_files else 0,
            key="sidebar_selected_prompt_template_selector"
        )
        st.session_state.selected_prompt_template = selected_template
        if st.sidebar.button("載入選定提示詞", key="sidebar_load_selected_prompt_button"):
            if st.session_state.selected_prompt_template:
                file_path = os.path.join(app_settings.PROMPTS_DIR, st.session_state.selected_prompt_template)
                try:
                    with open(file_path, "r", encoding="utf-8") as f: content = f.read()
                    st.session_state.main_gemini_prompt = content
                    logger.info(f"側邊欄：已從 '{file_path}' 載入提示詞到主要提示詞區域。")
                    st.sidebar.success(f"提示詞 '{st.session_state.selected_prompt_template}' 已載入！")
                except FileNotFoundError:
                    logger.error(f"側邊欄：嘗試載入提示詞失敗，文件未找到: {file_path}")
                    st.sidebar.error(f"錯誤：文件 '{st.session_state.selected_prompt_template}' 未找到。")
                except Exception as e:
                    logger.error(f"側邊欄：讀取提示詞文件 '{file_path}' 時出錯: {e}")
                    st.sidebar.error(f"讀取文件失敗: {e}")
            else:
                st.sidebar.warning("請先選擇一個提示詞模板。")
    st.sidebar.markdown("---")

def _render_data_cache_section():
    st.sidebar.header("🧹 數據快取管理")
    st.sidebar.caption("管理應用程式的數據快取 (例如 yfinance, FRED)。")
    if st.sidebar.button("清除所有數據快取", key="sidebar_clear_all_data_cache_button"):
        st.cache_data.clear()
        logger.info("側邊欄：用戶點擊按鈕，所有 Streamlit 數據快取 (@st.cache_data) 已被清除。")
        st.sidebar.success("所有數據快取已成功清除！")

def _render_gemini_cache_management_section():
    st.sidebar.header("🧠 Gemini 內容快取")
    st.sidebar.caption("管理 Gemini API 的內容快取。")
    valid_gemini_keys_for_cache_ops = [
        st.session_state.get(key_name) for key_name in api_keys_info.values()
        if "gemini" in key_name.lower() and st.session_state.get(key_name)
    ]
    gemini_api_key_for_cache = valid_gemini_keys_for_cache_ops[0] if valid_gemini_keys_for_cache_ops else None

    if not gemini_api_key_for_cache:
        st.sidebar.warning("需要有效的 Gemini API 金鑰才能管理內容快取。請在上方設定。")
    else:
        old_cache_display_name = st.session_state.get("cache_display_name_input", app_settings.DEFAULT_CACHE_DISPLAY_NAME)
        new_cache_display_name = st.sidebar.text_input(
            "快取顯示名稱:", value=old_cache_display_name, key="sidebar_cache_display_name_input"
        )
        if new_cache_display_name != old_cache_display_name:
            st.session_state.cache_display_name_input = new_cache_display_name

        old_cache_content = st.session_state.get("cache_content_input", st.session_state.get("main_gemini_prompt",""))
        new_cache_content = st.sidebar.text_area(
            "快取內容 (例如系統提示詞):", value=old_cache_content, height=150, key="sidebar_cache_content_input"
        )
        if new_cache_content != old_cache_content:
            st.session_state.cache_content_input = new_cache_content

        old_cache_ttl = st.session_state.get("cache_ttl_seconds_input", app_settings.DEFAULT_CACHE_TTL_SECONDS)
        new_cache_ttl = st.sidebar.number_input(
            "快取 TTL (秒):", min_value=60, value=old_cache_ttl, step=60, key="sidebar_cache_ttl_input"
        )
        if new_cache_ttl != old_cache_ttl:
            st.session_state.cache_ttl_seconds_input = new_cache_ttl

        if st.sidebar.button("創建/更新內容快取", key="sidebar_create_update_cache_button"):
            if st.session_state.cache_display_name_input and st.session_state.cache_content_input:
                selected_model = st.session_state.get("selected_model_name")
                if not selected_model:
                    st.sidebar.error("請先在上方選擇一個 Gemini 模型。")
                else:
                    with st.spinner("正在創建/更新快取..."):
                        cache_obj, error_msg = create_gemini_cache(
                            api_key=gemini_api_key_for_cache, model_name=selected_model,
                            cache_display_name=st.session_state.cache_display_name_input,
                            system_instruction=st.session_state.cache_content_input,
                            ttl_seconds=st.session_state.cache_ttl_seconds_input
                        )
                        if error_msg: st.sidebar.error(f"快取操作失敗: {error_msg}")
                        else:
                            st.sidebar.success(f"快取 '{cache_obj.display_name}' 已成功操作。")
                            caches, err = list_gemini_caches(gemini_api_key_for_cache)
                            if not err: st.session_state.gemini_caches_list = caches
                            else: st.sidebar.warning(f"刷新快取列表失敗: {err}")
            else:
                st.sidebar.warning("請提供快取顯示名稱和內容。")

        if st.sidebar.button("刷新/列出可用快取", key="sidebar_list_caches_button"):
            with st.spinner("正在列出快取..."):
                caches, error_msg = list_gemini_caches(gemini_api_key_for_cache)
                if error_msg:
                    st.sidebar.error(f"列出快取失敗: {error_msg}")
                    st.session_state.gemini_caches_list = []
                else:
                    st.session_state.gemini_caches_list = caches
                    st.sidebar.success(f"找到 {len(caches)} 個快取。" if caches else "目前沒有可用的內容快取。")

        if st.session_state.get("gemini_caches_list"):
            cache_options = {"(不使用快取)": None}
            for c in st.session_state.gemini_caches_list:
                if hasattr(c, 'display_name') and hasattr(c, 'name'):
                    cache_options[f"{c.display_name} (...{c.name.split('/')[-1][-12:]})"] = c.name

            current_selected_cache_name = st.session_state.get("selected_cache_for_generation", None)
            option_display_names = list(cache_options.keys())
            option_values = list(cache_options.values())
            try:
                current_index = option_values.index(current_selected_cache_name)
            except ValueError:
                current_index = 0
                st.session_state.selected_cache_for_generation = option_values[0]

            selected_display_key_for_gen = st.sidebar.selectbox(
                "選擇快取用於生成:", options=option_display_names, index=current_index, key="sidebar_select_cache_dropdown"
            )
            new_selected_cache_for_gen = cache_options[selected_display_key_for_gen]
            if new_selected_cache_for_gen != st.session_state.get("selected_cache_for_generation"):
                st.session_state.selected_cache_for_generation = new_selected_cache_for_gen
        else:
            st.sidebar.info("沒有可選擇的內容快取。")

        old_cache_to_delete = st.session_state.get("cache_name_to_delete_input","")
        new_cache_to_delete = st.sidebar.text_input(
            "要刪除的快取名稱 (完整名稱):", value=old_cache_to_delete, key="sidebar_cache_name_to_delete_input"
        )
        if new_cache_to_delete != old_cache_to_delete:
             st.session_state.cache_name_to_delete_input = new_cache_to_delete

        if st.sidebar.button("刪除指定快取", key="sidebar_delete_cache_button"):
            cache_to_delete_name = st.session_state.cache_name_to_delete_input
            if cache_to_delete_name:
                with st.spinner(f"正在刪除快取 {cache_to_delete_name}..."):
                    success, error_msg = delete_gemini_cache(gemini_api_key_for_cache, cache_to_delete_name)
                    if error_msg: st.sidebar.error(f"刪除失敗: {error_msg}")
                    else:
                        st.sidebar.success(f"快取 '{cache_to_delete_name}' 已成功刪除。")
                        if st.session_state.get("selected_cache_for_generation") == cache_to_delete_name:
                            st.session_state.selected_cache_for_generation = None
                        caches, err = list_gemini_caches(gemini_api_key_for_cache)
                        if not err: st.session_state.gemini_caches_list = caches
                        else: st.sidebar.warning(f"刷新快取列表失敗: {err}")
            else:
                st.sidebar.warning("請輸入要刪除的快取完整名稱。")

def render_sidebar():
    """
    渲染應用程式的側邊欄。
    通過調用各個獨立的渲染函數來組織側邊欄的內容。
    """
    logger.info("側邊欄：開始渲染 (render_sidebar)。")
    st.sidebar.title("⚙️ 全域設定與工具")

    _render_appearance_section()
    _render_api_keys_section()
    _render_gemini_model_settings_section()
    _render_main_prompt_section()
    _render_quick_prompts_section()
    _render_data_cache_section()
    _render_gemini_cache_management_section()

    logger.info("側邊欄：渲染完畢 (render_sidebar)。")

if __name__ == "__main__":
    pass
