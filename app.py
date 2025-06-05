import streamlit as st
import pandas as pd
import os
import yfinance as yf
from datetime import datetime, timedelta
from fredapi import Fred
import requests
import io
import google.generativeai as genai
import time

# Set page config
st.set_page_config(
    page_title="金融分析與洞察助理 (由 Gemini 驅動)",
    layout="wide"
)

# --- Function to load custom CSS ---
def load_custom_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("警告：style.css 檔案未找到。將使用預設樣式。")
    except Exception as e:
        st.error(f"載入自訂 CSS 時發生錯誤: {e}")

# --- Load CSS and Apply Theme Wrapper ---
load_custom_css()

# Apply a global div with the theme class.
st.markdown(f"<div class='theme-{st.session_state.get('active_theme', 'dark')}'>", unsafe_allow_html=True)

# --- Inject Dynamic Font Size CSS ---
font_size_css_map = {
    "小": "0.875rem", # Approx 14px if base is 16px
    "中": "1rem",    # Approx 16px (base)
    "大": "1.125rem"  # Approx 18px
}
selected_font_size_value = font_size_css_map.get(st.session_state.get("font_size_name", "中"), "1rem")

font_override_style = f"""
<style>
html {{
    font-size: {selected_font_size_value} !important;
}}
/* Add any element-specific overrides here if needed, e.g.: */
/*
.stButton button {{ font-size: 0.9em !important; }}
.stTextInput input {{ font-size: 1em !important; }}
*/
</style>
"""
st.markdown(font_override_style, unsafe_allow_html=True)

# API Key Definitions
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
    for key_name_snake_case in api_keys_info.keys():
        # Convert snake_case to UPPER_SNAKE_CASE for st.secrets
        secret_key_name = key_name_snake_case.upper()
        st.session_state[key_name_snake_case] = st.secrets.get(secret_key_name, "")
    st.session_state.initialized_keys = True

# Gemini Model Definitions
available_models = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]

# Initialize session state for Model Settings if not already done
if 'initialized_model_settings' not in st.session_state:
    st.session_state.selected_model_name = available_models[0]
    st.session_state.global_rpm_limit = 5
    st.session_state.global_tpm_limit = 200000
    st.session_state.initialized_model_settings = True

# Default Main Gemini Prompt
DEFAULT_MAIN_GEMINI_PROMPT = """請你分析我提供的所有文字檔。
你的任務是整理這些檔案中包含的社群媒體貼文。
請嚴格依照以下指示呈現結果：
1.  **來源識別**：確認每個貼文的原始檔案名稱。
2.  **內容摘要**：對每個貼文進行簡潔摘要。
3.  **情緒分析**：判斷每個貼文表達的情緒（例如，正面、負面、中性）。
4.  **關鍵主題**：提取每個貼文討論的核心主題。
5.  **建議行動**：如果貼文暗示了某種行動或建議，請明確指出。
請確保最終輸出結果嚴格遵循上述所有指示。"""

# Initialize session state for Prompt Settings if not already done
if 'initialized_prompt_settings' not in st.session_state:
    st.session_state.main_gemini_prompt = DEFAULT_MAIN_GEMINI_PROMPT
    st.session_state.initialized_prompt_settings = True

# Initialize session state for File Upload Settings if not already done
if 'initialized_file_upload_settings' not in st.session_state:
    st.session_state.uploaded_files_list = []
    st.session_state.uploaded_file_contents = {}
    st.session_state.initialized_file_upload_settings = True

# Initialize session state for Data Source Settings if not already done
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
    st.session_state.fetch_data_button_clicked = False # To track if button was clicked
    st.session_state.initialized_data_source_settings = True

# Initialize session state for Gemini Interaction Settings if not already done
if 'initialized_gemini_interaction_settings' not in st.session_state:
    st.session_state.chat_history = []
    st.session_state.active_gemini_key_index = 0
    st.session_state.gemini_api_key_usage = {} # {key_value: {'requests': [timestamp], 'tokens': [(timestamp, count)]}}
    st.session_state.gemini_caches_list = []
    st.session_state.selected_cache_for_generation = None
    st.session_state.initialized_gemini_interaction_settings = True

# Initialize Theme Settings
if 'initialized_theme_settings' not in st.session_state:
    st.session_state.active_theme = "dark"  # Default to dark theme
    st.session_state.initialized_theme_settings = True

# Initialize Font Size Settings
if 'initialized_font_settings' not in st.session_state:
    st.session_state.font_size_name = "中"  # Default to medium
    st.session_state.initialized_font_settings = True

