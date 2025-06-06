# Ai_wolf 專案元件概覽

本文檔旨在詳細介紹「善甲狼週報 - 人機協同聊天式分析平台 (Ai_wolf)」專案在模組化重構後的各主要元件及其職責。

## 目錄結構

重構後的專案主要目錄結構如下：

```
Ai_wolf/
|-- app.py                   # 主應用程式啟動和協調器
|-- style.css                # 自訂 CSS 樣式表
|-- README.md                # 專案說明與 Colab 部署指南
|-- COMPONENTS_OVERVIEW.md   # 本文件
|-- .streamlit/
|   |-- config.toml          # Streamlit 主題與基礎設定
|-- components/              # UI 渲染相關模組
|   |-- __init__.py
|   |-- sidebar.py           # 側邊欄 UI 元件
|   |-- main_page.py         # 主頁面內容 UI 元件
|   |-- chat_interface.py    # 聊天介面邏輯與渲染
|   |-- log_display.py       # 前端應用程式日誌顯示元件
|-- services/                # 後端業務邏輯處理模組
|   |-- __init__.py
|   |-- gemini_service.py    # Gemini API 呼叫與快取管理
|   |-- data_fetchers.py     # 外部數據 (yfinance, FRED, NY Fed) 獲取
|   |-- file_processors.py   # 檔案上傳與內容讀取處理
|-- utils/                   # 共用工具與輔助函數模組
|   |-- __init__.py
|   |-- session_state_manager.py # Streamlit Session State 初始化與管理
|   |-- css_utils.py         # CSS 載入與動態樣式注入
|   |-- log_utils.py         # 日誌系統設定與自訂日誌處理程序
|-- config/                  # 應用程式靜態設定模組
|   |-- __init__.py
|   |-- app_settings.py      # 全域設定 (模型列表, 預設提示詞, URL等)
|   |-- api_keys_config.py   # API 金鑰名稱與標籤定義
|-- logs/                    # (此目錄由 Colab 腳本創建，用於存放日誌檔案)
|   |-- streamlit.log        # Streamlit 應用程式日誌檔案
```

## 元件詳細說明

### 1. `app.py` (主應用程式)

*   **職責**: 作為整個 Streamlit 應用的入口點和主協調器。
*   **主要功能**:
    *   設定頁面標題、圖示和佈局 (`st.set_page_config`)。
    *   初始化日誌系統 (`utils.log_utils.setup_logging`)，配置日誌輸出到控制台、檔案以及前端 UI。
    *   初始化應用程式的會話狀態 (`utils.session_state_manager.initialize_session_state`)。
    *   載入自訂 CSS 樣式 (`utils.css_utils.load_custom_css`)。
    *   注入動態主題和字體大小的 CSS (`utils.css_utils.inject_dynamic_theme_css`, `utils.css_utils.inject_font_size_css`)。
    *   按順序渲染各個主要的 UI 元件：
        *   側邊欄 (`components.sidebar.render_sidebar()`)。
        *   主頁面內容 (`components.main_page.render_main_page_content()`)。
        *   聊天介面 (`components.chat_interface.render_chat()`)。
        *   應用程式日誌查看器 (`components.log_display.render_log_viewer()`)。
    *   包含一個全域的錯誤處理機制，以捕獲和顯示未預期的異常。

### 2. `config/` (設定模組)

*   **`api_keys_config.py`**:
    *   職責: 集中定義應用程式中使用的所有 API 金鑰的內部名稱和在 UI 上顯示的標籤。
    *   互動: 被 `utils.session_state_manager.py` 用於初始化 API 金鑰相關的會話狀態，被 `components.sidebar.py` 用於動態生成 API 金鑰輸入框。
*   **`app_settings.py`**:
    *   職責: 存放應用程式的靜態設定數據，例如可用的 Gemini 模型列表、預設的 Gemini 分析提示詞、NY Fed 數據的 URL 列表、yfinance 的數據間隔選項等。
    *   互動: 被多個 UI 元件和服務模組讀取以獲取預設值或配置選項。

