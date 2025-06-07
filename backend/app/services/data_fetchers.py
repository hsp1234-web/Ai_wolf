# services/data_fetchers.py
# import streamlit as st # Removed Streamlit import
import pandas as pd
import yfinance as yf
from datetime import datetime
from fredapi import Fred
import requests
import io
import logging
# Assuming app_settings.py contents are moved to backend/app/config/settings.py
from ..config.settings import NY_FED_POSITIONS_URLS, SBP_XML_SUM_COLS_CONFIG
from ..config.settings import YFINANCE_CACHE_TTL_SECONDS, FRED_CACHE_TTL_SECONDS, NY_FED_REQUEST_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)

# @st.cache_data(ttl=YFINANCE_CACHE_TTL_SECONDS) # Decorator removed
def fetch_yfinance_data(tickers_str: str, start_date_str: str, end_date_str: str, interval: str):
    """
    從 Yahoo Finance 獲取指定股票代碼的歷史數據。
    # TODO: Implement caching for this function in the API layer or via a dedicated caching library.

    Args:
        tickers_str (str): 以逗號分隔的股票代碼字符串。
        start_date_str (str): 開始日期字符串 (YYYYMMDD)。
        end_date_str (str): 結束日期字符串 (YYYYMMDD)。
        interval (str): yfinance 數據間隔 (例如 "1d", "1wk")。

    Returns:
        tuple: (data_frames, errors)
               data_frames (dict): 包含每個股票代碼 DataFrame 的字典。
               errors (list): 獲取數據過程中發生的錯誤列表。
    """
    logger.info(f"開始執行 fetch_yfinance_data。參數 - Tickers: '{tickers_str}', 開始日期: {start_date_str}, 結束日期: {end_date_str}, 間隔: '{interval}'")
    # Note: YFINANCE_CACHE_TTL_SECONDS is imported but not used here as caching is removed.
    data_frames = {}
    errors = []

    if not tickers_str.strip():
        msg = "YFinance 錯誤：Ticker 字串不可為空。"
        errors.append(msg)
        logger.error(msg)
        return data_frames, errors

    list_of_tickers = [ticker.strip().upper() for ticker in tickers_str.split(',') if ticker.strip()]
    if not list_of_tickers:
        msg = "YFinance 錯誤：未提供有效的 Ticker。"
        errors.append(msg)
        logger.error(msg)
        return data_frames, errors
    logger.debug(f"已解析的 YFinance Ticker 列表: {list_of_tickers}")

    try:
        start_dt = datetime.strptime(start_date_str, "%Y%m%d")
    except ValueError as e_start:
        msg = f"YFinance 錯誤：開始日期格式無效 '{start_date_str}'。應為 YYYYMMDD。詳細錯誤: {e_start}"
        errors.append(msg)
        logger.error(msg)
        return data_frames, errors
    try:
        end_dt = datetime.strptime(end_date_str, "%Y%m%d")
    except ValueError as e_end:
        msg = f"YFinance 錯誤：結束日期格式無效 '{end_date_str}'。應為 YYYYMMDD。詳細錯誤: {e_end}"
        errors.append(msg)
        logger.error(msg)
        return data_frames, errors

    if start_dt > end_dt:
        msg = f"YFinance 錯誤：開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。"
        errors.append(msg)
        logger.error(msg)
        return data_frames, errors

    for ticker in list_of_tickers:
        logger.info(f"開始下載 YFinance ticker: '{ticker}' (日期範圍: {start_date_str} - {end_date_str}, 間隔: {interval})")
        try:
            df = yf.download(ticker, start=start_dt, end=end_dt, interval=interval, progress=False)
            if df.empty:
                msg = f"YFinance 警告：Ticker '{ticker}' 在指定日期範圍內沒有找到數據。"
                errors.append(msg)
                logger.warning(msg)
            else:
                df.reset_index(inplace=True)
                # 處理 yfinance 可能返回 MultiIndex 的情況
                if isinstance(df.columns, pd.MultiIndex):
                    logger.info(f"YFinance ticker '{ticker}': 檢測到 MultiIndex 列，正在進行扁平化處理。原始列: {df.columns.tolist()}")
                    # 確保列名中的每個元素都是字符串，然後再連接
                    df.columns = ['_'.join(map(str, col)).strip() if isinstance(col, tuple) else str(col).strip() for col in df.columns.values]
                    logger.info(f"YFinance ticker '{ticker}': MultiIndex 列已扁平化。處理後列: {df.columns.tolist()}")
                else:
                    df.columns = df.columns.astype(str)

                data_frames[ticker] = df
                logger.info(f"成功下載 YFinance ticker '{ticker}' 的數據，共 {len(df)} 行。")
        except Exception as e:
            msg = f"YFinance 錯誤：下載 Ticker '{ticker}' 數據時發生錯誤: {type(e).__name__} - {str(e)}"
            errors.append(msg)
            logger.error(msg, exc_info=True)

    logger.info(f"YFinance 數據獲取流程結束。成功獲取 {len(data_frames)} 個 Ticker 的數據。共發生 {len(errors)} 個錯誤/警告。")
    return data_frames, errors

