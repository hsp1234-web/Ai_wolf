# === Ai_wolf 專案啟動 ===
# Cell 2: 在 Cell 1 成功執行後，執行此儲存格來啟動 Streamlit 應用程式。

# --- 檢查 app.py 是否存在 (可選，Cell 1 已做過) ---
# GDRIVE_PROJECT_DIR="/content/drive/MyDrive/wolfAI"
# APP_PY_PATH="${GDRIVE_PROJECT_DIR}/app.py"
# if [ ! -f "${APP_PY_PATH}" ]; then
#     print(f"❌ 錯誤：找不到應用程式檔案 {APP_PY_PATH}")
#     print("請先確保 Cell 1 已成功執行，並且專案檔案已正確下載到您的 Google Drive。")
# else
#     print(f"找到應用程式檔案: {APP_PY_PATH}")
#     print("準備啟動 Streamlit 應用程式...")
#     !streamlit run "${APP_PY_PATH}" --server.port 8501
# fi

# 簡化版：直接執行，Cell 1 應確保檔案已就緒
print("🚀 正在啟動 Streamlit 應用程式...")
print("請點擊 Colab 輸出中出現的 `https://*.googleusercontent.com/proxy/8501/` 網址來訪問應用。")
!streamlit run "/content/drive/MyDrive/wolfAI/app.py" --server.port 8501
