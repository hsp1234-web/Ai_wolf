# config/defaults.py

# --- yfinance 預設設定 ---
DEFAULT_YFINANCE_TICKERS = [
    "^GSPC", "^TWII", "2330.TW", "NVDA", "MSFT",
    "AAPL", "GOOG", "META", "TSM", "AMD", "INTC", "QCOM",
    "TXN", "ASML", "LRCX", "AMAT", "MU", "AVGO", "KLAC",
    "0050.TW", "0056.TW", "00878.TW"
]
DEFAULT_YFINANCE_PREVIEW_COUNT = 5

# --- FRED 預設設定 ---
DEFAULT_FRED_SERIES_IDS = [
    "GDP", "GDPC1", "CPIAUCSL", "UNRATE", "FEDFUNDS",
    "DGS10", "T10Y2Y", "WALCL", "M2SL", "PSAVERT",
    "TOTALSA", "PAYEMS", "ICSA", "PCE", "PCEDG"
]
DEFAULT_FRED_PREVIEW_COUNT = 5

# --- NY Fed 預設設定 (如果也需要中心化) ---
# (假設目前 NY Fed 的選擇是固定的，如果將來需要可配置，也可以移到這裡)
# DEFAULT_NYFED_INDICATORS = [...]
