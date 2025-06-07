# config/app_settings.py

# --- General App Settings ---
APP_NAME = "Wolf_V5" # Example, if needed
PROMPTS_DIR = "prompts" # Used in sidebar and main_page for agent prompts
DEFAULT_LOG_FILENAME = "streamlit.log" # Default name for the main application log file
DEFAULT_CSS_FILE = "style.css" # Default CSS file name

# --- Gemini API Configuration ---
DEFAULT_GEMINI_RPM_LIMIT = 3
DEFAULT_GEMINI_TPM_LIMIT = 100000 # Max tokens per minute (overall capacity)
TOKEN_SAFETY_FACTOR = 0.90 # Safety factor for calculating effective token limit for prompts
# Default generation config for Gemini
DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 32,
    "max_output_tokens": 8192 # Max tokens for a single response from the model
}

# --- Data Paths ---
# For local development, ensure Wolf_Data and its subdirectories exist in user's home.
# For Colab, these paths point to Google Drive after mounting.
USER_HOME_DIR = "~" # Placeholder, will be expanded by os.path.expanduser
BASE_DATA_DIR_NAME = "Wolf_Data" # Base directory name for both local and Colab

# Specific subdirectories within BASE_DATA_DIR_NAME
SOURCE_DOCUMENTS_DIR_NAME = "source_documents"
APP_LOG_DIR_NAME = "logs" # Used in app.py for log file path
CORE_DOC_SCAN_EXTENSIONS = (".txt", ".md") # Allowed extensions when scanning for core documents

# Colab specific base path prefix (after Drive mount)
COLAB_DRIVE_BASE_PATH = "/content/drive/MyDrive"

# --- Cache Settings ---
DEFAULT_CACHE_TTL_SECONDS = 3600 # General default for st.cache_data (e.g., model catalog)
YFINANCE_CACHE_TTL_SECONDS = 3600 # Cache TTL for yfinance data
FRED_CACHE_TTL_SECONDS = 86400    # Cache TTL for FRED data
DEFAULT_CACHE_DISPLAY_NAME = "my_default_cache" # Default name for Gemini content cache display

# --- Default Data Fetcher Settings ---
DEFAULT_YFINANCE_TICKERS = "SPY, ^GSPC, BTC-USD, ETH-USD"
DEFAULT_FRED_SERIES_IDS = "GDP,CPIAUCSL"
DEFAULT_YFINANCE_INTERVAL_LABEL = "1 Day" # Key from interval_options
NY_FED_REQUEST_TIMEOUT_SECONDS = 30 # Request timeout for NY Fed data

# --- UI Settings & Mappings ---
DEFAULT_THEME = "Light" # "Light" or "Dark"
DEFAULT_FONT_SIZE_NAME = "Medium" # "Small", "Medium", "Large"
TEXT_PREVIEW_MAX_CHARS = 500 # Max characters for text file previews
LOG_DISPLAY_HEIGHT = 300 # Default height for the log display text area in UI
MAX_UI_LOG_ENTRIES = 300 # Max number of log entries to keep for UI display
DEFAULT_CHAT_CONTAINER_HEIGHT = 400 # Default height for chat message container
AGENT_BUTTONS_PER_ROW = 3 # Max agent buttons per row on main page
ALLOWED_UPLOAD_FILE_TYPES = ["txt", "csv", "xls", "xlsx", "md", "py", "json", "xml", "html", "css", "js"]

# yfinance數據的時間間隔選項
YFINANCE_INTERVAL_OPTIONS = { # Renamed from interval_options for clarity
    "1 Day": "1d",
    "5 Days": "5d",
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
    "5 Years": "5y",
    "Max": "max"
}

# 字體大小名稱到CSS class的映射
FONT_SIZE_CSS_MAP = { # Renamed from font_size_css_map
    "Small": "font-small",
    "Medium": "font-medium",
    "Large": "font-large",
}

# --- Prompts ---
# 預設的主要Gemini提示詞
DEFAULT_MAIN_GEMINI_PROMPT = """
請作為一個多才多藝的AI助理，根據我提供的上下文資訊（如上傳的檔案內容、外部數據源的數據）和我的問題，提供精確且有深度的回答。
請確保你的回答不僅僅是重複資訊，而是能提供洞察、分析或創造性的內容。
如果涉及到數據分析，請清晰地展示你的分析過程和結果。
如果需要，請向我提問以澄清我的需求。
"""

# --- External Service URLs & Configs ---
# 紐約聯儲（NY FED）持倉數據的URL列表
NY_FED_POSITIONS_URLS = [ # Renamed from NY_FED_POSITIONS_URLS_CORRECTED
    {
        "name": "SOMA Holdings (Securities Held Outright)",
        "url": "https://markets.newyorkfed.org/api/soma/summary.xml",
        "type": "xml"
    },
    {
        "name": "Agency MBS Holdings (Agency Mortgage-Backed Securities)",
        "url": "https://markets.newyorkfed.org/api/ambs/all/summary.xml",
        "type": "xml"
    }
]

# 用於處理SBP數據的列名映射或需要求和的列 (SOMA Repo - Securities Held Outright in SOMA)
SBP_XML_SUM_COLS_CONFIG = { # Renamed from SBP_COLS_TO_SUM for clarity
    'current_face_value': 'Current Face Value',
    'par_value': 'Par Value',
}


# --- Deprecated or To Be Reviewed ---
# 可用的Gemini模型列表 (此列表已棄用，模型將從API動態獲取)
# AVAILABLE_MODELS_STATIC = [
# "gemini-1.0-pro",
# "gemini-1.5-pro-latest",
# "gemini-1.5-flash-latest",
# "gemini-pro-vision"
# ]