# Function to fetch yfinance data
@st.cache_data(ttl=3600)
def fetch_yfinance_data(tickers_str: str, start_date_str: str, end_date_str: str, interval: str):
    data_frames = {}
    errors = []

    if not tickers_str.strip():
        errors.append("Ticker 字串不可為空。")
        return data_frames, errors

    list_of_tickers = [ticker.strip().upper() for ticker in tickers_str.split(',') if ticker.strip()]
    if not list_of_tickers:
        errors.append("未提供有效的 Ticker。")
        return data_frames, errors

    try:
        start_dt = datetime.strptime(start_date_str, "%Y%m%d")
    except ValueError:
        errors.append(f"開始日期格式無效: {start_date_str}。請使用 YYYYMMDD 格式。")
        return data_frames, errors

    try:
        end_dt = datetime.strptime(end_date_str, "%Y%m%d")
        # yfinance 'end' is exclusive, so if we want to include the end_date_str, we might need to add a day.
        # For simplicity as per instructions, we'll use it as is for now, or adjust if necessary.
        # If end_dt is meant to be inclusive for user input, uncomment below:
        # end_dt = end_dt + timedelta(days=1)
    except ValueError:
        errors.append(f"結束日期格式無效: {end_date_str}。請使用 YYYYMMDD 格式。")
        return data_frames, errors

    if start_dt > end_dt:
        errors.append(f"開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。")
        return data_frames, errors

    for ticker in list_of_tickers:
        try:
            df = yf.download(ticker, start=start_dt, end=end_dt, interval=interval, progress=False)
            if df.empty:
                errors.append(f"Ticker {ticker}: 在指定日期範圍內沒有找到數據。")
            else:
                df.reset_index(inplace=True)
                # Convert all column names to string to avoid potential issues with non-string column names
                df.columns = df.columns.astype(str)
                data_frames[ticker] = df
        except Exception as e:
            errors.append(f"下載 Ticker {ticker} 數據時發生錯誤: {str(e)}")
            # Consider adding a small delay here if implementing retries in future
            # import time
            # time.sleep(1)

    return data_frames, errors

# Function to fetch FRED data
@st.cache_data(ttl=86400)
def fetch_fred_data(series_ids_str: str, start_date_str: str, end_date_str: str, api_key: str):
    data_series_dict = {}
    errors = []

    if not api_key:
        errors.append("錯誤：FRED API 金鑰未提供。")
        return data_series_dict, errors

    try:
        fred = Fred(api_key=api_key)
    except Exception as e:
        errors.append(f"FRED API 金鑰初始化失敗: {str(e)}。請檢查您的 API 金鑰。")
        return data_series_dict, errors

    if not series_ids_str.strip():
        errors.append("Series ID 字串不可為空。")
        return data_series_dict, errors

    list_of_series_ids = [sid.strip().upper() for sid in series_ids_str.split(',') if sid.strip()]
    if not list_of_series_ids:
        errors.append("未提供有效的 Series ID。")
        return data_series_dict, errors

    try:
        start_dt = datetime.strptime(start_date_str, "%Y%m%d")
    except ValueError:
        errors.append(f"開始日期格式無效: {start_date_str}。請使用 YYYYMMDD 格式。")
        return data_series_dict, errors

    try:
        end_dt = datetime.strptime(end_date_str, "%Y%m%d")
    except ValueError:
        errors.append(f"結束日期格式無效: {end_date_str}。請使用 YYYYMMDD 格式。")
        return data_series_dict, errors

    if start_dt > end_dt:
        errors.append(f"開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。")
        return data_series_dict, errors

    for series_id in list_of_series_ids:
        try:
            series_data = fred.get_series(series_id, observation_start=start_dt, observation_end=end_dt)
            if series_data.empty:
                errors.append(f"Series ID {series_id}: 在指定日期範圍內沒有找到數據。")
            else:
                df = series_data.to_frame(name=series_id)
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'Date', series_id: 'Value'}, inplace=True)
                # Ensure 'Date' column is datetime type, and 'Value' is numeric
                df['Date'] = pd.to_datetime(df['Date'])
                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                df.dropna(subset=['Value'], inplace=True) # Remove rows where value couldn't be converted
                data_series_dict[series_id] = df
        except ValueError as ve: # More specific exception for invalid series ID
             errors.append(f"Series ID {series_id} 無效或找不到: {str(ve)}")
        except Exception as e:
            errors.append(f"下載 Series ID {series_id} 數據時發生錯誤: {str(e)}")

    return data_series_dict, errors

# Constants for NY Fed Data Fetching
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

