# (中文內容)

# Wolf_V5

## 專案目標

本專案旨在打造一個在 Google Colaboratory (Colab) 環境中運行的、具有聊天式圖形化介面的人機協同智慧分析平台。平台將用於系統性地處理「善甲狼a機智生活」約150週的歷史貼文，輔助使用者回顧歷史交易機會，並最終由使用者將精煉內容手動整理至Google文件。

## 如何在 Colab 中運行

我們提供了兩種在 Google Colaboratory 中啟動 Ai_wolf (Wolf_V5) 應用程式的方法：

### 方法一：使用版本化的 `run_in_colab.ipynb` Notebook (推薦)

這是啟動應用程式的**推薦方法**，因為它使用了專案中版本化的 Notebook 檔案，確保了啟動腳本與專案程式碼的一致性。

1.  **點擊下方按鈕**：
    [![在 Colab 中打開](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/Ai_wolf/blob/main/run_in_colab.ipynb)

2.  **依照 Notebook 中的說明執行**：
    *   `run_in_colab.ipynb` 包含詳細的步驟說明，包括如何設定 API 金鑰 (透過 Colab Secrets Manager)、Google Drive 授權等。
    *   Notebook 中的第一個 Markdown Cell 提供了完整的操作指南。
    *   只需執行 Notebook 中的 Code Cell 即可完成所有操作：環境清理、專案下載、依賴安裝、以及啟動 Streamlit 應用程式。
    *   此 Notebook 設計為**「超穩健版」**，能直接捕獲並顯示 Streamlit 應用程式的所有輸出，包括啟動時的錯誤追蹤，方便快速定位問題。
    *   `run_in_colab.ipynb` Notebook 中也包含了一個可選的步驟来執行綜合健康度檢測，詳見下文「🔧 綜合健康度檢測」章節。

### 方法二：手動複製貼上單一儲存格腳本 (備用)

如果您希望直接在一個新的或現有的 Colab Notebook 中快速啟動，可以複製下方的完整腳本內容，並將其貼到 Colab 的一個程式碼儲存格中執行。

**請注意**：此處的腳本與 `run_in_colab.ipynb` 中的 Code Cell 內容是相同的。使用 `.ipynb` 檔案能更好地管理腳本的版本。

```python
#@title 🚀 一鍵啟動 Wolf_V5 (修正版)
# === Wolf_V5 專案：環境設置、部署、啟動與即時監控 (單一儲存格) ===
# 此版本已修正公開儲存庫的 git clone 問題，並整合了日誌路徑。

import os
import subprocess
import time
import threading
from IPython.display import display, HTML, clear_output

# 檢查是否在 Colab 環境
try:
    from google.colab import drive
    from google.colab.output import eval_js
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
    # 如果需要在本地模擬，定義 mock 函數
    def mock_drive_mount(path, force_remount=False): print(f"Mock: Drive mount requested for {path}")
    drive = type('Drive', (object,), {'mount': mock_drive_mount})()
    def mock_eval_js(code): print(f"Mock: eval_js called with {code}"); return "http://localhost:8501"
    eval_js = mock_eval_js
    print("非 Colab 環境，部分 Colab 特定功能將被模擬或跳過。")


# --- 階段一：環境設置與專案部署 ---
print("--- 階段一：環境設置與專案部署 ---")
print("\n[1/5] 正在安裝必要的 Python 套件...")
# 使用 get_ipython() 來執行 shell 命令
get_ipython().system('pip install streamlit google-generativeai yfinance pandas fredapi requests -q')
print("✅ 套件安裝完成！")

GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI" # Google Drive 中的專案路徑
LOCAL_PROJECT_DIR = "/content/wolfAI" # 本地 Colab 儲存的專案路徑
PROJECT_DIR_TO_USE = None # 實際使用的專案目錄

if IN_COLAB:
    print("\n[2/5] 正在嘗試掛載 Google Drive...")
    try:
        drive.mount('/content/drive', force_remount=True)
        print("✅ Google Drive 掛載成功！")
        PROJECT_DIR_TO_USE = GDRIVE_PROJECT_DIR

        # --- 當 Drive 掛載成功時，創建 Wolf_Data 目錄結構 ---
        WOLF_DATA_BASE_GDRIVE = "/content/drive/MyDrive/Wolf_Data"
        print(f"    檢查/創建 Wolf_Data 基礎目錄: {WOLF_DATA_BASE_GDRIVE}")
        if not os.path.exists(WOLF_DATA_BASE_GDRIVE):
            os.makedirs(WOLF_DATA_BASE_GDRIVE, exist_ok=True)
            print(f"    ✅ '{WOLF_DATA_BASE_GDRIVE}' 已創建。")
        else:
            print(f"    ➡️ '{WOLF_DATA_BASE_GDRIVE}' 已存在。")

        sub_dirs_to_create = ["source_documents/masters", "source_documents/shan_jia_lang", "weekly_reports", "logs"]
        for sub_dir in sub_dirs_to_create:
            full_sub_dir_path = os.path.join(WOLF_DATA_BASE_GDRIVE, sub_dir)
            print(f"    檢查/創建子目錄: {full_sub_dir_path}")
            if not os.path.exists(full_sub_dir_path):
                os.makedirs(full_sub_dir_path, exist_ok=True)
                print(f"    ✅ '{full_sub_dir_path}' 已創建。")
            else:
                print(f"    ➡️ '{full_sub_dir_path}' 已存在。")

    except Exception as e:
        print(f"⚠️ Google Drive 掛載失敗: {e}")
        print("將嘗試使用 Colab 本地儲存空間。")
        PROJECT_DIR_TO_USE = LOCAL_PROJECT_DIR
else:
    print("\n[2/5] 跳過 Google Drive 掛載 (非 Colab 環境)。")
    PROJECT_DIR_TO_USE = LOCAL_PROJECT_DIR

# 設定應用程式預期的日誌目錄路徑
WOLF_DATA_GDRIVE_BASE_INFO = "/content/drive/MyDrive/Wolf_Data"
WOLF_DATA_LOCAL_BASE_INFO = "/content/Wolf_Data"
APP_EXPECTED_LOG_DIR = None

if PROJECT_DIR_TO_USE == GDRIVE_PROJECT_DIR:
    APP_EXPECTED_LOG_DIR = os.path.join(WOLF_DATA_GDRIVE_BASE_INFO, "logs")
else:
    APP_EXPECTED_LOG_DIR = os.path.join(WOLF_DATA_LOCAL_BASE_INFO, "logs")
    if not os.path.exists(WOLF_DATA_LOCAL_BASE_INFO):
        os.makedirs(WOLF_DATA_LOCAL_BASE_INFO, exist_ok=True)
        print(f"    ✅ 已確認/建立模擬的本地 Wolf_Data 基礎目錄: {WOLF_DATA_LOCAL_BASE_INFO}")

print(f"\n[3/5] 設定專案路徑: {PROJECT_DIR_TO_USE}")
print(f"    應用程式資料/日誌目錄預期在: {APP_EXPECTED_LOG_DIR} (實際路徑由 app.py 設定)")

# 強制清理舊的專案目錄
if os.path.exists(PROJECT_DIR_TO_USE):
    print(f"    偵測到已存在的專案目錄 '{PROJECT_DIR_TO_USE}'。執行強制清理...")
    import shutil
    shutil.rmtree(PROJECT_DIR_TO_USE)
    print(f"    ✅ '{PROJECT_DIR_TO_USE}' 已成功刪除。")
else:
    print(f"    '{PROJECT_DIR_TO_USE}' 不存在，無需清理。")

project_parent_dir = os.path.dirname(PROJECT_DIR_TO_USE)
if not os.path.exists(project_parent_dir) and PROJECT_DIR_TO_USE != LOCAL_PROJECT_DIR:
     os.makedirs(project_parent_dir, exist_ok=True)

STREAMLIT_APP_PATH = os.path.join(PROJECT_DIR_TO_USE, "app.py")
REQUIREMENTS_PATH = os.path.join(PROJECT_DIR_TO_USE, "requirements.txt")
PORT = 8501

print(f"✅ 已確認/建立專案目錄。")

# --- [已修正] 從 GitHub 獲取程式碼 ---
print(f"\n[4/5] 正在從 GitHub 獲取最新程式碼...")
GIT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"

git_clone_command = ["git", "clone", "--depth", "1", GIT_REPO_URL, PROJECT_DIR_TO_USE]

# 建立一個新的環境變數，告訴 Git 不要進行互動式提問
git_env = os.environ.copy()
git_env["GIT_TERMINAL_PROMPT"] = "0"

# 使用新的環境變數來執行 git clone
result = subprocess.run(git_clone_command, capture_output=True, text=True, env=git_env)

if result.returncode == 0:
    print("    ✅ 專案克隆完成！")
else:
    print(f"    ❌ 專案克隆失敗:")
    print(result.stdout)
    print(result.stderr)
    raise SystemExit("Git clone 失敗，終止執行。")

# 使用 requirements.txt 安裝依賴
if os.path.isfile(REQUIREMENTS_PATH):
    print("    正在從 requirements.txt 安裝依賴...")
    pip_install_command = ["pip", "install", "-q", "-r", REQUIREMENTS_PATH]
    result_pip = subprocess.run(pip_install_command, capture_output=True, text=True)
    if result_pip.returncode == 0:
        print("    ✅ 依賴安裝完成！")
    else:
        print(f"    ❌ 依賴安裝失敗:")
        print(result_pip.stdout)
        print(result_pip.stderr)
else:
    print(f"    ⚠️ 警告: 未找到 requirements.txt。")


print(f"\n[5/5] 檢查主要應用程式檔案...")
if not os.path.isfile(STREAMLIT_APP_PATH):
    raise SystemExit(f"❌ 錯誤：未在 {PROJECT_DIR_TO_USE} 中找到 app.py！")
print(f"✅ 成功找到主要應用程式檔案: {STREAMLIT_APP_PATH}")
print("\n--- 環境設置與專案部署階段完成 ---\n")
time.sleep(2)
if IN_COLAB: clear_output(wait=True)

# --- 階段二：啟動 Streamlit 並直接監控其輸出 ---
print("--- 階段二：啟動 Streamlit 並直接監控其輸出 ---")
streamlit_process = None
monitor_thread = None
tunnel_url = None

try:
    import sys
    cmd_streamlit = [sys.executable, "-m", "streamlit", "run", STREAMLIT_APP_PATH, "--server.port", str(PORT), "--server.headless", "true", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]

    # 將 stderr 重定向到 stdout，以便捕獲所有輸出，包括錯誤
    streamlit_process = subprocess.Popen(cmd_streamlit, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', cwd=PROJECT_DIR_TO_USE)
    print("✅ Streamlit 啟動指令已送出。")
    print("⏳ 等待伺服器初始化並嘗試獲取連結...")

    def stream_watcher(identifier, stream):
        for line in iter(stream.readline, ''):
            if not line:
                break
            print(f"[{identifier}] {line}", end='', flush=True)
        stream.close()

    monitor_thread = threading.Thread(target=stream_watcher, args=('Streamlit', streamlit_process.stdout))
    monitor_thread.daemon = True # 設置為守護線程
    monitor_thread.start()

    if IN_COLAB:
        print("\n✅ 伺服器已在背景啟動。")
        print("   請等待約 15-30 秒讓服務完成初始化...")
        try:
            input("   初始化完成後，請按 Enter 鍵嘗試獲取應用程式網址...")
        except Exception:
            print("\n⚠️ 讀取用戶輸入時發生錯誤。將繼續嘗試獲取URL。")

        # 帶有重試機制的 URL 獲取
        print("\n🔗 開始嘗試獲取應用程式網址...")
        MAX_RETRIES = 5
        RETRY_DELAY_SECONDS = 5
        for attempt in range(MAX_RETRIES):
            print(f"   第 {attempt + 1}/{MAX_RETRIES} 次嘗試...")
            try:
                proxy_url_eval = eval_js(f'google.colab.kernel.proxyPort({PORT})', timeout_sec=10)
                if proxy_url_eval:
                    tunnel_url = proxy_url_eval
                    print(f"   🎉 成功獲取 Colab 代理 URL: {tunnel_url}")
                    break
                else:
                    print(f"   ⚠️ 第 {attempt + 1} 次嘗試：eval_js 未返回有效 URL。")
            except Exception as e:
                print(f"   ⚠️ 第 {attempt + 1} 次嘗試獲取 URL 時發生錯誤: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"   將在 {RETRY_DELAY_SECONDS} 秒後重試...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"   ❌ 達到最大重試次數，仍未能透過 eval_js 獲取網址。")

    if IN_COLAB: clear_output(wait=True)

    if tunnel_url:
        display(HTML(f"""
            <div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px;'>
                <h2 style='color: #2E7D32;'>🎉 應用程式已成功啟動！</h2>
                <p>日誌和錯誤將直接顯示在本儲存格的下方。</p>
                <p><a href='{tunnel_url}' target='_blank' style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:8px;'>
                   🚀 點此開啟 Wolf_V5 應用程式
                </a></p>
                <p style='font-size:0.8em; color:grey;'>如果無法訪問，請檢查下方 Streamlit 輸出日誌。</p>
            </div>
        """))
    else:
        display(HTML("<p style='color:red;'>❌ 未能獲取應用程式的公開訪問 URL。請檢查上方的日誌輸出以了解詳細原因。</p>"))

    print("\n--- 應用程式即時輸出 (包含日誌與錯誤) ---")
    monitor_thread.join()

except KeyboardInterrupt:
    print("\n\n⌨️ 偵測到手動中斷。")
except Exception as e:
    print(f"\n\n❌ 腳本執行期間發生錯誤: {e}")
    import traceback
    traceback.print_exc()
finally:
    print("\n\n--- 正在終止 Streamlit 服務 ---")
    if streamlit_process and streamlit_process.poll() is None:
        streamlit_process.terminate()
        try:
            streamlit_process.wait(timeout=10)
            print("    Streamlit 程序已終止。")
        except subprocess.TimeoutExpired:
            print("    Streamlit 程序未能優雅終止，強制結束。")
            streamlit_process.kill()
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join(timeout=5)
    print("--- 腳本執行完畢 ---")
```

**執行說明：**
*   上述腳本會先完成環境設置和專案部署，然後自動啟動 Streamlit 應用程式。
*   成功啟動後，會顯示一個**綠色的「點此開啟 Wolf_V5 應用程式」按鈕**。
*   成功啟動後，會顯示一個**綠色背景的「點此開啟 Wolf_V5 應用程式」大按鈕**。
*   儲存格的輸出區域將持續顯示應用程式的即時日誌。
*   要停止 Streamlit 服務，請**手動中斷此儲存格的執行** (例如，點擊儲存格左側的停止按鈕，或使用快捷鍵 `Ctrl+M I`)。

---
## 🔧 綜合健康度檢測

本專案提供了一個強大的綜合健康度檢測腳本 (`health_check_script_final.py`)，用於全面自動化地檢查應用程式的內外部環境、依賴套件、API 連接、前後端服務啟動以及核心功能的正確性。

**此檢測特別適用於：**
*   **開發者**：在修改程式碼後，快速驗證所有關鍵部分是否仍能正常運作。
*   **專案維護者**：定期檢查專案的健康狀況，確保外部 API 和環境依賴未發生非預期的變化。
*   **問題排查**：當應用程式遇到預期外的行為或錯誤時，提供詳細的錯誤報告以輔助定位問題。

**檢測範圍包括：**
*   Colab 環境配置（Python 版本、硬體資源等）。
*   專案檔案結構與依賴安裝。
*   API 金鑰讀取（需在 Colab Secrets 中預先設定，詳見下方說明）及外部服務（如 Google Gemini, FRED）的連通性。
*   後端 FastAPI 服務的啟動、資料庫初始化及核心 API 端點測試（包括認證、聊天、資料獲取、檔案上傳、資料庫備份等）。
*   前端 Streamlit 應用的啟動初步檢查。
*   執行專案自帶的 Pytest 單元測試。

**如何執行健康檢測：**

我們提供了兩種主要方式來執行此健康檢測：

### 方法一：通過 `run_in_colab.ipynb` Notebook 中的專用儲存格 (推薦)

這是執行健康檢測的**推薦方法**，因為它直接整合在主要的 Colab 啟動 Notebook 中，方便易用。

1.  **打開 `run_in_colab.ipynb` Notebook**：
    [![在 Colab 中打開](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hsp1234-web/Ai_wolf/blob/main/run_in_colab.ipynb)
2.  **執行主應用部署儲存格**：確保 `run_in_colab.ipynb` 中標題類似「🚀 一鍵啟動 Wolf_V5」或「1. 環境設置與專案部署」的儲存格已成功執行，這樣專案程式碼（包括 `health_check_script_final.py`）才會被正確下載到 Colab 環境中。
3.  **找到並執行健康檢測儲存格**：
    *   在 `run_in_colab.ipynb` Notebook 中，找到標題為「⚙️ (可選) 執行綜合健康度檢測」的程式碼儲存格。
    *   執行此儲存格。
4.  **查看報告**：
    *   腳本執行過程可能需要 1-3 分鐘。
    *   完成後，一份詳細的 HTML 格式檢測報告將直接顯示在該儲存格的輸出區域。

### 方法二：手動複製並執行腳本 (備用)

如果您需要在一個新的 Colab Notebook 中或以其他方式獨立執行檢測：

1.  **獲取腳本**：確保您的專案已克隆到 Colab 環境。找到位於專案根目錄下的 `health_check_script_final.py` 檔案。
2.  **複製內容**：打開 `health_check_script_final.py` 並複製其完整的 Python 程式碼。
3.  **貼上並執行**：在您的 Colab Notebook 中創建一個新的程式碼儲存格，將複製的腳本內容貼入，然後執行該儲存格。
4.  **查看報告**：執行完畢後，HTML 報告同樣會顯示在輸出區域。

**API 金鑰配置提示 (重要)：**
為了使健康檢測腳本能夠全面測試 API 金鑰的讀取和外部服務的連通性 (例如 Google Gemini API, FRED API)，您**必須**在 Colab 的「密鑰」(Secrets Manager) 中預先設定好以下名稱的密鑰及其對應值：
*   `GEMINI_API_KEY`: 您的 Google Gemini API 金鑰。(此金鑰主要由主應用程式使用，健康檢查腳本內部的模擬讀取會測試其存在性)
*   `COLAB_GOOGLE_API_KEY_FOR_TEST`: 您的 Google Gemini API 金鑰。(健康檢查腳本會使用此金鑰**直接測試**對 Google GenAI 服務的連通性)
*   `COLAB_FRED_API_KEY_FOR_TEST`: 您的 FRED API 金鑰。(健康檢查腳本會使用此金鑰**直接測試**對 FRED 服務的連通性)
如果未設定這些密鑰，相關的 API 連通性測試將會被標記為警告 (WARN) 或跳過 (SKIPPED)，但其他不依賴這些金鑰的檢測仍會執行。

---

### 應用程式操作指南

1.  **設定 Gemini API Key (重要)：**
    *   應用程式啟動後，請在側邊欄的 "API 設定" 區域輸入您的 Gemini API Key。優先推薦使用 Colab Secrets Manager (詳見下方附錄 A)。`app.py` 已設計為優先從 Colab Secrets (名稱 `GEMINI_API_KEY`) 加載金鑰。
    *   無有效 API Key，AI 分析功能無法使用。

2.  **從 Google Drive 讀取分析文件：**
    *   在側邊欄 "讀取 Google Drive 文件" 區域，輸入您想分析的、存於您 Google Drive `My Drive` 下的**相對於 `My Drive` 的文件路徑** (例如 `wolfAI/my_report.txt` 或 `Colab_Data/another_report.txt`)。
    *   **日期解析提示：** 為了讓 AI 能更好地進行市場回顧，建議您的文本文件內容中包含明確的日期標識，格式為 `日期：YYYY-MM-DD`。應用程式會嘗試從此標識解析基準日期。
    *   點擊 "讀取並設為當前分析文件"。

3.  **進行 AI 初步分析 (包含市場回顧)：**
    *   文件成功讀取後，主聊天區下方會出現 "AI 初步分析 (包含市場回顧)" 按鈕。
    *   點擊此按鈕：
        *   AI 會對文本內容進行摘要分析（包括「善甲狼」核心觀點等）。
        *   **市場回顧：** AI 會嘗試根據從文件中解析出的日期（若無則使用當前日期），自動獲取並展示台灣加權指數 (`^TWII`)、納斯達克綜合指數 (`^IXIC`)、標普500指數 (`^GSPC`)、費城半導體指數 (`^SOX`)和日經225指數 (`^N225`) 在該日期前一週的**日線走勢圖**和**數據摘要**。這些圖表和摘要將作為 AI 分析的一部分顯示在聊天區。
        *   `yfinance` 套件（用於獲取市場數據）已在 Cell 1 中自動安裝。

4.  **聊天互動：**
    *   您可以在聊天區底部的輸入框中與 AI 進行對話。進階的聊天指令功能（如查詢特定股票數據）正在規劃中。

### 注意事項
*   Colab Notebook 需保持運行。
*   環境重啟後需重新執行 Cell 1 和 Cell 2。
*   程式碼主要透過 GitHub 更新。

---

## 查看應用程式日誌 (Viewing Application Logs)

本應用程式內建了詳細的日誌記錄功能，以協助使用者和開發者追蹤執行狀況及進行問題排查。

### 如何查看日誌

1.  **位置**：在應用程式主頁面的底部，你會找到一個名為「📄 應用程式日誌 (Application Logs)」的可展開區域。
2.  **操作**：點擊該區域即可展開，查看即時的應用程式日誌訊息。日誌會顯示最新的事件在最上方。
3.  **清除日誌**：在此區域內還有一個「清除日誌紀錄」按鈕，可以清除當前顯示在介面中的日誌。這不會影響到伺服器控制台的日誌輸出。

### 日誌級別

日誌級別預設為 `DEBUG`。這表示會記錄非常詳細的應用程式執行信息，包括函數調用、變數狀態、API 請求與回應等。這對於深入了解應用程式的內部運作和快速定位問題非常有幫助。

### 日誌用途

這些日誌主要用於：
*   開發者進行應用程式偵錯。
*   在遇到預期外的行為或錯誤時，提供詳細的執行上下文。
*   幫助理解數據處理和 API 互動的流程。

---
### 附錄 A：安全設定 Gemini API Key (推薦)

(此部分內容與上一版 README.md 相同，保持不變)
為了更安全和持久地使用 API Key，建議使用 Colab 的 **Secrets Manager**：
1.  **在 Colab 中添加密鑰：** 左側鑰匙圖標 -> "+ 新增密鑰" -> 名稱 `GEMINI_API_KEY` -> 貼上金鑰值 -> 啟用 "筆記本訪問權限"。
2.  **應用程式中的讀取邏輯**：應用程式會透過 `utils/session_state_manager.py` 中的邏輯，優先從 Colab Secrets 讀取名為 `GEMINI_API_KEY` 的金鑰。

---

# (English Content)

# Wolf_V5

## Project Goal
(Same as previous version)

## How to Run in Colab (New Two-Cell Process)
(Same as previous version, up to Prerequisites)

### Prerequisites
*   A valid Google account.
*   A Gemini API Key is recommended for full AI analysis features. Obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Cell 1: Environment Setup and Project Deployment
Copy the entire script content below, paste it into the first code cell of your Colab Notebook, and then run this cell.
This cell will:
1.  Install necessary Python packages (`streamlit`, `google-generativeai`, `yfinance`, `pandas`).
2.  Mount your Google Drive.
3.  Create a `wolfAI` directory under `My Drive`.
4.  Clone/update the project code from GitHub (`https://github.com/hsp1234-web/Ai_wolf.git`) into `My Drive/wolfAI/`.

```python
#@title 1. Environment Setup & Ai_wolf Project Deployment (Click to expand code)
# === Colab Environment Setup & Ai_wolf Project Deployment ===
# Cell 1: Please run this cell to complete all initial setup.
import os

# --- 1. Install Necessary Python Packages ---
print("Installing necessary Python packages (streamlit, google-generativeai, yfinance, pandas)...")
!pip install streamlit google-generativeai yfinance pandas -q
# Added pandas because yfinance might need it, and it's also used in app.py
print("Package installation complete!\n")

# --- 2. Mount Google Drive ---
print("Attempting to mount Google Drive...")
from google.colab import drive
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive mounted successfully!\n")
except Exception as e:
    print(f"Failed to mount Google Drive: {e}")
    print("Please check the authorization steps in the pop-up window. If issues persist, try 'Runtime' -> 'Disconnect and delete runtime', then re-run this cell.") # Note: Colab-specific runtime management tip
    raise # Raise exception to stop execution if mounting fails

# --- 3. Define Project Path and Create Target Folder ---
# GDRIVE_PROJECT_DIR will be defined here, specifying the project directory in Google Drive
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI"
print(f"Project will be deployed to Google Drive path: {GDRIVE_PROJECT_DIR}")
# Using !mkdir -p to execute a shell command to create the directory if it doesn't already exist
!mkdir -p "{GDRIVE_PROJECT_DIR}"
# 同時創建日誌目錄
!mkdir -p "{GDRIVE_PROJECT_DIR}/logs"
print(f"Project directory confirmed/created and logs directory created.\n")

# --- 4. Clone or Update Ai_wolf Project Code from GitHub ---
GIT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
GIT_DIR_CHECK = f"{GDRIVE_PROJECT_DIR}/.git" # Used to check if the .git directory exists, indicating a Git repository

print(f"Fetching latest code from {GIT_REPO_URL}...")
if os.path.isdir(GIT_DIR_CHECK): # Use os.path.isdir to check if the directory exists
    print("Existing project Git repository detected, attempting to update (git pull)...")
    import subprocess # Import subprocess module to execute shell commands
    # This is a more robust update method: first fetch and reset to the latest state of the remote main branch, then pull
    git_pull_command = f"cd '{GDRIVE_PROJECT_DIR}' && git fetch origin main && git reset --hard origin/main && git pull origin main"
    print(f"Executing update command: {git_pull_command}")
    process = subprocess.run(git_pull_command, shell=True, capture_output=True, text=True)
    if process.returncode == 0:
        print("Project update successful (git pull)!")
        if process.stdout: print(f"Git Pull Output:\n{process.stdout}")
        if process.stderr: print(f"Git Pull Error Messages (if any):\n{process.stderr}")
    else:
        print(f"git pull failed (return code: {process.returncode}). Error details:")
        print(process.stderr)
        print("This could be due to local merge conflicts or network issues. Consider manually deleting the 'wolfAI' directory in Google Drive and re-running this cell for a fresh clone.")
else:
    print(f"No existing .git repository found, cloning project from {GIT_REPO_URL} to {GDRIVE_PROJECT_DIR} ...")
    # Using !git clone to execute a shell command to clone the repository, --depth 1 for a shallow clone (latest commit only)
    !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}"
    print("Project cloning complete!")

print("\n--- 5. Verify Project Files ---")
print(f"Listing contents of {GDRIVE_PROJECT_DIR}:")
# Using !ls -la to execute a shell command to list file details (including hidden files)
!ls -la "{GDRIVE_PROJECT_DIR}"
APP_PY_PATH = f"{GDRIVE_PROJECT_DIR}/app.py" # Define the path to the main application file
# Check if the main app.py file exists
if os.path.isfile(APP_PY_PATH): # Use os.path.isfile to check if the file exists
    print(f"\nSuccessfully found the main application file: {APP_PY_PATH}")
    print("\n✅ Cell 1 Setup Complete! You can now proceed to run Cell 2.")
else:
    print(f"\n❌ Error: Main application file app.py not found in {GDRIVE_PROJECT_DIR}!")
    print(f"Please check if app.py exists in the GitHub repository ({GIT_REPO_URL}) at the root level or if there were errors in previous steps.")

```
**Execution Notes:**
*   Monitor Colab output.
*   **Google Drive Authorization:** Authorize when prompted.
*   **GitHub Updates:** The script attempts to pull the latest code.

### Cell 2: Launch the Streamlit Application and Monitor Logs
After Cell 1 executes successfully, copy the following into the second Colab cell and run it.
This cell will:
1. Launch the Streamlit application.
2. Attempt to fetch and display a publicly accessible Colab proxy URL.
3. **Remain running** to maintain the Streamlit service and will **output live application logs**.
4. You can stop the Streamlit service by **manually interrupting this cell (Interrupt execution)**.

```python
#@title 2. 🚀 Launch Wolf_V5 App, Get Link & Monitor Logs (Click to execute)
# === Wolf_V5 Project Launch, Link Retrieval & Log Monitoring ===
# Cell 2: Execute this cell to launch the Streamlit application, automatically fetch the access link, and continuously output logs.
#         You can manually interrupt this cell at any time to stop the service.

import subprocess
import time
import os
import threading # For monitoring the Streamlit process
from IPython.display import display, HTML, clear_output
from google.colab.output import eval_js

# --- Configuration Parameters ---
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI" # Inherited from Cell 1 or redefined here
STREAMLIT_APP_PATH = f"{GDRIVE_PROJECT_DIR}/app.py"
LOG_DIR = f"{GDRIVE_PROJECT_DIR}/logs" # Log directory
LOG_FILE_PATH = f"{LOG_DIR}/streamlit.log" # Streamlit app should output logs here

PORT = 8501 # Port for the Streamlit app
WAIT_SECONDS_FOR_SERVER = 15
MAX_RETRIES_FOR_URL = 3
RETRY_DELAY_SECONDS = 5

# --- Clear Previous Output ---
# clear_output(wait=True) # Uncomment to clear previous output of this cell on each run

print("🚀 Preparing to launch Streamlit application...")
print(f"   Application path: {STREAMLIT_APP_PATH}")
print(f"   Log file path: {LOG_FILE_PATH}")
print(f"   Expected listening port: {PORT}")
print("-" * 70)

# --- Check if app.py Exists ---
if not os.path.exists(STREAMLIT_APP_PATH):
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Error: Streamlit application file not found!</p>" \
                 f"<p style='color:red;'>   Please ensure the path <code style='color:red; background-color:#f0f0f0; padding:2px 4px; border-radius:3px;'>{STREAMLIT_APP_PATH}</code> is correct,</p>" \
                 f"<p style='color:red;'>   and that you have successfully executed all steps in Cell 1.</p>"))
    raise SystemExit("Application file app.py not found, terminating execution.")

# --- Ensure Log Directory and File Exist ---
os.makedirs(LOG_DIR, exist_ok=True)
with open(LOG_FILE_PATH, 'a') as f: # 'a' mode creates the file if it doesn't exist
    f.write(f"--- Colab script log monitoring started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
print(f"Log file {LOG_FILE_PATH} confirmed/created.")
print("-" * 70)

# --- Launch Streamlit Server ---
streamlit_process = None
monitor_thread = None # Initialize monitor thread variable

try:
    print(f"⏳ Attempting to launch Streamlit in the background (approx. {WAIT_SECONDS_FOR_SERVER} seconds)...")
    cmd = ["streamlit", "run", STREAMLIT_APP_PATH,
           "--server.port", str(PORT),
           "--server.headless", "true",
           "--browser.gatherUsageStats", "false"]

    streamlit_process = subprocess.Popen(cmd)

    print(f"   Streamlit launch command sent (PID: {streamlit_process.pid if streamlit_process else 'Unknown'}).")
    print(f"   Allowing server {WAIT_SECONDS_FOR_SERVER} seconds to initialize...")
    time.sleep(WAIT_SECONDS_FOR_SERVER)

    if streamlit_process.poll() is not None:
        display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Streamlit appears to have failed to start or terminated unexpectedly (return code: {streamlit_process.returncode}).</p>" \
                     f"<p style='color:orange;'>   Please check if `app.py` has syntax errors, or try checking Colab's 'Runtime' -> 'View runtime logs'.</p>" \
                     f"<p style='color:orange;'>   If your Streamlit application has internal logging (e.g., writing to {LOG_FILE_PATH}), that file might contain more clues.</p>"))
        raise SystemExit(f"Streamlit process failed to stay running (return code: {streamlit_process.returncode}).")

    print("✅ Streamlit should now be running in the background.")
    print("-" * 70)

except Exception as e:
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ An unexpected error occurred while launching Streamlit:</p>" \
                 f"<p style='color:red; font-family:monospace; white-space:pre-wrap;'>{str(e)}</p>" \
                 f"<p style='color:orange;'>   Please check the error message, ensure Streamlit is correctly installed, and paths are correct.</p>"))
    if streamlit_process and streamlit_process.poll() is None:
        streamlit_process.terminate()
    raise SystemExit(f"Failed to launch Streamlit: {str(e)}")

# --- Attempt to Get Colab Proxy URL ---
print("🔗 Attempting to fetch Colab proxy access URL...")
proxy_url = None
for attempt in range(MAX_RETRIES_FOR_URL):
    print(f"   Attempt {attempt + 1}/{MAX_RETRIES_FOR_URL}...")
    try:
        proxy_url = eval_js(f'google.colab.kernel.proxyPort({PORT})')
        if proxy_url:
            print(f"   🎉 Successfully fetched proxy URL!")
            break
    except Exception as e_evaljs:
        print(f"      Failed to fetch URL on attempt {attempt + 1}: {str(e_evaljs)[:100]}...")
    if attempt < MAX_RETRIES_FOR_URL - 1:
        print(f"      Waiting {RETRY_DELAY_SECONDS} seconds before retry...")
        time.sleep(RETRY_DELAY_SECONDS)
print("-" * 70)

# --- Display Results and Monitor Logs ---
if proxy_url:
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; text-align: center; background-color: #f0fff0;'>" \
                 f"<h2 style='color: #2E7D32; margin-bottom:15px;'>🎉 Application Ready!</h2>" \
                 f"<p style='font-size:1.1em;'>Your Wolf_V5 analysis platform should be accessible via the link below:</p>" \
                 f"<p style='margin: 25px 0;'><a href='{proxy_url}' target='_blank' style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px; font-size:1.2em; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);'>🚀 Click here to open Wolf_V5 Application</a></p>" \
                 f"<p style='font-size:0.9em; color:gray;'>Link address: <a href='{proxy_url}' target='_blank'>{proxy_url}</a></p>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:15px;'>If the application doesn't load after clicking, ensure this Colab Notebook cell is still running and try refreshing the page.</p>" \
                 f"<p style='font-size:0.9em; color:orange; margin-top:10px;'><b>Note: This cell will remain running to display application logs. To stop the service, manually interrupt the execution of this cell.</b></p>" \
                 f"</div>"))

    print("\n--- Application Logs (refreshes every 10 seconds) ---")
    print(f"Log source file: {LOG_FILE_PATH}")
    print("If the application encounters issues, relevant error messages may appear here.")
    print("You can stop the service at any time by manually interrupting this cell (click the stop button to the left of this cell in Colab, or use Ctrl+M I).")
    print("-" * 70, flush=True)

    def monitor_streamlit_process():
        streamlit_process.wait()
        if streamlit_process.returncode is not None:
            print(f"\n🔴 Streamlit service has stopped (return code: {streamlit_process.returncode}). Please check logs. Log monitoring will now terminate.", flush=True)

    monitor_thread = threading.Thread(target=monitor_streamlit_process)
    monitor_thread.daemon = True
    monitor_thread.start()

    last_pos = 0
    try:
        while monitor_thread.is_alive():
            try:
                with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                    f.seek(last_pos)
                    new_logs = f.read()
                    if new_logs:
                        print(new_logs, end='', flush=True)
                        last_pos = f.tell()
            except FileNotFoundError:
                print(f"Warning: Log file {LOG_FILE_PATH} not found. Waiting for the application to create it...", flush=True)
            except Exception as e:
                print(f"Error reading log file: {e}", flush=True)

            if streamlit_process.poll() is not None:
                if monitor_thread.is_alive():
                    print("\nStreamlit process terminated, but monitor thread is still alive. Preparing to stop log monitoring.", flush=True)
                break

            time.sleep(10)
        print("\n--- Log monitoring loop ended (Streamlit service may have stopped) ---", flush=True)

    except KeyboardInterrupt:
        print("\n⌨️ Manual interruption detected (KeyboardInterrupt). Stopping service...", flush=True)
    except Exception as e_loop:
        print(f"\n💥 Unexpected error in log monitoring loop: {e_loop}", flush=True)
    finally:
        print("\n--- Attempting to terminate Streamlit service ---", flush=True)
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=10)
                print("✅ Streamlit service terminated successfully.", flush=True)
            except subprocess.TimeoutExpired:
                print("⚠️ Streamlit service termination timed out, attempting to kill...", flush=True)
                streamlit_process.kill()
                streamlit_process.wait()
                print("Streamlit service killed.", flush=True)
        else:
            print("ℹ️ Streamlit service had already stopped or did not start successfully.", flush=True)

        if monitor_thread and monitor_thread.is_alive():
            print("Waiting for log monitor thread to end...", flush=True)
            monitor_thread.join(timeout=5)
            if monitor_thread.is_alive():
                 print("Monitor thread did not end in time.", flush=True)
        print("--- Cell 2 execution finished ---", flush=True)

else:
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #F44336; padding: 20px; border-radius: 10px; text-align: center; background-color: #fff0f0;'>" \
                 f"<h2 style='color: #C62828; margin-bottom:15px;'>❌ Failed to automatically fetch Colab proxy URL</h2>" \
                 f"<p style='font-size:1.1em; color:#D32F2F;'>We could not automatically generate a clickable Colab proxy link for your application.</p>" \
                 f"<p style='color:orange; margin-top:15px;'>**Possible reasons and suggestions:**</p>" \
                 f"<ul style='text-align:left; display:inline-block; margin-top:10px;'>" \
                 f"<li>The Streamlit application might not have started successfully in the background (check for error messages).</li>" \
                 f"<li>Colab's proxy service might be temporarily unavailable or slow to respond.</li>" \
                 f"<li>You can try **re-running this cell**.</li>" \
                 f"<li>If the issue persists, please **check this cell's execution log for any error messages**. Streamlit itself might print an 'External URL' that you can try copying manually into your browser.</li>" \
                 f"</ul>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:20px;'>Note: The application needs to remain running in Colab to be accessible.</p>" \
                 f"</div>"))
    print("\n❌ Failed to launch application or get link, cell will not remain active. Please check previous error messages.")

```
**Execution Notes:**
*   After execution, Colab will attempt to provide a URL like `https://[random_string].googleusercontent.com/proxy/8501/`. Click this link to open the application in a new browser tab.
*   **This cell will continue to run** to keep the Streamlit service alive and will display logs from `{GDRIVE_PROJECT_DIR}/logs/streamlit.log`.
*   To stop the service, **manually interrupt the execution of this cell** (e.g., by clicking the stop button to the left of the cell or using the shortcut `Ctrl+M I`).

### 應用程式操作指南

1.  **設定 Gemini API Key (重要)：**
    *   應用程式啟動後，請在側邊欄的 "API 設定" 區域輸入您的 Gemini API Key。優先推薦使用 Colab Secrets Manager (詳見下方附錄 A)。`app.py` 已設計為優先從 Colab Secrets (名稱 `GEMINI_API_KEY`) 加載金鑰。
    *   無有效 API Key，AI 分析功能無法使用。

2.  **從 Google Drive 讀取分析文件：**
    *   在側邊欄 "讀取 Google Drive 文件" 區域，輸入您想分析的、存於您 Google Drive `My Drive` 下的**相對於 `My Drive` 的文件路徑** (例如 `wolfAI/my_report.txt` 或 `Colab_Data/another_report.txt`)。
    *   **日期解析提示：** 為了讓 AI 能更好地進行市場回顧，建議您的文本文件內容中包含明確的日期標識，格式為 `日期：YYYY-MM-DD`。應用程式會嘗試從此標識解析基準日期。
    *   點擊 "讀取並設為當前分析文件"。

3.  **進行 AI 初步分析 (包含市場回顧)：**
    *   文件成功讀取後，主聊天區下方會出現 "AI 初步分析 (包含市場回顧)" 按鈕。
    *   點擊此按鈕：
        *   AI 會對文本內容進行摘要分析（包括「善甲狼」核心觀點等）。
        *   **市場回顧：** AI 會嘗試根據從文件中解析出的日期（若無則使用當前日期），自動獲取並展示台灣加權指數 (`^TWII`)、納斯達克綜合指數 (`^IXIC`)、標普500指數 (`^GSPC`)、費城半導體指數 (`^SOX`)和日經225指數 (`^N225`) 在該日期前一週的**日線走勢圖**和**數據摘要**。這些圖表和摘要將作為 AI 分析的一部分顯示在聊天區。
        *   `yfinance` 套件（用於獲取市場數據）已在 Cell 1 中自動安裝。

4.  **聊天互動：**
    *   您可以在聊天區底部的輸入框中與 AI 進行對話。進階的聊天指令功能（如查詢特定股票數據）正在規劃中。

### 注意事項
*   Colab Notebook 需保持運行。
*   環境重啟後需重新執行 Cell 1 和 Cell 2。
*   程式碼主要透過 GitHub 更新。

---

## 查看應用程式日誌 (Viewing Application Logs)

本應用程式內建了詳細的日誌記錄功能，以協助使用者和開發者追蹤執行狀況及進行問題排查。

### 如何查看日誌

1.  **位置**：在應用程式主頁面的底部，你會找到一個名為「📄 應用程式日誌 (Application Logs)」的可展開區域。
2.  **操作**：點擊該區域即可展開，查看即時的應用程式日誌訊息。日誌會顯示最新的事件在最上方。
3.  **清除日誌**：在此區域內還有一個「清除日誌紀錄」按鈕，可以清除當前顯示在介面中的日誌。這不會影響到伺服器控制台的日誌輸出。

### 日誌級別

日誌級別預設為 `DEBUG`。這表示會記錄非常詳細的應用程式執行信息，包括函數調用、變數狀態、API 請求與回應等。這對於深入了解應用程式的內部運作和快速定位問題非常有幫助。

### 日誌用途

這些日誌主要用於：
*   開發者進行應用程式偵錯。
*   在遇到預期外的行為或錯誤時，提供詳細的執行上下文。
*   幫助理解數據處理和 API 互動的流程。

---
### 附錄 A：安全設定 Gemini API Key (推薦)

(此部分內容與上一版 README.md 相同，保持不變)
為了更安全和持久地使用 API Key，建議使用 Colab 的 **Secrets Manager**：
1.  **在 Colab 中添加密鑰：** 左側鑰匙圖標 -> "+ 新增密鑰" -> 名稱 `GEMINI_API_KEY` -> 貼上金鑰值 -> 啟用 "筆記本訪問權限"。
2.  **應用程式中的讀取邏輯**：應用程式會透過 `utils/session_state_manager.py` 中的邏輯，優先從 Colab Secrets 讀取名為 `GEMINI_API_KEY` 的金鑰。

---

# (English Content)

# Wolf_V5

## Project Goal
(Same as previous version)

## How to Run in Colab (New Two-Cell Process)
(Same as previous version, up to Prerequisites)

### Prerequisites
*   A valid Google account.
*   A Gemini API Key is recommended for full AI analysis features. Obtain one from [Google AI Studio](https://aistudio.google.com/app/apikey).

### Cell 1: Environment Setup and Project Deployment
Copy the entire script content below, paste it into the first code cell of your Colab Notebook, and then run this cell.
This cell will:
1.  Install necessary Python packages (`streamlit`, `google-generativeai`, `yfinance`, `pandas`).
2.  Mount your Google Drive.
3.  Create a `wolfAI` directory under `My Drive`.
4.  Clone/update the project code from GitHub (`https://github.com/hsp1234-web/Ai_wolf.git`) into `My Drive/wolfAI/`.

```python
#@title 1. Environment Setup & Ai_wolf Project Deployment (Click to expand code)
# === Colab Environment Setup & Ai_wolf Project Deployment ===
# Cell 1: Please run this cell to complete all initial setup.
import os

# --- 1. Install Necessary Python Packages ---
print("Installing necessary Python packages (streamlit, google-generativeai, yfinance, pandas)...")
!pip install streamlit google-generativeai yfinance pandas -q
# Added pandas because yfinance might need it, and it's also used in app.py
print("Package installation complete!\n")

# --- 2. Mount Google Drive ---
print("Attempting to mount Google Drive...")
from google.colab import drive
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive mounted successfully!\n")
except Exception as e:
    print(f"Failed to mount Google Drive: {e}")
    print("Please check the authorization steps in the pop-up window. If issues persist, try 'Runtime' -> 'Disconnect and delete runtime', then re-run this cell.") # Note: Colab-specific runtime management tip
    raise # Raise exception to stop execution if mounting fails

# --- 3. Define Project Path and Create Target Folder ---
# GDRIVE_PROJECT_DIR will be defined here, specifying the project directory in Google Drive
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI"
print(f"Project will be deployed to Google Drive path: {GDRIVE_PROJECT_DIR}")
# Using !mkdir -p to execute a shell command to create the directory if it doesn't already exist
!mkdir -p "{GDRIVE_PROJECT_DIR}"
# 同時創建日誌目錄
!mkdir -p "{GDRIVE_PROJECT_DIR}/logs"
print(f"Project directory confirmed/created and logs directory created.\n")

# --- 4. Clone or Update Ai_wolf Project Code from GitHub ---
GIT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
GIT_DIR_CHECK = f"{GDRIVE_PROJECT_DIR}/.git" # Used to check if the .git directory exists, indicating a Git repository

print(f"Fetching latest code from {GIT_REPO_URL}...")
if os.path.isdir(GIT_DIR_CHECK): # Use os.path.isdir to check if the directory exists
    print("Existing project Git repository detected, attempting to update (git pull)...")
    import subprocess # Import subprocess module to execute shell commands
    # This is a more robust update method: first fetch and reset to the latest state of the remote main branch, then pull
    git_pull_command = f"cd '{GDRIVE_PROJECT_DIR}' && git fetch origin main && git reset --hard origin/main && git pull origin main"
    print(f"Executing update command: {git_pull_command}")
    process = subprocess.run(git_pull_command, shell=True, capture_output=True, text=True)
    if process.returncode == 0:
        print("Project update successful (git pull)!")
        if process.stdout: print(f"Git Pull Output:\n{process.stdout}")
        if process.stderr: print(f"Git Pull Error Messages (if any):\n{process.stderr}")
    else:
        print(f"git pull failed (return code: {process.returncode}). Error details:")
        print(process.stderr)
        print("This could be due to local merge conflicts or network issues. Consider manually deleting the 'wolfAI' directory in Google Drive and re-running this cell for a fresh clone.")
else:
    print(f"No existing .git repository found, cloning project from {GIT_REPO_URL} to {GDRIVE_PROJECT_DIR} ...")
    # Using !git clone to execute a shell command to clone the repository, --depth 1 for a shallow clone (latest commit only)
    !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}"
    print("Project cloning complete!")

print("\n--- 5. Verify Project Files ---")
print(f"Listing contents of {GDRIVE_PROJECT_DIR}:")
# Using !ls -la to execute a shell command to list file details (including hidden files)
!ls -la "{GDRIVE_PROJECT_DIR}"
APP_PY_PATH = f"{GDRIVE_PROJECT_DIR}/app.py" # Define the path to the main application file
# Check if the main app.py file exists
if os.path.isfile(APP_PY_PATH): # Use os.path.isfile to check if the file exists
    print(f"\nSuccessfully found the main application file: {APP_PY_PATH}")
    print("\n✅ Cell 1 Setup Complete! You can now proceed to run Cell 2.")
else:
    print(f"\n❌ Error: Main application file app.py not found in {GDRIVE_PROJECT_DIR}!")
    print(f"Please check if app.py exists in the GitHub repository ({GIT_REPO_URL}) at the root level or if there were errors in previous steps.")

```
**Execution Notes:**
*   Monitor Colab output.
*   **Google Drive Authorization:** Authorize when prompted.
*   **GitHub Updates:** The script attempts to pull the latest code.

### Cell 2: Launch the Streamlit Application and Monitor Logs
After Cell 1 executes successfully, copy the following into the second Colab cell and run it.
This cell will:
1. Launch the Streamlit application.
2. Attempt to fetch and display a publicly accessible Colab proxy URL.
3. **Remain running** to maintain the Streamlit service and will **output live application logs**.
4. You can stop the Streamlit service by **manually interrupting this cell (Interrupt execution)**.

```python
#@title 2. 🚀 Launch Wolf_V5 App, Get Link & Monitor Logs (Click to execute)
# === Wolf_V5 Project Launch, Link Retrieval & Log Monitoring ===
# Cell 2: Execute this cell to launch the Streamlit application, automatically fetch the access link, and continuously output logs.
#         You can manually interrupt this cell at any time to stop the service.

import subprocess
import time
import os
import threading # For monitoring the Streamlit process
from IPython.display import display, HTML, clear_output
from google.colab.output import eval_js

# --- Configuration Parameters ---
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI" # Inherited from Cell 1 or redefined here
STREAMLIT_APP_PATH = f"{GDRIVE_PROJECT_DIR}/app.py"
LOG_DIR = f"{GDRIVE_PROJECT_DIR}/logs" # Log directory
LOG_FILE_PATH = f"{LOG_DIR}/streamlit.log" # Streamlit app should output logs here

PORT = 8501 # Port for the Streamlit app
WAIT_SECONDS_FOR_SERVER = 15
MAX_RETRIES_FOR_URL = 3
RETRY_DELAY_SECONDS = 5

# --- Clear Previous Output ---
# clear_output(wait=True) # Uncomment to clear previous output of this cell on each run

print("🚀 Preparing to launch Streamlit application...")
print(f"   Application path: {STREAMLIT_APP_PATH}")
print(f"   Log file path: {LOG_FILE_PATH}")
print(f"   Expected listening port: {PORT}")
print("-" * 70)

# --- Check if app.py Exists ---
if not os.path.exists(STREAMLIT_APP_PATH):
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Error: Streamlit application file not found!</p>" \
                 f"<p style='color:red;'>   Please ensure the path <code style='color:red; background-color:#f0f0f0; padding:2px 4px; border-radius:3px;'>{STREAMLIT_APP_PATH}</code> is correct,</p>" \
                 f"<p style='color:red;'>   and that you have successfully executed all steps in Cell 1.</p>"))
    raise SystemExit("Application file app.py not found, terminating execution.")

# --- Ensure Log Directory and File Exist ---
os.makedirs(LOG_DIR, exist_ok=True)
with open(LOG_FILE_PATH, 'a') as f: # 'a' mode creates the file if it doesn't exist
    f.write(f"--- Colab script log monitoring started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
print(f"Log file {LOG_FILE_PATH} confirmed/created.")
print("-" * 70)

# --- Launch Streamlit Server ---
streamlit_process = None
monitor_thread = None # Initialize monitor thread variable

try:
    print(f"⏳ Attempting to launch Streamlit in the background (approx. {WAIT_SECONDS_FOR_SERVER} seconds)...")
    cmd = ["streamlit", "run", STREAMLIT_APP_PATH,
           "--server.port", str(PORT),
           "--server.headless", "true",
           "--browser.gatherUsageStats", "false"]

    streamlit_process = subprocess.Popen(cmd)

    print(f"   Streamlit launch command sent (PID: {streamlit_process.pid if streamlit_process else 'Unknown'}).")
    print(f"   Allowing server {WAIT_SECONDS_FOR_SERVER} seconds to initialize...")
    time.sleep(WAIT_SECONDS_FOR_SERVER)

    if streamlit_process.poll() is not None:
        display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Streamlit appears to have failed to start or terminated unexpectedly (return code: {streamlit_process.returncode}).</p>" \
                     f"<p style='color:orange;'>   Please check if `app.py` has syntax errors, or try checking Colab's 'Runtime' -> 'View runtime logs'.</p>" \
                     f"<p style='color:orange;'>   If your Streamlit application has internal logging (e.g., writing to {LOG_FILE_PATH}), that file might contain more clues.</p>"))
        raise SystemExit(f"Streamlit process failed to stay running (return code: {streamlit_process.returncode}).")

    print("✅ Streamlit should now be running in the background.")
    print("-" * 70)

except Exception as e:
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ An unexpected error occurred while launching Streamlit:</p>" \
                 f"<p style='color:red; font-family:monospace; white-space:pre-wrap;'>{str(e)}</p>" \
                 f"<p style='color:orange;'>   Please check the error message, ensure Streamlit is correctly installed, and paths are correct.</p>"))
    if streamlit_process and streamlit_process.poll() is None:
        streamlit_process.terminate()
    raise SystemExit(f"Failed to launch Streamlit: {str(e)}")

# --- Attempt to Get Colab Proxy URL ---
print("🔗 Attempting to fetch Colab proxy access URL...")
proxy_url = None
for attempt in range(MAX_RETRIES_FOR_URL):
    print(f"   Attempt {attempt + 1}/{MAX_RETRIES_FOR_URL}...")
    try:
        proxy_url = eval_js(f'google.colab.kernel.proxyPort({PORT})')
        if proxy_url:
            print(f"   🎉 Successfully fetched proxy URL!")
            break
    except Exception as e_evaljs:
        print(f"      Failed to fetch URL on attempt {attempt + 1}: {str(e_evaljs)[:100]}...")
    if attempt < MAX_RETRIES_FOR_URL - 1:
        print(f"      Waiting {RETRY_DELAY_SECONDS} seconds before retry...")
        time.sleep(RETRY_DELAY_SECONDS)
print("-" * 70)

# --- Display Results and Monitor Logs ---
if proxy_url:
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; text-align: center; background-color: #f0fff0;'>" \
                 f"<h2 style='color: #2E7D32; margin-bottom:15px;'>🎉 Application Ready!</h2>" \
                 f"<p style='font-size:1.1em;'>Your Wolf_V5 analysis platform should be accessible via the link below:</p>" \
                 f"<p style='margin: 25px 0;'><a href='{proxy_url}' target='_blank' style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px; font-size:1.2em; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);'>🚀 Click here to open Wolf_V5 Application</a></p>" \
                 f"<p style='font-size:0.9em; color:gray;'>Link address: <a href='{proxy_url}' target='_blank'>{proxy_url}</a></p>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:15px;'>If the application doesn't load after clicking, ensure this Colab Notebook cell is still running and try refreshing the page.</p>" \
                 f"<p style='font-size:0.9em; color:orange; margin-top:10px;'><b>Note: This cell will remain running to display application logs. To stop the service, manually interrupt the execution of this cell.</b></p>" \
                 f"</div>"))

    print("\n--- Application Logs (refreshes every 10 seconds) ---")
    print(f"Log source file: {LOG_FILE_PATH}")
    print("If the application encounters issues, relevant error messages may appear here.")
    print("You can stop the service at any time by manually interrupting this cell (click the stop button to the left of this cell in Colab, or use Ctrl+M I).")
    print("-" * 70, flush=True)

    def monitor_streamlit_process():
        streamlit_process.wait()
        if streamlit_process.returncode is not None:
            print(f"\n🔴 Streamlit service has stopped (return code: {streamlit_process.returncode}). Please check logs. Log monitoring will now terminate.", flush=True)

    monitor_thread = threading.Thread(target=monitor_streamlit_process)
    monitor_thread.daemon = True
    monitor_thread.start()

    last_pos = 0
    try:
        while monitor_thread.is_alive():
            try:
                with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                    f.seek(last_pos)
                    new_logs = f.read()
                    if new_logs:
                        print(new_logs, end='', flush=True)
                        last_pos = f.tell()
            except FileNotFoundError:
                print(f"Warning: Log file {LOG_FILE_PATH} not found. Waiting for the application to create it...", flush=True)
            except Exception as e:
                print(f"Error reading log file: {e}", flush=True)

            if streamlit_process.poll() is not None:
                if monitor_thread.is_alive():
                    print("\nStreamlit process terminated, but monitor thread is still alive. Preparing to stop log monitoring.", flush=True)
                break

            time.sleep(10)
        print("\n--- Log monitoring loop ended (Streamlit service may have stopped) ---", flush=True)

    except KeyboardInterrupt:
        print("\n⌨️ Manual interruption detected (KeyboardInterrupt). Stopping service...", flush=True)
    except Exception as e_loop:
        print(f"\n💥 Unexpected error in log monitoring loop: {e_loop}", flush=True)
    finally:
        print("\n--- Attempting to terminate Streamlit service ---", flush=True)
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=10)
                print("✅ Streamlit service terminated successfully.", flush=True)
            except subprocess.TimeoutExpired:
                print("⚠️ Streamlit service termination timed out, attempting to kill...", flush=True)
                streamlit_process.kill()
                streamlit_process.wait()
                print("Streamlit service killed.", flush=True)
        else:
            print("ℹ️ Streamlit service had already stopped or did not start successfully.", flush=True)

        if monitor_thread and monitor_thread.is_alive():
            print("Waiting for log monitor thread to end...", flush=True)
            monitor_thread.join(timeout=5)
            if monitor_thread.is_alive():
                 print("Monitor thread did not end in time.", flush=True)
        print("--- Cell 2 execution finished ---", flush=True)

else:
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #F44336; padding: 20px; border-radius: 10px; text-align: center; background-color: #fff0f0;'>" \
                 f"<h2 style='color: #C62828; margin-bottom:15px;'>❌ Failed to automatically fetch Colab proxy URL</h2>" \
                 f"<p style='font-size:1.1em; color:#D32F2F;'>We could not automatically generate a clickable Colab proxy link for your application.</p>" \
                 f"<p style='color:orange; margin-top:15px;'>**Possible reasons and suggestions:**</p>" \
                 f"<ul style='text-align:left; display:inline-block; margin-top:10px;'>" \
                 f"<li>The Streamlit application might not have started successfully in the background (check for error messages).</li>" \
                 f"<li>Colab's proxy service might be temporarily unavailable or slow to respond.</li>" \
                 f"<li>You can try **re-running this cell**.</li>" \
                 f"<li>If the issue persists, please **check this cell's execution log for any error messages**. Streamlit itself might print an 'External URL' that you can try copying manually into your browser.</li>" \
                 f"</ul>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:20px;'>Note: The application needs to remain running in Colab to be accessible.</p>" \
                 f"</div>"))
    print("\n❌ Failed to launch application or get link, cell will not remain active. Please check previous error messages.")

```
**Execution Notes:**
*   After execution, Colab will attempt to provide a URL like `https://[random_string].googleusercontent.com/proxy/8501/`. Click this link to open the application in a new browser tab.
*   **This cell will continue to run** to keep the Streamlit service alive and will display logs from `{GDRIVE_PROJECT_DIR}/logs/streamlit.log`.
*   To stop the service, **manually interrupt the execution of this cell** (e.g., by clicking the stop button to the left of the cell or using the shortcut `Ctrl+M I`).

### 應用程式操作指南

1.  **設定 Gemini API Key (重要)：**
    *   應用程式啟動後，請在側邊欄的 "API 設定" 區域輸入您的 Gemini API Key。優先推薦使用 Colab Secrets Manager (詳見下方附錄 A)。`app.py` 已設計為優先從 Colab Secrets (名稱 `GEMINI_API_KEY`) 加載金鑰。
    *   無有效 API Key，AI 分析功能無法使用。

2.  **從 Google Drive 讀取分析文件：**
    *   在側邊欄 "讀取 Google Drive 文件" 區域，輸入您想分析的、存於您 Google Drive `My Drive` 下的**相對於 `My Drive` 的文件路徑** (例如 `wolfAI/my_report.txt` 或 `Colab_Data/another_report.txt`)。
    *   **日期解析提示：** 為了讓 AI 能更好地進行市場回顧，建議您的文本文件內容中包含明確的日期標識，格式為 `日期：YYYY-MM-DD`。應用程式會嘗試從此標識解析基準日期。
    *   點擊 "讀取並設為當前分析文件"。

3.  **進行 AI 初步分析 (包含市場回顧)：**
    *   文件成功讀取後，主聊天區下方會出現 "AI 初步分析 (包含市場回顧)" 按鈕。
    *   點擊此按鈕：
        *   AI 會對文本內容進行摘要分析（包括「善甲狼」核心觀點等）。
        *   **市場回顧：** AI 會嘗試根據從文件中解析出的日期（若無則使用當前日期），自動獲取並展示台灣加權指數 (`^TWII`)、納斯達克綜合指數 (`^IXIC`)、標普500指數 (`^GSPC`)、費城半導體指數 (`^SOX`)和日經225指數 (`^N225`) 在該日期前一週的**日線走勢圖**和**數據摘要**。這些圖表和摘要將作為 AI 分析的一部分顯示在聊天區。
        *   `yfinance` 套件（用於獲取市場數據）已在 Cell 1 中自動安裝。

4.  **聊天互動：**
    *   您可以在聊天區底部的輸入框中與 AI 進行對話。進階的聊天指令功能（如查詢特定股票數據）正在規劃中。

### 注意事項
*   Colab Notebook 需保持運行。
*   環境重啟後需重新執行 Cell 1 和 Cell 2。
*   程式碼主要透過 GitHub 更新。

---

## 查看應用程式日誌 (Viewing Application Logs)

本應用程式內建了詳細的日誌記錄功能，以協助使用者和開發者追蹤執行狀況及進行問題排查。

### 如何查看日誌

1.  **位置**：在應用程式主頁面的底部，你會找到一個名為「📄 應用程式日誌 (Application Logs)」的可展開區域。
2.  **操作**：點擊該區域即可展開，查看即時的應用程式日誌訊息。日誌會顯示最新的事件在最上方。
3.  **清除日誌**：在此區域內還有一個「清除日誌紀錄」按鈕，可以清除當前顯示在介面中的日誌。這不會影響到伺服器控制台的日誌輸出。

### 日誌級別

日誌級別預設為 `DEBUG`。這表示會記錄非常詳細的應用程式執行信息，包括函數調用、變數狀態、API 請求與回應等。這對於深入了解應用程式的內部運作和快速定位問題非常有幫助。

### 日誌用途

這些日誌主要用於：
*   開發者進行應用程式偵錯。
*   在遇到預期外的行為或錯誤時，提供詳細的執行上下文。
*   幫助理解數據處理和 API 互動的流程。

---
### 附錄 A：安全設定 Gemini API Key (推薦)

(此部分內容與上一版 README.md 相同，保持不變)
為了更安全和持久地使用 API Key，建議使用 Colab 的 **Secrets Manager**：
1.  **在 Colab 中添加密鑰：** 左側鑰匙圖標 -> "+ 新增密鑰" -> 名稱 `GEMINI_API_KEY` -> 貼上金鑰值 -> 啟用 "筆記本訪問權限"。
2.  **應用程式中的讀取邏輯**：應用程式會透過 `utils/session_state_manager.py` 中的邏輯，優先從 Colab Secrets 讀取名為 `GEMINI_API_KEY` 的金鑰。

---
