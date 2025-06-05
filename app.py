import streamlit as st
import pandas as pd
import os
import yfinance as yf
from datetime import datetime, timedelta
from fredapi import Fred
import requests
import io
import google.generativeai as genai
import google.api_core.exceptions
import time
import traceback
import logging
import sys

# --- Basic Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s',
    stream=sys.stderr
)

# Set page config - MUST be the first Streamlit command
st.set_page_config(
    page_title="金融分析與洞察助理 (由 Gemini 驅動)",
    layout="wide"
)

def main_app_logic():
    logger = logging.getLogger(__name__)

    # API Key Definitions (needed for initialization and validation)
    api_keys_info = {
        "gemini_api_key_1": "Gemini API Key 1",
        "gemini_api_key_2": "Gemini API Key 2",
        "gemini_api_key_3": "Gemini API Key 3",
        "fred_api_key": "FRED API Key",
        "alpha_vantage_api_key": "Alpha Vantage API Key",
        "api_key_fmpnb": "Financial Modeling Prep API Key",
        "api_key_finnhub": "Finnhub API Key",
        "api_key_figi": "OpenFigi API Key",
        "api_key_iex": "IEX Cloud API Key",
        "api_key_polygon": "Polygon API Key",
        "deepseek_api_key": "DeepSeek API Key",
    }

    # Initialize session state for API keys if not already done
    if 'initialized_keys' not in st.session_state:
        logger.info("Initializing API keys in session state from secrets.")
        for key_name_snake_case in api_keys_info.keys():
            secret_key_name = key_name_snake_case.upper()
            st.session_state[key_name_snake_case] = st.secrets.get(secret_key_name, "")
        st.session_state.initialized_keys = True

    # --- Helper function to check for valid Gemini API keys ---
    def are_gemini_keys_valid():
        for i in range(1, 4):  # Check gemini_api_key_1, _2, _3
            key_value = st.session_state.get(f"gemini_api_key_{i}", "")
            if key_value and key_value.strip():
                logger.info(f"Found valid Gemini API key: gemini_api_key_{i}")
                return True
        logger.warning("No valid Gemini API keys found in session state.")
        return False

    # --- Perform API Key Check and Display Guidance ---
    if not are_gemini_keys_valid():
        # This message will appear on the main page if keys are missing
        st.warning(
            "⚠️ **核心功能需要 Gemini API 金鑰**\n\n"
            "此應用程式的核心分析功能由 Google Gemini 提供技術支援。請在左側邊欄設定您的 Gemini API 金鑰以啟用完整功能。\n\n"
            "如果您還沒有金鑰，可以點擊以下連結獲取： "
            "[點此獲取 Gemini API 金鑰](https://aistudio.google.com/app/apikey)",
            icon="🔑"
        )
        with st.expander("🔧 如何設定 API 金鑰？(中文教學)", expanded=True):
            st.markdown("""
                ### 如何設定及使用 API 金鑰：

                1.  **獲取金鑰**：
                    *   前往 [Google AI Studio](https://aistudio.google.com/app/apikey) 網站。
                    *   登入您的 Google 帳戶。
                    *   點擊 "Create API key in new project" 或類似按鈕來創建一個新的 API 金鑰。
                    *   複製您獲得的 API 金鑰字串。

                2.  **在應用程式中設定**：
                    *   在本應用程式的左側邊欄找到「🔑 API 金鑰管理」部分。
                    *   將您複製的 API 金鑰貼到 "Gemini API Key 1", "Gemini API Key 2", 或 "Gemini API Key 3" 任一輸入框中。
                    *   至少需要設定一個有效的 Gemini API 金鑰。
                    *   （可選）您也可以在此處設定 FRED API 金鑰等其他金鑰。

                3.  **開始使用**：
                    *   金鑰設定完成後，應用程式的 Gemini 分析功能即可使用。

                **重要提示**：請妥善保管您的 API 金鑰，不要分享給他人或在公開的程式碼中洩漏。
            """)
        logger.info("API key guidance displayed on the main page.")

    # --- Function to load custom CSS ---
    def load_custom_css():
        try:
            with open("style.css", "r", encoding="utf-8") as f:
                css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        except FileNotFoundError:
            logger.warning("style.css 檔案未找到。將使用預設樣式。")
            st.warning("警告：style.css 檔案未找到。將使用預設樣式。")
        except Exception as e:
            logger.error(f"載入自訂 CSS 時發生錯誤: {e}", exc_info=True)
            st.error(f"載入自訂 CSS 時發生錯誤: {e}")

    # --- Load CSS and Apply Theme Wrapper ---
    load_custom_css()

    # Apply a global div with the theme class.
    # Ensure active_theme is initialized before this line if it's used.
    # It's initialized later, so using .get with a default is safe.
    st.markdown(f"<div class='theme-{st.session_state.get('active_theme', 'dark')}'>", unsafe_allow_html=True)

    # --- Inject Dynamic Font Size CSS ---
    font_size_css_map = {
        "小": "0.875rem",
        "中": "1rem",
        "大": "1.125rem"
    }
    selected_font_size_value = font_size_css_map.get(st.session_state.get("font_size_name", "中"), "1rem")
    font_override_style = f"""
<style>
html {{ font-size: {selected_font_size_value} !important; }}
</style>
"""
    st.markdown(font_override_style, unsafe_allow_html=True)

    # Gemini Model Definitions
    available_models = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]
    if 'initialized_model_settings' not in st.session_state:
        st.session_state.selected_model_name = available_models[0]
        st.session_state.global_rpm_limit = 5
        st.session_state.global_tpm_limit = 200000
        st.session_state.initialized_model_settings = True

    DEFAULT_MAIN_GEMINI_PROMPT = """請你分析我提供的所有文字檔。
你的任務是整理這些檔案中包含的社群媒體貼文。
請嚴格依照以下指示呈現結果：
1.  **來源識別**：確認每個貼文的原始檔案名稱。
2.  **內容摘要**：對每個貼文進行簡潔摘要。
3.  **情緒分析**：判斷每個貼文表達的情緒（例如，正面、負面、中性）。
4.  **關鍵主題**：提取每個貼文討論的核心主題。
5.  **建議行動**：如果貼文暗示了某種行動或建議，請明確指出。
請確保最終輸出結果嚴格遵循上述所有指示。"""
    if 'initialized_prompt_settings' not in st.session_state:
        st.session_state.main_gemini_prompt = DEFAULT_MAIN_GEMINI_PROMPT
        st.session_state.initialized_prompt_settings = True

    if 'initialized_file_upload_settings' not in st.session_state:
        st.session_state.uploaded_files_list = []
        st.session_state.uploaded_file_contents = {}
        st.session_state.initialized_file_upload_settings = True

    if 'initialized_data_source_settings' not in st.session_state:
        st.session_state.select_yfinance = False
        st.session_state.select_fred = False
        st.session_state.select_ny_fed = False
        st.session_state.select_all_sources = False
        st.session_state.data_start_date = "20230101"
        st.session_state.data_end_date = datetime.now().strftime("%Y%m%d")
        st.session_state.yfinance_tickers = "AAPL,^MOVE"
        st.session_state.yfinance_interval_label = "每日"
        st.session_state.fred_series_ids = "DGS10,VIXCLS"
        st.session_state.fetched_data_preview = {}
        st.session_state.fetch_errors = []
        st.session_state.fetch_data_button_clicked = False
        st.session_state.initialized_data_source_settings = True

    if 'initialized_gemini_interaction_settings' not in st.session_state:
        st.session_state.chat_history = []
        st.session_state.active_gemini_key_index = 0
        st.session_state.gemini_api_key_usage = {}
        st.session_state.gemini_caches_list = []
        st.session_state.selected_cache_for_generation = None
        st.session_state.initialized_gemini_interaction_settings = True

    if 'initialized_theme_settings' not in st.session_state:
        st.session_state.active_theme = "dark"
        st.session_state.initialized_theme_settings = True

    if 'initialized_font_settings' not in st.session_state:
        st.session_state.font_size_name = "中"
        st.session_state.initialized_font_settings = True

    @st.cache_data(ttl=3600)
    def fetch_yfinance_data(tickers_str: str, start_date_str: str, end_date_str: str, interval: str):
        logger.info(f"Fetching yfinance data for tickers: {tickers_str}, interval: {interval}")
        data_frames = {}
        errors = []
        if not tickers_str.strip():
            msg = "Ticker 字串不可為空。"
            errors.append(msg)
            logger.error(msg)
            return data_frames, errors
        list_of_tickers = [ticker.strip().upper() for ticker in tickers_str.split(',') if ticker.strip()]
        if not list_of_tickers:
            msg = "未提供有效的 Ticker。"
            errors.append(msg)
            logger.error(msg)
            return data_frames, errors
        try:
            start_dt = datetime.strptime(start_date_str, "%Y%m%d")
        except ValueError:
            msg = f"開始日期格式無效: {start_date_str}。請使用 YYYYMMDD 格式。"
            errors.append(msg)
            logger.error(msg)
            return data_frames, errors
        try:
            end_dt = datetime.strptime(end_date_str, "%Y%m%d")
        except ValueError:
            msg = f"結束日期格式無效: {end_date_str}。請使用 YYYYMMDD 格式。"
            errors.append(msg)
            logger.error(msg)
            return data_frames, errors
        if start_dt > end_dt:
            msg = f"開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。"
            errors.append(msg)
            logger.error(msg)
            return data_frames, errors
        for ticker in list_of_tickers:
            try:
                logger.info(f"Downloading yfinance data for {ticker}")
                df = yf.download(ticker, start=start_dt, end=end_dt, interval=interval, progress=False)
                if df.empty:
                    msg = f"Ticker {ticker}: 在指定日期範圍內沒有找到數據。"
                    errors.append(msg)
                    logger.warning(msg)
                else:
                    df.reset_index(inplace=True)
                    df.columns = df.columns.astype(str)
                    data_frames[ticker] = df
                    logger.info(f"Successfully downloaded yfinance data for {ticker}")
            except Exception as e:
                msg = f"下載 Ticker {ticker} 數據時發生錯誤: {str(e)}"
                errors.append(msg)
                logger.error(msg, exc_info=True)
        return data_frames, errors

    @st.cache_data(ttl=86400)
    def fetch_fred_data(series_ids_str: str, start_date_str: str, end_date_str: str, api_key: str):
        logger.info(f"Fetching FRED data for series: {series_ids_str}")
        data_series_dict = {}
        errors = []
        if not api_key:
            msg = "錯誤：FRED API 金鑰未提供。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        try:
            fred = Fred(api_key=api_key)
        except Exception as e:
            msg = f"FRED API 金鑰初始化失敗: {str(e)}。請檢查您的 API 金鑰。"
            errors.append(msg)
            logger.error(msg, exc_info=True)
            return data_series_dict, errors
        if not series_ids_str.strip():
            msg = "Series ID 字串不可為空。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        list_of_series_ids = [sid.strip().upper() for sid in series_ids_str.split(',') if sid.strip()]
        if not list_of_series_ids:
            msg = "未提供有效的 Series ID。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        try:
            start_dt = datetime.strptime(start_date_str, "%Y%m%d")
        except ValueError:
            msg = f"開始日期格式無效: {start_date_str}。請使用 YYYYMMDD 格式。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        try:
            end_dt = datetime.strptime(end_date_str, "%Y%m%d")
        except ValueError:
            msg = f"結束日期格式無效: {end_date_str}。請使用 YYYYMMDD 格式。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        if start_dt > end_dt:
            msg = f"開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。"
            errors.append(msg)
            logger.error(msg)
            return data_series_dict, errors
        for series_id in list_of_series_ids:
            try:
                logger.info(f"Downloading FRED data for {series_id}")
                series_data = fred.get_series(series_id, observation_start=start_dt, observation_end=end_dt)
                if series_data.empty:
                    msg = f"Series ID {series_id}: 在指定日期範圍內沒有找到數據。"
                    errors.append(msg)
                    logger.warning(msg)
                else:
                    df = series_data.to_frame(name=series_id)
                    df.reset_index(inplace=True)
                    df.rename(columns={'index': 'Date', series_id: 'Value'}, inplace=True)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                    df.dropna(subset=['Value'], inplace=True)
                    data_series_dict[series_id] = df
                    logger.info(f"Successfully downloaded FRED data for {series_id}")
            except ValueError as ve:
                 msg = f"Series ID {series_id} 無效或找不到: {str(ve)}"
                 errors.append(msg)
                 logger.error(msg, exc_info=True)
            except Exception as e:
                msg = f"下載 Series ID {series_id} 數據時發生錯誤: {str(e)}"
                errors.append(msg)
                logger.error(msg, exc_info=True)
        return data_series_dict, errors

    NY_FED_POSITIONS_URLS_CORRECTED = [
        "https://markets.newyorkfed.org/api/pd/get/SBN2024/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11L21_PDPOSGSC-G21.xlsx",
        "https://markets.newyorkfed.org/api/pd/get/SBN2022/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11L21_PDPOSGSC-G21.xlsx",
        "https://markets.newyorkfed.org/api/pd/get/SBN2015/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11.xlsx",
        "https://markets.newyorkfed.org/api/pd/get/SBN2013/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11.xlsx",
        "https://markets.newyorkfed.org/api/pd/get/SBP2013/timeseries/PDPUSGCS3LNOP_PDPUSGCS36NOP_PDPUSGCS611NOP_PDPUSGCSM11NOP.xlsx",
        "https://markets.newyorkfed.org/api/pd/get/SBP2001/timeseries/PDPUSGCS5LNOP_PDPUSGCS5MNOP.xlsx",
    ]
    SBP_COLS_TO_SUM = {
        "SBP2013": ["PDPUSGCS3LNOP", "PDPUSGCS36NOP", "PDPUSGCS611NOP", "PDPUSGCSM11NOP"],
        "SBP2001": ["PDPUSGCS5LNOP", "PDPUSGCS5MNOP"],
    }

    @st.cache_data(ttl=86400)
    def fetch_ny_fed_data():
        logger.info("Fetching NY Fed Primary Dealer Positions data.")
        all_positions_data = []
        errors = []
        HEADER_ROW_ASSUMPTION = 4
        DATE_COLUMN_INDEX_ASSUMPTION = 0
        for url in NY_FED_POSITIONS_URLS_CORRECTED:
            try:
                logger.info(f"Downloading NY Fed data from {url}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                excel_content = io.BytesIO(response.content)
                xls = pd.ExcelFile(excel_content)
                df = pd.read_excel(xls, sheet_name=0, header=HEADER_ROW_ASSUMPTION, index_col=DATE_COLUMN_INDEX_ASSUMPTION)
                df.index = pd.to_datetime(df.index, errors='coerce')
                df = df[df.index.notna()]
                if df.empty:
                    msg = f"檔案 {url} 在轉換日期後沒有有效數據。"
                    errors.append(msg)
                    logger.warning(msg)
                    continue
                source_type, target_cols = None, []
                if "SBN" in url:
                    source_type = "SBN"
                    target_cols = [col for col in df.columns if str(col).startswith("PDPOSGSC-")]
                elif "SBP2013" in url:
                    source_type = "SBP2013"
                    target_cols = [col for col in SBP_COLS_TO_SUM["SBP2013"] if col in df.columns]
                elif "SBP2001" in url:
                    source_type = "SBP2001"
                    target_cols = [col for col in SBP_COLS_TO_SUM["SBP2001"] if col in df.columns]
                if not target_cols:
                    msg = f"檔案 {url} (類型 {source_type}) 中未找到目標欄位或目標欄位列表為空。"
                    errors.append(msg)
                    logger.warning(msg)
                    continue
                df_target = df[target_cols].apply(pd.to_numeric, errors='coerce')
                if df_target.isnull().all().all():
                    msg = f"檔案 {url} (類型 {source_type}) 的目標欄位 {target_cols} 轉換為數字後均為空值。"
                    errors.append(msg)
                    logger.warning(msg)
                    continue
                daily_sum = df_target.sum(axis=1)
                all_positions_data.append(daily_sum)
                logger.info(f"Successfully processed NY Fed data from {url}")
            except requests.exceptions.HTTPError as http_err:
                msg = f"下載檔案 {url} 時發生 HTTP 錯誤: {http_err}"
                errors.append(msg)
                logger.error(msg, exc_info=True)
            except requests.exceptions.RequestException as req_err:
                msg = f"下載檔案 {url} 時發生錯誤: {req_err}"
                errors.append(msg)
                logger.error(msg, exc_info=True)
            except Exception as e:
                msg = f"處理檔案 {url} 時發生錯誤: {str(e)}"
                errors.append(msg)
                logger.error(msg, exc_info=True)
        if not all_positions_data:
            logger.warning("No data collected from any NY Fed URL.")
            return None, errors
        try:
            final_series = pd.concat(all_positions_data)
            final_series = final_series.groupby(final_series.index).last()
            final_series = final_series.sort_index()
            final_series = final_series.ffill()
            result_df = final_series.to_frame(name="Total_Dealer_Positions")
            result_df.reset_index(inplace=True)
            result_df.rename(columns={'index': 'Date'}, inplace=True)
            logger.info("Successfully combined and processed all NY Fed data.")
        except Exception as e:
            msg = f"合併和最終處理 NY Fed 數據時發生錯誤: {str(e)}"
            errors.append(msg)
            logger.error(msg, exc_info=True)
            return None, errors
        return result_df, errors

    def call_gemini_api(prompt_parts: list, api_keys_list: list, selected_model: str,
                        global_rpm: int, global_tpm: int,
                        generation_config_dict: dict = None, cached_content_name: str = None):
        logger.info(f"Calling Gemini API with model: {selected_model}, cache: {cached_content_name}")
        if not api_keys_list:
            logger.error("Gemini API call failed: No valid API keys provided.")
            return "錯誤：未提供有效的 Gemini API 金鑰。"
        active_key_index = st.session_state.get('active_gemini_key_index', 0)
        current_api_key = api_keys_list[active_key_index]
        now = time.time()
        if current_api_key not in st.session_state.gemini_api_key_usage:
            st.session_state.gemini_api_key_usage[current_api_key] = {'requests': [], 'tokens': []}
        st.session_state.gemini_api_key_usage[current_api_key]['requests'] = \
            [ts for ts in st.session_state.gemini_api_key_usage[current_api_key]['requests'] if now - ts < 60]
        if len(st.session_state.gemini_api_key_usage[current_api_key]['requests']) >= global_rpm:
            st.session_state.active_gemini_key_index = (active_key_index + 1) % len(api_keys_list)
            logger.warning(f"RPM limit reached for API key {current_api_key[:10]}...")
            return f"錯誤：API 金鑰 {current_api_key[:10]}... RPM 達到上限 ({global_rpm})。請稍後重試或切換金鑰。"
        try:
            genai.configure(api_key=current_api_key)
            model = genai.GenerativeModel(model_name=selected_model)
            gen_config_obj = genai.types.GenerationConfig(**generation_config_dict) if generation_config_dict else None
            final_prompt_content = "\n".join(map(str, prompt_parts))
            response = model.generate_content(
                final_prompt_content, generation_config=gen_config_obj, safety_settings=None,
                tools=None, tool_config=None, cached_content=cached_content_name
            )
            st.session_state.gemini_api_key_usage[current_api_key]['requests'].append(now)
            if response.usage_metadata and response.usage_metadata.total_token_count:
                st.session_state.gemini_api_key_usage[current_api_key]['tokens'].append((now, response.usage_metadata.total_token_count))
            st.session_state.active_gemini_key_index = (active_key_index + 1) % len(api_keys_list)
            logger.info("Gemini API call successful.")
            if response.parts: return "".join(part.text for part in response.parts if hasattr(part, 'text'))
            if response.text: return response.text
            logger.warning("Gemini API response has no text/parts.")
            return "模型未返回文字內容。"
        except genai.types.BlockedPromptException as bpe:
            logger.error(f"Gemini API Error (BlockedPromptException): {bpe}", exc_info=True)
            return f"錯誤：提示詞被 Gemini API 封鎖。原因: {bpe}"
        except genai.types.generation_types.StopCandidateException as sce:
            logger.error(f"Gemini API Error (StopCandidateException): {sce}", exc_info=True)
            return f"錯誤：內容生成因安全原因或其他限制而停止。原因: {sce}"
        except google.api_core.exceptions.PermissionDenied as e:
            logger.error(f"Gemini API Error (PermissionDenied): {str(e)}", exc_info=True)
            return f"錯誤：呼叫 Gemini API 權限不足或API金鑰無效。詳細資訊: {str(e)}"
        except google.api_core.exceptions.InvalidArgument as e:
            logger.error(f"Gemini API Error (InvalidArgument): {str(e)}", exc_info=True)
            return f"錯誤：呼叫 Gemini API 時參數無效 (例如模型名稱不正確或內容不当)。詳細資訊: {str(e)}"
        except google.api_core.exceptions.FailedPrecondition as e:
            logger.error(f"Gemini API Error (FailedPrecondition): {str(e)}", exc_info=True)
            return f"錯誤：呼叫 Gemini API 預設條件失敗 (例如，所選模型可能不支持快取)。詳細資訊: {str(e)}"
        except google.api_core.exceptions.DeadlineExceeded as e:
            logger.error(f"Gemini API Error (DeadlineExceeded): {str(e)}", exc_info=True)
            return f"錯誤：呼叫 Gemini API 超時。詳細資訊: {str(e)}"
        except google.api_core.exceptions.ServiceUnavailable as e:
            logger.error(f"Gemini API Error (ServiceUnavailable): {str(e)}", exc_info=True)
            return f"錯誤：Gemini服務暫時不可用，請稍後再試。詳細資訊: {str(e)}"
        except google.api_core.exceptions.InternalServerError as e:
            logger.error(f"Gemini API Error (InternalServerError): {str(e)}", exc_info=True)
            return f"錯誤：Gemini內部伺服器錯誤。詳細資訊: {str(e)}"
        except google.api_core.exceptions.Unknown as e:
            logger.error(f"Gemini API Error (Unknown): {str(e)}", exc_info=True)
            return f"錯誤：呼叫 Gemini API 時發生未知的Google API錯誤。詳細資訊: {str(e)}"
        except Exception as e:
            logger.exception("Unexpected error during Gemini API call:")
            error_message = str(e)
            if hasattr(e, 'message'): error_message = e.message
            elif hasattr(e, 'args') and e.args: error_message = str(e.args[0])
            return f"呼叫 Gemini API 時發生非預期錯誤: {error_message}"

    # --- Sidebar UI ---
    st.sidebar.title("⚙️ 全域設定與工具")
    st.sidebar.header("🎨 外觀主題與字體")
    active_theme = st.session_state.get("active_theme", "dark")
    current_theme_label = "暗色模式 (Gemini)" if active_theme == "dark" else "亮色模式 (預設)"
    toggle_label = f"切換到 {'亮色模式 (預設)' if active_theme == 'dark' else '暗色模式 (Gemini)'}"
    new_toggle_state_is_dark = st.sidebar.toggle(
        toggle_label, value=(active_theme == "dark"), key="theme_toggle_widget", help="點擊切換亮暗主題"
    )
    if new_toggle_state_is_dark and active_theme == "light":
        st.session_state.active_theme = "dark"; st.experimental_rerun()
    elif not new_toggle_state_is_dark and active_theme == "dark":
        st.session_state.active_theme = "light"; st.experimental_rerun()
    st.sidebar.caption(f"目前主題: {current_theme_label}")
    st.sidebar.markdown("##### 選擇字體大小:")
    font_cols = st.sidebar.columns(3)
    if font_cols[0].button("A- (小)", key="font_small_button", use_container_width=True):
        st.session_state.font_size_name = "小"; st.experimental_rerun()
    if font_cols[1].button("A (中)", key="font_medium_button", use_container_width=True):
        st.session_state.font_size_name = "中"; st.experimental_rerun()
    if font_cols[2].button("A+ (大)", key="font_large_button", use_container_width=True):
        st.session_state.font_size_name = "大"; st.experimental_rerun()
    st.sidebar.caption(f"目前字體: {st.session_state.get('font_size_name', '中')}")
    st.sidebar.markdown("---")

    st.sidebar.header("🔑 API 金鑰管理")
    st.sidebar.caption("請在此處管理您的 API 金鑰。")
    # This specific check for sidebar might be redundant if the main page already shows a big warning,
    # but keeping it doesn't hurt and provides context within the sidebar itself.
    if not are_gemini_keys_valid(): # Using the helper function here as well
        st.sidebar.warning("警告：至少需要一個有效的 Gemini API 金鑰才能使用 Gemini 分析功能。")
    for key_name_snake_case, key_label in api_keys_info.items():
        st.session_state[key_name_snake_case] = st.sidebar.text_input(
            key_label, type="password", value=st.session_state[key_name_snake_case], key=f"{key_name_snake_case}_input"
        )
    st.sidebar.success("API 金鑰已更新並儲存在會話中。") # This message might appear even if keys are not valid yet.

    st.sidebar.header("🤖 Gemini 模型設定")
    st.sidebar.caption("選擇並配置要使用的 Gemini 模型。")
    st.session_state.selected_model_name = st.sidebar.selectbox(
        "選擇 Gemini 模型:", options=available_models, index=available_models.index(st.session_state.selected_model_name), key="selected_model_name_selector"
    )
    st.session_state.global_rpm_limit = st.sidebar.number_input(
        "全域 RPM (每分鐘請求數):", min_value=1, value=st.session_state.global_rpm_limit, step=1, key="global_rpm_limit_input"
    )
    st.session_state.global_tpm_limit = st.sidebar.number_input(
        "全域 TPM (每分鐘詞元數):", min_value=1000, value=st.session_state.global_tpm_limit, step=10000, key="global_tpm_limit_input"
    )
    st.sidebar.caption("注意：請參考 Gemini 官方文件了解不同模型的具體 RPM/TPM 限制。")
    st.sidebar.header("📝 主要提示詞")
    st.sidebar.caption("設定用於指導 Gemini 分析的主要提示詞。")
    st.session_state.main_gemini_prompt = st.sidebar.text_area(
        "主要分析提示詞 (System Prompt):", value=st.session_state.main_gemini_prompt, height=300, key="main_gemini_prompt_input"
    )
    uploaded_prompt_file = st.sidebar.file_uploader("或從 .txt 檔案載入提示詞:", type=["txt"], key="prompt_file_uploader")
    if uploaded_prompt_file is not None:
        prompt_content = uploaded_prompt_file.read().decode("utf-8")
        st.session_state.main_gemini_prompt = prompt_content
    st.sidebar.header("🧹 快取管理")
    st.sidebar.caption("管理應用程式的數據快取。")
    if st.sidebar.button("清除所有數據快取", key="clear_all_cache_button"):
        st.cache_data.clear(); logger.info("All data caches cleared.")
        st.sidebar.success("所有數據快取已成功清除！下次獲取數據時將從源頭重新載入。")
    st.sidebar.caption("點擊此按鈕將清除所有已快取的 yfinance, FRED 及 NY Fed 數據。")
    st.sidebar.header("🧠 Gemini 內容快取")
    st.session_state.cache_display_name_input = st.sidebar.text_input(
        "要快取的內容名稱 (例如 system_prompt_cache):", value=st.session_state.get("cache_display_name_input", "system_prompt_main"), key="cache_display_name_input_widget"
    )
    st.session_state.cache_content_input = st.sidebar.text_area(
        "要快取的內容 (通常是 System Prompt):", value=st.session_state.get("cache_content_input", st.session_state.get("main_gemini_prompt","")), height=150, key="cache_content_input_widget"
    )
    st.session_state.cache_ttl_seconds_input = st.sidebar.number_input(
        "快取 TTL (秒, e.g., 3600 for 1 hour):", min_value=60, value=st.session_state.get("cache_ttl_seconds_input",3600), key="cache_ttl_input_widget"
    )

    if st.sidebar.button("創建/更新內容快取", key="create_cache_button"):
        logger.info(f"Attempting to create/update cache: {st.session_state.cache_display_name_input}")
        gemini_keys_for_cache = [st.session_state.get(f"gemini_api_key_{i+1}","") for i in range(3)]
        valid_gemini_key_for_cache = next((key for key in gemini_keys_for_cache if key), None)
        selected_model_for_cache = st.session_state.get("selected_model_name", "gemini-1.0-pro")
        if valid_gemini_key_for_cache and st.session_state.cache_display_name_input and st.session_state.cache_content_input:
            try:
                genai.configure(api_key=valid_gemini_key_for_cache)
                ttl_str = f"{st.session_state.cache_ttl_seconds_input}s"
                model_for_caching_api = f"models/{selected_model_for_cache}" if not selected_model_for_cache.startswith("models/") else selected_model_for_cache
                cached_content = genai.create_cached_content(
                    model=model_for_caching_api, display_name=st.session_state.cache_display_name_input,
                    system_instruction=st.session_state.cache_content_input, ttl=ttl_str
                )
                st.sidebar.success(f"快取 '{cached_content.display_name}' 已創建/更新。\n名稱: {cached_content.name}")
                logger.info(f"Cache '{cached_content.display_name}' created/updated successfully. Name: {cached_content.name}")
                st.session_state.gemini_caches_list = list(genai.list_cached_contents(api_key=valid_gemini_key_for_cache))
            except (google.api_core.exceptions.PermissionDenied, google.api_core.exceptions.InvalidArgument,
                    google.api_core.exceptions.FailedPrecondition, google.api_core.exceptions.DeadlineExceeded,
                    google.api_core.exceptions.ServiceUnavailable, google.api_core.exceptions.InternalServerError,
                    google.api_core.exceptions.Unknown) as e:
                logger.error(f"Failed to create/update cache ({type(e).__name__}): {st.session_state.cache_display_name_input} - {str(e)}", exc_info=True)
                st.sidebar.error(f"創建快取失敗 ({type(e).__name__}): {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error creating/updating cache: {st.session_state.cache_display_name_input} - {str(e)}", exc_info=True)
                st.sidebar.error(f"創建快取時發生非預期錯誤: {str(e)}")
        else:
            logger.warning("Cannot create/update cache: Missing Gemini API key, cache name, or content.")
            st.sidebar.warning("請提供有效的 Gemini API 金鑰、快取名稱和快取內容。")

    if st.sidebar.button("列出可用快取", key="list_caches_button"):
        logger.info("Attempting to list caches.")
        gemini_keys_for_cache_list = [st.session_state.get(f"gemini_api_key_{i+1}","") for i in range(3)]
        valid_gemini_key_for_cache_list = next((key for key in gemini_keys_for_cache_list if key), None)
        if valid_gemini_key_for_cache_list:
            try:
                genai.configure(api_key=valid_gemini_key_for_cache_list)
                st.session_state.gemini_caches_list = list(genai.list_cached_contents())
                if not st.session_state.gemini_caches_list:
                    st.sidebar.info("目前沒有可用的內容快取。")
                    logger.info("No caches found.")
                else:
                    logger.info(f"Found {len(st.session_state.gemini_caches_list)} caches.")
            except (google.api_core.exceptions.PermissionDenied, google.api_core.exceptions.DeadlineExceeded,
                    google.api_core.exceptions.ServiceUnavailable, google.api_core.exceptions.InternalServerError,
                    google.api_core.exceptions.Unknown) as e:
                logger.error(f"Failed to list caches ({type(e).__name__}): {str(e)}", exc_info=True)
                st.sidebar.error(f"列出快取失敗 ({type(e).__name__}): {str(e)}")
                st.session_state.gemini_caches_list = []
            except Exception as e:
                logger.error(f"Unexpected error listing caches: {str(e)}", exc_info=True)
                st.sidebar.error(f"列出快取時發生非預期錯誤: {str(e)}")
                st.session_state.gemini_caches_list = []
        else:
            logger.warning("Cannot list caches: Missing Gemini API key.")
            st.sidebar.warning("請先設定有效的 Gemini API 金鑰以列出快取。")

    if st.session_state.gemini_caches_list:
        cache_options = {"(不使用快取)": None}
        cache_options.update({f"{c.display_name} ({c.name.split('/')[-1][:8]}...)": c.name for c in st.session_state.gemini_caches_list})
        current_selected_cache_name = st.session_state.get("selected_cache_for_generation", None)
        options_list = list(cache_options.values())
        current_index = options_list.index(current_selected_cache_name) if current_selected_cache_name in options_list else 0
        selected_display_key = st.sidebar.selectbox(
            "選擇一個快取用於下次生成:", options=list(cache_options.keys()), index=current_index, key="select_cache_dropdown"
        )
        st.session_state.selected_cache_for_generation = cache_options.get(selected_display_key)

    st.session_state.cache_name_to_delete_input = st.sidebar.text_input(
        "要刪除的快取名稱 (projects/.../cachedContents/...):", value=st.session_state.get("cache_name_to_delete_input",""), key="cache_name_to_delete_input_widget"
    )
    if st.sidebar.button("刪除指定快取", key="delete_cache_button"):
        cache_to_delete = st.session_state.cache_name_to_delete_input
        logger.info(f"Attempting to delete cache: {cache_to_delete}")
        if cache_to_delete:
            gemini_keys_for_delete = [st.session_state.get(f"gemini_api_key_{i+1}","") for i in range(3)]
            valid_gemini_key_for_delete = next((key for key in gemini_keys_for_delete if key), None)
            if valid_gemini_key_for_delete:
                try:
                    genai.configure(api_key=valid_gemini_key_for_delete)
                    genai.delete_cached_content(name=cache_to_delete)
                    st.sidebar.success(f"快取 {cache_to_delete} 已成功刪除。")
                    logger.info(f"Cache {cache_to_delete} deleted successfully.")
                    st.session_state.gemini_caches_list = list(genai.list_cached_contents())
                    if st.session_state.selected_cache_for_generation == cache_to_delete:
                        st.session_state.selected_cache_for_generation = None
                except (google.api_core.exceptions.PermissionDenied, google.api_core.exceptions.NotFound,
                        google.api_core.exceptions.DeadlineExceeded, google.api_core.exceptions.ServiceUnavailable,
                        google.api_core.exceptions.InternalServerError, google.api_core.exceptions.Unknown) as e:
                    logger.error(f"Failed to delete cache {cache_to_delete} ({type(e).__name__}): {str(e)}", exc_info=True)
                    st.sidebar.error(f"刪除快取 {cache_to_delete} 失敗 ({type(e).__name__}): {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error deleting cache {cache_to_delete}: {str(e)}", exc_info=True)
                    st.sidebar.error(f"刪除快取 {cache_to_delete} 時發生非預期錯誤: {str(e)}")
            else:
                logger.warning("Cannot delete cache: Missing Gemini API key.")
                st.sidebar.warning("請設定有效的 Gemini API 金鑰以刪除快取。")
        else:
            logger.warning("Cannot delete cache: Cache name not provided.")
            st.sidebar.warning("請輸入要刪除的快取名稱。")

    # --- Main Page UI ---
    st.title("金融分析與洞察助理")

    # API Key Check is done earlier, this section is for file uploads etc.
    st.header("📄 步驟一：上傳與檢視文件")
    st.caption("請上傳您需要分析的文字檔案。")
    uploaded_files_from_widget = st.file_uploader(
        "請上傳您需要分析的文字檔案 (可多選 .txt):", type=["txt"], accept_multiple_files=True, key="file_uploader_widget"
    )
    if uploaded_files_from_widget:
        st.session_state.uploaded_files_list = uploaded_files_from_widget
        st.session_state.uploaded_file_contents = {}
        for file_obj in st.session_state.uploaded_files_list:
            try:
                content = file_obj.read().decode("utf-8")
                st.session_state.uploaded_file_contents[file_obj.name] = content
            except Exception as e:
                logger.error(f"讀取檔案 {file_obj.name} 時發生錯誤: {e}", exc_info=True)
                st.error(f"讀取檔案 {file_obj.name} 時發生錯誤: {e}")
        if st.session_state.uploaded_file_contents:
            logger.info(f"Successfully uploaded and read {len(st.session_state.uploaded_file_contents)} files.")
            st.success(f"成功上傳並讀取 {len(st.session_state.uploaded_file_contents)} 個檔案。")

    if st.session_state.uploaded_files_list:
        st.subheader("已上傳文件預覽:")
        if not st.session_state.uploaded_file_contents and uploaded_files_from_widget:
            st.warning("所有上傳的檔案都無法成功讀取內容。請檢查檔案格式或內容。")
        elif not st.session_state.uploaded_file_contents and not uploaded_files_from_widget:
            st.info("之前上傳的檔案內容已清除或目前沒有選擇檔案。請重新上傳。")
        for file_name, content in st.session_state.uploaded_file_contents.items():
            with st.expander(f"檔名: {file_name} (點擊展開/收起預覽)", expanded=False):
                st.text(content[:500] + "..." if len(content) > 500 else content)
    elif not uploaded_files_from_widget:
        st.info("請上傳文字檔案以開始分析。")

    st.header("📊 步驟二：引入外部數據 (可選)")
    with st.expander("📊 步驟二：選擇並載入外部數據 (點擊展開/收起)", expanded=False):
        st.caption("選擇 yfinance, FRED, NY Fed 等外部市場與總經數據源，設定參數並載入數據。")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            select_all_sources_widget = st.checkbox("🌍 全選/取消所有數據源", value=st.session_state.select_all_sources, key="select_all_sources_cb")
            if select_all_sources_widget != st.session_state.select_all_sources:
                st.session_state.select_all_sources = select_all_sources_widget
                st.session_state.select_yfinance = select_all_sources_widget
                st.session_state.select_fred = select_all_sources_widget
                st.session_state.select_ny_fed = select_all_sources_widget
                st.experimental_rerun()
        with col2: st.session_state.select_yfinance = st.checkbox("📈 yfinance 股市數據", value=st.session_state.select_yfinance, key="select_yfinance_cb")
        with col3: st.session_state.select_fred = st.checkbox("🏦 FRED 總經數據", value=st.session_state.select_fred, key="select_fred_cb")
        with col4: st.session_state.select_ny_fed = st.checkbox("🇺🇸 NY Fed 一級交易商數據", value=st.session_state.select_ny_fed, key="select_ny_fed_cb")
        date_col1, date_col2 = st.columns(2)
        with date_col1: st.session_state.data_start_date = st.text_input("輸入開始日期 (YYYYMMDD):", value=st.session_state.data_start_date, key="data_start_date_input")
        with date_col2: st.session_state.data_end_date = st.text_input("輸入結束日期 (YYYYMMDD):", value=st.session_state.data_end_date, key="data_end_date_input")
        param_col1, param_col2 = st.columns(2)
        interval_options = {"每日": "1d", "每週": "1wk", "每小時": "1h", "每5分鐘": "5m"}
        with param_col1:
            if st.session_state.select_yfinance:
                st.session_state.yfinance_tickers = st.text_input("yfinance 股票代碼 (逗號分隔):", value=st.session_state.yfinance_tickers, key="yfinance_tickers_input")
                current_interval_label = st.session_state.yfinance_interval_label
                if current_interval_label not in interval_options: current_interval_label = list(interval_options.keys())[0]; st.session_state.yfinance_interval_label = current_interval_label
                st.session_state.yfinance_interval_label = st.selectbox("yfinance 數據週期:", options=list(interval_options.keys()), index=list(interval_options.keys()).index(current_interval_label), key="yfinance_interval_label_select")
        with param_col2:
            if st.session_state.select_fred:
                st.session_state.fred_series_ids = st.text_input("FRED Series ID (逗號分隔):", value=st.session_state.fred_series_ids, key="fred_series_ids_input")
        st.markdown("---")
        if st.button("🔍 獲取並預覽選定數據", key="fetch_data_button"):
            st.session_state.fetch_data_button_clicked = True; st.session_state.fetched_data_preview = {}; st.session_state.fetch_errors = []
            something_selected = (st.session_state.select_yfinance or st.session_state.select_fred or st.session_state.select_ny_fed)
            if not something_selected: st.warning("請至少選擇一個數據源。"); st.session_state.fetch_data_button_clicked = False
            else:
                with st.spinner("正在獲取數據，請稍候..."):
                    if st.session_state.select_yfinance:
                        actual_interval = interval_options[st.session_state.yfinance_interval_label]
                        yfinance_data, yfinance_errs = fetch_yfinance_data(st.session_state.yfinance_tickers, st.session_state.data_start_date, st.session_state.data_end_date, actual_interval)
                        if yfinance_data: st.session_state.fetched_data_preview["yfinance"] = yfinance_data
                        if yfinance_errs: st.session_state.fetch_errors.extend([f"[yfinance] {e}" for e in yfinance_errs])
                    if st.session_state.select_fred:
                        fred_api_key = st.session_state.get("fred_api_key", "")
                        if not fred_api_key: msg = "[FRED] 錯誤：FRED API 金鑰未在側邊欄設定。請先設定。"; st.session_state.fetch_errors.append(msg); logger.error(msg)
                        else:
                            fred_data, fred_errs = fetch_fred_data(st.session_state.fred_series_ids, st.session_state.data_start_date, st.session_state.data_end_date, fred_api_key)
                            if fred_data: st.session_state.fetched_data_preview["fred"] = fred_data
                            if fred_errs: st.session_state.fetch_errors.extend([f"[FRED] {e}" for e in fred_errs])
                    if st.session_state.select_ny_fed:
                        ny_fed_data, ny_fed_errs = fetch_ny_fed_data()
                        if ny_fed_data is not None: st.session_state.fetched_data_preview["ny_fed"] = ny_fed_data
                        if ny_fed_errs: st.session_state.fetch_errors.extend([f"[NY Fed] {e}" for e in ny_fed_errs])
        if st.session_state.fetch_errors:
            st.subheader("數據獲取錯誤："); [st.error(err_msg) for err_msg in st.session_state.fetch_errors]
        if st.session_state.fetched_data_preview:
            st.subheader("已獲取數據預覽:")
            if "yfinance" in st.session_state.fetched_data_preview:
                st.markdown("#### yfinance 數據:")
                for ticker, df_yf in st.session_state.fetched_data_preview["yfinance"].items():
                    with st.expander(f"Ticker: {ticker} (共 {len(df_yf)} 行)", expanded=False): st.dataframe(df_yf.head())
            if "fred" in st.session_state.fetched_data_preview:
                st.markdown("#### FRED 數據:")
                for series_id, df_fred in st.session_state.fetched_data_preview["fred"].items():
                    with st.expander(f"Series ID: {series_id} (共 {len(df_fred)} 行)", expanded=False): st.dataframe(df_fred.head())
            if "ny_fed" in st.session_state.fetched_data_preview and not st.session_state.fetched_data_preview["ny_fed"].empty:
                st.markdown("#### NY Fed 一級交易商數據:")
                with st.expander(f"NY Fed 總持有量 (共 {len(st.session_state.fetched_data_preview['ny_fed'])} 行)", expanded=False): st.dataframe(st.session_state.fetched_data_preview["ny_fed"].head())
            has_data = any((isinstance(ds, dict) and ds) or (isinstance(ds, pd.DataFrame) and not ds.empty) for ds in st.session_state.fetched_data_preview.values())
            if has_data and not st.session_state.fetch_errors: st.success("數據已成功載入並準備好用於分析。")
            elif not has_data and not st.session_state.fetch_errors and st.session_state.fetch_data_button_clicked: st.info("未獲取到任何數據。請檢查您的選擇和輸入，或確認數據源在該時段有數據。")
        elif st.session_state.fetch_data_button_clicked and not st.session_state.fetch_errors:
            st.info("未獲取到任何數據。請檢查您的選擇和輸入，或確認數據源在該時段有數據。")

    st.header("💬 步驟三：與 Gemini 進行分析與討論")
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.chat_history:
            avatar_icon = "👤" if message["role"] == "user" else "✨"
            with st.chat_message(message["role"], avatar=avatar_icon):
                if message["role"] == "model" and message.get("is_error", False): st.error(message["parts"][0])
                else: st.markdown(message["parts"][0])

    user_input = st.chat_input("向 Gemini 提問或給出指令：", key="gemini_user_input")
    if user_input:
        logger.info(f"User input: {user_input}")
        st.session_state.chat_history.append({"role": "user", "parts": [user_input]})
        with st.spinner("Gemini 正在思考中，請稍候..."):
            model_response_text, is_error_response = "", False
            try:
                logger.info("Preparing data and prompt for Gemini.")
                full_prompt_parts = []
                if st.session_state.get("main_gemini_prompt"): full_prompt_parts.append(f"**主要指示 (System Prompt):**\n{st.session_state.main_gemini_prompt}\n\n---\n")
                if st.session_state.get("uploaded_file_contents"):
                    uploaded_texts_str = "**已上傳文件內容摘要:**\n" + "".join([f"檔名: {fn}\n內容片段:\n{ct[:1000]}...\n\n" for fn, ct in st.session_state.uploaded_file_contents.items()])
                    full_prompt_parts.append(uploaded_texts_str + "---\n")
                if st.session_state.get("fetched_data_preview"):
                    external_data_str = "**已引入的外部市場與總經數據摘要:**\n"
                    for source, data_items in st.session_state.fetched_data_preview.items():
                        external_data_str += f"\n來源: {source.upper()}\n"
                        if source in ["yfinance", "fred"] and isinstance(data_items, dict):
                            for item_name, df_item in data_items.items():
                                if isinstance(df_item, pd.DataFrame): external_data_str += f"  {item_name} (最近幾筆):\n{df_item.tail(3).to_string()}\n"
                        elif source == "ny_fed" and isinstance(data_items, pd.DataFrame) and not data_items.empty:
                             external_data_str += f"  NY Fed 總持有量 (最近幾筆):\n{data_items.tail(3).to_string()}\n"
                    full_prompt_parts.append(external_data_str + "---\n")
                full_prompt_parts.append(f"**使用者當前問題/指令:**\n{user_input}")

                valid_gemini_api_keys = [key for key in [st.session_state.get(f"gemini_api_key_{i+1}","") for i in range(3)] if key and key.strip()]
                selected_model_name = st.session_state.get("selected_model_name", "gemini-1.0-pro")
                generation_config = {"temperature": 0.7, "top_p": 1.0, "top_k": 32, "max_output_tokens": 8192}
                selected_cache_name_for_api = st.session_state.get("selected_cache_for_generation", None)

                if not valid_gemini_api_keys: model_response_text, is_error_response = "錯誤：請在側邊欄設定至少一個有效的 Gemini API 金鑰。", True
                elif not selected_model_name: model_response_text, is_error_response = "錯誤：請在側邊欄選擇一個 Gemini 模型。", True
                else:
                    model_response_text = call_gemini_api(
                        prompt_parts=full_prompt_parts, api_keys_list=valid_gemini_api_keys, selected_model=selected_model_name,
                        global_rpm=st.session_state.get("global_rpm_limit", 5), global_tpm=st.session_state.get("global_tpm_limit", 200000),
                        generation_config_dict=generation_config, cached_content_name=selected_cache_name_for_api
                    )
                    if model_response_text.startswith("錯誤："):
                        is_error_response = True
                        logger.error(f"Gemini call failed. Response: {model_response_text}")
            except Exception as e:
                logger.exception("Unexpected error during Gemini interaction step:")
                model_response_text, is_error_response = f"處理您的請求時發生未預期的錯誤： {str(e)}", True
            st.session_state.chat_history.append({"role": "model", "parts": [model_response_text], "is_error": is_error_response})
            st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main_app_logic()
    except Exception as e:
        fallback_logger = logging.getLogger(__name__)
        fallback_logger.exception("An unhandled exception occurred in main_app_logic:")

        st.error(f"""
        😞 應用程式執行時發生嚴重錯誤 😞
        很抱歉，應用程式遇到一個未預期的問題，可能無法正常運作。
        請嘗試重新整理頁面。如果問題持續發生，請聯繫技術支援。
        **錯誤詳細資訊:**
        類型: {type(e).__name__}
        訊息: {str(e)}
        """)
