import streamlit as st
from google.colab import drive
import os
import google.generativeai as genai
import yfinance as yf # 新增 yfinance
import pandas as pd # 用於處理 yfinance 返回的 DataFrame
import re # 用於正規表示式解析日期
from datetime import datetime, timedelta # 用於日期計算

# --- Google Drive 相關函數 ---
def mount_google_drive():
    """掛載 Google Drive 到 Colab 環境。"""
    try:
        drive.mount('/content/drive', force_remount=True)
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

# --- 日期解析函數 ---
def parse_date_from_text(text_content):
    """從文本中解析 '日期：YYYY-MM-DD'。"""
    match = re.search(r"日期：(\d{4}-\d{2}-\d{2})", text_content)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None

# --- yfinance 相關函數 ---
DEFAULT_TICKERS = {
    "台灣加權指數": "^TWII",
    "納斯達克綜合指數": "^IXIC",
    "標準普爾500指數": "^GSPC",
    "費城半導體指數": "^SOX",
    "日經225指數": "^N225"
}

def get_stock_data(tickers_dict, start_date, end_date, interval="1d"):
    """獲取指定股票/指數列表在給定日期範圍和間隔的數據。"""
    data_frames = {}
    errors = {}

    # yfinance 對於 download 多個 tickers 時，日期是以 UTC 的午夜對齊。
    # 為確保包含 end_date 當天的數據，通常 end_date 需要加一天（如果 interval 是 '1d'）
    # 或者確保 start_date 和 end_date 的時間部分能正確處理。
    # 對於日線，yfinance 的 end_date 是不包含的，所以需要加一天。
    if isinstance(end_date, datetime):
        query_end_date = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    elif isinstance(end_date, str): # 假設是 YYYY-MM-DD
        query_end_date = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    else: # date object
        query_end_date = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

    if isinstance(start_date, (datetime, pd.Timestamp)):
        query_start_date = start_date.strftime("%Y-%m-%d")
    else: # str or date object
        query_start_date = str(start_date)

    ticker_list_for_yf = list(tickers_dict.values())

    #st.write(f"DEBUG yfinance: 下載 {ticker_list_for_yf} 從 {query_start_date} 到 {query_end_date} (interval: {interval})")

    try:
        # 下載所有股票數據
        data = yf.download(ticker_list_for_yf, start=query_start_date, end=query_end_date, interval=interval, progress=False)

        if data.empty:
            return None, {"all": "未下載到任何數據。請檢查代號和日期範圍。"}

        # 如果只有一個 ticker，yfinance 返回的 DataFrame 結構不同
        if len(ticker_list_for_yf) == 1:
            single_ticker_name = ticker_list_for_yf[0]
            if not data.empty:
                # 為單一 ticker 創建一個字典，使其結構與多 ticker 時一致
                df_processed = data[['Open', 'High', 'Low', 'Close', 'Volume']]
                # Ensure columns are MultiIndex even for single ticker
                df_processed.columns = pd.MultiIndex.from_tuples([(col, single_ticker_name) for col in df_processed.columns])
                data = df_processed
            else: # 單一 ticker 無數據
                 errors[single_ticker_name] = "無數據返回。"

        # 將數據按 ticker 分割到字典中
        for display_name, ticker_symbol in tickers_dict.items():
            try:
                # 提取該 ticker 的所有列 (Open, High, Low, Close, Volume)
                # For multi-ticker download, columns are MultiIndex: (Metric, TickerSymbol)
                # e.g. ('Close', '^TWII')
                # We need to select all metrics for a given ticker_symbol

                # Check if ticker_symbol is even in the columns (it might not be if yf failed for it)
                if any(ticker_symbol in col_tuple for col_tuple in data.columns):
                    ticker_df = data.loc[:, pd.IndexSlice[:, ticker_symbol]]
                    # ticker_df will have columns like ('Open', ticker_symbol), ('Close', ticker_symbol)
                    # We want to rename them to just 'Open', 'Close' for simplicity in later processing
                    ticker_df.columns = ticker_df.columns.droplevel(1) # Drop the ticker_symbol level
                    if not ticker_df.empty:
                        # 移除所有列都是 NaN 的行 (通常是市場未開市的日期)
                        data_frames[display_name] = ticker_df.dropna(how='all')
                    else:
                        errors[display_name] = f"代號 {ticker_symbol} 無數據返回。"
                else:
                    errors[display_name] = f"代號 {ticker_symbol} 無數據下載 (可能 API 未返回此代號的任何欄位)。"
            except KeyError:
                errors[display_name] = f"代號 {ticker_symbol} 可能無效或在該時段無數據 (KeyError)。"
            except Exception as e:
                errors[display_name] = f"處理 {ticker_symbol} 數據時出錯: {str(e)}"

    except Exception as e:
        return None, {"all": f"yfinance 下載時發生錯誤: {str(e)}"}

    return data_frames if data_frames else None, errors if errors else None


