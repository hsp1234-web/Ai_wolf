# utils/log_utils.py
import logging
import streamlit as st
from io import StringIO
import os
import sys
# from config.app_settings import MAX_UI_LOG_ENTRIES # Will get from ui_settings
# It's possible app_settings is imported by other modules, so direct removal from here might be fine
# if those other modules ensure ui_settings is populated first.
# For now, assume st.session_state.ui_settings will have this.

class StreamlitLogHandler(logging.Handler):
    """
    一個自定義的日誌處理程序，它將日誌消息收集到一個內部列表 (self.logs)
    並且可選地也將日誌寫入 Streamlit session_state 中的一個指定列表，以便在 UI 中顯示。
    """
    def __init__(self, ui_log_key: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs = []  # 內部存儲，主要用於可能的後端檢查或完整日誌的保留
        self.ui_log_key = ui_log_key # Session state key for UI-specific logs

        # 確保 session_state 中的列表存在
        if self.ui_log_key:
            if self.ui_log_key not in st.session_state:
                st.session_state[self.ui_log_key] = []
            elif not isinstance(st.session_state.get(self.ui_log_key), list):
                # 如果存在但不是列表，則警告並重置
                # 使用 print 而不是 logger，因為 logger 可能尚未完全配置或可能導致循環
                print(f"Log Handler Init Warning: Session state key '{self.ui_log_key}' exists but is not a list. It will be reset.", flush=True)
                st.session_state[self.ui_log_key] = []


    def emit(self, record):
        """
        將日誌記錄格式化並寫入內部列表和可選的 session_state 列表。
        """
        log_entry = self.format(record)
        self.logs.append(log_entry)

        if self.ui_log_key:
            try:
                # 再次確保 st.session_state 中的目標確實是一個列表 (可能在 handler 初始化後被外部修改)
                if not isinstance(st.session_state.get(self.ui_log_key), list):
                    # 如果不是列表，則重置為列表，並記錄一條訊息到內部日誌和控制台
                    msg_reinit = f"StreamlitLogHandler Warning: Session state key '{self.ui_log_key}' was not a list during emit. Re-initializing."
                    self.logs.append(msg_reinit) # 記錄到自身logs
                    print(msg_reinit, flush=True) # 打印到控制台
                    st.session_state[self.ui_log_key] = []

                st.session_state[self.ui_log_key].append(log_entry)
                # 考慮限制 UI 日誌列表的長度，以避免 session_state 過大
                ui_settings = st.session_state.get("ui_settings", {})
                max_ui_logs = ui_settings.get("max_ui_log_entries", 300) # Fallback to 300 if not in settings

                if len(st.session_state[self.ui_log_key]) > max_ui_logs:
                    st.session_state[self.ui_log_key] = st.session_state[self.ui_log_key][-max_ui_logs:]
            except Exception as e:
                # 如果在寫入 session_state 時發生錯誤，至少記錄到內部日誌
                # 避免在這裡使用 logging.error() 以防止潛在的遞歸錯誤
                err_msg = f"StreamlitLogHandler ERROR: Failed to emit log to session_state.'{self.ui_log_key}': {e}"
                self.logs.append(err_msg)
                print(err_msg, flush=True)


    def get_logs(self, from_ui_store: bool = False) -> list[str]:
        """
        返回日誌列表。

        Args:
            from_ui_store (bool): 如果為 True，則從 session_state (UI) 存儲中獲取日誌。
                                  否則，從內部 self.logs 獲取。

        Returns:
            list[str]: 日誌條目列表。
        """
        if from_ui_store and self.ui_log_key:
            return st.session_state.get(self.ui_log_key, []) #確保返回列表
        return self.logs

    def clear_logs(self, clear_ui_store: bool = True):
        """
        清除日誌。

        Args:
            clear_ui_store (bool): 如果為 True 且設定了 ui_log_key，則同時清除 session_state 中的日誌。
        """
        old_internal_len = len(self.logs)
        self.logs = []
        cleared_ui = False
        if clear_ui_store and self.ui_log_key and self.ui_log_key in st.session_state:
            if isinstance(st.session_state[self.ui_log_key], list):
                old_ui_len = len(st.session_state[self.ui_log_key])
                st.session_state[self.ui_log_key] = []
                cleared_ui = True
                logging.info(f"UI 日誌 (session_state['{self.ui_log_key}']) 已清除 (原 {old_ui_len} 條)。")
        logging.info(f"內部日誌緩存已清除 (原 {old_internal_len} 條)。UI 日誌清除狀態: {cleared_ui}")


def setup_logging(
    log_level: int = logging.INFO,
    log_file_path: str = None,
    streamlit_ui_log_key: str = 'ui_logs'
) -> StreamlitLogHandler:
    """
    設定根日誌記錄器。

    Args:
        log_level (int): 日誌級別，例如 logging.INFO, logging.DEBUG。
        log_file_path (str, optional): 如果提供，則將日誌同時寫入到此檔案路徑。
        streamlit_ui_log_key (str, optional): 用於 StreamlitLogHandler 在 session_state 中存儲 UI 日誌的鍵。
                                            如果為 None，StreamlitLogHandler 將不會寫入 session_state。

    Returns:
        StreamlitLogHandler: StreamlitLogHandler 的實例，以便應用程式可以訪問其日誌。
    """
    # Python 的 logging 模組在 Jupyter/Colab 環境中可能需要特別處理，
    # 因為 notebook 環境可能已經預先配置了日誌。
    # force=True 在 logging.basicConfig 中是關鍵，用於移除並替換現有的根記錄器配置。

    log_format_str = "%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(log_format_str)

    handlers = []

    # 1. StreamlitLogHandler
    st_log_handler = StreamlitLogHandler(ui_log_key=streamlit_ui_log_key)
    st_log_handler.setFormatter(formatter)
    handlers.append(st_log_handler)

    # 2. StreamHandler (Console)
    console_handler = logging.StreamHandler(stream=sys.stdout) # 明確指定 sys.stdout 或 sys.stderr
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # 3. FileHandler
    if log_file_path:
        try:
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                 os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            print(f"日誌錯誤：無法設定檔案日誌處理程序到 '{log_file_path}': {e}", flush=True)

    # 配置根日誌記錄器
    # 移除所有現有的處理程序，然後添加我們自己的
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]: # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close() # 關閉處理程序以釋放資源

    root_logger.setLevel(log_level) # 設定根記錄器的級別
    for handler in handlers:
        root_logger.addHandler(handler)

    # 記錄一條訊息以確認配置
    # 這條訊息應該能被所有配置的 handlers 捕獲
    initial_log_message = (
        f"日誌系統已配置。級別: {logging.getLevelName(log_level)}。"
        f"處理程序數量: {len(handlers)}。"
    )
    if log_file_path and any(isinstance(h, logging.FileHandler) for h in handlers):
        initial_log_message += f" 檔案日誌路徑: '{log_file_path}'。"
    if streamlit_ui_log_key and any(isinstance(h, StreamlitLogHandler) and h.ui_log_key == streamlit_ui_log_key for h in handlers):
        initial_log_message += f" UI日誌鍵: '{streamlit_ui_log_key}'。"

    logging.info(initial_log_message) # 使用 logging.info 記錄，而不是 print

    return st_log_handler

