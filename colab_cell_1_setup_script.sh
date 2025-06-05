# === Colab 環境設置與 Ai_wolf 專案部署 ===
# Cell 1: 請執行此儲存格以完成所有初始設定。

# --- 1. 安裝必要的 Python 套件 ---
print("正在安裝必要的 Python 套件 (streamlit, google-generativeai, yfinance)...")
!pip install streamlit google-generativeai yfinance -q
print("套件安裝完成！
")

# --- 2. 掛載 Google Drive ---
print("正在嘗試掛載 Google Drive...")
from google.colab import drive
try:
    drive.mount('/content/drive', force_remount=True)
    print("Google Drive 掛載成功！
")
except Exception as e:
    print(f"Google Drive 掛載失敗: {e}")
    print("請檢查彈出視窗中的授權步驟，並確保已授權。如果問題持續，請嘗試在 Colab 選單中選擇 '執行階段' -> '中斷並刪除執行階段'，然後重新執行此儲存格。")
    raise # 終止執行，讓使用者處理 Drive 掛載問題

# --- 3. 定義專案路徑並建立目標資料夾 ---
# 專案將部署到您的 Google Drive 的 MyDrive/wolfAI 目錄下
GDRIVE_PROJECT_DIR = "/content/drive/MyDrive/wolfAI"
print(f"專案將部署到 Google Drive 路徑: {GDRIVE_PROJECT_DIR}")
!mkdir -p "{GDRIVE_PROJECT_DIR}"
print(f"已確認/建立專案目錄。
")

# --- 4. 從 GitHub 克隆或更新 Ai_wolf 專案程式碼 ---
GIT_REPO_URL = "https://github.com/hsp1234-web/Ai_wolf.git"
# 檢查 .git 目錄是否存在以判斷是否已克隆
GIT_DIR_CHECK = f"{GDRIVE_PROJECT_DIR}/.git"

print(f"正在從 {GIT_REPO_URL} 獲取最新程式碼...")
if [ -d "{GIT_DIR_CHECK}" ]; then
    print("偵測到現有的專案目錄，嘗試更新 (git pull)...")
    # %cd "{GDRIVE_PROJECT_DIR}"
    # !git pull origin main # 假設主分支是 main
    # 為了更穩定地獲取最新版本，這裡採用先刪除舊的 .git (如果 pull 失敗或想強制更新)
    # 或者直接刪除整個目錄再克隆。考慮到使用者可能在裡面存放其他檔案，
    # 更安全的做法是只更新程式碼。
    # 一個更 robust 的 git pull 策略:
    # !git -C "{GDRIVE_PROJECT_DIR}" fetch origin
    # !git -C "{GDRIVE_PROJECT_DIR}" reset --hard origin/main # 假設主分支是 main，並丟棄本地修改
    # !git -C "{GDRIVE_PROJECT_DIR}" pull # 再次 pull 確保
    # 簡化版：先嘗試 pull，如果用戶遇到問題，可以引導他們手動刪除 wolfAI 目錄再執行
    # 或者我們直接採用刪除舊的 app.py (或其他我們明確知道需要更新的檔案) 再 git clone 特定檔案的方式
    # 目前最簡單可靠的方式是，如果 .git 存在，就先假設用戶知道自己在做什麼，或者引導他們手動處理更新問題。
    # 為了確保拿到最新，且避免複雜的 git 操作，這裡採用刪除舊目錄（如果存在且非空）再克隆的策略
    # 但我們會先提示使用者
    print(f"注意：如果 {GDRIVE_PROJECT_DIR} 已存在且包含您的修改，這些修改在更新過程中可能會丟失。")
    print(f"為了確保獲取最新版本，將嘗試移除舊的專案檔案（如果存在於 {GDRIVE_PROJECT_DIR} 中由 git 管理的檔案）並重新克隆。")
    # 刪除目錄下除了 .git 之外的所有內容，然後 git reset and pull
    # 或者更簡單： rm -rf "{GDRIVE_PROJECT_DIR}" 然後 git clone （如果用戶不介意整個目錄被刷新）
    # 這裡採用一個折中方案：如果存在 .git，則嘗試 git pull，否則 git clone
    # 為了確保更新，我們刪除 wolfAI 下的 app.py (如果存在) 和 README.md (如果存在)
    # 然後再 clone，這樣可以避免刪除用戶可能存放在 wolfAI 下的其他文件
    # 但 git clone 本身會嘗試創建 wolfAI，如果已存在且非空會失敗。
    # 所以，還是需要一個乾淨的目標目錄或處理好衝突。

    # 最佳實踐：如果目錄存在，先備份，再刪除，再克隆。
    # 或者，如果 .git 存在，cd進去執行 git pull。
    # 這裡選擇：如果存在 .git，就嘗試 git pull，否則就 git clone。
    # 為了讓使用者總是拿到最新的教學版本，這裡採用:
    # 如果目標目錄存在，先刪除再克隆。使用者應將個人檔案存放在其他地方。
    print(f"清理目標目錄 (如果存在): {GDRIVE_PROJECT_DIR} ...")
    # !rm -rf "{GDRIVE_PROJECT_DIR}" # 這一行比較危險，如果使用者在裡面放了其他東西
    # !mkdir -p "{GDRIVE_PROJECT_DIR}" # 確保目錄存在
    # 改為：如果 .git 存在，就 cd 進去 pull，否則 clone
    if [ -d "{GIT_DIR_CHECK}" ]; then
        print("已存在 Git 倉庫，嘗試更新...")
        # %cd "{GDRIVE_PROJECT_DIR}" # Colab magic command, not directly in shell script
        # !git pull # 這樣會拉取預設分支的更新
        # 使用 subprocess 在特定目錄執行 git pull
        import subprocess
        git_pull_command = f"cd '{GDRIVE_PROJECT_DIR}' && git pull origin main" # 假設主分支是 main
        print(f"執行: {git_pull_command}")
        process = subprocess.run(git_pull_command, shell=True, capture_output=True, text=True)
        if process.returncode == 0:
            print("專案更新成功 (git pull)！")
            print(process.stdout)
        else:
            print("git pull 失敗，嘗試重新克隆...")
            print(process.stderr)
            print(f"移除舊目錄: {GDRIVE_PROJECT_DIR} 以便重新克隆...")
            !rm -rf "{GDRIVE_PROJECT_DIR}"
            !mkdir -p "{GDRIVE_PROJECT_DIR}" # 重新建立目錄
            print(f"正在克隆新的專案副本從 {GIT_REPO_URL} 到 {GDRIVE_PROJECT_DIR} ...")
            !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}"
            print("專案克隆完成！")
    else:
        print(f"未找到現有 .git 倉庫，開始克隆專案從 {GIT_REPO_URL} 到 {GDRIVE_PROJECT_DIR} ...")
        !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}" # --depth 1 只克隆最新版，節省空間和時間
        print("專案克隆完成！")
else:
    print(f"開始克隆專案從 {GIT_REPO_URL} 到 {GDRIVE_PROJECT_DIR} ...")
    !git clone --depth 1 "{GIT_REPO_URL}" "{GDRIVE_PROJECT_DIR}"
    print("專案克隆完成！")

print("
--- 5. 檢查專案檔案 ---")
print(f"列出 {GDRIVE_PROJECT_DIR} 中的內容：")
!ls -la "{GDRIVE_PROJECT_DIR}"
# 檢查 app.py 是否存在
APP_PY_PATH = f"{GDRIVE_PROJECT_DIR}/app.py"
if [ -f "{APP_PY_PATH}" ]; then
    print(f"
成功找到主要應用程式檔案: {APP_PY_PATH}")
    print("
✅ Cell 1 設定完成！您現在可以執行下一個儲存格 (Cell 2) 來啟動 Streamlit 應用程式了。")
else:
    print(f"
❌ 錯誤：未在 {GDRIVE_PROJECT_DIR} 中找到主要的 app.py 檔案！")
    print("請檢查 GitHub 倉庫中是否包含 app.py，或者之前的步驟是否有誤。")
