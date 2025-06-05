## 專案開發彙整報告：善甲狼週報 - 人機協同聊天式分析平台

**專案版本：** 2.1 (強化部署與訪問方式)
**日期：** 2025年6月5日

**核心目標：** 打造一個在Colab環境中運行的、具有聊天式圖形化介面的人機協同智慧分析平台，用於系統性地處理「善甲狼a機智生活」約150週的歷史貼文，回顧歷史交易機會，並最終由使用者將精煉內容手動整理至Google文件。

### 1\. 核心功能與使用者體驗 ✨

1.  **聊天式圖形化介面 (GUI) in Colab：**

      * **運行方式：** 透過在Colab中啟動一個輕量級Python網頁框架應用（推薦Streamlit），並利用Colab內建的端口轉發功能或外部隧道服務生成可訪問的網址。使用者點擊此網址即可在瀏覽器新分頁中打開操作介面。
      * **介面風格：** 採用類似現代聊天應用的介面，使用 `st.chat_message` 展示AI（助手角色）和使用者（使用者角色）的對話內容，`st.chat_input` 供使用者輸入指令、問題或修改意見。
      * **美觀輸出：** 利用Markdown進行內容格式化，確保輸出清晰、易讀、層次分明。

2.  **逐週分析與導航：**

      * 提供清晰的週次選擇機制（如 `st.selectbox` 或按鈕列表）。
      * 包含「上一週」、「下一週」的導航按鈕，方便使用者按順序或跳轉處理不同週次的內容。

3.  **AI輔助的初步分析 (聊天機器人第一輪發言)：**

      * 選定週次後，系統自動讀取該週「善甲狼」貼文。
      * AI助手（Gemini API）主動發起對話，呈現初步分析結果，涵蓋：
          * A. 週次與日期範圍。
          * B. 「善甲狼」核心觀點摘要。
          * C. 當週市場重點回顧（全球與台灣主要經濟/金融事件、主要市場動態）。
          * D. 當週其他市場觀點/大師風向探索（可整合先前提供的其他專家摘要內容）。
          * E. 「看到-\>想到-\>做到」框架下的潛在交易機會回顧初稿。

4.  **聊天式人機互動與內容精煉：**

      * 使用者可以針對AI初步分析的任何部分，在 `st.chat_input` 中輸入問題、補充資訊、修改意見或要求AI從不同角度重新分析。
      * 使用者的輸入作為「使用者」訊息展示。
      * AI接收指令後，進行再處理，並將精煉後的內容作為新的「AI助手」訊息展示。
      * 此聊天互動和精煉過程可以針對每個細節反覆進行，直到使用者滿意為止。使用者可明確「確認本節內容」。

5.  **整合Google搜尋的智慧查詢 (聊天中觸發)：**

      * 在聊天過程中，如果需要即時資訊或對特定主題進行深入查詢，使用者可以明確指示AI（例如：「請AI幫我用Google搜尋查一下[查詢內容]及其對市場的影響」）。
      * 後端調用配置了「Google搜尋工具」的Gemini API，整合搜尋結果後在聊天中回覆，並需符合Google搜尋建議的顯示規定。

6.  **多組API Key的智慧管理 (後端)：**

      * 後端系統自動管理和輪換使用多組Gemini API Key [cite: 117]。
      * 監控每個Key的RPM/TPM使用情況，避免單一Key過載，並在觸發速率限制時自動切換和重試 [cite: 117]。
      * 確保並行處理時的線程安全。

7.  **快取技術應用 (後端與前端狀態)：**

      * **API請求快取：** 使用 `requests-cache` 快取對Gemini API的請求 [cite: 3, 117]。
      * **週次分析進度快取：** 每週的聊天對話記錄（包含AI的各版本分析和使用者的所有互動指令）以及各部分最終確認的文本內容，以結構化檔案（如JSON）形式，按週次命名，儲存於Google Drive。
      * 當使用者選擇一個已處理過的週次時，系統應優先從Google Drive載入並恢復先前的聊天記錄和已確認的內容，在此基礎上繼續。

8.  **最終報告內容的生成與匯出：**

      * 當使用者透過聊天互動，對某週所有分析內容（A-E各節）都感到滿意並確認後，介面提供一個「生成本週報告預覽(供複製)」的功能。
      * 系統將各部分最終確認的文本內容，按照預設順序彙整成一個排版整潔的文本塊（推薦Markdown格式，因其易於轉換和閱讀）。
      * 使用者可以方便地一鍵複製此文本塊，然後手動貼到Google文件中進行最終的個人化排版和永久儲存。