# Function to fetch NY Fed Primary Dealer Positions
@st.cache_data(ttl=86400)
def fetch_ny_fed_data():
    all_positions_data = []
    errors = []
    # Assuming header at row index 4, date in first column (index 0) for all files as a simplification.
    HEADER_ROW_ASSUMPTION = 4
    DATE_COLUMN_INDEX_ASSUMPTION = 0

    for url in NY_FED_POSITIONS_URLS_CORRECTED:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status() # Will raise an HTTPError if the HTTP request returned an unsuccessful status code

            excel_content = io.BytesIO(response.content)
            xls = pd.ExcelFile(excel_content)

            # Simplified parsing based on assumption
            df = pd.read_excel(xls, sheet_name=0, header=HEADER_ROW_ASSUMPTION, index_col=DATE_COLUMN_INDEX_ASSUMPTION)

            df.index = pd.to_datetime(df.index, errors='coerce')
            df = df[df.index.notna()] # Remove rows where date could not be parsed

            if df.empty:
                errors.append(f"檔案 {url} 在轉換日期後沒有有效數據。")
                continue

            source_type = None
            target_cols = []

            if "SBN" in url:
                source_type = "SBN"
                # Filter columns that exist in the DataFrame
                target_cols = [col for col in df.columns if str(col).startswith("PDPOSGSC-")]
            elif "SBP2013" in url:
                source_type = "SBP2013"
                target_cols = [col for col in SBP_COLS_TO_SUM["SBP2013"] if col in df.columns]
            elif "SBP2001" in url:
                source_type = "SBP2001"
                target_cols = [col for col in SBP_COLS_TO_SUM["SBP2001"] if col in df.columns]

            if not target_cols:
                errors.append(f"檔案 {url} (類型 {source_type}) 中未找到目標欄位或目標欄位列表為空。")
                continue

            # Ensure target columns are numeric before summing
            df_target = df[target_cols].apply(pd.to_numeric, errors='coerce')

            # Check if all target columns became NaN (e.g. if they were not numeric)
            if df_target.isnull().all().all():
                errors.append(f"檔案 {url} (類型 {source_type}) 的目標欄位 {target_cols} 轉換為數字後均為空值。")
                continue

            daily_sum = df_target.sum(axis=1)
            all_positions_data.append(daily_sum)

        except requests.exceptions.HTTPError as http_err:
            errors.append(f"下載檔案 {url} 時發生 HTTP 錯誤: {http_err}")
        except requests.exceptions.RequestException as req_err:
            errors.append(f"下載檔案 {url} 時發生錯誤: {req_err}")
        except Exception as e:
            errors.append(f"處理檔案 {url} 時發生錯誤: {str(e)}")

    if not all_positions_data:
        return None, errors

    try:
        final_series = pd.concat(all_positions_data)
        # Group by index (date) and take the last non-null value for that date.
        # This handles overlaps where one file might have a more up-to-date value for a given Wednesday.
        final_series = final_series.groupby(final_series.index).last()
        final_series = final_series.sort_index()
        final_series = final_series.ffill() # Forward fill any remaining NaNs

        result_df = final_series.to_frame(name="Total_Dealer_Positions")
        result_df.reset_index(inplace=True)
        result_df.rename(columns={'index': 'Date'}, inplace=True)
        # Ensure Date column is just date, not datetime, if desired (usually it's weekly data)
        # result_df['Date'] = result_df['Date'].dt.date
    except Exception as e:
        errors.append(f"合併和最終處理 NY Fed 數據時發生錯誤: {str(e)}")
        return None, errors

    return result_df, errors

# Gemini API Call Function
def call_gemini_api(prompt_parts: list, api_keys_list: list, selected_model: str,
                    global_rpm: int, global_tpm: int, # TPM not strictly enforced yet
                    generation_config_dict: dict = None, cached_content_name: str = None):

    if not api_keys_list:
        return "錯誤：未提供有效的 Gemini API 金鑰。"

    active_key_index = st.session_state.get('active_gemini_key_index', 0)
    current_api_key = api_keys_list[active_key_index]

    # Simplified RPM Check (non-blocking, returns error if limit would be hit)
    now = time.time()
    if current_api_key not in st.session_state.gemini_api_key_usage:
        st.session_state.gemini_api_key_usage[current_api_key] = {'requests': [], 'tokens': []}

    # Remove timestamps older than 60 seconds
    st.session_state.gemini_api_key_usage[current_api_key]['requests'] = \
        [ts for ts in st.session_state.gemini_api_key_usage[current_api_key]['requests'] if now - ts < 60]

    if len(st.session_state.gemini_api_key_usage[current_api_key]['requests']) >= global_rpm:
        # Rotate key immediately if current one is rate-limited for this attempt
        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(api_keys_list)
        return f"錯誤：API 金鑰 {current_api_key[:10]}... RPM 達到上限 ({global_rpm})。請稍後重試或切換金鑰。"

    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel(model_name=selected_model) # Ensure model_name is passed

        gen_config_obj = None
        if generation_config_dict:
            gen_config_obj = genai.types.GenerationConfig(**generation_config_dict)

        # Construct the full prompt string from parts for API call
        # The API expects a list of parts, but for a simple text prompt, it's often a single string.
        # If prompt_parts is already structured for the API (e.g. list of TextPart or similar), use as is.
        # For this initial implementation, assuming prompt_parts is a list of strings to be joined.
        final_prompt_content = "\n".join(map(str, prompt_parts))

        response = model.generate_content(
            final_prompt_content, # Pass the combined string
            generation_config=gen_config_obj,
            safety_settings=None,
            tools=None,
            tool_config=None,
            cached_content=cached_content_name
        )

        # Record usage
        st.session_state.gemini_api_key_usage[current_api_key]['requests'].append(now)
        token_count = 0
        if response.usage_metadata and response.usage_metadata.total_token_count:
            token_count = response.usage_metadata.total_token_count
            st.session_state.gemini_api_key_usage[current_api_key]['tokens'].append((now, token_count))

        st.session_state.active_gemini_key_index = (active_key_index + 1) % len(api_keys_list)

        # Handle cases where response.text might be missing
        if response.parts:
            return "".join(part.text for part in response.parts if hasattr(part, 'text'))
        elif response.text: # Fallback for older versions or different response structures
             return response.text
        else: # If no text or parts, likely an issue or non-text response
            return "模型未返回文字內容。"


    except genai.types.BlockedPromptException as bpe:
        return f"錯誤：提示詞被 Gemini API 封鎖。原因: {bpe}"
    except genai.types.generation_types.StopCandidateException as sce:
        return f"錯誤：內容生成因安全原因或其他限制而停止。原因: {sce}"
    except Exception as e:
        # Attempt to get more detailed error message if available
        error_message = str(e)
        if hasattr(e, 'message'): # Some specific API errors might have a 'message' attribute
            error_message = e.message
        elif hasattr(e, 'args') and e.args: # General exceptions often store info in args
            error_message = str(e.args[0])

        # Log the full error for debugging if needed, but return a user-friendly one
        # print(f"Gemini API Error: {e}") # For server-side logging
        return f"呼叫 Gemini API 時發生錯誤: {error_message}"


