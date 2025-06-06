# (中文內容)

# 善甲狼週報 - 人機協同聊天式分析平台

## 專案目標

本專案旨在打造一個在 Google Colaboratory (Colab) 環境中運行的、具有聊天式圖形化介面的人機協同智慧分析平台。平台將用於系統性地處理「善甲狼a機智生活」約150週的歷史貼文，輔助使用者回顧歷史交易機會，並最終由使用者將精煉內容手動整理至Google文件。

## 如何在 Colab 中運行 (全新雙儲存格流程)

以下步驟將指導您如何在 Google Colab 環境中，僅透過兩個主要儲存格 (Cell) 來設置並運行此 Streamlit 應用程式。

### 前置準備

*   一個有效的 Google 帳戶。
*   建議擁有一個 Gemini API Key 以體驗完整的 AI 分析功能。您可以從 [Google AI Studio](https://aistudio.google.com/app/apikey) 獲取。

### Cell 1: 環境設置與專案部署

複製以下完整腳本內容，並將其貼到 Colab Notebook 的第一個程式碼儲存格中，然後執行此儲存格。
此儲存格會完成以下工作：
1.  安裝所有必要的 Python 套件 (`streamlit`, `google-generativeai`, `yfinance`, `pandas`)。
2.  掛載您的 Google Drive。
3.  在您的 Google Drive `My Drive` 下創建一個 `wolfAI` 目錄。
4.  從 GitHub (`https://github.com/hsp1234-web/Ai_wolf.git`) 克隆最新的專案程式碼到 `My Drive/wolfAI/`，如果已存在則嘗試更新。

```python
#@title 1. 環境設置與 Ai_wolf 專案部署 (請點此展開程式碼)
# === Colab 環境設置與 Ai_wolf 專案部署 ===
# Cell 1: 請執行此儲存格以完成所有初始設定。
import os

# --- 1. 安裝必要的 Python 套件 ---
print("正在安裝必要的 Python 套件 (streamlit, google-generativeai, yfinance, pandas)...")
!pip install streamlit google-generativeai yfinance pandas -q
# 添加了 pandas 因為 yfinance 可能需要它，且 app.py 中也用到了
print("套件安裝完成！\n")

# --- 2. 掛載 Google Drive ---
print("正在嘗試掛載 Google Drive...")
from google.colab import drive
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive 掛載成功！\n")
except Exception as e:
    print(f"Google Drive 掛載失敗: {e}")
    print("請檢查彈出視窗中的授權步驟，並確保已授權。如果問題持續，請嘗試在 Colab 選單中選擇 '執行階段' -> '中斷並刪除執行階段'，然後重新執行此儲存格。") # 註：Colab 特有的執行階段管理提示
    raise # 拋出異常以停止執行，如果掛載失敗

# --- 3. 定義專案路徑並建立目標資料夾 ---
# GDRIVE_PROJECT_DIR 將在此步驟定義，用於指定 Google Drive 中的專案目錄
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI"
print(f"專案將部署到 Google Drive 路徑: {GDRIVE_PROJECT_DIR}")
# 使用 !mkdir -p 執行 shell 指令來建立資料夾，如果尚不存在的話
!mkdir -p "{GDRIVE_PROJECT_DIR}"
print(f"已確認/建立專案目錄。\n")

# --- 4. 從 GitHub 克隆或更新 Ai_wolf 專案程式碼 ---
GIT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
GIT_DIR_CHECK = f"{GDRIVE_PROJECT_DIR}/.git" # 用於檢查 .git 目錄是否存在，以判斷是否為 Git 倉庫

print(f"正在從 {GIT_REPO_URL} 獲取最新程式碼...")
if os.path.isdir(GIT_DIR_CHECK): # 使用 os.path.isdir 檢查目錄是否存在
    print("偵測到現有的專案 Git 倉庫，嘗試更新 (git pull)...")
    import subprocess # 引入 subprocess 模組以執行 shell 指令
    # 這是一個較穩健的更新方法：先 fetch 並 reset 到遠端 main 分支的最新狀態，然後再 pull
    git_pull_command = f"cd '{GDRIVE_PROJECT_DIR}' && git fetch origin main && git reset --hard origin/main && git pull origin main"
    print(f"執行更新指令: {git_pull_command}")
    process = subprocess.run(git_pull_command, shell=True, capture_output=True, text=True)
    if process.returncode == 0:
        print("專案更新成功 (git pull)！")
        if process.stdout: print(f"Git Pull 輸出:\n{process.stdout}")
        if process.stderr: print(f"Git Pull 錯誤訊息 (如果有):\n{process.stderr}")
    else:
        print(f"git pull 失敗 (返回碼: {process.returncode})。詳細錯誤訊息如下：")
        print(process.stderr)
        print("這可能是由於本地修改衝突或網路問題。建議檢查上述錯誤，或考慮手動刪除 Google Drive 中的 'wolfAI' 目錄後重新執行此儲存格以進行全新克隆。")
else:
    print(f"未找到現有 .git 倉庫，開始克隆專案從 {GIT_REPO_URL} 到 {GDRIVE_PROJECT_DIR} ...")
    # 使用 !git clone 執行 shell 指令來克隆倉庫，--depth 1 表示淺克隆，只獲取最新的 commit
    !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}"
    print("專案克隆完成！")

print("\n--- 5. 檢查專案檔案 ---")
print(f"列出 {GDRIVE_PROJECT_DIR} 中的內容：")
# 使用 !ls -la 執行 shell 指令列出檔案詳細資訊（包含隱藏檔案）
!ls -la "{GDRIVE_PROJECT_DIR}"
APP_PY_PATH = f"{GDRIVE_PROJECT_DIR}/app.py" # 定義主應用程式檔案的路徑
# 檢查主要 app.py 檔案是否存在
if os.path.isfile(APP_PY_PATH): # 使用 os.path.isfile 檢查檔案是否存在
    print(f"\n成功找到主要應用程式檔案: {APP_PY_PATH}")
    print("\n✅ Cell 1 設定完成！您現在可以執行下一個儲存格 (Cell 2) 來啟動 Streamlit 應用程式了。")
else:
    print(f"\n❌ 錯誤：未在 {GDRIVE_PROJECT_DIR} 中找到主要的 app.py 檔案！")
    print("請檢查 GitHub 倉庫中是否包含 app.py (位於根目錄)，或者之前的步驟是否有誤。")
    print(f"如果確認 GitHub ({GIT_REPO_URL}) 內容無誤，但此處仍找不到 app.py，可能是 Colab 與 Google Drive 之間的文件同步延遲，或磁碟空間問題。")

```
**執行說明：**
*   執行此儲存格時，請留意 Colab 的輸出。
*   **Google Drive 授權：** 首次執行或長時間未使用後，Colab 會彈出一個視窗要求您授權訪問 Google Drive。
*   **GitHub 更新：** 此腳本會嘗試從 GitHub 拉取最新程式碼。

### Cell 2: 啟動 Streamlit 應用程式

在 Cell 1 成功執行完畢後，複製以下指令到 Colab Notebook 的第二個程式碼儲存格中，然後執行它。

```python
#@title 2. 🚀 啟動 Ai_wolf 應用並獲取訪問連結 (點此執行)
# === Ai_wolf 專案啟動與連結獲取 ===
# Cell 2: 執行此儲存格來啟動 Streamlit 應用程式，並自動獲取訪問連結。

import subprocess
import time
import os
from IPython.display import display, HTML, clear_output
from google.colab.output import eval_js

# --- 配置參數 ---
STREAMLIT_APP_PATH = "/content/drive/MyDrive/wolfAI/app.py"
PORT = 8501
WAIT_SECONDS_FOR_SERVER = 15 # 等待伺服器啟動的時間
MAX_RETRIES_FOR_URL = 3 # 嘗試獲取 URL 的最大次數
RETRY_DELAY_SECONDS = 5 # 每次重試之間的延遲

# --- 清理先前輸出 (如果需要) ---
# clear_output(wait=True) # 如果希望每次執行都清空之前此儲存格的輸出，取消此行註解

print("🚀 正在準備啟動 Streamlit 應用程式...")
print(f"   應用程式路徑: {STREAMLIT_APP_PATH}")
print(f"   預計監聽端口: {PORT}")
print("-" * 70)

# --- 檢查 app.py 是否存在 ---
if not os.path.exists(STREAMLIT_APP_PATH):
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ 錯誤：找不到 Streamlit 應用程式檔案！</p>" \
                 f"<p style='color:red;'>   請確認路徑 <code style='color:red; background-color:#f0f0f0; padding:2px 4px; border-radius:3px;'>{STREAMLIT_APP_PATH}</code> 是否正確，</p>" \
                 f"<p style='color:red;'>   並且您已成功執行 Cell 1 中的所有步驟。</p>"))
    # 使用 raise SystemExit() 會終止儲存格執行但不會顯示 traceback
    # 如果需要顯示 traceback，可以直接 raise Exception()
    raise SystemExit("應用程式檔案 app.py 未找到，終止執行。")

# --- 啟動 Streamlit 伺服器 ---
streamlit_process = None
try:
    print(f"⏳ 正在嘗試於背景啟動 Streamlit (約需 {WAIT_SECONDS_FOR_SERVER} 秒)...")
    # 將 Streamlit 的 stdout 和 stderr 重定向，以避免其日誌充滿 Colab 輸出
    # 如果需要調試 Streamlit 自身的啟動問題，可以移除 stdout 和 stderr 的重定向，或將其導向檔案
    cmd = ["streamlit", "run", STREAMLIT_APP_PATH, "--server.port", str(PORT), "--server.headless", "true", "--browser.gatherUsageStats", "false"]

    # 注意：在 Colab 中，subprocess 的行為有時與本機不同，特別是對於長時間運行的伺服器。
    # DEVNULL 可能會導致某些情況下 server 過早退出，如果遇到問題，可以嘗試重定向到檔案或移除重定向進行調試。
    streamlit_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"   Streamlit 啟動指令已送出 (PID: {streamlit_process.pid if streamlit_process else '未知'})。")
    print(f"   給予伺服器 {WAIT_SECONDS_FOR_SERVER} 秒進行初始化...")
    time.sleep(WAIT_SECONDS_FOR_SERVER)

    # 檢查 Streamlit 是否仍在運行
    if streamlit_process.poll() is not None:
        # 如果 poll() 返回非 None，表示進程已結束
        display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Streamlit 似乎未能成功啟動或已意外終止。</p>" \
                     f"<p style='color:orange;'>   請嘗試重新執行 Cell 1 確認環境，然後再次執行此 Cell 2。</p>" \
                     f"<p style='color:orange;'>   如果問題持續，您可能需要檢查 `app.py` 是否有錯誤，或者嘗試移除上面 Popen 中的 `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` 來查看詳細日誌。</p>"))
        raise SystemExit("Streamlit 進程未能持續運行。")

    print("✅ Streamlit 應已在背景運行。")
    print("-" * 70)

except Exception as e:
    display(HTML(f"<p style='color:red; font-weight:bold;'>❌ 啟動 Streamlit 時發生預期之外的錯誤:</p>" \
                 f"<p style='color:red; font-family:monospace; white-space:pre-wrap;'>{str(e)}</p>" \
                 f"<p style='color:orange;'>   請檢查錯誤訊息，確認 Streamlit 是否已正確安裝，以及相關路徑是否無誤。</p>"))
    if streamlit_process and streamlit_process.poll() is None:
        streamlit_process.terminate() # 嘗試終止進程
    raise SystemExit(f"啟動 Streamlit 失敗: {str(e)}")

# --- 嘗試獲取 Colab 代理 URL ---
print("🔗 現在嘗試獲取 Colab 代理訪問網址...")
proxy_url = None
for attempt in range(MAX_RETRIES_FOR_URL):
    print(f"   嘗試第 {attempt + 1}/{MAX_RETRIES_FOR_URL} 次...")
    try:
        proxy_url = eval_js(f'google.colab.kernel.proxyPort({PORT})')
        if proxy_url:
            print(f"   🎉 成功獲取到代理 URL！")
            break # 成功獲取到 URL，跳出循環
    except Exception as e_evaljs:
        print(f"      獲取 URL 第 {attempt + 1} 次失敗: {str(e_evaljs)[:100]}...") # 只顯示部分錯誤訊息避免過長

    if attempt < MAX_RETRIES_FOR_URL - 1: # 如果不是最後一次嘗試，則等待
        print(f"      等待 {RETRY_DELAY_SECONDS} 秒後重試...")
        time.sleep(RETRY_DELAY_SECONDS)
print("-" * 70)

# --- 顯示結果 ---
if proxy_url:
    # 清理之前的 print 輸出，只顯示最終的按鈕和重要訊息
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; text-align: center; background-color: #f0fff0;'>" \
                 f"<h2 style='color: #2E7D32; margin-bottom:15px;'>🎉 應用程式已準備就緒！</h2>" \
                 f"<p style='font-size:1.1em;'>您的 Ai_wolf 分析平台應該可以透過下面的連結訪問：</p>" \
                 f"<p style='margin: 25px 0;'><a href='{proxy_url}' target='_blank' style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px; font-size:1.2em; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);'>🚀 點此開啟 Ai_wolf 應用程式</a></p>" \
                 f"<p style='font-size:0.9em; color:gray;'>連結地址: <a href='{proxy_url}' target='_blank'>{proxy_url}</a></p>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:15px;'>如果點擊後應用程式未載入，請確保此 Colab Notebook 仍在運行，並可嘗試刷新頁面或重新執行此儲存格。</p>" \
                 f"</div>"))
else:
    # 清理之前的 print 輸出
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #F44336; padding: 20px; border-radius: 10px; text-align: center; background-color: #fff0f0;'>" \
                 f"<h2 style='color: #C62828; margin-bottom:15px;'>❌ 未能自動獲取到 Colab 代理網址</h2>" \
                 f"<p style='font-size:1.1em; color:#D32F2F;'>我們未能為您的應用程式自動生成一個可點擊的 Colab 代理連結。</p>" \
                 f"<p style='color:orange; margin-top:15px;'>**可能的原因與建議：**</p>" \
                 f"<ul style='text-align:left; display:inline-block; margin-top:10px;'>" \
                 f"<li>Streamlit 應用程式可能未能成功在背景啟動。</li>" \
                 f"<li>Colab 的代理服務可能暫時無法使用或響應較慢。</li>" \
                 f"<li>您可以嘗試**重新執行一次此儲存格**。</li>" \
                 f"<li>如果問題持續，請**檢查此儲存格執行時是否有任何錯誤日誌輸出**（在 `clear_output` 清理前）。Streamlit 本身可能會打印一個 'External URL'，您可以嘗試手動複製該 URL 到瀏覽器中訪問。</li>" \
                 f"</ul>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:20px;'>請注意：應用程式需要在 Colab 中保持運行才能被訪問。</p>" \
                 f"</div>"))

# 提示：如果 Streamlit 應用程式有自己的退出機制或使用者可以從其UI中停止它，
# streamlit_process.terminate() 或 .kill() 可能需要在 Notebook 關閉或重新運行此儲存格前被調用，
# 以避免端口衝突。但對於一個簡單的 README 腳本，我們暫時不處理這種複雜的生命週期管理。
# 如果需要手動停止，使用者可以中斷 Colab 的執行階段。
```
**執行說明：**
*   執行後，Colab 會提供一個 `https://[一串隨機字符].googleusercontent.com/proxy/8501/` 格式的網址。點擊此網址即可在瀏覽器新分頁中打開應用。

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
2.  **`app.py` 中的讀取邏輯**：最新版的 `app.py` 已包含優先從 Colab Secrets 讀取 `GEMINI_API_KEY` 的邏輯。

---

# (English Content)

# ShanJiaLang Weekly - Human-Computer Collaborative Chat-based Analysis Platform

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
print(f"Project directory confirmed/created.\n")

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

### Cell 2: Launch the Streamlit Application
After Cell 1 executes successfully, copy the following into the second Colab cell and run it.

```python
#@title 2. Launch Streamlit Application (Background Process)
# === Ai_wolf Project Launch ===
# Cell 2: After Cell 1 has run successfully, execute this cell to launch the Streamlit application.
#         This cell will attempt to launch Streamlit in the background.

print("🚀 Attempting to launch Streamlit application in the background...")
print("⏳ Please wait a few seconds for the application to start running.")
print("After this cell executes, please proceed to run 【the next cell (Cell 3)】 to get and display the application access link.")
print("\n" + "="*70)
print("Executing Streamlit command...")

!streamlit run "/content/drive/MyDrive/wolfAI/app.py" --server.port 8501 &

print("\n" + "="*70)
print("The command to launch Streamlit in the background has been sent.")
print("Please execute 【the next cell (Cell 3)】 to obtain the accessible link.")
print("If Cell 3 is unable to fetch the link after a while, you can check the output log of this cell for an 'External URL' to copy manually.")
```
**Execution Notes:**
*   Click the `https://*.googleusercontent.com/proxy/8501/` URL from Colab output.

### Cell 3: Get and Display Application Access Link

After Cell 2 has finished executing and indicated that Streamlit has been launched in the background, run this cell to obtain a publicly accessible link to the application.

```python
#@title 3. 🔗 Get and Display Application Access Link (Click to expand code)
# === Ai_wolf Project Link Retrieval ===
# Cell 3: After Streamlit is launched by Cell 2, execute this cell to get and display the access link.

from IPython.display import display, HTML
from google.colab.output import eval_js
import time

print("⏳ Attempting to fetch the Colab proxy URL...")
print("   This might take a few seconds, please wait.")

# Allow Colab some time to register the port and prepare the proxy
# If your Streamlit application is large or starts slowly, you might need to increase this delay
time.sleep(8) # Wait for 8 seconds

try:
    proxy_url = eval_js(f'google.colab.kernel.proxyPort(8501)')

    if proxy_url:
        display(HTML(f"<hr><p style='font-size:1.3em; font-weight:bold; margin:20px 0; text-align:center; color:green;'>🎉 Great! Your application should be accessible via the link below:</p>" \
                     f"<p style='font-size:1.2em; text-align:center;'><a href='{proxy_url}' target='_blank' style='padding:10px 15px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px;'>Click here to open Ai_wolf Application</a></p>" \
                     f"<p style='font-size:0.9em; color:gray; text-align:center; margin-top:10px;'>Link address: {proxy_url}</p>" \
                     "<p style='font-size:0.9em; color:gray; text-align:center;'>If the application doesn't load after clicking, please ensure Streamlit from Cell 2 is still running and consider re-running this Cell 3 (sometimes another try or a short wait helps).</p><hr>"))
    else:
        display(HTML("<hr><p style='color:red; font-weight:bold; text-align:center;'>❌ Failed to automatically fetch the Colab proxy URL.</p>" \
                     "<p style='color:orange; text-align:center;'>Please go back to the output log of Cell 2 to see if Streamlit started successfully and displayed an 'External URL'.</p>" \
                     "<p style='color:orange; text-align:center;'>If you see an 'External URL', you can try manually copying that URL into your browser.</p>" \
                     "<p style='color:orange; text-align:center;'>If Cell 2 did not launch Streamlit successfully, check its log for error messages.</p><hr>"))
except Exception as e:
    display(HTML(f"<hr><p style='color:red; font-weight:bold; text-align:center;'>❌ An error occurred while trying to fetch the proxy URL:</p><p style='color:red; text-align:center;'>{str(e)}</p>" \
                 "<p style='color:orange; text-align:center;'>Please go back to the output log of Cell 2, see if Streamlit started successfully and displayed an 'External URL', then try manually copying that URL into your browser.</p><hr>"))

print("\n" + "="*70)
print("Link retrieval attempt finished.")
print(" - If a green 'Click here to open Ai_wolf Application' button appeared above, please use that link.")
print(" - If link retrieval failed, please follow the instructions in the message above.")
```

### Application Usage Guide

1.  **Set Gemini API Key (Important):**
    *   In the app's sidebar ("API 設定"), enter your Gemini API Key. Using Colab Secrets (Appendix A) is highly recommended and `app.py` is designed to prioritize it.
    *   AI analysis won't work without a key.

2.  **Read Analysis File from Google Drive:**
    *   In the sidebar ("讀取 Google Drive 文件"), enter the file path **relative to `My Drive`** (e.g., `wolfAI/my_report.txt` or `Colab_Data/report.txt`).
    *   **Date Parsing Tip:** For optimal market review, ensure your text file includes a date in `日期：YYYY-MM-DD` format. The app will try to parse this.
    *   Click "讀取並設為當前分析文件" (Read and Set as Current Analysis File).

3.  **Perform AI Preliminary Analysis (with Market Review):**
    *   After loading a file, click "AI 初步分析 (包含市場回顧)" (AI Preliminary Analysis (with Market Review)).
    *   The AI will summarize the text content.
    *   **Market Review:** Based on the parsed date from the file (or current date if not found), the AI will automatically fetch and display **daily price charts** and a **data summary** for the preceding week for these indices: Taiwan Weighted (`^TWII`), Nasdaq Composite (`^IXIC`), S&P 500 (`^GSPC`), Philadelphia Semiconductor Index (`^SOX`), and Nikkei 225 (`^N225`). These will appear in the chat area as part of the AI's analysis.
    *   The `yfinance` package for market data is installed by Cell 1.

4.  **Chat Interaction:**
    *   Use the input box at the bottom of the chat area to interact with the AI. Advanced chat command features are planned.

### Important Notes
*   Keep Colab Notebook running.
*   Re-run Cell 1 and Cell 2 after runtime restarts.
*   Code is primarily updated via GitHub.

---

## Viewing Application Logs

This application includes detailed logging features to help users and developers track execution status and troubleshoot issues.

### How to View Logs

1.  **Location**: At the bottom of the application's main page, you will find an expandable section titled "📄 應用程式日誌 (Application Logs)".
2.  **Operation**: Click on this section to expand it and view real-time application log messages. Logs are displayed with the newest events at the top.
3.  **Clear Logs**: Within this section, there is also a "清除日誌紀錄" (Clear Logs) button that can clear the logs currently displayed in the interface. This does not affect log output in the server console.

### Log Level

The log level is set to `DEBUG` by default. This means that very detailed application execution information will be recorded, including function calls, variable states, API requests and responses, etc. This is very helpful for understanding the internal workings of the application and quickly identifying issues.

### Purpose of Logs

These logs are primarily used for:
*   Developers to debug the application.
*   Providing detailed execution context when encountering unexpected behavior or errors.
*   Helping to understand the flow of data processing and API interactions.

---
### Appendix A: Securely Setting Gemini API Key (Recommended)

(This section remains the same as the previous README.md version)
Use Colab's **Secrets Manager** for better security:
1.  **Add Secret in Colab:** Key icon (Secrets) -> "+ New secret" -> Name `GEMINI_API_KEY` -> Paste key value -> Enable "Notebook access".
2.  **Reading Logic in `app.py`**: The latest `app.py` prioritizes reading `GEMINI_API_KEY` from Colab Secrets.

---
