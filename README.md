# (中文內容)

# 善甲狼週報 - 人機協同聊天式分析平台

## 專案目標

本專案旨在打造一個在 Google Colaboratory (Colab) 環境中運行的、具有聊天式圖形化介面的人機協同智慧分析平台。平台將用於系統性地處理「善甲狼a機智生活」約150週的歷史貼文，輔助使用者回顧歷史交易機會，並最終由使用者將精煉內容手動整理至Google文件。

## 如何在 Colab 中運行

以下步驟將指導您如何在 Google Colab 環境中設置並運行此 Streamlit 應用程式。

### 步驟 1：準備 Colab Notebook

1.  打開 [Google Colab](https://colab.research.google.com/)。
2.  創建一個新的 Python 3 Notebook。

### 步驟 2：安裝必要的 Python 套件

在 Notebook 的一個程式碼儲存格中，執行以下指令來安裝 Streamlit 和 Google Generative AI SDK：
```python
!pip install streamlit google-generativeai -q
```
執行此儲存格後，等待安裝完成。

### 步驟 3：將應用程式腳本寫入 Colab 環境

我們需要將 `app.py`（Streamlit 應用程式的主要程式碼）的內容加載到 Colab 的虛擬機中。在新的程式碼儲存格中，複製並貼上下列程式碼。

**重要提示：**
*   下方的 `app.py` 內容是截至目前的版本。如果專案後續更新了 `app.py`，您需要從 GitHub 倉庫獲取最新版本的 `app.py` 內容，並替換掉 `%%writefile app.py` 之後的程式碼。
*   **關於 Gemini API Key 的安全：** 此版本的 `app.py` 允許您直接在側邊欄輸入 API Key，這主要是為了方便快速測試。**強烈建議您不要將 API Key 直接硬編碼到任何腳本中或以明文方式長期保存在筆記本中。** 更安全的方式是使用 Colab 的 Secrets Manager (密鑰管理員)。請參考下方“步驟 6：設定 Gemini API Key”中的建議。

```python
%%writefile app.py
import streamlit as st
from google.colab import drive
import os
import google.generativeai as genai # 新增 Gemini API 套件

# --- Google Drive 相關函數 ---
def mount_google_drive():
    """掛載 Google Drive 到 Colab 環境。"""
    try:
        drive.mount('/content/drive', force_remount=True) # 添加 force_remount
        return True, "/content/drive/MyDrive/"
    except Exception as e:
        return False, str(e)

def read_file_from_drive(file_path):
    """從已掛載的 Google Drive 讀取文件內容。"""
    if not os.path.exists(file_path):
        return False, "文件路徑不存在。"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return True, content
    except Exception as e:
        return False, f"讀取文件失敗：{str(e)}"

# --- Gemini API 相關函數 ---
def get_gemini_summary(api_key, document_content, week_info):
    """使用 Gemini API 生成初步分析摘要。"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro') # 或者選擇其他合適的模型

        prompt = f"""
        作為一個專業的金融市場分析助手，請基於以下提供的「善甲狼週報」內容，生成一份初步分析報告。
        請專注於以下兩點：
        1.  確認並列出週次與日期範圍（基於提供的週資訊：{week_info}）。
        2.  提取「善甲狼」當週的核心觀點摘要。

        提供的週報內容如下：
        ---
        {document_content}
        ---

        請用中文回答。
        """

        response = model.generate_content(prompt)
        return True, response.text
    except Exception as e:
        return False, f"調用 Gemini API 失敗：{str(e)}"

# --- Streamlit 應用程式界面 ---

# 主應用程式標題
st.title("善甲狼週報 - 人機協同聊天式分析平台")

# --- Session State 初始化 ---
default_values = {
    'drive_mounted': False,
    'drive_mount_path': "/content/drive/MyDrive/" if 'google.colab' in str(globals().get('get_ipython', '')) else "./",
    'file_content': "",
    'file_read_status': "",
    'current_week_file': None,
    'gemini_api_key': "",
    'messages': []
}
for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 側邊欄 ---
st.sidebar.header("操作選單")

# API Key 輸入
st.sidebar.subheader("API 設定")
st.session_state.gemini_api_key = st.sidebar.text_input("請輸入您的 Gemini API Key：", type="password", value=st.session_state.gemini_api_key)
if not st.session_state.gemini_api_key:
    st.sidebar.warning("請提供 Gemini API Key 以啟用 AI 分析功能。")

# Google Drive 文件讀取區
st.sidebar.subheader("讀取 Google Drive 文件")
colab_env = 'google.colab' in str(globals().get('get_ipython', ''))

if colab_env:
    if st.sidebar.button("掛載 Google Drive"):
        success, path_or_msg = mount_google_drive()
        st.session_state.drive_mounted = success
        if success:
            st.session_state.drive_mount_path = path_or_msg
            st.sidebar.success(f"Google Drive 已掛載到: {path_or_msg}")
        else:
            st.sidebar.error(f"Google Drive 掛載失敗: {path_or_msg}")
else:
    st.sidebar.info("非 Colab 環境，請確保文件路徑可直接訪問。")

drive_file_path_input = st.sidebar.text_input("請輸入 Drive 中的文件路徑 (例如：folder/myfile.txt)", "demo_week_report.txt")

if st.sidebar.button("讀取並設為當前分析文件"):
    if colab_env and not st.session_state.drive_mounted:
        st.sidebar.warning("請先掛載 Google Drive。")
    else:
        full_path = os.path.join(st.session_state.drive_mount_path, drive_file_path_input) if colab_env else drive_file_path_input
        st.sidebar.info(f"嘗試讀取路徑: {full_path}")
        success, content_or_error = read_file_from_drive(full_path)
        if success:
            st.session_state.file_content = content_or_error
            st.session_state.current_week_file = drive_file_path_input
            st.session_state.file_read_status = f"文件 '{drive_file_path_input}' 已成功讀取並設為當前分析目標。"
            st.sidebar.success("文件讀取成功！")
            st.session_state.messages = []
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("您好！我已經讀取了新的文件，請問需要我做什麼分析嗎？ （您可以點擊下方的 'AI 初步分析' 按鈕）")
            st.session_state.messages.append({"role": "assistant", "content": "您好！我已經讀取了新的文件，請問需要我做什麼分析嗎？ （您可以點擊下方的 'AI 初步分析' 按鈕）"})
        else:
            st.session_state.file_content = ""
            st.session_state.current_week_file = None
            st.session_state.file_read_status = f"讀取文件 '{drive_file_path_input}' 失敗: {content_or_error}"
            st.sidebar.error("文件讀取失敗。")

# --- 主聊天界面 ---
st.subheader("聊天分析區")

# 顯示聊天記錄
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

# AI 初步分析按鈕
if st.session_state.current_week_file and st.session_state.file_content:
    if st.button("AI 初步分析 (A, B 部分)"):
        if not st.session_state.gemini_api_key:
            st.error("請先在側邊欄輸入您的 Gemini API Key。")
            st.session_state.messages.append({"role": "assistant", "content": "錯誤：請先在側邊欄輸入您的 Gemini API Key。"})
        else:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("AI 正在分析中，請稍候..."):
                    week_info_display = f"從文件名 '{st.session_state.current_week_file}' 推斷的週資訊"

                    api_success, summary_or_error = get_gemini_summary(
                        st.session_state.gemini_api_key,
                        st.session_state.file_content,
                        week_info_display
                    )
                    if api_success:
                        response_text = summary_or_error
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"AI 分析失敗：{summary_or_error}")
                        st.session_state.messages.append({"role": "assistant", "content": f"AI 分析失敗：{summary_or_error}"})

# 聊天輸入框
if prompt := st.chat_input("請輸入您的指令或問題..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。")
    st.session_state.messages.append({"role": "assistant", "content": f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。"})

# --- 文件內容預覽 (移至 Expander) ---
if st.session_state.file_content:
    with st.expander("點此查看已讀取的文件內容", expanded=False):
        st.info(st.session_state.file_read_status)
        st.text_area("文件內容：", st.session_state.file_content, height=300, key="file_content_preview")
elif st.session_state.file_read_status:
    st.info(st.session_state.file_read_status)
else:
    st.markdown("*目前沒有文件內容可顯示。請從側邊欄讀取文件。*")

st.sidebar.markdown("---")
st.sidebar.subheader("測試輸入框")
user_input_sidebar = st.sidebar.text_input("請在此輸入文字：", "你好！Side Bar!", key="sidebar_test_input")
st.sidebar.write(f"您在側邊欄輸入的是： {user_input_sidebar}")
```
執行此儲存格。

### 步驟 4：運行 Streamlit 應用程式

在一個新的程式碼儲存格中，執行以下指令來啟動 Streamlit 應用程式：
```python
!streamlit run app.py --server.port 8501
```

### 步驟 5：訪問應用程式與操作指南

1.  **訪問應用程式介面：**
    點擊 Colab 輸出中提供的 `https://*.googleusercontent.com/proxy/8501/` 格式的網址。

2.  **設定 Gemini API Key (重要)：**
    *   在應用程式側邊欄的 "API 設定" 區域，將您的 Gemini API Key 粘貼到 "請輸入您的 Gemini API Key：" 輸入框中。**此操作在每次應用程式啟動或頁面刷新後可能都需要進行，除非您修改 `app.py` 以更持久地存儲金鑰（見下方安全建議）。**
    *   如果沒有提供 API Key，AI 分析功能將無法使用。

3.  **掛載 Google Drive (僅限 Colab 環境)：**
    *   在側邊欄 "讀取 Google Drive 文件" 區域，點擊 "掛載 Google Drive" 按鈕。
    *   按照提示完成 Google Drive 授權。

4.  **讀取分析文件：**
    *   在側邊欄輸入框中提供您想分析的、存於 Google Drive 中的文件名（相對於 "我的雲端硬碟" 的路徑）。
    *   點擊 "讀取並設為當前分析文件" 按鈕。成功讀取後，AI 會在聊天區發出問候。

5.  **進行 AI 初步分析：**
    *   文件成功讀取後，主聊天區下方會出現 "AI 初步分析 (A, B 部分)" 按鈕。
    *   點擊此按鈕，AI 將會根據文件內容，提供關於「週次與日期範圍」和「核心觀點摘要」的分析。結果會顯示在聊天區。

6.  **聊天互動：**
    *   您可以在聊天區底部的 "請輸入您的指令或問題..." 輸入框中與 AI 進行對話。
    *   目前，AI 對於使用者輸入的回應還很基礎，主要功能是接收訊息並確認收到。後續版本將會增強此互動能力。

### 步驟 6：設定 Gemini API Key (安全建議)

直接在 Streamlit 介面輸入 API Key 是為了方便開發和臨時測試。為了更安全和持久地使用您的 API Key，特別是在 Colab 環境中，強烈建議您使用 Colab 的 **Secrets Manager**：

1.  **在 Colab 中添加密鑰：**
    *   點擊 Colab 介面左側的鑰匙圖標 (密鑰)。
    *   點擊 "+ 新增密鑰"。
    *   **名稱 (Name)：** 輸入一個名稱，例如 `GEMINI_API_KEY`。
    *   **值 (Value)：** 粘貼您的真實 Gemini API Key。
    *   開啟 "Notebook access" (筆記本訪問權限)。

2.  **在 `app.py` 中讀取密鑰 (修改建議)：**
    您可以修改 `app.py` 腳本的 API Key 處理部分，使其優先從 Colab Secrets 讀取金鑰。例如：
    ```python
    # 在 app.py 的開頭部分添加：
    # from google.colab import userdata # 如果在 Colab 中

    # ... (其他 import) ...

    # 在側邊欄 API Key 輸入部分修改：
    # st.sidebar.subheader("API 設定")
    # api_key_from_secret = ""
    # if 'google.colab' in str(globals().get('get_ipython', '')):
    #     try:
    #         api_key_from_secret = userdata.get('GEMINI_API_KEY') # 假設您將密鑰命名為 GEMINI_API_KEY
    #     except userdata.SecretNotFoundError:
    #         st.sidebar.warning("未在 Colab Secrets 中找到 GEMINI_API_KEY。")
    #     except Exception as e:
    #         st.sidebar.error(f"讀取 Colab Secret 時出錯: {e}")

    # current_api_key = st.session_state.get('gemini_api_key', '') # 從 session state 獲取已輸入的值
    # if api_key_from_secret and not current_api_key: # 如果 secret 中有值且用戶未手動輸入，則使用 secret 中的值
    #    st.session_state.gemini_api_key = api_key_from_secret
    #    st.sidebar.info("已從 Colab Secrets 加載 API Key。")
    # elif current_api_key:
    #    st.sidebar.info("正在使用手動輸入的 API Key。")


    # st.session_state.gemini_api_key = st.sidebar.text_input(
    #     "請輸入您的 Gemini API Key（或留空以使用 Colab Secret）：",
    #     type="password",
    #     value=st.session_state.gemini_api_key
    # )
    # if not st.session_state.gemini_api_key and not api_key_from_secret:
    #     st.sidebar.warning("請提供 Gemini API Key。")
    # elif not st.session_state.gemini_api_key and api_key_from_secret:
    #      st.session_state.gemini_api_key = api_key_from_secret # 確保如果輸入框清空，仍能回退到 secret
    ```
    上述程式碼片段僅為修改方向的示例，您需要將其整合到 `app.py` 的現有邏輯中。主要思路是：優先嘗試從 `userdata.get()` 獲取金鑰，如果獲取到則使用它，同時仍然保留手動輸入作為備選項或覆蓋項。

**注意：**
*   Colab Notebook 需保持運行。
*   每次 Colab 環境重啟，可能需重新掛載 Drive 和確認 API Key。

---

# (English Content)

# ShanJiaLang Weekly - Human-Computer Collaborative Chat-based Analysis Platform

## Project Goal
(Same as previous version)

## How to Run in Colab

(Same as previous version, up to Step 2)

### Step 2: Install Necessary Python Packages

In a code cell of your Notebook, execute the following command to install Streamlit and the Google Generative AI SDK:
```python
!pip install streamlit google-generativeai -q
```
After executing this cell, wait for the installation to complete.

### Step 3: Write the Application Script into the Colab Environment

Copy and paste the following code into a new code cell.

**Important Notes:**
*   The `app.py` content below is the current version. Always get the latest from GitHub if the project evolves.
*   **Gemini API Key Security:** This version of `app.py` allows direct API key input in the sidebar for quick testing. **It is strongly recommended not to hardcode API keys or save them in plaintext in notebooks for long-term use.** A more secure method is using Colab's Secrets Manager. Refer to "Step 6: Setting up the Gemini API Key" below for recommendations.

```python
%%writefile app.py
import streamlit as st
from google.colab import drive
import os
import google.generativeai as genai

# --- Google Drive related functions ---
def mount_google_drive():
    """Mounts Google Drive to the Colab environment."""
    try:
        drive.mount('/content/drive', force_remount=True)
        return True, "/content/drive/MyDrive/"
    except Exception as e:
        return False, str(e)

def read_file_from_drive(file_path):
    """Reads file content from the mounted Google Drive."""
    if not os.path.exists(file_path):
        return False, "File path does not exist."
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return True, content
    except Exception as e:
        return False, f"Failed to read file: {str(e)}"

# --- Gemini API related functions ---
def get_gemini_summary(api_key, document_content, week_info):
    """Uses Gemini API to generate a preliminary analysis summary."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        As a professional financial market analysis assistant, please generate a preliminary analysis report based on the provided "ShanJiaLang Weekly" content.
        Focus on these two points:
        1. Confirm and list the week number and date range (based on the provided week information: {week_info}).
        2. Extract the core viewpoints summary of "ShanJiaLang" for the week.

        Provided weekly report content:
        ---
        {document_content}
        ---

        Please answer in Chinese.
        """

        response = model.generate_content(prompt)
        return True, response.text
    except Exception as e:
        return False, f"Failed to call Gemini API: {str(e)}"

# --- Streamlit Application Interface ---
st.title("善甲狼週報 - 人機協同聊天式分析平台") # ShanJiaLang Weekly - Human-Computer Collaborative Chat-based Analysis Platform

# --- Session State Initialization ---
default_values = {
    'drive_mounted': False,
    'drive_mount_path': "/content/drive/MyDrive/" if 'google.colab' in str(globals().get('get_ipython', '')) else "./",
    'file_content': "",
    'file_read_status': "",
    'current_week_file': None,
    'gemini_api_key': "",
    'messages': []
}
for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Sidebar ---
st.sidebar.header("操作選單") # Operation Menu

# API Key Input
st.sidebar.subheader("API 設定") # API Settings
st.session_state.gemini_api_key = st.sidebar.text_input("請輸入您的 Gemini API Key：", type="password", value=st.session_state.gemini_api_key) # "Please enter your Gemini API Key:"
if not st.session_state.gemini_api_key:
    st.sidebar.warning("請提供 Gemini API Key 以啟用 AI 分析功能。") # "Please provide Gemini API Key to enable AI analysis."

# Google Drive File Reading Section
st.sidebar.subheader("讀取 Google Drive 文件") # "Read Google Drive File"
colab_env = 'google.colab' in str(globals().get('get_ipython', ''))

if colab_env:
    if st.sidebar.button("掛載 Google Drive"): # "Mount Google Drive"
        success, path_or_msg = mount_google_drive()
        st.session_state.drive_mounted = success
        if success:
            st.session_state.drive_mount_path = path_or_msg
            st.sidebar.success(f"Google Drive 已掛載到: {path_or_msg}") # "Google Drive mounted at:"
        else:
            st.sidebar.error(f"Google Drive 掛載失敗: {path_or_msg}") # "Google Drive mount failed:"
else:
    st.sidebar.info("Not in Colab environment. Please ensure file path is directly accessible.")

drive_file_path_input = st.sidebar.text_input("請輸入 Drive 中的文件路徑 (例如：folder/myfile.txt)", "demo_week_report.txt") # "Enter file path in Drive (e.g., folder/myfile.txt)"

if st.sidebar.button("讀取並設為當前分析文件"): # "Read and Set as Current Analysis File"
    if colab_env and not st.session_state.drive_mounted:
        st.sidebar.warning("請先掛載 Google Drive。") # "Please mount Google Drive first."
    else:
        full_path = os.path.join(st.session_state.drive_mount_path, drive_file_path_input) if colab_env else drive_file_path_input
        st.sidebar.info(f"嘗試讀取路徑: {full_path}") # "Attempting to read path:"
        success, content_or_error = read_file_from_drive(full_path)
        if success:
            st.session_state.file_content = content_or_error
            st.session_state.current_week_file = drive_file_path_input
            st.session_state.file_read_status = f"文件 '{drive_file_path_input}' 已成功讀取並設為當前分析目標。" # File successfully read and set as current analysis target.
            st.sidebar.success("文件讀取成功！") # "File read successfully!"
            st.session_state.messages = []
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown("您好！我已經讀取了新的文件，請問需要我做什麼分析嗎？ （您可以點擊下方的 'AI 初步分析' 按鈕）") # "Hello! I have read the new file. What analysis can I do for you? (You can click the 'AI Preliminary Analysis' button below)"
            st.session_state.messages.append({"role": "assistant", "content": "您好！我已經讀取了新的文件，請問需要我做什麼分析嗎？ （您可以點擊下方的 'AI 初步分析' 按鈕）"})
        else:
            st.session_state.file_content = ""
            st.session_state.current_week_file = None
            st.session_state.file_read_status = f"讀取文件 '{drive_file_path_input}' 失敗: {content_or_error}" # "Failed to read file:"
            st.sidebar.error("文件讀取失敗。") # "File reading failed."

# --- Main Chat Interface ---
st.subheader("聊天分析區") # "Chat Analysis Area"

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

# AI Preliminary Analysis Button
if st.session_state.current_week_file and st.session_state.file_content:
    if st.button("AI 初步分析 (A, B 部分)"): # "AI Preliminary Analysis (Parts A, B)"
        if not st.session_state.gemini_api_key:
            st.error("請先在側邊欄輸入您的 Gemini API Key。") # "Please enter your Gemini API Key in the sidebar first."
            st.session_state.messages.append({"role": "assistant", "content": "錯誤：請先在側邊欄輸入您的 Gemini API Key。"}) # "Error: Please enter your Gemini API Key in the sidebar first."
        else:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("AI 正在分析中，請稍候..."): # "AI is analyzing, please wait..."
                    week_info_display = f"從文件名 '{st.session_state.current_week_file}' 推斷的週資訊" # Week info inferred from filename

                    api_success, summary_or_error = get_gemini_summary(
                        st.session_state.gemini_api_key,
                        st.session_state.file_content,
                        week_info_display
                    )
                    if api_success:
                        response_text = summary_or_error
                        st.markdown(response_text)
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"AI 分析失敗：{summary_or_error}") # "AI analysis failed:"
                        st.session_state.messages.append({"role": "assistant", "content": f"AI 分析失敗：{summary_or_error}"})

# Chat input
if prompt := st.chat_input("請輸入您的指令或問題..."): # "Please enter your command or question..."
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。") # "I received your message: ... But I haven't implemented further processing for user input yet."
    st.session_state.messages.append({"role": "assistant", "content": f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。"})

# --- File Content Preview (Moved to Expander) ---
if st.session_state.file_content:
    with st.expander("點此查看已讀取的文件內容", expanded=False): # "Click here to view the content of the read file"
        st.info(st.session_state.file_read_status)
        st.text_area("文件內容：", st.session_state.file_content, height=300, key="file_content_preview") # "File content:"
elif st.session_state.file_read_status:
    st.info(st.session_state.file_read_status)
else:
    st.markdown("*目前沒有文件內容可顯示。請從側邊欄讀取文件。*") # "*No file content to display. Please read a file from the sidebar.*"

st.sidebar.markdown("---")
st.sidebar.subheader("測試輸入框") # "Test Input Box"
user_input_sidebar = st.sidebar.text_input("請在此輸入文字：", "你好！Side Bar!", key="sidebar_test_input") # "Please enter text here:", "Hello! Side Bar!"
st.sidebar.write(f"您在側邊欄輸入的是： {user_input_sidebar}") # "You entered in sidebar:"

```
Execute this cell.

### Step 4: Run the Streamlit Application

(Same as previous version)

### Step 5: Accessing the Application and Operating Guide

1.  **Access the Application Interface:**
    Click the `https://*.googleusercontent.com/proxy/8501/` URL provided in the Colab output.

2.  **Set Gemini API Key (Important):**
    *   In the application's sidebar under "API 設定" (API Settings), paste your Gemini API Key into the "請輸入您的 Gemini API Key：" input field. **This might be required every time the app starts or the page refreshes, unless you modify `app.py` to store the key more persistently (see security advice below).**
    *   AI analysis features will not work without a valid API Key.

3.  **Mount Google Drive (Colab environment only):**
    *   In the sidebar's "讀取 Google Drive 文件" (Read Google Drive File) section, click "掛載 Google Drive" (Mount Google Drive).
    *   Follow the prompts to authorize Google Drive access.

4.  **Read Analysis File:**
    *   In the sidebar input field, provide the filename (relative to "My Drive") of the file you want to analyze from your Google Drive.
    *   Click "讀取並設為當前分析文件" (Read and Set as Current Analysis File). Upon successful read, the AI will greet you in the chat area.

5.  **Perform AI Preliminary Analysis:**
    *   After a file is successfully read, an "AI 初步分析 (A, B 部分)" (AI Preliminary Analysis (Parts A, B)) button will appear below the main chat area.
    *   Click this button. The AI will provide an analysis of the "week and date range" and "core viewpoint summary" based on the document content. Results will be displayed in the chat area.

6.  **Chat Interaction:**
    *   You can interact with the AI by typing in the "請輸入您的指令或問題..." (Please enter your command or question...) input box at the bottom of the chat area.
    *   Currently, the AI's response to user input is basic (acknowledging receipt). This interactive capability will be enhanced in future versions.

### Step 6: Setting up the Gemini API Key (Security Recommendation)

Entering the API Key directly into the Streamlit interface is for development convenience and temporary testing. For more secure and persistent use of your API Key, especially in the Colab environment, it is **strongly recommended** to use Colab's **Secrets Manager**:

1.  **Add a Secret in Colab:**
    *   Click the key icon (Secrets) on the left side of the Colab interface.
    *   Click "+ New secret".
    *   **Name:** Enter a name, e.g., `GEMINI_API_KEY`.
    *   **Value:** Paste your actual Gemini API Key.
    *   Enable "Notebook access".

2.  **Read the Secret in `app.py` (Suggested Modification):**
    You can modify the API Key handling part of your `app.py` script to prioritize reading the key from Colab Secrets. For example:
    ```python
    # Add at the beginning of app.py:
    # from google.colab import userdata # If in Colab

    # ... (other imports) ...

    # Modify in the sidebar API Key input section:
    # st.sidebar.subheader("API 設定") # API Settings
    # api_key_from_secret = ""
    # if 'google.colab' in str(globals().get('get_ipython', '')):
    #     try:
    #         api_key_from_secret = userdata.get('GEMINI_API_KEY') # Assuming your secret is named GEMINI_API_KEY
    #     except userdata.SecretNotFoundError:
    #         st.sidebar.warning("GEMINI_API_KEY not found in Colab Secrets.")
    #     except Exception as e:
    #         st.sidebar.error(f"Error reading Colab Secret: {e}")

    # current_api_key = st.session_state.get('gemini_api_key', '')
    # if api_key_from_secret and not current_api_key:
    #    st.session_state.gemini_api_key = api_key_from_secret
    #    st.sidebar.info("API Key loaded from Colab Secrets.")
    # elif current_api_key:
    #    st.sidebar.info("Using manually entered API Key.")

    # st.session_state.gemini_api_key = st.sidebar.text_input(
    #     "請輸入您的 Gemini API Key（或留空以使用 Colab Secret）：", # "Enter your Gemini API Key (or leave blank to use Colab Secret):"
    #     type="password",
    #     value=st.session_state.gemini_api_key
    # )
    # if not st.session_state.gemini_api_key and not api_key_from_secret:
    #     st.sidebar.warning("請提供 Gemini API Key。") # "Please provide Gemini API Key."
    # elif not st.session_state.gemini_api_key and api_key_from_secret:
    #      st.session_state.gemini_api_key = api_key_from_secret
    ```
    The code snippet above is an example of the modification direction; you'll need to integrate it into the existing logic in `app.py`. The main idea is to try fetching the key from `userdata.get()` first, use it if available, while still allowing manual input as a fallback or override.

**Notes:**
*   The Colab Notebook must remain running.
*   Each time the Colab environment restarts, you may need to re-mount Drive and confirm the API Key.