# Sidebar
st.sidebar.title("⚙️ 全域設定與工具")

# Theme Toggle UI & Font Size
st.sidebar.header("🎨 外觀主題與字體")
active_theme = st.session_state.get("active_theme", "dark")
current_theme_label = "暗色模式 (Gemini)" if active_theme == "dark" else "亮色模式 (預設)"
toggle_label = f"切換到 {'亮色模式 (預設)' if active_theme == 'dark' else '暗色模式 (Gemini)'}"
new_toggle_state_is_dark = st.sidebar.toggle(
    toggle_label,
    value=(active_theme == "dark"),
    key="theme_toggle_widget",
    help="點擊切換亮暗主題"
)
if new_toggle_state_is_dark and active_theme == "light":
    st.session_state.active_theme = "dark"
    st.experimental_rerun()
elif not new_toggle_state_is_dark and active_theme == "dark":
    st.session_state.active_theme = "light"
    st.experimental_rerun()
st.sidebar.caption(f"目前主題: {current_theme_label}")

st.sidebar.markdown("##### 選擇字體大小:")
font_cols = st.sidebar.columns(3)
if font_cols[0].button("A- (小)", key="font_small_button", use_container_width=True):
    st.session_state.font_size_name = "小"
    st.experimental_rerun()
if font_cols[1].button("A (中)", key="font_medium_button", use_container_width=True):
    st.session_state.font_size_name = "中"
    st.experimental_rerun()
if font_cols[2].button("A+ (大)", key="font_large_button", use_container_width=True):
    st.session_state.font_size_name = "大"
    st.experimental_rerun()
st.sidebar.caption(f"目前字體: {st.session_state.get('font_size_name', '中')}")
st.sidebar.markdown("---")

# API Key Management
st.sidebar.header("🔑 API 金鑰管理")
st.sidebar.caption("請在此處管理您的 API 金鑰。")
# ... (rest of the sidebar code for API keys, model settings, etc. remains unchanged from this point)

# Check for essential API keys and display a warning if missing
gemini_keys_present = any(st.session_state.get(f"gemini_api_key_{i+1}", "") for i in range(3))
if not gemini_keys_present:
    st.sidebar.warning("警告：至少需要一個有效的 Gemini API 金鑰才能使用 Gemini 分析功能。")

# Create text input fields for each API key
for key_name_snake_case, key_label in api_keys_info.items():
    st.session_state[key_name_snake_case] = st.sidebar.text_input(
        key_label,
        type="password",
        value=st.session_state[key_name_snake_case],
        key=f"{key_name_snake_case}_input" # Unique key for each widget
    )

st.sidebar.success("API 金鑰已更新並儲存在會話中。") # Optional confirmation

st.sidebar.header("🤖 Gemini 模型設定")
st.sidebar.caption("選擇並配置要使用的 Gemini 模型。")

# Gemini Model Selection
st.session_state.selected_model_name = st.sidebar.selectbox(
    "選擇 Gemini 模型:",
    options=available_models,
    index=available_models.index(st.session_state.selected_model_name), # Ensure current session value is selected
    key="selected_model_name_selector"
)

# Global RPM Setting
st.session_state.global_rpm_limit = st.sidebar.number_input(
    "全域 RPM (每分鐘請求數):",
    min_value=1,
    value=st.session_state.global_rpm_limit,
    step=1,
    key="global_rpm_limit_input"
)

# Global TPM Setting
st.session_state.global_tpm_limit = st.sidebar.number_input(
    "全域 TPM (每分鐘詞元數):",
    min_value=1000,
    value=st.session_state.global_tpm_limit,
    step=10000,
    key="global_tpm_limit_input"
)
st.sidebar.caption("注意：請參考 Gemini 官方文件了解不同模型的具體 RPM/TPM 限制。")

st.sidebar.header("📝 主要提示詞")
st.sidebar.caption("設定用於指導 Gemini 分析的主要提示詞。")

# Main Gemini Prompt Text Area
st.session_state.main_gemini_prompt = st.sidebar.text_area(
    "主要分析提示詞 (System Prompt):",
    value=st.session_state.main_gemini_prompt,
    height=300,
    key="main_gemini_prompt_input"
)

# Prompt File Uploader
uploaded_prompt_file = st.sidebar.file_uploader(
    "或從 .txt 檔案載入提示詞:",
    type=["txt"],
    key="prompt_file_uploader"
)

if uploaded_prompt_file is not None:
    prompt_content = uploaded_prompt_file.read().decode("utf-8")
    st.session_state.main_gemini_prompt = prompt_content
    # The text_area will update automatically on the next Streamlit rerun
    # because its value is bound to st.session_state.main_gemini_prompt.
    # For immediate visual feedback if desired, one could add:
    # st.sidebar.success("提示詞已從檔案載入！")
    # However, this might be slightly redundant if the text_area updates promptly.

