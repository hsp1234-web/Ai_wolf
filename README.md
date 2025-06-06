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
# 同時創建日誌目錄
!mkdir -p "{GDRIVE_PROJECT_DIR}/logs"
print(f"已確認/建立專案目錄及日誌目錄。\n")

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

### Cell 2: 啟動 Streamlit 應用程式並監控日誌

在 Cell 1 成功執行完畢後，複製以下指令到 Colab Notebook 的第二個程式碼儲存格中，然後執行它。
此儲存格會：
1.  啟動 Streamlit 應用程式。
2.  嘗試獲取並顯示一個可公開訪問的 Colab 代理 URL。
3.  **保持運行狀態**以維持 Streamlit 服務，並會**即時輸出應用程式日誌**。
4.  您可以透過**手動中斷此儲存格 (Interrupt execution)** 來停止 Streamlit 服務。

```python
#@title 2. 🚀 啟動 Ai_wolf 應用 (兩階段啟動 & 日誌監控)
# === Ai_wolf 專案啟動、連結獲取與日誌監控 (兩階段) ===
# Cell 2: 執行此儲存格。首次執行會顯示準備按鈕。
#         點擊該按鈕後 (會重新執行此儲存格)，將實際啟動應用並顯示日誌。
#         您可以隨時手動中斷此儲存格來停止服務。

import subprocess
import time
import os
import threading
from IPython.display import display, HTML, clear_output
from google.colab.output import eval_js
import urllib.parse # 用於創建帶參數的 URL

# --- 配置參數 ---
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI"
STREAMLIT_APP_PATH = f"{GDRIVE_PROJECT_DIR}/app.py"
LOG_DIR = f"{GDRIVE_PROJECT_DIR}/logs"
LOG_FILE_PATH = f"{LOG_DIR}/streamlit.log"

PORT = 8501
WAIT_SECONDS_FOR_SERVER = 15
MAX_RETRIES_FOR_URL = 3
RETRY_DELAY_SECONDS = 5

# --- 狀態管理 ---
# 透過 URL 參數來簡單模擬階段切換
# google.colab.kernel.notebookPath() 在某些 Colab 環境下可能不按預期工作或引發錯誤,
# 特別是如果 kernel 不是 'Python 3' (例如 'Python 3 with GPU')。
# 使用 try-except 塊來優雅地處理這種情況。
try:
    current_notebook_path = eval_js('google.colab.kernel.notebookPath()')
    query_params = urllib.parse.parse_qs(urllib.parse.urlparse(current_notebook_path).query)
    current_stage = query_params.get('stage', ['initial'])[0]
except Exception as e_notebook_path:
    print(f"注意：無法獲取 Colab Notebook 路徑參數來控制階段。錯誤: {e_notebook_path}")
    print("將預設為 'initial' 階段。如果已點擊過啟動按鈕但未生效，請嘗試手動在網址列尾部添加 '?stage=launch' 並回車。")
    current_stage = 'initial' # 預設到初始階段

if current_stage == 'initial':
    clear_output(wait=True)
    # 第一階段：顯示準備訊息和啟動按鈕
    # 嘗試獲取當前 Notebook 的 URL 以便創建帶參數的連結
    try:
        button_url = eval_js('google.colab.kernel.notebookPath()') + "?stage=launch"
        display_html = f"""
            <div style='border: 2px solid #1A73E8; padding: 20px; border-radius: 10px; text-align: center; background-color: #e9f0fa;'>
                <h2 style='color: #0D5ACB;'>準備啟動 Ai_wolf 分析平台</h2>
                <p style='font-size:1.1em;'>點擊下方按鈕以開始啟動 Streamlit 應用程式並監控其日誌。</p>
                <p style='margin: 25px 0;'>
                    <a href='{button_url}' target='_self'
                       style='padding:10px 20px; background-color:#1A73E8; color:white; text-decoration:none; border-radius:8px; font-size:1.1em; box-shadow: 0 2px 4px 0 rgba(0,0,0,0.2);'>
                       🚀 啟動應用程式
                    </a>
                </p>
                <p style='font-size:0.9em; color:gray;'>點擊後，此儲存格將重新執行並開始啟動程序。</p>
            </div>
        """
    except Exception as e_button_url:
        # 如果無法生成按鈕URL，顯示備用訊息
        display_html = f"""
            <div style='border: 2px solid #F44336; padding: 20px; border-radius: 10px; text-align: center; background-color: #fff0f0;'>
                <h2 style='color: #C62828;'>啟動準備階段出錯</h2>
                <p style='font-size:1.1em; color:#D32F2F;'>無法自動生成啟動按鈕的連結。</p>
                <p>您可以嘗試手動在此 Colab Notebook 的網址尾部添加 <code>?stage=launch</code> 然後按 Enter 鍵刷新頁面以進入下一階段。</p>
                <p>錯誤詳情: {e_button_url}</p>
            </div>
        """
    display(HTML(display_html))
    print("第一階段：已顯示準備訊息。如果看到按鈕，請點擊以繼續；否則請依照提示操作。")

elif current_stage == 'launch':
    clear_output(wait=True)
    print("🚀 第二階段：正在準備啟動 Streamlit 應用程式...")
    print(f"   應用程式路徑: {STREAMLIT_APP_PATH}")
    print(f"   日誌檔案路徑: {LOG_FILE_PATH}")
    print(f"   預計監聽端口: {PORT}")
    print("-" * 70)

    if not os.path.exists(STREAMLIT_APP_PATH):
        display(HTML(f"<p style='color:red; font-weight:bold;'>❌ 錯誤：找不到 Streamlit 應用程式檔案！</p><p>路徑: {STREAMLIT_APP_PATH}</p>"))
        raise SystemExit("應用程式檔案 app.py 未找到。")

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE_PATH, 'a') as f:
        f.write(f"--- Colab 腳本日誌監控開始於 {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    print(f"日誌檔案 {LOG_FILE_PATH} 已確認/創建。")
    print("-" * 70)

    streamlit_process = None
    monitor_thread = None

    try:
        print(f"⏳ 正在嘗試於背景啟動 Streamlit (約需 {WAIT_SECONDS_FOR_SERVER} 秒)...")
        cmd = ["streamlit", "run", STREAMLIT_APP_PATH, "--server.port", str(PORT), "--server.headless", "true", "--browser.gatherUsageStats", "false"]
        streamlit_process = subprocess.Popen(cmd)
        print(f"   Streamlit 啟動指令已送出 (PID: {streamlit_process.pid if streamlit_process else '未知'})。")
        time.sleep(WAIT_SECONDS_FOR_SERVER)

        if streamlit_process.poll() is not None:
            display(HTML(f"<p style='color:red; font-weight:bold;'>❌ Streamlit 未能成功啟動或已意外終止 (返回碼: {streamlit_process.returncode})。</p>"))
            raise SystemExit(f"Streamlit 進程未能持續運行。")
        print("✅ Streamlit 應已在背景運行。")
        print("-" * 70)

    except Exception as e:
        display(HTML(f"<p style='color:red; font-weight:bold;'>❌ 啟動 Streamlit 時發生錯誤:</p><p style='font-family:monospace;'>{str(e)}</p>"))
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
        raise SystemExit(f"啟動 Streamlit 失敗: {str(e)}")

    print("🔗 現在嘗試獲取 Colab 代理訪問網址...")
    proxy_url = None
    for attempt in range(MAX_RETRIES_FOR_URL):
        print(f"   嘗試第 {attempt + 1}/{MAX_RETRIES_FOR_URL} 次...")
        try:
            proxy_url = eval_js(f'google.colab.kernel.proxyPort({PORT})')
            if proxy_url:
                print(f"   🎉 成功獲取到代理 URL！")
                break
        except Exception as e_evaljs:
            print(f"      獲取 URL 第 {attempt + 1} 次失敗 (可能服務尚未完全就緒): {str(e_evaljs)[:100]}...")
        if attempt < MAX_RETRIES_FOR_URL - 1:
            time.sleep(RETRY_DELAY_SECONDS)
    print("-" * 70)

    if proxy_url:
        clear_output(wait=True)
        display(HTML(f"""
            <div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px; text-align: center; background-color: #e8f5e9;'>
                <h2 style='color: #2E7D32; margin-bottom:15px;'>🎉 應用程式已成功啟動！</h2>
                <p style='font-size:1.1em;'>您的 Ai_wolf 分析平台可以透過下面的連結訪問：</p>
                <p style='margin: 25px 0;'>
                    <a href='{proxy_url}' target='_blank'
                       style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:8px; font-size:1.2em; font-weight: 600; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); display:inline-block;'>
                       🚀 點此開啟 Ai_wolf 應用程式
                    </a>
                </p>
                <p style='font-size:0.9em; color:gray;'>連結地址: <a href='{proxy_url}' target='_blank'>{proxy_url}</a></p>
                <p style='font-size:0.9em; color:gray; margin-top:15px;'>如果點擊後應用程式未載入，請確保此 Colab Notebook 儲存格仍在運行。</p>
                <p style='font-size:0.9em; color:orange; margin-top:10px;'>
                   <b>注意：此儲存格將持續運行以顯示應用程式日誌。要停止服務，請手動中斷此儲存格的執行。</b>
                </p>
            </div>
        """))

        print("\n--- 應用程式日誌 (每 10 秒刷新一次) ---")
    print(f"日誌來源檔案: {LOG_FILE_PATH}")
    print("如果應用程式出現問題，此處可能會顯示相關錯誤訊息。")
    print("您可以隨時手動中斷此儲存格 (點擊 Colab 中此儲存格左側的停止按鈕或使用 Ctrl+M I) 來停止服務。")
    print("-" * 70, flush=True)

    def monitor_streamlit_process():
        streamlit_process.wait()
        if streamlit_process.returncode is not None:
            print(f"\n🔴 Streamlit 服務已停止 (返回碼: {streamlit_process.returncode})。請檢查日誌。日誌監控將終止。", flush=True)

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
                print(f"警告：日誌檔案 {LOG_FILE_PATH} 未找到。等待應用程式創建它...", flush=True)
            except Exception as e:
                print(f"讀取日誌時發生錯誤: {e}", flush=True)

            if streamlit_process.poll() is not None:
                if monitor_thread.is_alive():
                    print("\nStreamlit 進程已終止，但監控線程仍在運行。準備停止日誌監控。", flush=True)
                break

            time.sleep(10)
        print("\n--- 日誌監控循環結束 (Streamlit 服務可能已停止) ---", flush=True)

    except KeyboardInterrupt:
        print("\n⌨️ 偵測到手動中斷 (KeyboardInterrupt)。正在停止服務...", flush=True)
    except Exception as e_loop:
        print(f"\n💥 日誌監控循環中發生未預期錯誤: {e_loop}", flush=True)
    finally:
        print("\n--- 正在嘗試終止 Streamlit 服務 ---", flush=True)
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=10)
                print("✅ Streamlit 服務已成功終止。", flush=True)
            except subprocess.TimeoutExpired:
                print("⚠️ Streamlit 服務終止超時，嘗試強制終止...", flush=True)
                streamlit_process.kill()
                streamlit_process.wait()
                print("強制終止 Streamlit 服務。", flush=True)
        else:
            print("ℹ️ Streamlit 服務已經停止或未成功啟動。", flush=True)

        if monitor_thread and monitor_thread.is_alive():
            print("等待日誌監控線程結束...", flush=True)
            monitor_thread.join(timeout=5)
            if monitor_thread.is_alive():
                 print("監控線程未能及時結束。", flush=True)
        print("--- Cell 2 執行完畢 ---", flush=True)

else:
    clear_output(wait=True)
    display(HTML(f"<div style='border: 2px solid #F44336; padding: 20px; border-radius: 10px; text-align: center; background-color: #fff0f0;'>" \
                 f"<h2 style='color: #C62828; margin-bottom:15px;'>❌ 未能自動獲取到 Colab 代理網址</h2>" \
                 f"<p style='font-size:1.1em; color:#D32F2F;'>我們未能為您的應用程式自動生成一個可點擊的 Colab 代理連結。</p>" \
                 f"<p style='color:orange; margin-top:15px;'>**可能的原因與建議：**</p>" \
                 f"<ul style='text-align:left; display:inline-block; margin-top:10px;'>" \
                 f"<li>Streamlit 應用程式可能未能成功在背景啟動 (檢查是否有錯誤訊息)。</li>" \
                 f"<li>Colab 的代理服務可能暫時無法使用或響應較慢。</li>" \
                 f"<li>您可以嘗試**重新執行一次此儲存格**。</li>" \
                 f"<li>如果問題持續，請**檢查此儲存格執行時是否有任何錯誤日誌輸出**。Streamlit 本身可能會打印一個 'External URL'，您可以嘗試手動複製該 URL 到瀏覽器中訪問。</li>" \
                 f"</ul>" \
                 f"<p style='font-size:0.9em; color:gray; margin-top:20px;'>請注意：應用程式需要在 Colab 中保持運行才能被訪問。</p>" \
                 f"</div>"))
    print("\n❌ 未能啟動應用程式或獲取連結，儲存格將不會保持活動狀態。請檢查之前的錯誤訊息。")

```
**執行說明：**
*   執行後，Colab 會嘗試提供一個 `https://[一串隨機字符].googleusercontent.com/proxy/8501/` 格式的網址。點擊此網址即可在瀏覽器新分頁中打開應用。
*   **此儲存格會持續運行**以保持 Streamlit 服務，並會顯示來自 `{GDRIVE_PROJECT_DIR}/logs/streamlit.log` 的日誌。
*   要停止服務，請**手動中斷此儲存格的執行** (例如，點擊儲存格左側的停止按鈕，或使用快捷鍵 `Ctrl+M I`)。

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
#@title 2. 🚀 Launch Ai_wolf App, Get Link & Monitor Logs (Click to execute)
# === Ai_wolf Project Launch, Link Retrieval & Log Monitoring ===
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
                 f"<p style='font-size:1.1em;'>Your Ai_wolf analysis platform should be accessible via the link below:</p>" \
                 f"<p style='margin: 25px 0;'><a href='{proxy_url}' target='_blank' style='padding:12px 25px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:5px; font-size:1.2em; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);'>🚀 Click here to open Ai_wolf Application</a></p>" \
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