# @st.cache_data(ttl=FRED_CACHE_TTL_SECONDS) # Decorator removed
def fetch_fred_data(series_ids_str: str, start_date_str: str, end_date_str: str, api_key: str):
    """
    從 FRED (Federal Reserve Economic Data) 獲取指定經濟序列的數據。日誌記錄已添加。
    # TODO: Implement caching for this function in the API layer or via a dedicated caching library.

    Args:
        series_ids_str (str): 以逗號分隔的 FRED Series ID 字符串。
        start_date_str (str): 開始日期字符串 (YYYYMMDD)。
        end_date_str (str): 結束日期字符串 (YYYYMMDD)。
        api_key (str): FRED API 金鑰。

    Returns:
        tuple: (data_series_dict, errors)
               data_series_dict (dict): 包含每個 Series ID DataFrame 的字典。
               errors (list): 獲取數據過程中發生的錯誤列表。
    """
    logger.info(f"開始執行 fetch_fred_data。參數 - Series IDs: '{series_ids_str}', 開始日期: {start_date_str}, 結束日期: {end_date_str}, API金鑰提供情況: {'是' if api_key else '否'}")
    # Note: FRED_CACHE_TTL_SECONDS is imported but not used here as caching is removed.
    data_series_dict = {}
    errors = []

    if not api_key:
        msg = "FRED 錯誤：API 金鑰未提供。"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors

    try:
        logger.debug("正在初始化 Fred 客戶端...")
        fred = Fred(api_key=api_key)
        logger.debug("Fred 客戶端初始化成功。")
    except Exception as e:
        msg = f"FRED 錯誤：API 金鑰初始化失敗: {str(e)}。"
        errors.append(msg)
        logger.error(msg, exc_info=True)
        return data_series_dict, errors

    if not series_ids_str.strip():
        msg = "FRED 錯誤：Series ID 字串不可為空。"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors

    list_of_series_ids = [sid.strip().upper() for sid in series_ids_str.split(',') if sid.strip()]
    if not list_of_series_ids:
        msg = "FRED 錯誤：未提供有效的 Series ID。"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors
    logger.debug(f"已解析的 FRED Series ID 列表: {list_of_series_ids}")

    try:
        start_dt = datetime.strptime(start_date_str, "%Y%m%d")
    except ValueError as e_start:
        msg = f"FRED 錯誤：開始日期格式無效 '{start_date_str}'。應為 YYYYMMDD。詳細錯誤: {e_start}"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors
    try:
        end_dt = datetime.strptime(end_date_str, "%Y%m%d")
    except ValueError as e_end:
        msg = f"FRED 錯誤：結束日期格式無效 '{end_date_str}'。應為 YYYYMMDD。詳細錯誤: {e_end}"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors

    if start_dt > end_dt:
        msg = f"FRED 錯誤：開始日期 ({start_date_str}) 不能晚於結束日期 ({end_date_str})。"
        errors.append(msg)
        logger.error(msg)
        return data_series_dict, errors

    for series_id in list_of_series_ids:
        logger.info(f"開始下載 FRED Series ID: '{series_id}' (日期: {start_date_str} - {end_date_str})")
        try:
            series_data = fred.get_series(series_id, observation_start=start_dt, observation_end=end_dt)
            if series_data.empty:
                msg = f"FRED 警告：Series ID '{series_id}' 在指定日期範圍內沒有找到數據。"
                errors.append(msg)
                logger.warning(msg)
            else:
                df = series_data.to_frame(name=series_id)
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'Date', series_id: 'Value'}, inplace=True)
                df['Date'] = pd.to_datetime(df['Date'])
                df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                df.dropna(subset=['Value'], inplace=True)
                data_series_dict[series_id] = df
                logger.info(f"成功下載 FRED Series ID '{series_id}' 的數據，共 {len(df)} 行。")
        except ValueError as ve:
            msg = f"FRED 錯誤：Series ID '{series_id}' 無效或找不到: {str(ve)}"
            errors.append(msg)
            logger.error(msg, exc_info=True)
        except Exception as e:
            msg = f"FRED 錯誤：下載 Series ID '{series_id}' 數據時發生錯誤: {type(e).__name__} - {str(e)}"
            errors.append(msg)
            logger.error(msg, exc_info=True)

    logger.info(f"FRED 數據獲取流程結束。成功獲取 {len(data_series_dict)} 個 Series 的數據。共發生 {len(errors)} 個錯誤/警告。")
    return data_series_dict, errors