# --- Gemini API 相關函數 ---
def get_gemini_analysis(api_key, document_content, week_info, market_data_summary=None):
    """使用 Gemini API 生成分析。"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt_parts = [
            f"作為一個專業的金融市場分析助手，請基於以下提供的「善甲狼週報」內容（日期資訊：{week_info}）以及相關的市場數據，生成一份包含以下部分的分析報告：",
            "1. 確認並列出週次與日期範圍。",
            "2. 提取「善甲狼」當週的核心觀點摘要。"
        ]

        if market_data_summary:
            prompt_parts.append("3. 根據提供的市場數據，撰寫當週市場重點回顧（全球與台灣主要經濟/金融事件、主要市場動態，特別關注提供的指數表現）。市場數據摘要如下：")
            prompt_parts.append(market_data_summary)
        else:
            prompt_parts.append("3. 當週市場重點回顧（因缺乏即時市場數據，請基於週報內容進行推測性總結）。")

        prompt_parts.append("\n提供的週報內容如下：\n---\n" + document_content + "\n---\n請用中文回答，風格專業且易於理解。")

        prompt = "\n".join(prompt_parts)
        # st.write("DEBUG Gemini Prompt:", prompt) # 用於調試
        response = model.generate_content(prompt)
        return True, response.text
    except Exception as e:
        return False, f"調用 Gemini API 失敗：{str(e)}"

# --- Streamlit 應用程式界面 ---
st.set_page_config(layout="wide") # 頁面寬度調整
st.title("善甲狼週報 - 人機協同聊天式分析平台")

# --- Session State 初始化 ---
default_values = {
    'drive_mounted': False,
    'drive_mount_path': "/content/drive/MyDrive/" if 'google.colab' in str(globals().get('get_ipython', '')) else "./",
    'file_content': "",
    'file_read_status': "",
    'current_week_file': None,
    'parsed_report_date': None, # 新增：存儲解析出的報告日期
    'gemini_api_key': "",
    'messages': [],
    'market_data_cache': None, # 新增：緩存市場數據
    'market_data_errors': None # 新增：緩存市場數據獲取錯誤
}
for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 側邊欄 ---
st.sidebar.header("操作選單")

# API Key 輸入
st.sidebar.subheader("API 設定")
# 嘗試從 Colab Secrets 讀取 API Key
api_key_from_secrets = "" # 確保變數存在
if 'google.colab' in str(globals().get('get_ipython', '')):
    try:
        from google.colab import userdata
        api_key_from_secrets = userdata.get('GEMINI_API_KEY')
        if api_key_from_secrets and not st.session_state.gemini_api_key: # 只有當 session state 為空時才用 secrets 填充
             st.session_state.gemini_api_key = api_key_from_secrets
             st.sidebar.info("已從 Colab Secrets 自動加載 API Key。")
    except Exception:
        pass # 忽略錯誤，允許手動輸入

st.session_state.gemini_api_key = st.sidebar.text_input(
    "請輸入您的 Gemini API Key：",
    type="password",
    value=st.session_state.gemini_api_key
)
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

drive_file_path_input = st.sidebar.text_input("請輸入 Drive 中的文件路徑 (例如：folder/myfile.txt)", getattr(st.session_state, 'last_typed_path', "demo_week_report.txt"))
st.session_state.last_typed_path = drive_file_path_input # 記住上次輸入

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
            st.session_state.parsed_report_date = parse_date_from_text(content_or_error) # 解析日期
            date_info_for_status = f"(解析到日期: {st.session_state.parsed_report_date})" if st.session_state.parsed_report_date else "(未解析到明確日期)"
            st.session_state.file_read_status = f"文件 '{drive_file_path_input}' 已成功讀取 {date_info_for_status}。"
            st.sidebar.success(f"文件讀取成功！{date_info_for_status}")
            st.session_state.messages = []
            st.session_state.market_data_cache = None # 清空舊市場數據
            st.session_state.market_data_errors = None

            # AI 打招呼
            ai_greeting = "您好！我已經讀取了新的文件。"
            if st.session_state.parsed_report_date:
                ai_greeting += f" 文件日期為 {st.session_state.parsed_report_date}。"
            ai_greeting += " 您可以點擊下方的 'AI 初步分析' 按鈕開始，或直接與我對話。"

            # 清理舊的聊天記錄，並添加新的 AI 打招呼訊息
            st.session_state.messages = [{"role": "assistant", "content": ai_greeting}]
            # 不直接在這裡用 st.chat_message 渲染，統一由後面的循環處理
        else:
            st.session_state.file_content = ""
            st.session_state.current_week_file = None
            st.session_state.parsed_report_date = None
            st.session_state.file_read_status = f"讀取文件 '{drive_file_path_input}' 失敗: {content_or_error}"
            st.sidebar.error("文件讀取失敗。")

# --- 主聊天界面 ---
st.subheader("聊天分析區")

# AI 初步分析按鈕
analysis_button_placeholder = st.empty() # Placeholder for the button
charts_placeholder = st.empty() # Placeholder for charts area

if st.session_state.current_week_file and st.session_state.file_content:
    if analysis_button_placeholder.button("AI 初步分析 (包含市場回顧)"):
        if not st.session_state.gemini_api_key:
            st.error("請先在側邊欄輸入您的 Gemini API Key。")
            st.session_state.messages.append({"role": "assistant", "content": "錯誤：請先在側邊欄輸入您的 Gemini API Key。"})
        else:
            # 清空之前的圖表和市場數據錯誤信息
            charts_placeholder.empty()
            st.session_state.market_data_cache = None
            st.session_state.market_data_errors = None

            with st.chat_message("assistant", avatar="🤖"): # AI 分析的整體容器
                with st.spinner("AI 正在分析中，請稍候...（可能包含市場數據獲取）"):
                    # 準備市場數據
                    market_data_summary_for_gemini = "本週無額外市場數據提供。"

                    report_date = st.session_state.parsed_report_date
                    if not report_date:
                        report_date = datetime.now().date()
                        st.warning(f"警告：未從文件中解析出日期，將使用當前日期 {report_date} 作為基準進行市場回顧（過去一週）。")

                    end_date_query = report_date
                    start_date_query = end_date_query - timedelta(days=7)

                    market_data, market_errors = get_stock_data(DEFAULT_TICKERS, start_date_query, end_date_query)
                    st.session_state.market_data_cache = market_data
                    st.session_state.market_data_errors = market_errors

                    if market_data:
                        temp_summary_list = [f"以下為 {start_date_query.strftime('%Y-%m-%d')} 至 {end_date_query.strftime('%Y-%m-%d')} 的主要市場指數表現："]
                        for name, df in market_data.items():
                            if not df.empty and 'Close' in df.columns and not df['Close'].dropna().empty:
                                first_close = df['Close'].dropna().iloc[0]
                                last_close = df['Close'].dropna().iloc[-1]
                                change_percent = ((last_close - first_close) / first_close) * 100
                                temp_summary_list.append(f"- {name} ({DEFAULT_TICKERS[name]}): 期間收盤價從 {first_close:.2f} 變動至 {last_close:.2f} (漲跌幅: {change_percent:.2f}%).")
                            else:
                                temp_summary_list.append(f"- {name} ({DEFAULT_TICKERS[name]}): 在此期間無有效數據或收盤價。")
                        market_data_summary_for_gemini = "\n".join(temp_summary_list)

                    if market_errors:
                         st.error(f"獲取部分市場數據時發生錯誤: {market_errors}")

                    week_info_for_gemini = str(st.session_state.parsed_report_date) if st.session_state.parsed_report_date else "未知"
                    api_success, summary_or_error = get_gemini_analysis(
                        st.session_state.gemini_api_key,
                        st.session_state.file_content,
                        week_info_for_gemini,
                        market_data_summary_for_gemini
                    )
                    if api_success:
                        response_text = summary_or_error
                        st.markdown(response_text) # 直接在 chat_message 容器中顯示 AI 分析文本
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"AI 分析失敗：{summary_or_error}")
                        st.session_state.messages.append({"role": "assistant", "content": f"AI 分析失敗：{summary_or_error}"})

            # 在 AI 分析文本下方顯示市場數據圖表 (使用新的 placeholder)
            with charts_placeholder.container():
                if st.session_state.market_data_cache:
                    st.markdown("--- \n**附錄：相關市場指數週線圖 (收盤價)**")
                    # 決定列的數量，最多3列
                    num_charts = len(st.session_state.market_data_cache)
                    num_cols = min(num_charts, 3)

                    chart_keys = list(st.session_state.market_data_cache.keys())
                    for i in range(0, num_charts, num_cols):
                        cols = st.columns(num_cols)
                        for j in range(num_cols):
                            if i + j < num_charts:
                                display_name = chart_keys[i+j]
                                df_index_data = st.session_state.market_data_cache[display_name]
                                with cols[j]:
                                    if not df_index_data.empty and 'Close' in df_index_data.columns and not df_index_data['Close'].dropna().empty:
                                        st.subheader(display_name)
                                        st.line_chart(df_index_data['Close'])
                                    else:
                                        st.subheader(display_name)
                                        st.warning(f"'{display_name}' 無有效收盤價數據可繪製。")
                if st.session_state.market_data_errors:
                     st.warning(f"部分指數數據未能獲取或繪製，錯誤訊息: {st.session_state.market_data_errors}")


# 顯示聊天記錄 (包含 AI 初步分析的結果)
# 這個循環應該在所有潛在的 st.session_state.messages 修改之後
# st.markdown("--- CHAT HISTORY BELOW ---") # Debug separator
for msg_idx, message_data in enumerate(st.session_state.messages):
    with st.chat_message(message_data["role"], avatar="🧑‍💻" if message_data["role"] == "user" else "🤖"):
        # 如果是AI分析按鈕觸發的內容，並且已經由按鈕下方的 st.markdown() 顯示過，則不再重複顯示。
        # 這裡通過檢查內容是否與按鈕生成的最後一條 AI 消息相同來避免重複。
        # 但由於按鈕下的 markdown 是即時的，而這裡是遍歷歷史，所以這個邏輯有點複雜。
        # 簡化：AI分析按鈕生成的內容是直接 markdown 到頁面，然後也存入 messages。
        # 這裡的循環會再次渲染它。如果希望避免，AI分析按鈕的內容不應直接 markdown，只存入 messages。
        # 目前的設計是按鈕後直接顯示，然後聊天記錄也顯示，可能會導致 AI 分析內容出現兩次（一次在按鈕下，一次在歷史記錄裡）。
        # 解決方案：AI 分析按鈕點擊後，其結果只存入 messages，然後依賴下面的循環來顯示所有消息。
        # 因此，移除按鈕下方的 st.markdown(response_text)
        st.markdown(message_data["content"])


# 聊天輸入框
if prompt := st.chat_input("請輸入您的指令或問題..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 立即顯示用戶消息
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        response_text = f"我收到了您的訊息：'{prompt}'。進階的聊天回應功能（例如根據您的指令查詢特定股票或執行特定分析）仍在開發中。"
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.experimental_rerun() # Rerun to show the new messages immediately including AI's ack


# --- 文件內容預覽 (移至 Expander) ---
if st.session_state.file_content:
    with st.expander("點此查看已讀取的文件內容", expanded=False):
        st.info(st.session_state.file_read_status)
        st.text_area("文件內容：", st.session_state.file_content, height=300, key="file_content_preview")
elif st.session_state.file_read_status:
    st.info(st.session_state.file_read_status)
else:
    st.markdown("*目前沒有文件內容可顯示。請從側邊欄讀取文件。*")

# 側邊欄測試輸入框 (保留)
st.sidebar.markdown("---")
st.sidebar.subheader("測試輸入框")
user_input_sidebar = st.sidebar.text_input("請在此輸入文字：", "你好！Side Bar!", key="sidebar_test_input")
st.sidebar.write(f"您在側邊欄輸入的是： {user_input_sidebar}")