st.sidebar.header("🧹 快取管理")
st.sidebar.caption("管理應用程式的數據快取。")

if st.sidebar.button("清除所有數據快取", key="clear_all_cache_button"):
    st.cache_data.clear()
    st.sidebar.success("所有數據快取已成功清除！下次獲取數據時將從源頭重新載入。")
st.sidebar.caption("點擊此按鈕將清除所有已快取的 yfinance, FRED 及 NY Fed 數據。")

st.sidebar.header("🧠 Gemini 內容快取")
st.session_state.cache_display_name_input = st.sidebar.text_input(
    "要快取的內容名稱 (例如 system_prompt_cache):",
    value=st.session_state.get("cache_display_name_input", "system_prompt_main"), # Provide default
    key="cache_display_name_input_widget"
)
st.session_state.cache_content_input = st.sidebar.text_area(
    "要快取的內容 (通常是 System Prompt):",
    value=st.session_state.get("cache_content_input", st.session_state.get("main_gemini_prompt","")), # Default to main prompt
    height=150,
    key="cache_content_input_widget"
)
st.session_state.cache_ttl_seconds_input = st.sidebar.number_input(
    "快取 TTL (秒, e.g., 3600 for 1 hour):",
    min_value=60,
    value=st.session_state.get("cache_ttl_seconds_input",3600),
    key="cache_ttl_input_widget"
)

if st.sidebar.button("創建/更新內容快取", key="create_cache_button"):
    gemini_keys_for_cache = [
        st.session_state.get("gemini_api_key_1",""),
        st.session_state.get("gemini_api_key_2",""),
        st.session_state.get("gemini_api_key_3","")
    ]
    valid_gemini_key_for_cache = next((key for key in gemini_keys_for_cache if key), None)
    selected_model_for_cache = st.session_state.get("selected_model_name", "gemini-1.0-pro") # Default if not set

    if valid_gemini_key_for_cache and st.session_state.cache_display_name_input and st.session_state.cache_content_input:
        try:
            genai.configure(api_key=valid_gemini_key_for_cache) # Configure for CachingClient or direct calls
            ttl_str = f"{st.session_state.cache_ttl_seconds_input}s"
            # Ensure model name is in "models/model-name" format for caching
            model_for_caching_api = f"models/{selected_model_for_cache}" if not selected_model_for_cache.startswith("models/") else selected_model_for_cache

            cached_content = genai.create_cached_content(
                model=model_for_caching_api,
                display_name=st.session_state.cache_display_name_input,
                system_instruction=st.session_state.cache_content_input, # Using system_instruction for content
                ttl=ttl_str
            )
            st.sidebar.success(f"快取 '{cached_content.display_name}' 已創建/更新。\n名稱: {cached_content.name}")
            # Refresh cache list after creation
            st.session_state.gemini_caches_list = list(genai.list_cached_contents(api_key=valid_gemini_key_for_cache))
        except Exception as e:
            st.sidebar.error(f"創建快取失敗: {str(e)}")
    else:
        st.sidebar.warning("請提供有效的 Gemini API 金鑰、快取名稱和快取內容。")

if st.sidebar.button("列出可用快取", key="list_caches_button"):
    gemini_keys_for_cache_list = [
        st.session_state.get("gemini_api_key_1",""),
        st.session_state.get("gemini_api_key_2",""),
        st.session_state.get("gemini_api_key_3","")
    ]
    valid_gemini_key_for_cache_list = next((key for key in gemini_keys_for_cache_list if key), None)
    if valid_gemini_key_for_cache_list:
        try:
            genai.configure(api_key=valid_gemini_key_for_cache_list)
            st.session_state.gemini_caches_list = list(genai.list_cached_contents())
            if not st.session_state.gemini_caches_list:
                st.sidebar.info("目前沒有可用的內容快取。")
        except Exception as e:
            st.sidebar.error(f"列出快取失敗: {str(e)}")
            st.session_state.gemini_caches_list = [] # Clear on error
    else:
        st.sidebar.warning("請先設定有效的 Gemini API 金鑰以列出快取。")


if st.session_state.gemini_caches_list:
    cache_options = {"(不使用快取)": None}
    cache_options.update({f"{c.display_name} ({c.name.split('/')[-1][:8]}...)": c.name for c in st.session_state.gemini_caches_list})

    # Find current index for selectbox
    current_selected_cache_name = st.session_state.get("selected_cache_for_generation", None)
    options_list = list(cache_options.values())
    try:
        current_index = options_list.index(current_selected_cache_name)
    except ValueError:
        current_index = 0 # Default to "(不使用快取)"

    selected_display_key = st.sidebar.selectbox(
        "選擇一個快取用於下次生成:",
        options=list(cache_options.keys()),
        index=current_index, # Use the found index
        key="select_cache_dropdown"
    )
    st.session_state.selected_cache_for_generation = cache_options.get(selected_display_key)