### 3. `utils/` (共用工具模組)

*   **`log_utils.py`**:
    *   職責: 設定和管理應用程式的日誌系統。
    *   主要功能:
        *   `StreamlitLogHandler`: 自訂的日誌處理程序，能將日誌記錄同時捕獲到記憶體列表 (供前端 UI 使用)。
        *   `setup_logging()`: 初始化 Python 的 `logging` 模組，配置日誌級別、格式，並添加多個處理程序 (如 `StreamHandler` 到控制台, `FileHandler` 到日誌檔案, `StreamlitLogHandler` 到 UI)。
    *   互動: 在 `app.py` 中被調用以初始化日誌。`StreamlitLogHandler` 的實例被存儲在 `st.session_state.log_handler` 中，供 `components.log_display.py` 讀取和顯示日誌。
*   **`css_utils.py`**:
    *   職責: 處理 CSS 相關的操作。
    *   主要功能:
        *   `load_custom_css()`: 從 `style.css` 檔案讀取樣式並應用到 Streamlit 應用。
        *   `inject_dynamic_theme_css()`: 根據當前選擇的主題 (暗色/亮色) 向頁面注入一個包裹 `div`，以便 `style.css` 中的主題特定樣式生效。
        *   `inject_font_size_css()`: 根據使用者選擇的字體大小，動態生成並注入 CSS 以覆蓋 HTML 根元素的字體大小。
    *   互動: 在 `app.py` 中被調用以應用樣式。
*   **`session_state_manager.py`**:
    *   職責: 集中初始化和管理 Streamlit 的會話狀態 (`st.session_state`)。
    *   主要功能:
        *   `initialize_session_state()`: 檢查並初始化應用程式運行所需的所有 `st.session_state` 變數的預設值，例如 API 金鑰、模型選擇、聊天歷史、上傳文件列表、外部數據、UI狀態（如主題、字體大小）等。
    *   互動: 在 `app.py` 啟動時被調用，確保所有需要的會話狀態變數都有初始值。

### 4. `services/` (後端服務模組)

*   **`file_processors.py`**:
    *   職責: 處理文件上傳和內容讀取。
    *   主要功能:
        *   `handle_file_uploads()`: 接收 Streamlit 文件上傳元件 (`st.file_uploader`) 的結果，讀取每個檔案的內容 (嘗試以 UTF-8 和 latin-1 解碼)，並將檔案名稱和內容存儲到 `st.session_state.uploaded_files_list` 和 `st.session_state.uploaded_file_contents` 中。
    *   互動: 被 `components.main_page.py` 中的文件上傳邏輯調用。
*   **`data_fetchers.py`**:
    *   職責: 從各種外部來源獲取金融和經濟數據。
    *   主要功能:
        *   `fetch_yfinance_data()`: 使用 `yfinance` 庫下載股票市場數據。
        *   `fetch_fred_data()`: 使用 `fredapi` 庫從 FRED (Federal Reserve Economic Data) 獲取經濟數據。
        *   `fetch_ny_fed_data()`: 從紐約聯儲網站下載一級交易商持倉數據。
        *   所有獲取函數都使用了 `@st.cache_data` 裝飾器來快取結果，避免重複下載。
    *   互動: 被 `components.main_page.py` 中獲取外部數據的邏輯調用。
*   **`gemini_service.py`**:
    *   職責: 封裝與 Google Gemini API 的所有互動。
    *   主要功能:
        *   `call_gemini_api()`: 構建完整的提示，處理 API 金鑰的輪換和速率限制 (RPM)，調用 Gemini API 進行內容生成，並處理可能的錯誤。
        *   `create_gemini_cache()`: 創建 Gemini 內容快取。
        *   `list_gemini_caches()`: 列出可用的 Gemini 內容快取。
        *   `delete_gemini_cache()`: 刪除指定的 Gemini 內容快取。
    *   互動: 被 `components.chat_interface.py` 調用以獲取 AI 回應，被 `components.sidebar.py` 調用以管理內容快取。