# @st.cache_data(ttl=86400) # Decorator removed, NY_FED_CACHE_TTL_SECONDS is an alias for 86400, kept for consistency if used elsewhere
def fetch_ny_fed_data():
    """
    從紐約聯儲網站獲取主要交易商持倉數據。日誌記錄已添加。
    使用 config.settings 中定義的 NY_FED_POSITIONS_URLS 和 SBP_XML_SUM_COLS_CONFIG。
    # TODO: Implement caching for this function in the API layer or via a dedicated caching library.

    Returns:
        tuple: (final_df, errors)
               final_df (pd.DataFrame or None): 包含合併和處理後的數據的 DataFrame，如果失敗則為 None。
               errors (list): 獲取數據過程中發生的錯誤列表。
    """
    logger.info("開始執行 fetch_ny_fed_data (紐約聯儲數據)。")
    # Note: NY_FED_REQUEST_TIMEOUT_SECONDS is used directly below.
    all_positions_data = []
    errors = []

    HEADER_ROW_ASSUMPTION = 4
    DATE_COLUMN_INDEX_ASSUMPTION = 0
    logger.debug(f"NY Fed 配置 - 表頭行(假設): {HEADER_ROW_ASSUMPTION}, 日期列索引(假設): {DATE_COLUMN_INDEX_ASSUMPTION}")

    for item in NY_FED_POSITIONS_URLS:
        url = item["url"]
        name = item["name"]
        file_type = item.get("type", "excel")

        logger.info(f"開始處理 NY Fed 數據源: '{name}' (類型: {file_type}) 從 URL: {url}")
        try:
            response = requests.get(url, timeout=NY_FED_REQUEST_TIMEOUT_SECONDS) # Use imported constant
            response.raise_for_status()
            logger.debug(f"成功從 URL '{url}' ({name}) 下載數據，狀態碼: {response.status_code}，內容長度: {len(response.content)}")

            if file_type == "xml":
                try:
                    logger.debug(f"開始使用 pandas.read_xml 解析來自 '{url}' ({name}) 的 XML 數據。")
                    df_list = pd.read_xml(io.BytesIO(response.content), parser='lxml')

                    if not isinstance(df_list, list) or not df_list or df_list[0].empty:
                        logger.warning(f"NY Fed XML ({name}) 從 {url} 未解析出有效數據列表或第一個 DataFrame 為空。")
                        errors.append(f"NY Fed XML ({name}) 從 {url} 未解析出數據或數據為空。")
                        continue

                    df = df_list[0]
                    logger.info(f"NY Fed XML ({name}) 解析成功，初步 DataFrame shape: {df.shape}, Columns: {df.columns.tolist()}")

                    if 'asOfDate' in df.columns and ('parAmount' in df.columns or 'quantity' in df.columns):
                        value_col = 'parAmount' if 'parAmount' in df.columns else 'quantity'
                        df.rename(columns={'asOfDate': 'Date', value_col: 'Value'}, inplace=True)
                        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                        df.dropna(subset=['Date', 'Value'], inplace=True)

                        if df.empty:
                            logger.warning(f"NY Fed XML ({name}) 在數據轉換後為空。")
                            errors.append(f"NY Fed XML ({name}) 轉換後無有效數據。")
                            continue

                        daily_sum = df.groupby('Date')['Value'].sum()
                        all_positions_data.append(daily_sum)
                        logger.info(f"成功處理並轉換 NY Fed XML 數據 ({name})，獲取 {len(daily_sum)} 條聚合記錄。")
                    else:
                        logger.warning(f"NY Fed XML ({name}) 從 {url} 缺少預期的日期 ('asOfDate') 或數值 ('parAmount'/'quantity') 列。實際列: {df.columns.tolist()}")
                        errors.append(f"NY Fed XML ({name}) 缺少關鍵數據列，無法處理。")
                        continue

                except Exception as e_xml_parse:
                    msg = f"NY Fed 錯誤：解析 XML 數據 ({name}) 從 {url} 時發生錯誤: {type(e_xml_parse).__name__} - {str(e_xml_parse)}"
                    errors.append(msg)
                    logger.error(msg, exc_info=True)
                    continue

            elif file_type == "excel":
                excel_content = io.BytesIO(response.content)
                xls = pd.ExcelFile(excel_content)
                logger.debug(f"NY Fed Excel ({name}) 成功讀取到 BytesIO。Sheet names: {xls.sheet_names}")

                if not xls.sheet_names:
                    logger.warning(f"NY Fed Excel ({name}) 檔案 '{url}' 不包含任何工作表 (sheets)。")
                    errors.append(f"NY Fed Excel ({name}) 檔案不包含工作表。")
                    continue

                df = pd.read_excel(xls, sheet_name=0, header=HEADER_ROW_ASSUMPTION, index_col=DATE_COLUMN_INDEX_ASSUMPTION)
                logger.info(f"NY Fed Excel ({name}) 初步讀取 shape: {df.shape}, Columns: {df.columns.tolist()}")

                df.index = pd.to_datetime(df.index, errors='coerce')
                df = df[df.index.notna()]
                logger.debug(f"NY Fed Excel ({name}) 日期轉換後 shape: {df.shape}")

                if df.empty:
                    msg = f"NY Fed 警告：Excel 檔案 {url} ({name}) 在轉換日期或初步處理後沒有有效數據。"
                    errors.append(msg)
                    logger.warning(msg)
                    continue

                current_cols_to_sum = []
                matched_sbp_key = next((key for key in SBP_XML_SUM_COLS_CONFIG if key in url), None)
                if matched_sbp_key:
                    # SBP_XML_SUM_COLS_CONFIG is expected to be a dict where values are lists of column names
                    config_cols = SBP_XML_SUM_COLS_CONFIG.get(matched_sbp_key, [])
                    current_cols_to_sum = [col for col in config_cols if col in df.columns]
                    logger.info(f"NY Fed Excel ({name}): 根據 URL 中的 '{matched_sbp_key}'，匹配到的 SBP 列: {current_cols_to_sum}")

                if not current_cols_to_sum and ("SBN" in url or "SOMA" in name): # Fallback for SBN/SOMA if no specific key match
                    current_cols_to_sum = [col for col in df.columns if isinstance(col, str) and col.startswith("PDPOSGSC-")]
                    logger.info(f"NY Fed Excel ({name}): 未匹配到 SBP key，但檢測到 SBN/SOMA 類型，使用通用 PDPOSGSC- 列: {current_cols_to_sum}")

                if not current_cols_to_sum:
                    msg = f"NY Fed 警告：Excel 檔案 {url} ({name}) 中未找到配置的目標欄位 (SBP_XML_SUM_COLS_CONFIG 或通用 PDPOSGSC-)。跳過此檔案。可用列: {df.columns.tolist()}"
                    errors.append(msg)
                    logger.warning(msg)
                    continue

                logger.debug(f"NY Fed Excel ({name}): 最終選擇的加總列: {current_cols_to_sum}")
                df_target = df[current_cols_to_sum].apply(pd.to_numeric, errors='coerce')

                if df_target.isnull().all().all():
                    msg = f"NY Fed 警告：Excel 檔案 {url} ({name}) 的目標欄位 {current_cols_to_sum} 轉換為數字後均為空值。"
                    errors.append(msg)
                    logger.warning(msg)
                    continue

                daily_sum = df_target.sum(axis=1)
                all_positions_data.append(daily_sum)
                logger.info(f"成功處理 NY Fed Excel 數據 ({name}) 從 {url}，生成 {len(daily_sum)} 條日度總和記錄。")

            else:
                msg = f"NY Fed 錯誤：不支持的檔案類型 '{file_type}' 從 URL: {url} ({name})"
                logger.error(msg)
                errors.append(msg)
                continue

        except requests.exceptions.HTTPError as http_err:
            msg = f"NY Fed 錯誤：下載檔案 {url} ({name}) 時發生 HTTP 錯誤: {type(http_err).__name__} - {http_err}"
            errors.append(msg)
            logger.error(msg, exc_info=True)
        except requests.exceptions.RequestException as req_err:
            msg = f"NY Fed 錯誤：下載檔案 {url} ({name}) 時發生請求錯誤: {type(req_err).__name__} - {req_err}"
            errors.append(msg)
            logger.error(msg, exc_info=True)
        except Exception as e:
            msg = f"NY Fed 錯誤：處理檔案 {url} ({name}) 時發生一般錯誤: {type(e).__name__} - {str(e)}"
            errors.append(msg)
            logger.error(msg, exc_info=True)

    if not all_positions_data:
        logger.warning("NY Fed 數據獲取：未能從任何 URL 收集到有效數據。列表為空。")
        return None, errors

    try:
        logger.info(f"開始合併 {len(all_positions_data)} 個 NY Fed 數據序列...")
        final_series = pd.concat(all_positions_data)
        logger.debug(f"NY Fed 數據序列合併後長度: {len(final_series)}")

        final_series = final_series.groupby(final_series.index).last()
        final_series = final_series.sort_index()
        final_series = final_series.ffill()
        logger.info(f"NY Fed 數據序列排序、去重(last)和填充後長度: {len(final_series)}")

        result_df = final_series.to_frame(name="Total_Dealer_Positions")
        result_df.reset_index(inplace=True)
        result_df.rename(columns={'index': 'Date'}, inplace=True)
        logger.info(f"成功合併和處理所有 NY Fed 數據。最終 DataFrame shape: {result_df.shape}。日期範圍: {result_df['Date'].min().strftime('%Y-%m-%d')} 到 {result_df['Date'].max().strftime('%Y-%m-%d') if not result_df.empty else 'N/A'}")
    except Exception as e:
        msg = f"NY Fed 錯誤：合併和最終處理 NY Fed 數據時發生錯誤: {type(e).__name__} - {str(e)}"
        errors.append(msg)
        logger.error(msg, exc_info=True)
        return None, errors

    logger.info(f"NY Fed 數據獲取流程結束。返回 DataFrame shape: {result_df.shape if result_df is not None else 'None'}。共發生 {len(errors)} 個錯誤/警告。")
    return result_df, errors

