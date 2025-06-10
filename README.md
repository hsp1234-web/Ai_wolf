# (中文內容)

# Wolf_V5

## 專案目標

本專案旨在打造一個在 Google Colaboratory (Colab) 環境中運行的、具有聊天式圖形化介面的人機協同智慧分析平台。平台將用於系統性地處理「善甲狼a機智生活」約150週的歷史貼文，輔助使用者回顧歷史交易機會，並最終由使用者將精煉內容手動整理至Google文件。

### 🚀 快速開始 (Google Colab)

我們提供了一個極其簡單的一鍵啟動方式，讓您可以直接在 Google Colab 的免費環境中執行本專案。

1.  點擊下方的徽章，即可在 Colab 中打開我們的專案啟動器：

    [![在 Colab 中打開](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/wolfAI_v1/blob/main/run_in_colab.ipynb)

2.  筆記本載入後，您會看到一個程式碼儲存格。**在點擊執行按鈕前，您可以從該儲存格上方的下拉選單中選擇執行模式：**
    *   **正常模式**: 預設選項，為一般使用者設計，提供最穩定、簡潔的啟動流程。此模式會隱藏詳細技術日誌。
    *   **除錯模式**: 為開發者設計。此模式會輸出詳細的安裝與執行日誌，並在服務啟動後自動執行一系列系統健康檢查（涵蓋後端API、前端服務、核心功能等），最後將結果打印在日誌中。這有助於快速定位潛在問題。

3.  選擇好模式後，點擊儲存格左側的 **▶️ 執行按鈕**。

4.  請稍待幾分鐘，系統將自動完成所有安裝與設定。成功後，會直接顯示您可以公開訪問的服務網址。

**API 金鑰配置提示 (為使除錯模式下的健康檢查更完整)：**
如果選擇「除錯模式」，為了使其能全面測試 API 金鑰的讀取和外部服務的連通性 (例如 Google Gemini API, FRED API)，建議您在 Colab 的「密鑰」(Secrets Manager) 中預先設定好以下名稱的密鑰及其對應值：
*   `GEMINI_API_KEY`: 您的 Google Gemini API 金鑰。
*   `COLAB_FRED_API_KEY_FOR_TEST`: 您的 FRED API 金鑰 (用於測試)。
*(如果專案未來增加了對其他需金鑰服務的測試，也請在此處列出)*
如果未設定這些密鑰，除錯模式中的相關 API 連通性測試可能會被跳過或標記為警告。正常模式啟動不受此影響（除非應用本身核心功能必須依賴這些金鑰）。

**疑難排解：**
如果執行過程中顯示「服務啟動失敗」，這通常是 Colab 環境的偶發問題。請依照筆記本輸出中的中文提示，點擊選單【執行階段】->【中斷並重新啟動執行階段】，然後再次點擊執行按鈕即可解決。

---




# (English Content)

# Wolf_V5

## Project Goal
This project aims to create an AI-assisted analysis platform running in Google Colaboratory (Colab). The platform, featuring a chat-based graphical interface, will systematically process approximately 150 weeks of historical posts from "善甲狼a機智生活" (ShanJiaLang's Witty Life). It will help users review historical trading opportunities, with the ultimate goal of users manually curating refined content into Google Docs.

### 🚀 Quick Start (Google Colab)

We offer an extremely simple one-click launch method, allowing you to run this project directly in Google Colab's free environment.

1.  Click the badge below to open our project launcher in Colab:

    [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/wolfAI_v1/blob/main/run_in_colab.ipynb)

2.  Once the notebook loads, you will see a code cell. **Before clicking the run button, you can select the execution mode from the dropdown menu above this cell:**
    *   **Normal Mode**: The default option, designed for general users, providing the most stable and clean startup process. This mode hides detailed technical logs.
    *   **Debug Mode**: Designed for developers. This mode outputs detailed installation and execution logs, and after the services start, it automatically runs a series of system health checks (covering backend APIs, frontend services, core functionalities, etc.), printing the results in the log. This helps in quickly identifying potential issues.

3.  After selecting your mode, click the **▶️ Run button** to the left of the cell.

4.  Please wait a few minutes for the system to automatically complete all installations and configurations. Upon success, a publicly accessible URL for the service will be displayed directly.

**API Key Configuration Tip (to ensure comprehensive Debug Mode health checks):**
If you select "Debug Mode," to enable it to fully test API key reading and connectivity to external services (e.g., Google Gemini API, FRED API), it is recommended to pre-configure the following secrets in Colab's Secrets Manager:
*   `GEMINI_API_KEY`: Your Google Gemini API key.
*   `COLAB_FRED_API_KEY_FOR_TEST`: Your FRED API key (for testing).
*(If the project adds tests for other key-dependent services in the future, please list them here too.)*
If these secrets are not set, related API connectivity tests in Debug Mode may be skipped or marked as warnings. Normal mode startup is not affected by this (unless the application's core functionality itself depends on these keys).

**Troubleshooting:**
If "Service startup failed" is displayed during execution, this is usually an occasional issue with the Colab environment. Please follow the Chinese prompts in the notebook output, click on the "Runtime" menu -> "Interrupt and restart runtime," and then click the run button again to resolve.


---

### Application Usage Guide

1.  **Set Your Gemini API Key (Important):**
    *   After the application launches, enter your Gemini API Key in the "API Settings" section of the sidebar. Using Colab Secrets Manager is highly recommended (see Appendix A below). The `app.py` is designed to preferentially load the key from a Colab Secret named `GEMINI_API_KEY`.
    *   AI analysis features will not work without a valid API Key.

2.  **Read Analysis File from Google Drive:**
    *   In the "Read Google Drive File" section of the sidebar, enter the path to your analysis file, relative to your Google Drive's `My Drive` (e.g., `wolfAI/my_report.txt` or `Colab_Data/another_report.txt`).
    *   **Date Parsing Tip:** For optimal market review by the AI, it's recommended that your text file includes a clear date identifier in the format `日期：YYYY-MM-DD` (Date: YYYY-MM-DD). The application will attempt to parse the base date from this identifier.
    *   Click "Read and Set as Current Analysis File."

3.  **Perform Initial AI Analysis (Includes Market Review):**
    *   Once a file is successfully read, an "AI Initial Analysis (Includes Market Review)" button will appear below the main chat area.
    *   Clicking this button will:
        *   Trigger the AI to perform a summary analysis of the text content (including "ShanJiaLang" core viewpoints, etc.).
        *   **Market Review:** Based on the date parsed from the file (or the current date if none is found), the AI will attempt to automatically fetch and display daily charts and data summaries for the Taiwan Weighted Index (`^TWII`), Nasdaq Composite (`^IXIC`), S&P 500 (`^GSPC`), Philadelphia Semiconductor Index (`^SOX`), and Nikkei 225 (`^N225`) for the week preceding the identified date. These charts and summaries will be displayed in the chat area as part of the AI's analysis.
        *   The `yfinance` package (used for fetching market data) is automatically installed by the `run_in_colab.ipynb` script.

4.  **Chat Interaction:**
    *   You can interact with the AI via the input box at the bottom of the chat area. Advanced chat commands (e.g., querying specific stock data) are planned for future development.

### Notes
*   The Colab Notebook must remain running for the application to be accessible.
*   If the Colab environment restarts, you will need to re-run the setup and launch cell(s) in `run_in_colab.ipynb`.
*   Code updates are primarily managed through GitHub.

---

## Viewing Application Logs

The application features built-in detailed logging to assist users and developers in tracking execution status and troubleshooting issues.

### How to View Logs

1.  **Location**: At the bottom of the application's main page, you will find an expandable section titled "📄 Application Logs."
2.  **Operation**: Click this section to expand it and view real-time application log messages. Logs display the most recent events at the top.
3.  **Clear Logs**: Within this section, there is also a "Clear Log Records" button that clears the logs currently displayed in the interface. This does not affect server console log output.

### Log Level

The default log level is `DEBUG`. This means very detailed application execution information is recorded, including function calls, variable states, API requests/responses, etc. This is highly beneficial for understanding the application's internal workings and quickly pinpointing issues.

### Purpose of Logs

These logs are primarily used for:
*   Developers to debug the application.
*   Providing detailed execution context when encountering unexpected behavior or errors.
*   Helping to understand data processing and API interaction flows.

---
### Appendix A: Securely Setting Your Gemini API Key (Recommended)

To use your API Key more securely and persistently, it is recommended to use Colab's **Secrets Manager**:
1.  **Add Secret in Colab:** Click the key icon (🔑) on the left sidebar -> "+ Add a new secret" -> Name: `GEMINI_API_KEY` -> Paste your key value -> Enable "Notebook access."
2.  **Application's Reading Logic**: The application, through logic in `utils/session_state_manager.py` (or similar, handled within `app.py` or the notebook environment), will preferentially attempt to read the key named `GEMINI_API_KEY` from Colab Secrets. If you've set it this way, you might not need to enter it manually in the UI.

---