if __name__ == "__main__":
    # 模擬 Streamlit 環境進行測試
    # 注意：由於 Streamlit 的 session_state 在普通 Python 腳本中不可用，
    # 我們需要一個 Mock 來模擬它。

    # 創建一個 MockStreamlit 類來模擬 st 和 st.session_state
    class MockSessionState(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class MockStreamlit:
        def __init__(self):
            self.session_state = MockSessionState()
        # 可以根據需要添加其他 st 方法的模擬
        def warning(self, message):
            print(f"ST.WARNING: {message}", flush=True)

    # 將 st 替換為我們的 MockStreamlit 實例
    # 這只會影響此 __main__ 塊內的 'st'
    _st_original = st
    st = MockStreamlit()
    import sys # 確保 sys 在此作用域內

    print("--- 日誌工具測試 ---")

    UI_LOG_KEY = "test_ui_logs"
    LOG_FILE = "test_app.log"

    # 清理之前的測試日誌檔案
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    # 測試1: 完整配置 (DEBUG級別, 檔案日誌, UI日誌)
    print("\n[測試 1: 完整配置 (DEBUG)]")
    handler_instance = setup_logging(log_level=logging.DEBUG, log_file_path=LOG_FILE, streamlit_ui_log_key=UI_LOG_KEY)

    logging.debug("這是一條 DEBUG 級別的日誌。")
    logging.info("這是一條 INFO 級別的日誌。")
    logging.warning("這是一條 WARNING 級別的日誌。")
    logging.error("這是一條 ERROR 級別的日誌。")

    print(f"  內部日誌 (handler_instance.logs): {handler_instance.get_logs(from_ui_store=False)}")
    print(f"  UI 日誌 (st.session_state['{UI_LOG_KEY}']): {st.session_state.get(UI_LOG_KEY)}")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            print(f"  檔案日誌內容 ({LOG_FILE}):\n{f.read().strip()}")

    # 測試2: 清除日誌
    print("\n[測試 2: 清除日誌]")
    handler_instance.clear_logs(clear_ui_store=True)
    print(f"  清除後 - 內部日誌: {handler_instance.get_logs(from_ui_store=False)}")
    print(f"  清除後 - UI 日誌: {st.session_state.get(UI_LOG_KEY)}")
    logging.info("日誌清除後的測試訊息。") # 這條應該會重新出現

    # 測試3: 僅 UI 日誌 (INFO 級別)
    print("\n[測試 3: 僅 UI 日誌 (INFO)]")
    handler_no_file = setup_logging(log_level=logging.INFO, streamlit_ui_log_key=UI_LOG_KEY)
    logging.debug("這條 DEBUG 日誌不應出現 (級別 INFO)。")
    logging.info("這條 INFO 日誌應該出現在 UI 和控制台。")
    print(f"  UI 日誌: {st.session_state.get(UI_LOG_KEY)}") # 應該包含上一條和這一條 INFO

    # 測試4: 僅檔案和控制台日誌 (ui_log_key=None)
    print("\n[測試 4: 僅檔案和控制台日誌 (ui_log_key=None)]")
    st.session_state[UI_LOG_KEY] = ["之前的UI日誌不應被修改"] # 預設值
    handler_no_ui = setup_logging(log_level=logging.INFO, log_file_path=LOG_FILE, streamlit_ui_log_key=None)
    logging.info("這條 INFO 日誌應寫入檔案和控制台，但不影響 UI。")
    print(f"  UI 日誌 (應未改變): {st.session_state.get(UI_LOG_KEY)}")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f_content:
            print(f"  檔案日誌應包含新條目 (檢查 {LOG_FILE})")
            # print(f.read()) # 打印出來會比較長

    # 恢復原始的 st 對象 (如果後續還有代碼依賴它)
    st = _st_original
    print("\n--- 日誌工具測試完畢 ---")
    pass
