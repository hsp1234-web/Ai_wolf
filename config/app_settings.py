# config/app_settings.py

# 可用的Gemini模型列表
available_models = [
    "gemini-1.0-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.5-flash-latest",
    "gemini-pro-vision" # 雖然是視覺模型，但為完整性保留
]

# 預設的主要Gemini提示詞
DEFAULT_MAIN_GEMINI_PROMPT = """
請作為一個多才多藝的AI助理，根據我提供的上下文資訊（如上傳的檔案內容、外部數據源的數據）和我的問題，提供精確且有深度的回答。
請確保你的回答不僅僅是重複資訊，而是能提供洞察、分析或創造性的內容。
如果涉及到數據分析，請清晰地展示你的分析過程和結果。
如果需要，請向我提問以澄清我的需求。
"""

# 紐約聯儲（NY FED）持倉數據的URL列表 (修正後)
NY_FED_POSITIONS_URLS_CORRECTED = [
    {
        "name": "SOMA Holdings (Securities Held Outright)",
        "url": "https://markets.newyorkfed.org/api/soma/summary.xml",
        "type": "xml" # 新增類型以備將來解析特定格式
    },
    {
        "name": "Agency MBS Holdings (Agency Mortgage-Backed Securities)",
        "url": "https://markets.newyorkfed.org/api/ambs/all/summary.xml",
        "type": "xml"
    }
    # 可根據需要添加更多URL
]

# 用於處理SBP數據的列名映射或需要求和的列
SBP_COLS_TO_SUM = {
    'current_face_value': 'Current Face Value',
    'par_value': 'Par Value',
    # 可以根據實際XML結構添加更多需要處理的列
}

# yfinance數據的時間間隔選項
interval_options = {
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
font_size_css_map = {
    "Small": "font-small",
    "Medium": "font-medium",
    "Large": "font-large",
}