### 2\. 解決方案架構與技術選型 🛠️

  * **運行環境：** Google Colaboratory (Colab)
      * 提供Python執行環境和內建端口轉發功能。
  * **後端邏輯：** Python
      * 檔案I/O (Google Drive整合)。
      * Gemini API 互動 (內容生成、摘要、分析、Google搜尋)。
      * 多API Key智慧管理 [cite: 117]。
      * `requests-cache` 快取 [cite: 3, 117]。
      * 處理前端Streamlit的請求。
  * **前端使用者介面 (GUI)：** Streamlit
      * 透過 `st.chat_message`、`st.chat_input`、`st.selectbox`、`st.button` 等元件搭建聊天式互動介面。
      * 詳細的網址暴露方式見下方「5. 應用程式部署與訪問方式」。
  * **資料儲存 (持久化)：** Google Drive
      * 存放「善甲狼」原始貼文檔案。
      * 存放 `requests-cache` 的快取資料庫 [cite: 3, 4]。
      * 存放每週分析的聊天記錄及最終確認內容的JSON快取檔案。

### 3\. 核心人機協同聊天流程 💬

1.  **啟動與週次選擇：** 使用者在Colab中啟動Streamlit應用，透過指定方式獲取並打開訪問網址。在介面選擇目標「週次」。
2.  **恢復進度/啟動新分析：** 系統檢查Google Drive是否有該週次的快取檔案。
      * **有快取：** 載入並恢復聊天記錄和已確認的各節內容，使用者可以在此基礎上繼續。
      * **無快取：** AI助手發起開場白，提供對「善甲狼」原始貼文的初步分析（A-E節初稿）。
3.  **聊天式互動精煉：** 使用者針對AI的發言，在聊天輸入框中提出問題、修改意見、要求補充、或指示AI使用Google搜尋。
4.  AI根據使用者指令進行再處理，並以新的聊天訊息回覆。
5.  過程反覆，直到該部分內容使用者滿意。使用者可明確「確認本節內容」。
6.  **智慧搜尋整合：** 使用者可在聊天中隨時要求AI進行Google搜尋以獲取額外資訊。
7.  **保存進度：** 互動過程中，系統會定期或在使用者操作後，自動將當前聊天狀態和已確認內容更新到Google Drive的快取檔案。
8.  **完成與複製：** 所有部分確認完畢後，使用者點擊「生成報告預覽」，系統將最終內容整理好供複製。
9.  **切換週次：** 使用者可隨時切換到其他週次，重複流程。

### 4\. 開發與實施建議 🚀

1.  **模組化開發：** 將後端邏輯（Gemini互動、檔案處理、快取管理、API Key管理）與前端Streamlit介面邏輯分離，便於維護和測試。
2.  **提示工程 (Prompt Engineering)：** 持續優化與Gemini API互動的提示詞，以獲得更高品質、更相關的分析內容，並能有效整合使用者的聊天反饋。
3.  **Streamlit介面迭代：** 從核心的聊天和內容展示功能開始，逐步完善導航、狀態顯示、複製功能等。
4.  **快取策略細化：** 詳細設計Google Drive上JSON快取檔案的結構，確保能完整記錄聊天進程和各部分的最終文本。
5.  **錯誤處理與日誌：** 建立全面的錯誤捕獲機制和日誌記錄，方便追蹤問題 [cite: 73, 101]。
6.  **分階段實現：**
      * **階段一 (核心聊天與AI分析)：** 實現單週的「善甲狼」貼文載入、AI初步分析（B-E節初稿）在聊天介面中的呈現、以及基於使用者輸入的單輪AI再回應。實現方法一的網址訪問。
      * **階段二 (互動深化與快取)：** 完善多輪聊天互動邏輯、實現Google Drive的週次分析結果快取（讀取與儲存）、加入「上一週/下一週」導航。
      * **階段三 (進階功能與部署選項)：** 整合「智慧Google搜尋」功能、實現多組API Key的智慧管理 [cite: 117]。研究並實作方法二、三的網址訪問方式。
      * **階段四 (優化與測試)：** 全面測試150週的處理流程，優化介面美觀性、回應速度和使用者體驗。

### 5\. 應用程式部署與訪問方式 (在 Colab 環境) 🌐

本節詳細說明如何在 Colab 環境中啟動 Streamlit 應用程式，並透過不同方式獲取訪問網址。