st.session_state.cache_name_to_delete_input = st.sidebar.text_input(
    "要刪除的快取名稱 (projects/.../cachedContents/...):",
    value=st.session_state.get("cache_name_to_delete_input",""),
    key="cache_name_to_delete_input_widget"
)
if st.sidebar.button("刪除指定快取", key="delete_cache_button"):
    cache_to_delete = st.session_state.cache_name_to_delete_input
    if cache_to_delete:
        gemini_keys_for_delete = [
            st.session_state.get("gemini_api_key_1",""),
            st.session_state.get("gemini_api_key_2",""),
            st.session_state.get("gemini_api_key_3","")
        ]
        valid_gemini_key_for_delete = next((key for key in gemini_keys_for_delete if key), None)
        if valid_gemini_key_for_delete:
            try:
                genai.configure(api_key=valid_gemini_key_for_delete)
                genai.delete_cached_content(name=cache_to_delete)
                st.sidebar.success(f"快取 {cache_to_delete} 已成功刪除。")
                # Refresh cache list
                st.session_state.gemini_caches_list = list(genai.list_cached_contents())
                if st.session_state.selected_cache_for_generation == cache_to_delete:
                    st.session_state.selected_cache_for_generation = None # Reset if deleted cache was selected
            except Exception as e:
                st.sidebar.error(f"刪除快取 {cache_to_delete} 失敗: {str(e)}")
        else:
            st.sidebar.warning("請設定有效的 Gemini API 金鑰以刪除快取。")
    else:
        st.sidebar.warning("請輸入要刪除的快取名稱。")

# Main page
st.title("金融分析與洞察助理")

st.header("📄 步驟一：上傳與檢視文件")
st.caption("請上傳您需要分析的文字檔案。")

# File Uploader
uploaded_files_from_widget = st.file_uploader(
    "請上傳您需要分析的文字檔案 (可多選 .txt):",
    type=["txt"],
    accept_multiple_files=True,
    key="file_uploader_widget"
)

# Process and store uploaded files
if uploaded_files_from_widget:
    st.session_state.uploaded_files_list = uploaded_files_from_widget
    st.session_state.uploaded_file_contents = {} # Clear old contents
    for file in st.session_state.uploaded_files_list:
        try:
            content = file.read().decode("utf-8")
            st.session_state.uploaded_file_contents[file.name] = content
        except Exception as e:
            st.error(f"讀取檔案 {file.name} 時發生錯誤: {e}")
    if st.session_state.uploaded_file_contents: # Check if any file was successfully read
        st.success(f"成功上傳並讀取 {len(st.session_state.uploaded_file_contents)} 個檔案。")

# Display uploaded file information and previews
if st.session_state.uploaded_files_list:
    st.subheader("已上傳文件預覽:")
    if not st.session_state.uploaded_file_contents and uploaded_files_from_widget:
        # This case can happen if all files failed to read in the block above
        st.warning("所有上傳的檔案都無法成功讀取內容。請檢查檔案格式或內容。")
    elif not st.session_state.uploaded_file_contents and not uploaded_files_from_widget:
        # This case implies files were in session_state.uploaded_files_list from a previous run,
        # but their contents were cleared, or uploader is now empty. This should ideally not be hit
        # if logic is correct, but acts as a fallback.
        st.info("之前上傳的檔案內容已清除或目前沒有選擇檔案。請重新上傳。")

    for file_name, content in st.session_state.uploaded_file_contents.items():
        with st.expander(f"檔名: {file_name} (點擊展開/收起預覽)", expanded=False):
            st.text(content[:500] + "..." if len(content) > 500 else content)
elif not uploaded_files_from_widget: # Only show this if the uploader is also empty in the current run
    st.info("請上傳文字檔案以開始分析。")


st.header("📊 步驟二：引入外部數據 (可選)")
# st.caption("選擇並載入 yfinance, FRED, NY Fed 等外部市場與總經數據。") # Caption is part of expander now

