# components/sidebar.py
import streamlit as st
import logging
import os
from config.api_keys_config import api_keys_info # Still needed for primary_gemini_key_name logic, though its utility is decreasing
# from config import app_settings # No longer importing the whole module
# from config.app_settings import DEFAULT_THEME, DEFAULT_FONT_SIZE_NAME, DEFAULT_CACHE_DISPLAY_NAME # These will come from ui_settings
from services.model_catalog import format_model_display_name # get_available_models will be removed
from services.gemini_service import (
    create_gemini_cache, # This service itself might be refactored or removed if cache ops move to backend
    list_gemini_caches,
    delete_gemini_cache
)

logger = logging.getLogger(__name__)

def _render_appearance_section():
    st.sidebar.header("🎨 外觀主題與字體")
    # Use ui_settings with a fallback to a static default if not found
    ui_settings = st.session_state.get("ui_settings", {})
    active_theme = st.session_state.get("active_theme", ui_settings.get("default_theme", "Light"))
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
    font_size_css_map_fallback = {"Small": "font-small", "Medium": "font-medium", "Large": "font-large"}
    font_size_options = list(st.session_state.get("font_size_css_map", ui_settings.get("font_size_css_map", font_size_css_map_fallback)).keys())
    current_font_size_name = st.session_state.get("font_size_name", ui_settings.get("default_font_size_name", "Medium"))

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
    # logger.info("側邊欄：渲染 API 金鑰管理部分。") # Kept for logging if needed
    st.sidebar.info(
        "API 金鑰現在統一由後端管理。\n"
        "請確保後端服務已正確配置所需金鑰 (例如，通過 .env 文件)。"
    )
    # The following code for direct API key input in the sidebar is now removed.
    # has_valid_gemini_key = any(
    #     st.session_state.get(key_name, "") for key_name in api_keys_info.values() if "gemini" in key_name.lower()
    # )
    # if not has_valid_gemini_key:
    #     logger.warning("側邊欄：未檢測到有效的 Gemini API 金鑰。")
    #     st.sidebar.warning("警告：至少需要一個有效的 Gemini API 金鑰才能使用 Gemini 分析功能。")

    # keys_updated_in_sidebar = False
    # for key_label, key_name_snake_case in api_keys_info.items():
    #     old_value = st.session_state.get(key_name_snake_case, "")
    #     new_value = st.sidebar.text_input(
    #         key_label, type="password", value=old_value, key=f"sidebar_{key_name_snake_case}_input"
    #     )
    #     if new_value != old_value:
    #         st.session_state[key_name_snake_case] = new_value
    #         logger.info(f"側邊欄：API 金鑰 '{key_label}' ({key_name_snake_case}) 已更新。新值長度: {len(new_value)} (0表示清空)")
    #         keys_updated_in_sidebar = True
    #         if "gemini" in key_name_snake_case.lower() and not new_value:
    #              logger.warning(f"側邊欄：Gemini API 金鑰 '{key_label}' 已被清空。")
    #         elif "gemini" in key_name_snake_case.lower() and new_value:
    #              logger.info(f"側邊欄：Gemini API 金鑰 '{key_label}' 已設定。")

    # if keys_updated_in_sidebar:
    #     logger.info("側邊欄：至少一個 API 金鑰被更新，顯示成功訊息。")
    #     st.sidebar.success("API 金鑰已更新並儲存在會話中。")
    st.sidebar.markdown("---") # Add separator if it was removed implicitly by removing other elements