### 5. `components/` (UI 元件模組)

*   **`sidebar.py`**:
    *   職責: 渲染應用程式的側邊欄介面。
    *   主要功能: `render_sidebar()` 函數包含了所有側邊欄元素的創建和邏輯，例如：
        *   外觀主題 (暗色/亮色) 切換。
        *   字體大小選擇。
        *   API 金鑰輸入框。
        *   Gemini 模型選擇和 RPM/TPM 設定。
        *   主要分析提示詞的文本區域和文件上傳。
        *   清除應用程式數據快取的按鈕。
        *   Gemini 內容快取的管理介面 (創建、列出、選擇用於生成、刪除)。
    *   互動: 在 `app.py` 中被調用。讀取和更新 `st.session_state` 中的相關設定。
*   **`main_page.py`**:
    *   職責: 渲染應用程式主顯示區域的內容。
    *   主要功能: `render_main_page_content()` 函數包含：
        *   應用程式標題。
        *   文件上傳區塊 (使用 `st.file_uploader`，並調用 `services.file_processors.handle_file_uploads`)。
        *   已上傳文件的預覽區塊。
        *   外部數據源選擇區塊 (yfinance, FRED, NY Fed)，包含日期選擇、參數輸入，並觸發調用 `services.data_fetchers` 中的函數。
        *   獲取到的外部數據的預覽和錯誤顯示。
        *   當 Gemini API 金鑰缺失時，顯示警告和設定指南。
    *   互動: 在 `app.py` 中被調用。與 `st.session_state` 和 `services` 模組互動以獲取和顯示數據。
*   **`chat_interface.py`**:
    *   職責: 渲染聊天介面並處理聊天邏輯。
    *   主要功能: `render_chat()` 函數包含：
        *   使用 `st.chat_message` 顯示聊天歷史 (`st.session_state.chat_history`)。
        *   提供聊天輸入框 (`st.chat_input`) 讓使用者輸入問題。
        *   當使用者提交輸入時，準備完整的上下文提示 (包含系統提示、上傳文件內容、外部數據摘要和使用者當前問題)。
        *   調用 `services.gemini_service.call_gemini_api` 獲取模型回應。
        *   將使用者輸入和模型回應添加到聊天歷史中並觸發頁面刷新。
    *   互動: 在 `app.py` 中被調用。與 `st.session_state` (尤其是 `chat_history`) 和 `services.gemini_service` 互動。
*   **`log_display.py`**:
    *   職責: 在前端介面中顯示應用程式的日誌。
    *   主要功能: `render_log_viewer()` 函數包含：
        *   一個可展開的區域 (`st.expander`) 用於顯示日誌。
        *   從 `st.session_state.ui_logs` (由 `utils.log_utils.StreamlitLogHandler` 填充) 讀取日誌內容。
        *   提供一個按鈕來清除 `st.session_state.ui_logs` 中的日誌。
    *   互動: 在 `app.py` 中被調用。讀取 `st.session_state.ui_logs`。

## 日誌與樣式

*   **`style.css`**: 全局 CSS 樣式表，定義了應用程式的自訂外觀，特別是 Gemini 風格的暗色主題。
*   **`.streamlit/config.toml`**: Streamlit 的主題配置文件，設定了基礎顏色和字體，與 `style.css` 協同工作。
*   **`logs/streamlit.log`**: 在 Colab 環境中，應用程式的詳細日誌會被寫入此檔案，並由 `README.md` 中的 Colab Cell 2 腳本即時讀取並顯示在儲存格輸出中。

## 總結

透過這樣的模組化設計，我們期望提高程式碼的可讀性、可維護性和可擴展性。每個模組都有其明確的職責，使得未來的功能增強或問題修復能夠更精準地定位到相關的程式碼區塊。
