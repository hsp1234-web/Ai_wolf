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
# (確保所有需要的 session state 鍵都已初始化)
default_values = {
    'drive_mounted': False,
    'drive_mount_path': "/content/drive/MyDrive/" if 'google.colab' in str(globals().get('get_ipython', '')) else "./",
    'file_content': "",
    'file_read_status': "",
    'current_week_file': None, # 用於存儲當前分析的文件名
    'gemini_api_key': "",
    'messages': [] # 存儲聊天記錄
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
            st.session_state.current_week_file = drive_file_path_input # 設定當前文件
            st.session_state.file_read_status = f"文件 '{drive_file_path_input}' 已成功讀取並設為當前分析目標。"
            st.sidebar.success("文件讀取成功！")
            # 清空舊聊天記錄並由 AI 發起新對話
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
        else:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("AI 正在分析中，請稍候..."):
                    # 模擬週次與日期範圍 (可從文件名解析)
                    week_info_display = f"從文件名 '{st.session_state.current_week_file}' 推斷的週資訊 (此處為模擬)"

                    api_success, summary_or_error = get_gemini_summary(
                        st.session_state.gemini_api_key,
                        st.session_state.file_content,
                        st.session_state.current_week_file # 將文件名作為週資訊傳遞
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

    # 此處為後續 AI 回應使用者輸入的邏輯 (暫未實現)
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。")
    st.session_state.messages.append({"role": "assistant", "content": f"我收到了您的訊息：'{prompt}'。但我目前還沒有實現針對使用者輸入的進一步處理功能。"})


# --- 文件內容預覽 (移至 Expander) ---
if st.session_state.file_content:
    with st.expander("點此查看已讀取的文件內容", expanded=False):
        st.info(st.session_state.file_read_status)
        st.text_area("文件內容：", st.session_state.file_content, height=300, key="file_content_preview")
elif st.session_state.file_read_status: # 只有狀態沒有內容 (例如讀取失敗)
    st.info(st.session_state.file_read_status)
else:
    st.markdown("*目前沒有文件內容可顯示。請從側邊欄讀取文件。*")

# 側邊欄測試輸入框 (保留)
st.sidebar.markdown("---")
st.sidebar.subheader("測試輸入框")
user_input_sidebar = st.sidebar.text_input("請在此輸入文字：", "你好！Side Bar!", key="sidebar_test_input")
st.sidebar.write(f"您在側邊欄輸入的是： {user_input_sidebar}")