#### 5.1. 方法一：Colab 內建代理網址 (最直接，無需額外註冊)

  * **運作方式：**
    當您在 Colab 中使用 `streamlit run your_app.py` 啟動 Streamlit 應用程式時，Colab 通常會自動偵測到這個網頁服務，並提供一個 `https://*.googleusercontent.com/proxy/...` 格式的代理網址。
  * **實作步驟 (在 Colab Notebook 中)：**
    1.  安裝 Streamlit:
        ```python
        !pip install streamlit -q
        ```
    2.  建立您的 Streamlit 應用程式腳本 (例如 `app.py`)：
        ```python
        %%writefile app.py
        import streamlit as st
        st.title("善甲狼週報分析平台")
        # ... 您的應用程式主要邏輯 ...
        # 例如：
        # if 'messages' not in st.session_state:
        #     st.session_state.messages = []
        # for message in st.session_state.messages:
        #     with st.chat_message(message["role"]):
        #         st.markdown(message["content"])
        # if prompt := st.chat_input("請輸入您的指令..."):
        #     st.session_state.messages.append({"role": "user", "content": prompt})
        #     with st.chat_message("user"):
        #         st.markdown(prompt)
        #     # AI 回應邏輯
        #     with st.chat_message("assistant"):
        #         response = f"AI收到：{prompt}" # 替換為真實AI回應
        #         st.markdown(response)
        #     st.session_state.messages.append({"role": "assistant", "content": response})
        ```
    3.  運行 Streamlit 應用程式 (建議指定一個明確的端口)：
        ```python
        !streamlit run app.py --server.port 8501
        ```
    4.  Colab 的輸出儲存格會顯示相關網址，其中應包含一個可點擊的 `*.googleusercontent.com` 連結。點擊此連結即可在新分頁打開應用。
  * **優點：**
      * 無需額外註冊或安裝外部工具。
      * 與 Colab 環境緊密整合。
  * **缺點：**
      * 網址通常在每次 Colab 執行環境重啟後改變。
      * Colab Notebook 必須保持運行狀態。