def _render_gemini_model_settings_section():
    st.sidebar.header("🤖 Gemini 模型設定")
    st.sidebar.caption("選擇並配置要使用的 Gemini 模型。")

    # Since API keys are backend-managed, we assume if the app is running, keys are set.
    # The check for `current_api_key` might need to be re-evaluated or removed if
    # model fetching logic is also moved to backend or relies on backend's key status.
    # For now, we'll keep the logic that tries to fetch models,
    # assuming the backend will use its configured key.
    # If `get_available_models` is refactored to not need an explicit key from frontend,
    # then `current_api_key` here becomes less relevant for *this specific function call*.
    # However, other parts of the app might still use `st.session_state.gemini_api_key` if not fully refactored.
    # The task is to remove KEY INPUT and STORAGE in frontend session state from frontend sources.

    ui_settings = st.session_state.get("ui_settings", {})

    # Model selection now uses settings from backend via ui_settings
    available_models = ui_settings.get("available_gemini_models", []) # Expects a list of model name strings
    default_model = ui_settings.get("default_gemini_model", None)

    if not available_models:
        st.sidebar.warning("未能從後端獲取可用模型列表。請檢查後端設定。")
        # Provide a minimal fallback if absolutely necessary for UI rendering
        available_models = [default_model] if default_model else ["gemini-pro (備用)"]
        if not default_model: default_model = available_models[0]


    current_selected_model_name = st.session_state.get("selected_model_name", default_model)
    # Ensure current_selected_model_name is valid, otherwise reset to default
    if current_selected_model_name not in available_models:
        current_selected_model_name = default_model
        st.session_state.selected_model_name = current_selected_model_name # Persist the reset

    selected_model_name_from_sb = st.sidebar.selectbox(
        "選擇 Gemini 模型:",
        options=available_models, # List of model name strings
        index=available_models.index(current_selected_model_name) if current_selected_model_name in available_models else 0,
        key="sidebar_selected_model_name_selector", # Changed key to reflect it stores name now
        disabled=not bool(available_models)
    )

    if selected_model_name_from_sb and st.session_state.get("selected_model_name") != selected_model_name_from_sb:
        st.session_state.selected_model_name = selected_model_name_from_sb
        logger.info(f"側邊欄：用戶選擇的 Gemini 模型更改為: '{selected_model_name_from_sb}'")

    # RPM/TPM limits - defaults from ui_settings
    default_rpm = ui_settings.get("default_gemini_rpm_limit", 3)
    old_rpm = st.session_state.get("global_rpm_limit", default_rpm)
    new_rpm = st.sidebar.number_input(
        "全域 RPM (每分鐘請求數):", min_value=1, value=old_rpm, step=1, key="sidebar_global_rpm_limit_input"
    )
    if new_rpm != old_rpm:
        st.session_state.global_rpm_limit = new_rpm
        logger.info(f"側邊欄：全域 RPM 上限更改為: {new_rpm}")

    default_tpm = ui_settings.get("default_gemini_tpm_limit", 100000)
    old_tpm = st.session_state.get("global_tpm_limit", default_tpm)
    new_tpm = st.sidebar.number_input(
        "全域 TPM (每分鐘詞元數):", min_value=1000, value=old_tpm, step=10000, key="sidebar_global_tpm_limit_input"
    )
    if new_tpm != old_tpm:
        st.session_state.global_tpm_limit = new_tpm
        logger.info(f"側邊欄：全域 TPM 上限更改為: {new_tpm}")
    st.sidebar.caption("注意：RPM/TPM 設定為前端建議值，實際限制由後端執行。")

def _render_main_prompt_section():
    st.sidebar.header("📝 主要提示詞")
    st.sidebar.caption("設定用於指導 Gemini 分析的主要提示詞。")
    ui_settings = st.session_state.get("ui_settings", {})
    default_prompt_fallback = "請根據上下文和我的問題提供分析。" # Simple static fallback
    default_main_prompt = ui_settings.get("default_main_gemini_prompt", default_prompt_fallback)

    old_prompt = st.session_state.get("main_gemini_prompt", default_main_prompt)
    new_prompt_text_area = st.sidebar.text_area(
        "主要分析提示詞 (System Prompt):", value=old_prompt, height=250, key="sidebar_main_gemini_prompt_input"
    )
    if new_prompt_text_area != old_prompt:
        st.session_state.main_gemini_prompt = new_prompt_text_area
        logger.info(f"側邊欄：主要 Gemini 提示詞已通過文本區域更新。新提示詞長度: {len(new_prompt_text_area)}")