# if __name__ == "__main__":
    # 簡易測試 (需要 Streamlit 環境和有效的 API Key / 網路連接)
    # # st.session_state.fred_api_key = "YOUR_FRED_KEY" # 替換為你的 FRED key

    # # logger.info("--- 測試 YFinance ---")
    # # yf_data, yf_errs = fetch_yfinance_data("AAPL,MSFT", "20230101", "20230110", "1d")
    # # if yf_errs: print("YFinance Errors:", yf_errs)
    # # if yf_data: print("YFinance AAPL Head:", yf_data.get("AAPL", pd.DataFrame()).head())

    # # logger.info("--- 測試 FRED ---")
    # # fred_api_key_to_test = "YOUR_FRED_API_KEY" # Replace with your actual key for testing
    # # fred_data, fred_errs = fetch_fred_data("GDP,CPIAUCSL", "20220101", "20230101", fred_api_key_to_test)
    # # if fred_errs: print("FRED Errors:", fred_errs)
    # # if fred_data: print("FRED GDP Head:", fred_data.get("GDP", pd.DataFrame()).head())

    # # logger.info("--- 測試 NY Fed ---")
    # # nyfed_df, nyfed_errs = fetch_ny_fed_data()
    # # if nyfed_errs: print("NY Fed Errors:", nyfed_errs)
    # # if nyfed_df is not None: print("NY Fed Data Head:", nyfed_df.head())
    # pass