with st.expander("📊 步驟二：選擇並載入外部數據 (點擊展開/收起)", expanded=False):
    st.caption("選擇 yfinance, FRED, NY Fed 等外部市場與總經數據源，設定參數並載入數據。")

    # --- Row 1: Select All & Data Source Checkboxes ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        select_all_sources_widget = st.checkbox(
            "🌍 全選/取消所有數據源",
            value=st.session_state.select_all_sources,
            key="select_all_sources_cb"
        )
        if select_all_sources_widget != st.session_state.select_all_sources:
            st.session_state.select_all_sources = select_all_sources_widget
            st.session_state.select_yfinance = select_all_sources_widget
            st.session_state.select_fred = select_all_sources_widget
            st.session_state.select_ny_fed = select_all_sources_widget
            st.experimental_rerun()
    with col2:
        st.session_state.select_yfinance = st.checkbox(
            "📈 yfinance 股市數據",
            value=st.session_state.select_yfinance,
            key="select_yfinance_cb" # Give a key to ensure it's treated as a separate widget
        )
    with col3:
        st.session_state.select_fred = st.checkbox(
            "🏦 FRED 總經數據",
            value=st.session_state.select_fred,
            key="select_fred_cb"
        )
    with col4:
        st.session_state.select_ny_fed = st.checkbox(
            "🇺🇸 NY Fed 一級交易商數據",
            value=st.session_state.select_ny_fed,
            key="select_ny_fed_cb"
        )

    # --- Row 2: Date Inputs ---
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        st.session_state.data_start_date = st.text_input(
            "輸入開始日期 (YYYYMMDD):",
            value=st.session_state.data_start_date,
            key="data_start_date_input"
        )
    with date_col2:
        st.session_state.data_end_date = st.text_input(
            "輸入結束日期 (YYYYMMDD):",
            value=st.session_state.data_end_date,
            key="data_end_date_input"
        )

    # --- Row 3: Conditional Inputs for yfinance and FRED ---
    param_col1, param_col2 = st.columns(2)
    with param_col1:
        if st.session_state.select_yfinance:
            st.session_state.yfinance_tickers = st.text_input(
                "yfinance 股票代碼 (逗號分隔):",
                value=st.session_state.yfinance_tickers,
                key="yfinance_tickers_input"
            )
            interval_options = {"每日": "1d", "每週": "1wk", "每小時": "1h", "每5分鐘": "5m"}
            # Ensure the current session state value is a valid option for index()
            current_interval_label = st.session_state.yfinance_interval_label
            if current_interval_label not in interval_options: # Fallback if label is somehow invalid
                current_interval_label = list(interval_options.keys())[0]
                st.session_state.yfinance_interval_label = current_interval_label

            st.session_state.yfinance_interval_label = st.selectbox(
                "yfinance 數據週期:",
                options=list(interval_options.keys()),
                index=list(interval_options.keys()).index(current_interval_label),
                key="yfinance_interval_label_select"
            )
    with param_col2:
        if st.session_state.select_fred:
            st.session_state.fred_series_ids = st.text_input(
                "FRED Series ID (逗號分隔):",
                value=st.session_state.fred_series_ids,
                key="fred_series_ids_input"
            )

    st.markdown("---") # Visual separator

    # --- Row 4: Fetch Data Button ---
    # Using st.session_state.fetch_data_button_clicked to control display of "no data" message
    if st.button("🔍 獲取並預覽選定數據", key="fetch_data_button"):
        st.session_state.fetch_data_button_clicked = True
        st.session_state.fetched_data_preview = {}
        st.session_state.fetch_errors = []

        something_selected = (st.session_state.select_yfinance or
                              st.session_state.select_fred or
                              st.session_state.select_ny_fed)

        if not something_selected:
            st.warning("請至少選擇一個數據源。")
            st.session_state.fetch_data_button_clicked = False
        else:
            with st.spinner("正在獲取數據，請稍候..."):
                if st.session_state.select_yfinance:
                    actual_interval = interval_options[st.session_state.yfinance_interval_label]
                    yfinance_data, yfinance_errs = fetch_yfinance_data(
                        st.session_state.yfinance_tickers,
                        st.session_state.data_start_date,
                        st.session_state.data_end_date,
                        actual_interval
                    )
                    if yfinance_data:
                        st.session_state.fetched_data_preview["yfinance"] = yfinance_data
                    if yfinance_errs:
                        st.session_state.fetch_errors.extend([f"[yfinance] {e}" for e in yfinance_errs])

                if st.session_state.select_fred:
                    fred_api_key = st.session_state.get("fred_api_key", "")
                    if not fred_api_key:
                         st.session_state.fetch_errors.append("[FRED] 錯誤：FRED API 金鑰未在側邊欄設定。請先設定。")
                    else:
                        fred_data, fred_errs = fetch_fred_data(
                            st.session_state.fred_series_ids,
                            st.session_state.data_start_date,
                            st.session_state.data_end_date,
                            fred_api_key
                        )
                        if fred_data:
                            st.session_state.fetched_data_preview["fred"] = fred_data
                        if fred_errs:
                            st.session_state.fetch_errors.extend([f"[FRED] {e}" for e in fred_errs])

                if st.session_state.select_ny_fed:
                    ny_fed_data, ny_fed_errs = fetch_ny_fed_data()
                    if ny_fed_data is not None:
                        st.session_state.fetched_data_preview["ny_fed"] = ny_fed_data
                    if ny_fed_errs:
                        st.session_state.fetch_errors.extend([f"[NY Fed] {e}" for e in ny_fed_errs])

    # --- Data Preview Area (Conditional Display) ---
    if st.session_state.fetch_errors: # Ensure errors are always displayed if they exist
        st.subheader("數據獲取錯誤：")
        for err_msg in st.session_state.fetch_errors: # Iterate through messages
            st.error(err_msg) # Display each error message

    if st.session_state.fetched_data_preview:
        st.subheader("已獲取數據預覽:")
        if "yfinance" in st.session_state.fetched_data_preview:
            st.markdown("#### yfinance 數據:")
            for ticker, df_yf in st.session_state.fetched_data_preview["yfinance"].items():
                with st.expander(f"Ticker: {ticker} (共 {len(df_yf)} 行)", expanded=False):
                    st.dataframe(df_yf.head())

        if "fred" in st.session_state.fetched_data_preview:
            st.markdown("#### FRED 數據:")
            for series_id, df_fred in st.session_state.fetched_data_preview["fred"].items():
                with st.expander(f"Series ID: {series_id} (共 {len(df_fred)} 行)", expanded=False):
                    st.dataframe(df_fred.head())

        if "ny_fed" in st.session_state.fetched_data_preview:
            df_ny = st.session_state.fetched_data_preview["ny_fed"]
            if not df_ny.empty:
                st.markdown("#### NY Fed 一級交易商數據:")
                with st.expander(f"NY Fed 總持有量 (共 {len(df_ny)} 行)", expanded=False):
                    st.dataframe(df_ny.head())

        has_data_in_preview = any(
            (isinstance(data_source, dict) and data_source) or
            (isinstance(data_source, pd.DataFrame) and not data_source.empty)
            for data_source in st.session_state.fetched_data_preview.values()
        )

        if has_data_in_preview and not st.session_state.fetch_errors:
             st.success("數據已成功載入並準備好用於分析。")
        elif not has_data_in_preview and not st.session_state.fetch_errors and st.session_state.fetch_data_button_clicked :
             st.info("未獲取到任何數據。請檢查您的選擇和輸入，或確認數據源在該時段有數據。")

    elif st.session_state.fetch_data_button_clicked and not st.session_state.fetch_errors:
        st.info("未獲取到任何數據。請檢查您的選擇和輸入，或確認數據源在該時段有數據。")


