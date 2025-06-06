# services/file_processors.py
import streamlit as st
import logging
import pandas as pd
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)

def handle_file_uploads(uploaded_files) -> None:
    """
    處理 Streamlit file_uploader 上傳的檔案。
    更新 session_state 中的 uploaded_files_list 和 uploaded_file_contents。

    Args:
        uploaded_files: st.file_uploader() 返回的檔案列表。
                        每個元素都是一個 UploadedFile 對象。
    """
    logger.info(f"開始執行 handle_file_uploads。接收到 {len(uploaded_files) if uploaded_files else 0} 個檔案。")

    if not uploaded_files:
        if st.session_state.get("uploaded_files_list"): # 檢查之前是否有文件
            logger.info("上傳檔案列表為空或已被清除。正在清空 session_state 中的已上傳檔案列表和內容。")
            st.session_state.uploaded_files_list = []
            st.session_state.uploaded_file_contents = {}
        else:
            logger.info("沒有新的上傳檔案，且之前也沒有已上傳的檔案。")
        return

    # 提取新上傳檔案的名稱列表以供比較
    newly_uploaded_filenames = sorted([f.name for f in uploaded_files]) # 排序以確保順序一致性

    # 獲取先前存儲在 session_state 中的檔案名稱列表 (如果存在)
    # 確保它是列表類型，並且也排序以便比較
    existing_stored_filenames = sorted(st.session_state.get("uploaded_files_list", []))

    # 比較新舊檔案列表是否完全相同 (名稱和數量)
    # 注意: Streamlit 的 UploadedFile 對象在每次上傳操作時即使是相同檔案也會是新的實例。
    # 因此，僅比較文件名列表是否改變，作為是否需要重新處理的依據。
    # 如果文件名和數量都沒變，我們假設內容也沒變，除非強制重新加載。
    # 為了簡化，這裡我們總是重新處理所有傳入的檔案，因為 UploadedFile 對象本身是新的。
    # 如果需要更精細的控制（例如基於文件內容的哈希值），則需要更複雜的邏輯。

    logger.info(f"接收到 {len(uploaded_files)} 個新上傳的檔案。準備處理...")

    current_uploaded_files_list = [] # 用於存儲本次成功處理的檔案名
    current_uploaded_file_contents = {} # 用於存儲本次成功處理的檔案內容

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        logger.info(f"開始處理檔案: '{filename}' (大小: {uploaded_file.size} 字節, 類型: {uploaded_file.type})")
        current_uploaded_files_list.append(filename) # 先加入列表，即使後續處理失敗也記錄文件名

        try:
            content = None
            file_type_processed = "未知"

            # 嘗試以文本方式讀取常見文本文件類型
            if filename.endswith((".txt", ".py", ".json", ".csv", ".md", ".log", ".xml", ".html", ".css", ".js")):
                file_type_processed = "文本"
                logger.debug(f"檔案 '{filename}' 被識別為文本類型。嘗試 UTF-8 解碼...")
                try:
                    content_bytes = uploaded_file.getvalue()
                    content = content_bytes.decode("utf-8")
                    logger.info(f"成功使用 UTF-8 解碼檔案 '{filename}'。內容長度: {len(content)} 字符。")
                except UnicodeDecodeError:
                    logger.warning(f"檔案 '{filename}' 使用 UTF-8 解碼失敗。嘗試使用 'latin-1' 解碼...")
                    try:
                        # uploaded_file.seek(0) # 如果 getvalue() 不能重複調用，可能需要 seek(0)
                        content = content_bytes.decode("latin-1") # 使用之前讀取的 bytes
                        logger.info(f"成功使用 latin-1 解碼檔案 '{filename}'。內容長度: {len(content)} 字符。")
                    except UnicodeDecodeError as e_latin1: # 如果 latin-1 也失敗
                        logger.error(f"檔案 '{filename}' 使用 latin-1 解碼也失敗: {e_latin1}。將作為原始字節存儲。")
                        content = content_bytes # 存儲原始字節
                        file_type_processed = "字節 (解碼失敗)"
                except Exception as e_utf8: # 其他 UTF-8 解碼或getvalue()時的錯誤
                    logger.error(f"讀取或 UTF-8 解碼檔案 '{filename}' 時發生未知錯誤: {e_utf8}。將作為原始字節存儲。", exc_info=True)
                    content = uploaded_file.getvalue() # 嘗試重新獲取字節
                    file_type_processed = "字節 (讀取/UTF-8未知錯誤)"

            # 嘗試讀取表格數據 (如 CSV, Excel)
            # 注意：CSV 檔案也可能在上面被作為文本文件讀取。這裡提供專門的DataFrame處理。
            # 如果希望CSV總是作為DataFrame，可以調整上面的if/elif順序或條件。
            # 目前的邏輯是，如果endsswith .csv，它會先被嘗試當作文本文件，如果UTF-8或latin-1成功，則為文本。
            # 這裡的 elif 意味著如果上面文本處理成功，這裡就不會執行。
            # 如果希望 .csv 優先由 pandas 處理，需要調整邏輯。
            # 為了與原計劃一致，我們假設 .csv 在文本處理後，如果還想作為DataFrame，則需要用戶指定或此處邏輯調整。
            # 假設：如果上面作為文本讀取成功，這裡不再重複處理為DataFrame。
            # 但如果上面失敗並存為字節，這裡可以嘗試 pandas。

            # 根據目前的需求，如果一個 .csv 文件在上面被成功解碼為文本，它將作為文本內容存儲。
            # 如果我們希望 .csv 和 .xlsx 文件總是優先被解析為 DataFrame，我們需要調整條件判斷的順序。
            # 暫時維持原邏輯，即文本優先，然後才是特定二進製或 pandas 處理。
            # 更新：將 .csv 和 .xlsx 的處理移到文本處理之前，以優先解析為 DataFrame。

            # --- 調整後：優先處理表格文件 ---
            if filename.endswith((".csv")):
                file_type_processed = "CSV (DataFrame)"
                logger.debug(f"檔案 '{filename}' 被識別為 CSV。嘗試使用 pandas 讀取...")
                try:
                    uploaded_file.seek(0) # pandas 需要從頭讀取
                    df = pd.read_csv(uploaded_file)
                    content = df # 存儲 DataFrame
                    logger.info(f"成功將 CSV 檔案 '{filename}' 讀取為 DataFrame。Shape: {df.shape}")
                except Exception as e_csv_pandas:
                    logger.error(f"使用 pandas 讀取 CSV 檔案 '{filename}' 失敗: {e_csv_pandas}。嘗試作為文本讀取。", exc_info=True)
                    # 回退到文本讀取 (與上面邏輯類似)
                    try:
                        uploaded_file.seek(0)
                        content_bytes = uploaded_file.getvalue()
                        content = content_bytes.decode("utf-8")
                        logger.info(f"回退：成功使用 UTF-8 解碼 CSV 檔案 '{filename}' 為文本。")
                        file_type_processed = "文本 (CSV回退)"
                    except UnicodeDecodeError:
                        logger.warning(f"回退：檔案 '{filename}' (CSV) 使用 UTF-8 解碼失敗，嘗試 latin-1...")
                        try:
                            uploaded_file.seek(0)
                            content = content_bytes.decode("latin-1")
                            logger.info(f"回退：成功使用 latin-1 解碼 CSV 檔案 '{filename}' 為文本。")
                            file_type_processed = "文本 (CSV回退)"
                        except Exception as e_latin1_csv:
                            logger.error(f"回退：檔案 '{filename}' (CSV) 使用 latin-1 解碼也失敗: {e_latin1_csv}。將作為原始字節存儲。")
                            content = content_bytes
                            file_type_processed = "字節 (CSV回退失敗)"

            elif filename.endswith((".xls", ".xlsx")):
                file_type_processed = "Excel (DataFrame)"
                logger.debug(f"檔案 '{filename}' 被識別為 Excel。嘗試使用 pandas 讀取...")
                try:
                    uploaded_file.seek(0) # pandas 需要從頭讀取
                    df = pd.read_excel(uploaded_file, engine=None) # 自動選擇引擎
                    content = df
                    logger.info(f"成功將 Excel 檔案 '{filename}' 讀取為 DataFrame。Shape: {df.shape}")
                except Exception as e_excel:
                    logger.error(f"使用 pandas 讀取 Excel 檔案 '{filename}' 失敗: {e_excel}。將作為原始字節存儲。", exc_info=True)
                    uploaded_file.seek(0)
                    content = uploaded_file.getvalue() # 存儲原始字節
                    file_type_processed = "字節 (Excel讀取失敗)"

            # 如果以上特定類型都不是，或者上面嘗試 DataFrame 失敗後回退到這裡
            elif content is None: # 確保 content 未被設定
                file_type_processed = "文本 (通用)"
                logger.debug(f"檔案 '{filename}' 被識別為通用文本類型。嘗試 UTF-8 解碼...")
                try:
                    uploaded_file.seek(0)
                    content_bytes = uploaded_file.getvalue()
                    content = content_bytes.decode("utf-8")
                    logger.info(f"成功使用 UTF-8 解碼檔案 '{filename}'。")
                except UnicodeDecodeError:
                    logger.warning(f"檔案 '{filename}' 使用 UTF-8 解碼失敗，嘗試 'latin-1'...")
                    try:
                        uploaded_file.seek(0)
                        content = content_bytes.decode("latin-1")
                        logger.info(f"成功使用 latin-1 解碼檔案 '{filename}'。")
                    except UnicodeDecodeError as e_latin1_fallback:
                        logger.error(f"檔案 '{filename}' 使用 latin-1 解碼也失敗: {e_latin1_fallback}。將作為原始字節存儲。")
                        content = content_bytes
                        file_type_processed = "字節 (通用解碼失敗)"
                except Exception as e_text_fallback:
                    logger.error(f"讀取或解码檔案 '{filename}' 為文本時發生未知錯誤: {e_text_fallback}。將作為原始字節存儲。", exc_info=True)
                    uploaded_file.seek(0)
                    content = uploaded_file.getvalue()
                    file_type_processed = "字節 (通用讀取/解碼未知錯誤)"

            current_uploaded_file_contents[filename] = content
            logger.debug(f"檔案 '{filename}' 處理完畢，存儲類型: {type(content).__name__}，處理方式標記: {file_type_processed}")

        except Exception as e_outer:
            logger.error(f"處理檔案 '{filename}' 過程中發生頂層錯誤: {type(e_outer).__name__} - {str(e_outer)}", exc_info=True)
            st.error(f"處理檔案 '{filename}' 時發生嚴重錯誤: {e_outer}")
            current_uploaded_file_contents[filename] = f"處理檔案時發生嚴重錯誤: {e_outer}"

    # 更新 session_state
    st.session_state.uploaded_files_list = current_uploaded_files_list # 更新為本次實際處理的檔案名列表
    st.session_state.uploaded_file_contents = current_uploaded_file_contents

    logger.info(f"所有上傳檔案處理完成。最終檔案列表數量: {len(st.session_state.uploaded_files_list)}, 檔案內容數量: {len(st.session_state.uploaded_file_contents)}")
    logger.debug(f"更新後的檔案列表 (session_state.uploaded_files_list): {st.session_state.uploaded_files_list}")

