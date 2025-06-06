# components/sidebar.py
import streamlit as st
import logging
from config.api_keys_config import api_keys_info
from config.app_settings import available_models
from services.gemini_service import (
    create_gemini_cache,
    list_gemini_caches,
    delete_gemini_cache
)

logger = logging.getLogger(__name__)

def render_sidebar():
    """
    渲染應用程式的側邊欄。
    包含主題切換、字體大小調整、API金鑰管理、Gemini模型設定、
    主要提示詞設定、數據快取清除以及Gemini內容快取管理。
    """
    logger.info("側邊欄：開始渲染 (render_sidebar)。")
    st.sidebar.title("⚙️ 全域設定與工具")

    # --- 外觀主題與字體 ---
    st.sidebar.header("🎨 外觀主題與字體")
    active_theme = st.session_state.get("active_theme", "Light") # 默認為 Light
    # current_theme_label = "暗色模式 (Dark)" if active_theme == "Dark" else "亮色模式 (Light)"
    toggle_label = f"切換到 {'亮色模式' if active_theme == 'Dark' else '暗色模式'}"

    original_theme = st.session_state.active_theme

    # 使用 st.session_state.active_theme 直接作為 toggle 的 value
    # 如果 active_theme 是 'Dark'，toggle 應為 True
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
        st.rerun() # 使用 st.rerun() 替代 st.experimental_rerun()

    st.sidebar.caption(f"目前主題: {st.session_state.active_theme}")

    st.sidebar.markdown("##### 選擇字體大小:")
    font_size_options = list(st.session_state.get("font_size_css_map", {"Small": "", "Medium": "", "Large": ""}).keys())
    current_font_size_name = st.session_state.get("font_size_name", "Medium")

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

    # --- API 金鑰管理 ---
    st.sidebar.header("🔑 API 金鑰管理")
    st.sidebar.caption("請在此處管理您的 API 金鑰。")

    # 檢查 Gemini API 金鑰是否有效 (從 session_state 初始化後)
    # 這個檢查可以更通用，例如檢查 st.session_state 中是否有任何以 "gemini_api_key_" 開頭且有值的鍵
    has_valid_gemini_key = any(
        st.session_state.get(key_name, "") for key_name in api_keys_info.values() if "gemini" in key_name.lower() # 確保比較時大小寫不敏感
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
        # st.rerun() # 考慮是否需要，如果其他組件依賴於此處的即時更新

    # --- Gemini 模型設定 ---
    st.sidebar.header("🤖 Gemini 模型設定")
    st.sidebar.caption("選擇並配置要使用的 Gemini 模型。")

    old_selected_model = st.session_state.get("selected_model_name", available_models[0] if available_models else "")
    new_selected_model = st.sidebar.selectbox(
        "選擇 Gemini 模型:",
        options=available_models,
        index=available_models.index(old_selected_model) if old_selected_model in available_models else 0,
        key="sidebar_selected_model_name_selector"
    )
    if new_selected_model != old_selected_model:
        st.session_state.selected_model_name = new_selected_model
        logger.info(f"側邊欄：用戶選擇的 Gemini 模型更改為: '{new_selected_model}'")

    old_rpm = st.session_state.get("global_rpm_limit", 3)
    new_rpm = st.sidebar.number_input(
        "全域 RPM (每分鐘請求數):",
        min_value=1,
        value=old_rpm,
        step=1,
        key="sidebar_global_rpm_limit_input"
    )
    if new_rpm != old_rpm:
        st.session_state.global_rpm_limit = new_rpm
        logger.info(f"側邊欄：全域 RPM 上限更改為: {new_rpm}")

    old_tpm = st.session_state.get("global_tpm_limit", 100000)
    new_tpm = st.sidebar.number_input(
        "全域 TPM (每分鐘詞元數):",
        min_value=1000,
        value=old_tpm,
        step=10000,
        key="sidebar_global_tpm_limit_input"
    )
    if new_tpm != old_tpm:
        st.session_state.global_tpm_limit = new_tpm
        logger.info(f"側邊欄：全域 TPM 上限更改為: {new_tpm}")

    st.sidebar.caption("注意：請參考 Gemini 官方文件了解不同模型的具體 RPM/TPM 限制。")

    # --- 主要提示詞設定 ---
    st.sidebar.header("📝 主要提示詞")
    st.sidebar.caption("設定用於指導 Gemini 分析的主要提示詞。")

    old_prompt = st.session_state.get("main_gemini_prompt", "")
    new_prompt_text_area = st.sidebar.text_area(
        "主要分析提示詞 (System Prompt):",
        value=old_prompt,
        height=250,
        key="sidebar_main_gemini_prompt_input"
    )
    if new_prompt_text_area != old_prompt:
        st.session_state.main_gemini_prompt = new_prompt_text_area
        logger.info(f"側邊欄：主要 Gemini 提示詞已通過文本區域更新。新提示詞長度: {len(new_prompt_text_area)}")

    # --- 快取管理 ---
    st.sidebar.header("🧹 數據快取管理")
    st.sidebar.caption("管理應用程式的數據快取 (例如 yfinance, FRED)。")
    if st.sidebar.button("清除所有數據快取", key="sidebar_clear_all_data_cache_button"):
        st.cache_data.clear()
        logger.info("側邊欄：用戶點擊按鈕，所有 Streamlit 數據快取 (@st.cache_data) 已被清除。")
        st.sidebar.success("所有數據快取已成功清除！")
        # st.rerun()

    # --- Gemini 內容快取管理 ---
    st.sidebar.header("🧠 Gemini 內容快取")
    st.sidebar.caption("管理 Gemini API 的內容快取。")
    logger.debug("側邊欄：渲染 Gemini 內容快取管理區域。")

    valid_gemini_keys_for_cache_ops = [
        st.session_state.get(key_name) for key_name in api_keys_info.values()
        if "gemini" in key_name.lower() and st.session_state.get(key_name)
    ]
    gemini_api_key_for_cache = valid_gemini_keys_for_cache_ops[0] if valid_gemini_keys_for_cache_ops else None

    if not gemini_api_key_for_cache:
        logger.warning("側邊欄：無有效 Gemini API 金鑰，無法進行內容快取操作。")
        st.sidebar.warning("需要有效的 Gemini API 金鑰才能管理內容快取。請在上方設定。")
    else:
        logger.debug(f"側邊欄：使用 API 金鑰尾號 ...{gemini_api_key_for_cache[-4:]} 進行快取操作。")

        # 創建/更新快取
        # Inputs for cache creation
        old_cache_display_name = st.session_state.get("cache_display_name_input", "my_default_cache")
        new_cache_display_name = st.sidebar.text_input(
            "快取顯示名稱:", value=old_cache_display_name, key="sidebar_cache_display_name_input"
        )
        if new_cache_display_name != old_cache_display_name:
            st.session_state.cache_display_name_input = new_cache_display_name
            logger.debug(f"側邊欄：快取顯示名稱輸入更改為: '{new_cache_display_name}'")

        old_cache_content = st.session_state.get("cache_content_input", st.session_state.get("main_gemini_prompt",""))
        new_cache_content = st.sidebar.text_area(
            "快取內容 (例如系統提示詞):", value=old_cache_content, height=150, key="sidebar_cache_content_input"
        )
        if new_cache_content != old_cache_content:
            st.session_state.cache_content_input = new_cache_content
            logger.debug(f"側邊欄：快取內容輸入更改，長度: {len(new_cache_content)}")

        old_cache_ttl = st.session_state.get("cache_ttl_seconds_input", 3600)
        new_cache_ttl = st.sidebar.number_input(
            "快取 TTL (秒):", min_value=60, value=old_cache_ttl, step=60, key="sidebar_cache_ttl_input"
        )
        if new_cache_ttl != old_cache_ttl:
            st.session_state.cache_ttl_seconds_input = new_cache_ttl
            logger.debug(f"側邊欄：快取 TTL 輸入更改為: {new_cache_ttl} 秒")

        if st.sidebar.button("創建/更新內容快取", key="sidebar_create_update_cache_button"):
            logger.info("側邊欄：用戶點擊 '創建/更新內容快取' 按鈕。")
            if st.session_state.cache_display_name_input and st.session_state.cache_content_input:
                selected_model = st.session_state.get("selected_model_name")
                if not selected_model:
                    logger.error("側邊欄：無法創建快取，因為未選擇 Gemini 模型。")
                    st.sidebar.error("請先在上方選擇一個 Gemini 模型。")
                else:
                    logger.info(f"側邊欄：準備調用 create_gemini_cache。顯示名稱: '{st.session_state.cache_display_name_input}', 模型: '{selected_model}', TTL: {st.session_state.cache_ttl_seconds_input}")
                    with st.spinner("正在創建/更新快取..."):
                        cache_obj, error_msg = create_gemini_cache(
                            api_key=gemini_api_key_for_cache,
                            model_name=selected_model,
                            cache_display_name=st.session_state.cache_display_name_input,
                            system_instruction=st.session_state.cache_content_input,
                            ttl_seconds=st.session_state.cache_ttl_seconds_input
                        )
                        if error_msg:
                            logger.error(f"側邊欄：創建/更新快取失敗: {error_msg}")
                            st.sidebar.error(f"快取操作失敗: {error_msg}")
                        else:
                            logger.info(f"側邊欄：創建/更新快取成功。快取名稱: {cache_obj.name}, 顯示名稱: {cache_obj.display_name}")
                            st.sidebar.success(f"快取 '{cache_obj.display_name}' 已成功操作 (名稱: ...{cache_obj.name.split('/')[-1][-12:]})。")

                            logger.debug("側邊欄：創建/更新快取後，自動刷新快取列表。")
                            caches, err = list_gemini_caches(gemini_api_key_for_cache)
                            if not err:
                                st.session_state.gemini_caches_list = caches
                            else:
                                logger.error(f"側邊欄：刷新快取列表失敗: {err}")
                                st.sidebar.warning(f"刷新快取列表失敗: {err}")
            else:
                logger.warning("側邊欄：用戶嘗試創建/更新快取，但缺少顯示名稱或內容。")
                st.sidebar.warning("請提供快取顯示名稱和內容。")

        if st.sidebar.button("刷新/列出可用快取", key="sidebar_list_caches_button"):
            logger.info("側邊欄：用戶點擊 '刷新/列出可用快取' 按鈕。")
            with st.spinner("正在列出快取..."):
                caches, error_msg = list_gemini_caches(gemini_api_key_for_cache)
                if error_msg:
                    logger.error(f"側邊欄：列出快取失敗: {error_msg}")
                    st.sidebar.error(f"列出快取失敗: {error_msg}")
                    st.session_state.gemini_caches_list = []
                else:
                    st.session_state.gemini_caches_list = caches
                    logger.info(f"側邊欄：成功列出 {len(caches)} 個快取。")
                    if not caches:
                        st.sidebar.info("目前沒有可用的內容快取。")
                    else:
                        st.sidebar.success(f"找到 {len(caches)} 個快取。")

        if "gemini_caches_list" not in st.session_state:
            st.session_state.gemini_caches_list = []
            logger.debug("側邊欄：初始化空的 gemini_caches_list 到 session_state。")


        if st.session_state.get("gemini_caches_list"): # 檢查是否有快取可供選擇
            cache_options = {"(不使用快取)": None}
            for c in st.session_state.gemini_caches_list:
                if hasattr(c, 'display_name') and hasattr(c, 'name'):
                    cache_options[f"{c.display_name} (...{c.name.split('/')[-1][-12:]})"] = c.name
                else:
                    logger.warning(f"側邊欄：檢測到格式不正確的快取對象 {c}，已跳過。")

            current_selected_cache_name = st.session_state.get("selected_cache_for_generation", None)
            option_display_names = list(cache_options.keys())
            option_values = list(cache_options.values())

            try:
                current_index = option_values.index(current_selected_cache_name)
            except ValueError: # 如果當前選中的值不在選項中 (例如被刪除後)，則默認選第一個
                current_index = 0
                st.session_state.selected_cache_for_generation = option_values[0] # 更新 session_state
                logger.debug(f"側邊欄：之前選中的快取 '{current_selected_cache_name}' 無效，已重置為: {option_values[0]}")


            old_selected_cache_for_gen = st.session_state.get("selected_cache_for_generation")
            selected_display_key_for_gen = st.sidebar.selectbox(
                "選擇快取用於生成:",
                options=option_display_names,
                index=current_index,
                key="sidebar_select_cache_dropdown"
            )
            new_selected_cache_for_gen = cache_options[selected_display_key_for_gen]
            if new_selected_cache_for_gen != old_selected_cache_for_gen:
                st.session_state.selected_cache_for_generation = new_selected_cache_for_gen
                logger.info(f"側邊欄：用戶選擇用於生成的 Gemini 快取更改為: '{new_selected_cache_for_gen}' (顯示名: '{selected_display_key_for_gen}')")
        else:
            logger.debug("側邊欄：沒有可供選擇的內容快取。")
            st.sidebar.info("沒有可選擇的內容快取。請先創建或刷新列表。")

        old_cache_to_delete = st.session_state.get("cache_name_to_delete_input","")
        new_cache_to_delete = st.sidebar.text_input(
            "要刪除的快取名稱 (完整名稱):",
            value=old_cache_to_delete,
            key="sidebar_cache_name_to_delete_input"
        )
        if new_cache_to_delete != old_cache_to_delete:
             st.session_state.cache_name_to_delete_input = new_cache_to_delete
             logger.debug(f"側邊欄：待刪除快取名稱輸入更改為: '{new_cache_to_delete}'")


        if st.sidebar.button("刪除指定快取", key="sidebar_delete_cache_button"):
            cache_to_delete_name = st.session_state.cache_name_to_delete_input
            logger.info(f"側邊欄：用戶點擊 '刪除指定快取' 按鈕。目標快取: '{cache_to_delete_name}'")
            if cache_to_delete_name:
                with st.spinner(f"正在刪除快取 {cache_to_delete_name}..."):
                    success, error_msg = delete_gemini_cache(gemini_api_key_for_cache, cache_to_delete_name)
                    if error_msg:
                        logger.error(f"側邊欄：刪除快取 '{cache_to_delete_name}' 失敗: {error_msg}")
                        st.sidebar.error(f"刪除失敗: {error_msg}")
                    else:
                        logger.info(f"側邊欄：成功刪除快取 '{cache_to_delete_name}'。")
                        st.sidebar.success(f"快取 '{cache_to_delete_name}' 已成功刪除。")
                        if st.session_state.get("selected_cache_for_generation") == cache_to_delete_name:
                            st.session_state.selected_cache_for_generation = None
                            logger.info("側邊欄：已刪除的快取是當前選中用於生成的快取，已將其重置為 None。")

                        logger.debug("側邊欄：刪除快取後，自動刷新快取列表。")
                        caches, err = list_gemini_caches(gemini_api_key_for_cache)
                        if not err:
                            st.session_state.gemini_caches_list = caches
                        else:
                             logger.error(f"側邊欄：刷新快取列表失敗: {err}")
                             st.sidebar.warning(f"刷新快取列表失敗: {err}")
            else:
                logger.warning("側邊欄：用戶嘗試刪除快取，但未提供快取名稱。")
                st.sidebar.warning("請輸入要刪除的快取完整名稱。")

    logger.info("側邊欄：渲染完畢 (render_sidebar)。")

if __name__ == "__main__":
    # 此處的測試代碼需要一個正在運行的 Streamlit 環境和已初始化的 session_state
    # st.session_state.update({ ... 初始化 sidebar 需要的鍵 ...})
    # render_sidebar()
    pass