st.header("💬 步驟三：與 Gemini 進行分析與討論")

# Chat history display
chat_container = st.container(height=400)
with chat_container:
    for message in st.session_state.chat_history:
        avatar_icon = "👤" if message["role"] == "user" else "✨" # User: 👤, Model: ✨ (or 🤖)
        with st.chat_message(message["role"], avatar=avatar_icon):
            if message["role"] == "model" and message.get("is_error", False): # Check for error flag
                st.error(message["parts"][0])
            else:
                st.markdown(message["parts"][0])

# User input
user_input = st.chat_input("向 Gemini 提問或給出指令：", key="gemini_user_input")

if user_input:
    st.session_state.chat_history.append({"role": "user", "parts": [user_input]})

    with st.spinner("Gemini 正在思考中，請稍候..."):
        model_response_text = ""
        is_error_response = False
        try:
            # Prepare prompt parts for Gemini
            full_prompt_parts = []
            if st.session_state.get("main_gemini_prompt"):
                full_prompt_parts.append(f"**主要指示 (System Prompt):**\n{st.session_state.main_gemini_prompt}\n\n---\n")

            uploaded_texts_str = ""
            if st.session_state.get("uploaded_file_contents"):
                uploaded_texts_str += "**已上傳文件內容摘要:**\n"
                for file_name, content in st.session_state.uploaded_file_contents.items():
                    uploaded_texts_str += f"檔名: {file_name}\n內容片段:\n{content[:1000]}...\n\n"
                full_prompt_parts.append(uploaded_texts_str + "---\n")

            external_data_str = ""
            if st.session_state.get("fetched_data_preview"):
                external_data_str += "**已引入的外部市場與總經數據摘要:**\n"
                for source, data_items in st.session_state.fetched_data_preview.items():
                    external_data_str += f"\n來源: {source.upper()}\n"
                    if source == "yfinance" or source == "fred":
                        if isinstance(data_items, dict):
                            for item_name, df_item in data_items.items():
                                if isinstance(df_item, pd.DataFrame):
                                    external_data_str += f"  {item_name} (最近幾筆):\n{df_item.tail(3).to_string()}\n"
                    elif source == "ny_fed" and isinstance(data_items, pd.DataFrame) and not data_items.empty:
                         external_data_str += f"  NY Fed 總持有量 (最近幾筆):\n{data_items.tail(3).to_string()}\n"
                full_prompt_parts.append(external_data_str + "---\n")

            full_prompt_parts.append(f"**使用者當前問題/指令:**\n{user_input}")

            gemini_api_keys_raw = [
                st.session_state.get("gemini_api_key_1", ""),
                st.session_state.get("gemini_api_key_2", ""),
                st.session_state.get("gemini_api_key_3", "")
            ]
            valid_gemini_api_keys = [key for key in gemini_api_keys_raw if key and key.strip()]

            selected_model_name = st.session_state.get("selected_model_name", "gemini-1.0-pro")
            global_rpm_limit = st.session_state.get("global_rpm_limit", 5)
            global_tpm_limit = st.session_state.get("global_tpm_limit", 200000)

            generation_config = {
                "temperature": 0.7, "top_p": 1.0, "top_k": 32, "max_output_tokens": 8192,
            }
            selected_cache_name_for_api = st.session_state.get("selected_cache_for_generation", None)

            if not valid_gemini_api_keys:
                model_response_text = "錯誤：請在側邊欄設定至少一個有效的 Gemini API 金鑰。"
                is_error_response = True
            elif not selected_model_name:
                model_response_text = "錯誤：請在側邊欄選擇一個 Gemini 模型。"
                is_error_response = True
            else:
                model_response_text = call_gemini_api(
                    prompt_parts=full_prompt_parts,
                    api_keys_list=valid_gemini_api_keys,
                    selected_model=selected_model_name,
                    global_rpm=global_rpm_limit,
                    global_tpm=global_tpm_limit,
                    generation_config_dict=generation_config,
                    cached_content_name=selected_cache_name_for_api
                )
                if model_response_text.startswith("錯誤："):
                    is_error_response = True

        except Exception as e: # Catch any unexpected error during prompt assembly or pre-API call logic
            model_response_text = f"處理您的請求時發生未預期的錯誤： {str(e)}"
            is_error_response = True

        st.session_state.chat_history.append({"role": "model", "parts": [model_response_text], "is_error": is_error_response})
        st.experimental_rerun()

# --- This div closure MUST be the VERY LAST THING in your app.py script ---
st.markdown("</div>", unsafe_allow_html=True)
