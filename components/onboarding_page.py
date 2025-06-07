# components/onboarding_page.py
import streamlit as st
import logging
from config.api_keys_config import api_keys_info
# from config.app_settings import available_models # No longer needed here
from services.model_catalog import get_available_models, format_model_display_name

logger = logging.getLogger(__name__)

def render_onboarding_page():
    """
    渲染引導頁面，用於首次設定 API 金鑰和核心模型。
    """
    st.title("歡迎使用 Ai_wolf！請先完成設定。")

    primary_gemini_key_label = api_keys_info.get('Google Gemini API Key 1', 'GOOGLE_API_KEY_PRIMARY')

    # 初始化臨時的 session state key 來保存 onboarding 過程中的輸入
    if 'onboarding_gemini_api_key' not in st.session_state:
        st.session_state.onboarding_gemini_api_key = st.session_state.get(primary_gemini_key_label, "")

    st.session_state.onboarding_gemini_api_key = st.text_input(
        f"請輸入您的 Google Gemini API Key ({primary_gemini_key_label})",
        value=st.session_state.onboarding_gemini_api_key,
        type="password",
        help="這是使用 Gemini 模型所必需的 API 金鑰。",
        key="onboarding_api_key_input_field" # Added key for stability
    )

    # 動態獲取模型列表
    dynamic_models = []
    if st.session_state.onboarding_gemini_api_key and st.session_state.onboarding_gemini_api_key.strip():
        with st.spinner("正在從 API 獲取可用模型列表..."):
            dynamic_models = get_available_models(api_key=st.session_state.onboarding_gemini_api_key)
        if not dynamic_models:
            st.warning("無法獲取模型列表，請檢查您的 API 金鑰或網路連線。將使用預設列表（如果可用）。")
            # Fallback to static list from config if absolutely necessary, or handle error
            # from config.app_settings import available_models as static_available_models
            # dynamic_models_options = static_available_models # This line should be adapted if static list is to be used as fallback
            # For now, we'll proceed assuming dynamic_models might be empty, and selectbox will handle it.
            # Or, show an error and prevent proceeding. For now, let it be empty if fetch fails.

    # 模型選擇的 session state key (儲存選擇的 model object)
    if 'onboarding_selected_model_object' not in st.session_state:
        st.session_state.onboarding_selected_model_object = None

    # 如果 dynamic_models 成功獲取，更新 selectbox 的 options
    # 並且嘗試保持之前的選擇 (如果存在且有效)
    current_selection_name = st.session_state.get('onboarding_selected_model', None) # This was storing name string
    current_selected_object = None

    if dynamic_models:
        options_for_selectbox = dynamic_models
        # Try to find the previously selected model name in the new list of objects
        if current_selection_name:
            for model_obj in dynamic_models:
                if model_obj.name == current_selection_name:
                    current_selected_object = model_obj
                    break
        # If no prior selection or prior selection not in new list, default to first model
        if not current_selected_object and dynamic_models:
            current_selected_object = dynamic_models[0]

        st.session_state.onboarding_selected_model_object = st.selectbox(
            "請選擇核心模型",
            options=options_for_selectbox,
            format_func=format_model_display_name,
            index=options_for_selectbox.index(current_selected_object) if current_selected_object in options_for_selectbox else 0,
            help="選擇您希望應用程式主要使用的語言模型。"
        )
    elif st.session_state.onboarding_gemini_api_key: # API key provided but no models fetched
        st.error("未能獲取到模型列表。請確認您的 API 金鑰是否正確且具有存取模型的權限。")
        # Prevent button from being effective if no models
        st.session_state.onboarding_selected_model_object = None


    if st.button("完成設定並繼續"):
        api_key_provided = bool(st.session_state.onboarding_gemini_api_key and st.session_state.onboarding_gemini_api_key.strip())
        # model_selected is now based on the object, not just a name string
        selected_model_object = st.session_state.get('onboarding_selected_model_object', None)
        model_actually_selected = selected_model_object is not None

        if api_key_provided and model_actually_selected:
            st.session_state[primary_gemini_key_label] = st.session_state.onboarding_gemini_api_key
            st.session_state.selected_model_name = selected_model_object.name # Store the model's unique name
            st.session_state.setup_complete = True
            logger.info(f"使用者引導完成。API Key 已提供: {'是' if api_key_provided else '否'}，選擇模型: {selected_model_object.name}")

            # 清理 onboarding 過程中使用的臨時 session state keys
            if 'onboarding_gemini_api_key' in st.session_state: # This is the input field's content
                del st.session_state.onboarding_gemini_api_key
            if 'onboarding_selected_model_object' in st.session_state: # This stored the selected model object
                del st.session_state.onboarding_selected_model_object
            if 'onboarding_selected_model' in st.session_state: # old key, ensure it's cleaned up
                 del st.session_state.onboarding_selected_model

            st.rerun()
        else:
            if not api_key_provided:
                st.error("請務必填寫 Google Gemini API Key。")
            if not model_selected:
                st.error("請選擇一個核心模型。")
            logger.warning("使用者引導儲存失敗：API Key 或模型未提供/選擇。")