def _render_quick_prompts_section():
    st.sidebar.header("🚀 快捷提示詞載入")
    ui_settings = st.session_state.get("ui_settings", {})
    prompts_dir_from_settings = ui_settings.get("prompts_dir", "prompts") # Fallback to "prompts"

    st.sidebar.caption(f"從 '{prompts_dir_from_settings}' 文件夾快速載入預設提示詞模板。")
    prompt_files = []
    try:
        if os.path.exists(prompts_dir_from_settings) and os.path.isdir(prompts_dir_from_settings):
            prompt_files = [
                f for f in os.listdir(prompts_dir_from_settings)
                if f.endswith(".txt") and not f.startswith("agent_")
            ]
            if not prompt_files: # If no non-agent prompts, list all .txt files as fallback
                 prompt_files = [f for f in os.listdir(prompts_dir_from_settings) if f.endswith(".txt")]
        else:
            logger.warning(f"側邊欄：快捷提示詞目錄 '{prompts_dir_from_settings}' 不存在。")
    except Exception as e:
        logger.error(f"側邊欄：讀取快捷提示詞目錄 '{prompts_dir_from_settings}' 時出錯: {e}")
        st.sidebar.error(f"讀取提示詞目錄失敗: {e}")

    if not prompt_files:
        st.sidebar.info(f"在 '{prompts_dir_from_settings}' 目錄下未找到 .txt 格式的提示詞模板。")
    else:
        if "selected_prompt_template" not in st.session_state:
            st.session_state.selected_prompt_template = prompt_files[0] if prompt_files else None

        current_selection_index = 0
        if st.session_state.selected_prompt_template in prompt_files:
            current_selection_index = prompt_files.index(st.session_state.selected_prompt_template)

        selected_template = st.sidebar.selectbox(
            "選擇提示詞範本:", options=prompt_files,
            index=current_selection_index,
            key="sidebar_selected_prompt_template_selector"
        )
        st.session_state.selected_prompt_template = selected_template # Update session state with current selection

        if st.sidebar.button("載入選定提示詞", key="sidebar_load_selected_prompt_button"):
            if st.session_state.selected_prompt_template:
                file_path = os.path.join(prompts_dir_from_settings, st.session_state.selected_prompt_template)
                try:
                    with open(file_path, "r", encoding="utf-8") as f: content = f.read()
                    st.session_state.main_gemini_prompt = content # This updates the main prompt text area
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
    current_api_key = None # Placeholder, as key is not directly available from frontend input
    # The logic for `gemini_api_key_for_cache` needs to be re-evaluated.
    # Cache operations will likely need to be backend calls.
    # For now, this section might become non-functional or display a message.
    # OR, it could optimistically try, assuming backend has a key.

    # Let's assume cache operations will be refactored to backend calls.
    # So, we can disable or message this section for now.
    st.sidebar.info("內容快取管理功能正在調整以配合後端金鑰管理。")
    gemini_api_key_for_cache = None # Explicitly set to None

    if not gemini_api_key_for_cache: # This will always be true now, as gemini_api_key_for_cache is None
        st.sidebar.warning("內容快取管理目前已停用，因 API 金鑰及相關操作已移至後端或待重構。")
    else:
        # This 'else' block is currently unreachable due to gemini_api_key_for_cache being None.
        # If cache functionality is re-introduced via backend, this UI might be re-enabled.
        ui_settings = st.session_state.get("ui_settings", {})
        default_cache_name = ui_settings.get("default_cache_display_name", "my_cache")
        default_ttl = ui_settings.get("default_cache_ttl_seconds", 3600)

        old_cache_display_name = st.session_state.get("cache_display_name_input", default_cache_name)
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

        old_cache_ttl = st.session_state.get("cache_ttl_seconds_input", default_ttl)
        new_cache_ttl = st.sidebar.number_input(
            "快取 TTL (秒):", min_value=60, value=old_cache_ttl, step=60, key="sidebar_cache_ttl_input"
        )
        if new_cache_ttl != old_cache_ttl:
            st.session_state.cache_ttl_seconds_input = new_cache_ttl

        if st.sidebar.button("創建/更新內容快取 (已停用)", key="sidebar_create_update_cache_button", disabled=True):
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
