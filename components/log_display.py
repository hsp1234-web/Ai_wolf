# components/log_display.py
import streamlit as st
import logging
from config.app_settings import LOG_DISPLAY_HEIGHT # Import specific setting

logger = logging.getLogger(__name__)

def render_log_viewer():
    """
    渲染應用程式日誌查看器。
    從 st.session_state.log_handler 獲取日誌並在可展開區域中顯示。
    提供一個按鈕來清除已顯示的日誌。
    """
    logger.info("日誌顯示：開始渲染日誌查看器 (render_log_viewer)。")
    st.markdown("---") # 分隔線

    with st.expander("📄 應用程式日誌 (Application Logs)", expanded=False):
        logger.debug("日誌顯示：日誌查看器 expander 已創建。")
        ui_logs_from_state = st.session_state.get('ui_logs', []) # 從 session_state 獲取

        if not isinstance(ui_logs_from_state, list):
            logger.error(f"日誌顯示：session_state 中的 'ui_logs' 不是列表 (實際類型: {type(ui_logs_from_state)})。將顯示為空日誌。")
            ui_logs_to_display = []
            st.warning("日誌數據格式錯誤，無法顯示。")
        else:
            ui_logs_to_display = ui_logs_from_state
            logger.debug(f"日誌顯示：從 session_state['ui_logs'] 獲取到 {len(ui_logs_to_display)} 條日誌記錄。")


        log_text_display = "\\n".join(reversed(ui_logs_to_display))

        st.text_area(
            "日誌內容 (最新的在最上方):",
            value=log_text_display,
            height=app_settings.LOG_DISPLAY_HEIGHT,
            key="ui_log_display_text_area",
            disabled=True,
            help="此處顯示應用程式運行時的 UI 相關日誌。詳細的後端日誌請查看控制台或日誌檔案。"
        )

        if st.button("清除顯示的日誌", key="clear_ui_logs_button"):
            logger.info("日誌顯示：用戶點擊 '清除顯示的日誌' 按鈕。")
            if 'ui_logs' in st.session_state and isinstance(st.session_state.get('ui_logs'), list):
                original_log_count = len(st.session_state.ui_logs)
                st.session_state.ui_logs = [] # 清除 UI 日誌列表
                logger.info(f"日誌顯示：已清除 st.session_state.ui_logs (原 {original_log_count} 條)。")
                st.success("顯示的日誌已清除。")
            else:
                logger.warning("日誌顯示：嘗試清除 UI 日誌，但 'ui_logs' 未在 session_state 中找到或格式不正確。")
                st.warning("無法清除 UI 日誌：日誌列表未正確初始化。")

            # 關於是否同時清除 StreamlitLogHandler 內部緩存 (self.logs):
            # StreamlitLogHandler 的 clear_logs 方法現在有一個 clear_ui_store 參數。
            # 如果我們在這裡清除了 st.session_state.ui_logs，
            # 並且 StreamlitLogHandler 的主要目的是填充這個 ui_logs，
            # 那麼可能不需要再單獨調用 log_handler.clear_logs(clear_ui_store=False)。
            # 但如果 StreamlitLogHandler 的 self.logs 有獨立用途（例如更長期的內存記錄），則可以選擇保留。
            # 目前的設計是 StreamlitLogHandler 主要服務於 UI，所以清除 ui_logs 即可。
            # 如果需要，可以取消註釋以下代碼：
            # if 'log_handler' in st.session_state and hasattr(st.session_state.log_handler, 'clear_logs'):
            #     logger.debug("日誌顯示：同時請求 StreamlitLogHandler 清除其內部緩存 (但不影響已手動清除的 ui_logs)。")
            #     st.session_state.log_handler.clear_logs(clear_ui_store=False) # clear_ui_store=False 避免重複操作或錯誤

            st.rerun()

    logger.info("日誌顯示：日誌查看器渲染結束 (render_log_viewer)。")

if __name__ == "__main__":
    # 為了測試，模擬 Streamlit 環境和 session_state
    # class MockLogHandler:
    #     def __init__(self): self.logs = ["Log entry 1", "Log entry 2 - some error", "Log entry 3 - more info"]
    #     def get_logs(self): return self.logs
    #     def clear_logs(self): self.logs = []; print("Mock logs cleared.")

    # class MockSessionState:
    #     def __init__(self, initial_state=None): self._state = initial_state if initial_state else {}
    #     def get(self, key, default=None): return self._state.get(key, default)
    #     def __setitem__(self, key, value): self._state[key] = value
    #     def __getitem__(self, key): return self._state[key]
    #     def __contains__(self, key): return key in self._state
    #     def update(self, d): self._state.update(d)

    # st.session_state = MockSessionState({"log_handler": MockLogHandler()})

    # st.markdown = print
    # st.expander = lambda label, expanded: MockExpander(label, expanded)
    # st.text_area = lambda label, value, height, key, disabled, help: print(f"---Log Area---\n{value}\n---End Log Area---")
    # st.button = lambda label, key: MockButton(label, key) # 簡易模擬
    # st.success = print
    # st.warning = print
    # st.error = print
    # st.rerun = lambda: print("--- ST.RERUN CALLED (Log Display) ---")

    # class MockExpander:
    #     def __init__(self, label, expanded): print(f"Expander: {label}, Expanded: {expanded}")
    #     def __enter__(self): return self
    #     def __exit__(self, type, value, traceback): pass

    # class MockButton:
    #     def __init__(self, label, key): self.label = label; print(f"Button created: {label}")
    #     def __call__(self): # 模擬按鈕點擊
    #         if self.label == "清除日誌顯示":
    #             st.session_state.log_handler.clear_logs()
    #             st.rerun()
    #         return True

    # print("--- Rendering Log Viewer ---")
    # render_log_viewer()
    # print("--- Simulating Clear Logs Button Click ---")
    # # 模擬按鈕點擊 (在真實Streamlit中，這是由用戶互動觸發的)
    # # if st.button("清除日誌顯示", key="clear_displayed_logs_button"): # 這行不會在腳本模式下執行
    # #    st.session_state.log_handler.clear_logs()
    # #    st.rerun()
    # # 手動調用模擬按鈕的行為
    # clear_button = MockButton("清除日誌顯示", "clear_displayed_logs_button")
    # clear_button() # 觸發清除和重跑
    # print("--- Rendering Log Viewer After Clear ---")
    # render_log_viewer()
    pass
