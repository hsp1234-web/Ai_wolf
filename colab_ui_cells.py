# Colab Cell 1: Installation and Imports
# Comments are in English to prevent any parsing issues.
# !pip install --upgrade streamlit google-generativeai yfinance pandas fredapi requests ipywidgets Pillow &> /dev/null
# print("✅ Necessary packages checked/installed.")
#
# import ipywidgets as widgets
# from IPython.display import display, clear_output, HTML, Javascript
# import subprocess
# import os
# import sys
# import time
# import threading
# import re
# import importlib
#
# if not os.path.exists("wolf_debugger.py"):
#     print("❌ ERROR: wolf_debugger.py not found. Please ensure it was created in the previous step.")
# else:
#     print("✅ wolf_debugger.py found.")
#
# if 'wolf_debugger' in sys.modules:
#     importlib.reload(sys.modules['wolf_debugger'])
#     print("🔄 wolf_debugger module reloaded.")
# else:
#     import wolf_debugger
#     print("wolf_debugger module imported.")

# Colab Cell 2: Google Drive Mount Option and Project Configuration
# use_gdrive_checkbox = widgets.Checkbox(
#     value=False,
#     description='Mount and use Google Drive?',
#     disabled=False,
#     indent=False,
#     style={'description_width': 'initial'}
# )
# project_name_text = widgets.Text(
#     value='wolfAI',
#     placeholder='Enter project directory name here',
#     description='Project Directory Name:',
#     disabled=False,
#     style={'description_width': 'initial'}
# )
#
# # Placeholder for drive instructions.
# # The complex HTML block is removed to prevent syntax errors.
# # You can add detailed instructions in a separate Markdown cell in your Colab Notebook.
# print("--- Google Drive Configuration Guide ---")
# print("If 'Mount and use Google Drive?' is checked:")
# print("  - Logs and app.py will be in /content/drive/MyDrive/<Project Directory Name>/.")
# print("If not checked:")
# print("  - Operations will use /content/<Project Directory Name>/ (temporary storage).")
# print("Please enter your desired directory name in 'Project Directory Name'.")
# print("--- End of Guide ---")
#
# display(use_gdrive_checkbox, project_name_text)
# print("\nⓘ Configure Google Drive and Project Name settings above before proceeding to Cell 3.")

# Colab Cell 3: Main Control Buttons and Log Output Area