#### 5.2. 方法二：透過 ngrok 建立臨時公開網址

  * **運作方式：**
    ngrok 創建一個從您的 Colab 實例到 ngrok 公共服務器的安全隧道，並為您提供一個 `*.ngrok.io` 或 `*.ngrok-free.app` 的公開網址。
  * **實作步驟 (在 Colab Notebook 中)：**
    1.  安裝 `pyngrok`：
        ```python
        !pip install pyngrok -q
        ```
    2.  獲取並設定 ngrok Authtoken：
          * 前往 [ngrok.com](https://ngrok.com) 註冊免費帳戶並獲取 Authtoken。
          * 在 Colab secrets 中安全地儲存您的 Authtoken，或直接在程式碼中設定（注意安全風險）：
            ```python
            from pyngrok import ngrok, conf
            import os

            # 優先從 Colab secrets 讀取 (推薦)
            # from google.colab import userdata
            # NGROK_AUTH_TOKEN = userdata.get('NGROK_AUTH_TOKEN')
            # if NGROK_AUTH_TOKEN:
            #    conf.get_default().auth_token = NGROK_AUTH_TOKEN
            # else:
            #    print("請設定 NGROK_AUTH_TOKEN Colab secret")
            #    # 或者直接在這裡設定，但不推薦用於分享的筆記本
            #    # conf.get_default().auth_token = "YOUR_NGROK_AUTHTOKEN_HERE"

            # 假設您已將 token 存在環境變數或手動輸入
            ngrok_token = "YOUR_NGROK_AUTHTOKEN_HERE" # 替換為您的真實 token
            if not ngrok_token or ngrok_token == "YOUR_NGROK_AUTHTOKEN_HERE":
                 print("警告：請替換為您的真實 ngrok Authtoken！")
            else:
                conf.get_default().auth_token = ngrok_token
            ```
    3.  確保您的 Streamlit 應用程式 (`app.py`) 已準備就緒。
    4.  啟動 Streamlit 應用並建立 ngrok 隧道：
        ```python
        import subprocess
        import time
        from pyngrok import ngrok

        # 在背景啟動 Streamlit 應用
        process = subprocess.Popen(['streamlit', 'run', 'app.py', '--server.port', '8501'])
        print("Streamlit 應用程式啟動中...")
        time.sleep(5) # 等待 Streamlit 啟動

        # 關閉可能已存在的 ngrok 隧道
        try:
            ngrok.kill()
        except Exception as e:
            print(f"關閉舊 ngrok 隧道時出錯 (可能本來就沒有): {e}")

        # 建立到 8501 端口的隧道
        try:
            public_url = ngrok.connect(8501)
            print(f"ngrok 公開網址: {public_url}")
        except Exception as e:
            print(f"建立 ngrok 隧道失敗: {e}")
            print("請確認您的 ngrok Authtoken 是否已正確設定。")
        ```
  * **優點：**
      * 提供可在任何地方訪問的真實公開網址。
      * 預設 HTTPS。
  * **缺點：**
      * 免費版 ngrok 的網址是隨機的，且在重啟 ngrok 進程後會改變。
      * 免費版有使用限制（如頻寬、連接時間等）。
      * 強烈建議註冊免費帳戶並使用 Authtoken。
      * Colab Notebook 仍需保持運行。

#### 5.3. 方法三：透過 `localtunnel` 或類似服務建立臨時公開網址

  * **運作方式：**
    `localtunnel` 與 ngrok 類似，但通常不需要註冊即可快速生成臨時公開網址 (例如 `*.loca.lt`)。
  * **實作步驟 (在 Colab Notebook 中)：**
    1.  安裝 `localtunnel` (通常透過 Node.js 的 npm)：
        ```python
        !npm install -g localtunnel
        ```
    2.  確保您的 Streamlit 應用程式 (`app.py`) 已準備就緒。
    3.  在背景啟動 Streamlit 應用程式：
        ```python
        import subprocess
        import time

        streamlit_process = subprocess.Popen(['streamlit', 'run', 'app.py', '--server.port', '8501'])
        print("Streamlit 應用程式啟動中...")
        time.sleep(5) # 等待 Streamlit 啟動
        ```
    4.  啟動 `localtunnel`（注意：在 Colab 中自動捕獲其輸出的 URL 可能較為複雜，通常需要手動查看輸出）：
        ```python
        # 運行 localtunnel，它會在終端輸出 URL
        # 您需要手動從下方的輸出中複製 URL
        # !lt --port 8501

        # 或者嘗試用 Python 捕獲，但 localtunnel 的交互性可能使這不穩定
        import shlex
        print("嘗試啟動 localtunnel，請留意其輸出以獲取URL。")
        lt_command = f"npx localtunnel --port 8501"
        # localtunnel 會持續運行，因此 Popen 更合適，但捕獲 URL 仍是個挑戰
        # 最簡單的方式是直接在一個新的 Colab code cell 運行 `!lt --port 8501 --print-requests`
        # 然後從輸出中手動複製 `your url is: https://xxxx.loca.lt`

        # 這裡提供一個非阻塞的嘗試，但您可能需要手動檢查：
        lt_process = subprocess.Popen(shlex.split(lt_command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print("localtunnel 正在背景啟動。請檢查其日誌或手動執行 `!npx localtunnel --port 8501` 來獲取 URL。")
        # 由於無法穩定捕獲 URL，提示使用者手動操作
        print(f"如果 localtunnel 啟動成功，請手動在新儲存格執行 `!npx localtunnel --port 8501` 並複製URL。")
        ```
        **建議：** 在 Colab 中，更可靠的方式可能是在一個新的程式碼儲存格中直接運行 `!lt --port 8501`，然後從命令輸出中手動複製 `your url is: https://...` 的網址。`localtunnel` 有時會要求您訪問一個驗證網址來啟動隧道。
  * **優點：**
      * 通常無需註冊帳戶。
      * 命令相對簡單。
  * **缺點：**
      * 網址是隨機的且臨時。
      * 穩定性和使用限制可能比 ngrok 免費版更嚴格。
      * 在 Colab 中自動化獲取 URL 可能比較困難，常需手動介入。
      * Colab Notebook 仍需保持運行。

#### 5.4. 部署與訪問方式總結與選擇考量

  * **方法一 (Colab 內建代理)：** 最適合快速、私密的開發和測試。無需額外設定，但網址會變動。
  * **方法二 (ngrok)：** 當需要一個較為穩定的臨時公開網址（例如，短期分享給他人測試）時是個好選擇。建議使用免費帳戶的 Authtoken。
  * **方法三 (`localtunnel`)：** 作為備選，特別是在不想進行任何註冊時。但在 Colab 環境下的自動化程度和穩定性可能稍遜。

**重要共通點：** 上述所有方法都依賴於 Colab Notebook 的活躍運行狀態。若 Colab 會話中斷或執行環境重設，應用程式將無法訪問，且臨時網址（尤其是方法一、三和 ngrok 免費版）可能會失效或改變。若需永久託管，則應考慮將應用部署到專用雲平台。

### 6\. 結論與建議

構建「善甲狼週報 - 人機協同聊天式分析平台」是一個結合了自然語言處理、Web應用開發與金融市場理解的有趣專案。透過上述詳細的規劃，您應能逐步完成。

核心建議：

  * **從簡開始，逐步迭代：** 先完成核心的聊天分析與內容生成（階段一），再逐步加入快取、進階功能和不同的部署選項。
  * **重視提示工程：** 與 Gemini API 的互動效果高度依賴於提示詞的設計。
  * **使用者體驗優先：** 確保聊天介面流暢、直觀，輸出內容清晰易懂。
  * **持續測試：** 特別是處理150週的歷史資料時，邊緣案例和效能瓶頸可能會出現。

這份更新後的報告整合了應用程式的部署與訪問細節，希望能為您的開發工作提供更全面的指導。祝您專案開發順利！