if __name__ == "__main__":
    # 模擬 Streamlit 環境進行測試
    class MockUploadedFile:
        def __init__(self, name, value):
            self.name = name
            self._value = value

        def getvalue(self):
            return self._value

    class MockSessionState:
        def __init__(self):
            self._state = {
                "uploaded_files_list": [],
                "uploaded_file_contents": {}
            }
        def __setitem__(self, key, value):
            self._state[key] = value
        def __getitem__(self, key):
            return self._state[key]
        def __contains__(self, key):
            return key in self._state
        def get(self, key, default=None):
            return self._state.get(key, default)

    # st.session_state = MockSessionState() # 取消註釋以在本地運行此腳本進行測試

    # 創建一些模擬檔案
    # file1 = MockUploadedFile("test.txt", b"This is a test file.")
    # file2 = MockUploadedFile("data.csv", b"col1,col2\\n1,2\\n3,4")
    # file3 = MockUploadedFile("image.jpg", b"some image bytes") # 非文本文件
    # file4_invalid_utf8 = MockUploadedFile("invalid.txt", b'\xff\xfeA\x00B\x00') # 無效的UTF-8序列

    # uploaded_files = [file1, file2, file3, file4_invalid_utf8]
    # handle_file_uploads(uploaded_files)

    # print("Uploaded files list:", st.session_state.uploaded_files_list)
    # for name, content in st.session_state.uploaded_file_contents.items():
    #     if isinstance(content, pd.DataFrame):
    #         print(f"Content of {name}: DataFrame with shape {content.shape}")
    #     elif isinstance(content, bytes):
    #          print(f"Content of {name}: Bytes with length {len(content)}")
    #     else:
    #         print(f"Content of {name}: {content[:100]}...") # 打印部分內容
    pass