# --- Button Definitions ---
# btn_run_debugger = widgets.Button(description="🔍 啟動除錯模式", button_style='info', icon='search',
#                                   tooltip='Run all debug tests based on current Drive/Project settings')
# btn_launch_server_initial = widgets.Button(description="🚀 啟動服務器 (步驟1)", button_style='success', icon='rocket',
#                                            tooltip='Begin the server launch sequence')
# btn_confirm_launch_server = widgets.Button(description="✅ 確認啟動服務器 (步驟2)", button_style='warning', icon='check', visible=False,
#                                            tooltip='Confirm and execute Streamlit server launch')
# btn_open_app = widgets.Button(description="🔗 打開應用 (URL將顯示於此)", button_style='primary', icon='link', visible=False,
#                               layout=widgets.Layout(width='auto'), tooltip='Open the launched Streamlit application')
# btn_stop_server = widgets.Button(description="🛑 停止服務器", button_style='danger', icon='stop', visible=False,
#                                  tooltip='Attempt to stop the running Streamlit server')
#
# # --- Output Areas for Logs ---
# out_debug_logs = widgets.Output(layout={'border': '1px solid lightblue', 'padding': '5px', 'max_height': '450px', 'overflow_y': 'auto'})
# out_server_logs = widgets.Output(layout={'border': '1px solid lightgreen', 'padding': '5px', 'max_height': '450px', 'overflow_y': 'auto'})
#
# log_accordion = widgets.Accordion(children=[out_debug_logs, out_server_logs])
# log_accordion.set_title(0, '除錯模式日誌 (Debug Mode Logs)')
# log_accordion.set_title(1, '服務器模式日誌 (Server Mode Logs)')
#
# # --- Global variables for server process and URL monitoring ---
# streamlit_process_global = None
# streamlit_url_global = None
# monitor_thread_global = None
# stop_monitor_event = threading.Event()
#
# # --- Button Click Handler Functions ---
# def run_debugger_action(button_instance):
#     with out_debug_logs:
#         clear_output(wait=True)
#         display(HTML("<h4>🔍 執行除錯模式中... (Executing Debug Mode...)</h4>"))
#         print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         current_use_gdrive = use_gdrive_checkbox.value
#         current_project_name = project_name_text.value if project_name_text.value else "wolfAI"
#         try:
#             if 'wolf_debugger' in sys.modules: importlib.reload(sys.modules['wolf_debugger'])
#             else: import wolf_debugger
#             wolf_debugger.initialize_paths(use_gdrive=current_use_gdrive, project_dir_name=current_project_name)
#             results = wolf_debugger.run_all_tests(use_gdrive=current_use_gdrive, project_dir_name=current_project_name)
#             print(f"\n✅ 除錯模式執行完畢. 請檢查上方詳細日誌. Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         except Exception as e:
#             print(f"❌ 在執行除錯模式時發生未預期錯誤 (Unexpected error during debug mode): {e}")
#             import traceback; traceback.print_exc()
#
# def launch_server_step1_action(button_instance):
#     with out_server_logs:
#         clear_output(wait=True)
#         display(HTML("<h4>🚀 服務器啟動 - 步驟 1 (Server Launch - Step 1)</h4>"))
#         print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         print("⏳ 服務器準備啟動，請等待約 5 秒... (Preparing server launch, please wait approx. 5 seconds...)")
#     btn_launch_server_initial.disabled = True
#     btn_run_debugger.disabled = True
#     time.sleep(5)
#     with out_server_logs:
#         print("👉 請點擊「確認啟動服務器 (步驟2)」按鈕來實際啟動服務.")
#         print("(Please click 'Confirm Server Launch (Step 2)' to actually start the service.)")
#     btn_confirm_launch_server.visible = True
#     btn_open_app.visible = False
#     btn_stop_server.visible = False
#     btn_launch_server_initial.disabled = False
#     btn_run_debugger.disabled = False
#
# def find_url_in_streamlit_output(line_of_output):
#     url_patterns = [
#         r"URL: (https://\S+\.ngrok-free\.app)",
#         r"URL: (https://\S+\.ngrok\.io)",
#         r"External URL: (https://\S+)",
#         r"Network URL: (http://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+)"
#     ]
#     for pattern in url_patterns:
#         match = re.search(pattern, line_of_output)
#         if match: return match.group(1)
#     return None
#
# def streamlit_output_monitor_func(process, output_area):
#     global streamlit_url_global, btn_open_app, btn_stop_server
#     stop_monitor_event.clear()
#     if not process or not process.stdout:
#         with output_area: print("❌ Error: Streamlit process or its stdout is not available for monitoring.")
#         return
#     for line_bytes in iter(process.stdout.readline, b''):
#         if stop_monitor_event.is_set():
#             with output_area: print("🛑 Output monitoring thread received stop signal and is terminating.")
#             break
#         line_str = line_bytes.decode('utf-8', errors='replace').strip()
#         with output_area: print(line_str)
#         if not streamlit_url_global:
#             url = find_url_in_streamlit_output(line_str)
#             if url:
#                 streamlit_url_global = url
#                 btn_open_app.description = f"🔗 打開應用: {streamlit_url_global}"
#                 btn_open_app.visible = True
#                 btn_stop_server.visible = True
#                 try: btn_open_app.on_click(None, remove=True)
#                 except: pass
#                 def open_app_action(b, captured_url=streamlit_url_global):
#                     display(Javascript(f'window.open("{captured_url}", "_blank");'))
#                     with output_area: display(HTML(f'<i>Attempting to open <a href="{captured_url}" target="_blank">{captured_url}</a> in a new tab...</i>'))
#                 btn_open_app.on_click(open_app_action)
#                 with output_area:
#                     print(f"🎉 偵測到 Streamlit URL (Detected Streamlit URL): {streamlit_url_global}")
#                     display(HTML(f'<p style="font-size:large; background-color:yellow; padding:5px;"><b>應用程式網址 (App URL):</b> <a href="{streamlit_url_global}" target="_blank" style="color:blue;">{streamlit_url_global}</a></p>'))
#         if process.poll() is not None: break
#     with output_area: print("ℹ️ Streamlit process has ended or output monitoring was stopped.")
#     btn_confirm_launch_server.disabled = False
#     btn_launch_server_initial.disabled = False
#     btn_run_debugger.disabled = False
#     if not streamlit_process_global or streamlit_process_global.poll() is not None:
#         btn_stop_server.visible = False
#
# def launch_server_step2_action(button_instance):
#     global streamlit_process_global, streamlit_url_global, monitor_thread_global
#     with out_server_logs:
#         clear_output(wait=True)
#         display(HTML("<h4>🚀 服務器啟動 - 步驟 2 (Server Launch - Step 2)</h4>"))
#         print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         print("🚀 正在啟動 Streamlit 服務器... (Launching Streamlit server...)")
#     btn_confirm_launch_server.disabled = True; btn_launch_server_initial.disabled = True; btn_run_debugger.disabled = True
#     btn_open_app.visible = False; btn_stop_server.visible = False; streamlit_url_global = None
#     current_use_gdrive = use_gdrive_checkbox.value
#     current_project_name = project_name_text.value if project_name_text.value else "wolfAI"
#     if 'wolf_debugger' in sys.modules: importlib.reload(sys.modules['wolf_debugger'])
#     else: import wolf_debugger
#     wolf_debugger.initialize_paths(use_gdrive=current_use_gdrive, project_dir_name=current_project_name)
#     app_py_actual_path = wolf_debugger.APP_PY_PATH
#     if not os.path.exists(app_py_actual_path):
#         with out_server_logs:
#             print(f"❌ 錯誤: Streamlit 應用程式 'app.py' 未在預期路徑找到: {app_py_actual_path}.")
#             print("請確保 'app.py' 存在於您的專案目錄中.")
#         btn_confirm_launch_server.disabled = False; btn_launch_server_initial.disabled = False; btn_run_debugger.disabled = False
#         return
#     try:
#         streamlit_cmd = [sys.executable, "-m", "streamlit", "run", app_py_actual_path, "--server.headless", "true", "--server.port", "0", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false", "--global.developmentMode", "false"]
#         streamlit_env = os.environ.copy()
#         streamlit_env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"; streamlit_env["STREAMLIT_SERVER_HEADLESS"] = "true"
#         streamlit_process_global = subprocess.Popen(streamlit_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=streamlit_env)
#         with out_server_logs: print(f"⏳ Streamlit process started (PID: {streamlit_process_global.pid}). Monitoring output for URL...")
#         stop_monitor_event.clear()
#         monitor_thread_global = threading.Thread(target=streamlit_output_monitor_func, args=(streamlit_process_global, out_server_logs))
#         monitor_thread_global.daemon = True
#         monitor_thread_global.start()
#     except FileNotFoundError:
#         with out_server_logs:
#             print("❌ 錯誤: `streamlit` 命令執行失敗. 請確保 Streamlit 已正確安裝並且在系統 PATH 中.")
#         btn_confirm_launch_server.disabled = False; btn_launch_server_initial.disabled = False; btn_run_debugger.disabled = False
#     except Exception as e:
#         with out_server_logs:
#             print(f"❌ 啟動 Streamlit 時發生未預期錯誤 (Unexpected error launching Streamlit): {e}")
#             import traceback; traceback.print_exc()
#         btn_confirm_launch_server.disabled = False; btn_launch_server_initial.disabled = False; btn_run_debugger.disabled = False
#
# def stop_server_action(button_instance):
#     global streamlit_process_global, streamlit_url_global, monitor_thread_global
#     with out_server_logs:
#         print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         print("🛑 正在嘗試停止 Streamlit 服務器... (Attempting to stop Streamlit server...)")
#     stop_monitor_event.set()
#     if monitor_thread_global and monitor_thread_global.is_alive():
#         monitor_thread_global.join(timeout=2)
#         if monitor_thread_global.is_alive():
#             with out_server_logs: print("⚠️ Monitor thread did not stop in time.")
#     if streamlit_process_global and streamlit_process_global.poll() is None:
#         try:
#             streamlit_process_global.terminate(); streamlit_process_global.wait(timeout=5)
#             with out_server_logs: print("✅ Streamlit 服務器已成功終止 (SIGTERM).")
#         except subprocess.TimeoutExpired:
#             with out_server_logs: print("⚠️ Streamlit 服務器未在5秒內響應終止信號，將嘗試強制停止 (SIGKILL)...")
#             streamlit_process_global.kill(); streamlit_process_global.wait()
#             with out_server_logs: print("✅ Streamlit 服務器已被強制停止 (SIGKILL).")
#         except Exception as e:
#             with out_server_logs: print(f"❌ 停止 Streamlit 時發生錯誤 (Error stopping Streamlit): {e}")
#     else:
#         with out_server_logs: print("ℹ️ Streamlit 服務器似乎已經停止或未曾成功運行.")
#     streamlit_process_global = None; streamlit_url_global = None; monitor_thread_global = None
#     btn_confirm_launch_server.disabled = False; btn_launch_server_initial.disabled = False; btn_run_debugger.disabled = False
#     btn_open_app.visible = False; btn_stop_server.visible = False
#
# # --- Register Button Click Actions ---
# btn_run_debugger.on_click(run_debugger_action)
# btn_launch_server_initial.on_click(launch_server_step1_action)
# btn_confirm_launch_server.on_click(launch_server_step2_action)
# btn_stop_server.on_click(stop_server_action)
#
# # --- Display UI Layout ---
# button_group_1 = widgets.HBox([btn_run_debugger, btn_launch_server_initial])
# button_group_2 = widgets.HBox([btn_confirm_launch_server, btn_stop_server, btn_open_app])
# ui_layout = widgets.VBox([button_group_1, button_group_2, HTML("<hr style='margin: 15px 0;'><h3>📜 日誌輸出區域 (Log Output Area):</h3>"), log_accordion])
# display(ui_layout)
#
# # Initial messages in the log areas
# with out_server_logs:
#     display(HTML("<h4>🚀 服務器啟動流程 (Server Launch Process)</h4>"))
#     print("ℹ️ 請先在上方「儲存格 2」中配置 Google Drive 和專案名稱設定.")
#     print("   然後點擊相關按鈕開始操作. 日誌將顯示於此.")
# with out_debug_logs:
#     display(HTML("<h4>🔍 除錯模式日誌 (Debug Mode Logs)</h4>"))
#     print("ℹ️ 點擊「啟動除錯模式」按鈕以開始執行所有檢查.")
#
# # Note: Because this is a .py file, lines starting with `!` (shell commands)
# # and `display()` calls (IPython specific) are commented out.
# # You will need to uncomment them or adapt them when pasting into a Colab notebook.
# # For example, `!pip install` becomes a shell command in a Colab cell.
# # `display(widget)` works in Colab directly.
# # `import wolf_debugger` will work if `wolf_debugger.py` is in the same directory
# # or in sys.path in the Colab environment.
#
# # For the `display(Javascript(...))` parts, ensure that the Colab environment
# # can execute Javascript from Python cells, which is typical.
#
# # The HTML parts like `display(HTML(...))` should also work fine in Colab.
#
# # Remember to create a separate Markdown cell in Colab for the detailed
# # `drive_instructions` HTML that was removed from Cell 2.
#
# print("--- colab_ui_cells.py created successfully ---")
# print("This file contains the Python code for the three Colab UI cells.")
# print("Please copy and paste the content of each cell into your Colab Notebook.")
# print("Remember to handle '!pip install' and other Colab-specific commands appropriately.")
# print("The detailed HTML for drive instructions should be placed in a separate Markdown cell in Colab.")
#
# # End of colab_ui_cells.py
