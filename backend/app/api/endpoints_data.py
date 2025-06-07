import logging
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from app.services import data_fetchers # Corrected import path
from app.config.settings import FRED_API_KEY # Corrected import path

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class YFinanceRequestParams(BaseModel):
    tickers: str = Field(..., description="以逗號分隔的股票代碼字符串")
    interval: str = Field("1d", description="yfinance 數據間隔 (例如 '1d', '1wk')")

class FredRequestParams(BaseModel):
    seriesIds: str = Field(..., description="以逗號分隔的 FRED Series ID 字符串")

class DataFetchRequest(BaseModel):
    yfinance: Optional[YFinanceRequestParams] = None
    fred: Optional[FredRequestParams] = None
    startDate: str = Field(..., description="開始日期 (YYYYMMDD)", pattern=r"^\d{8}$")
    endDate: str = Field(..., description="結束日期 (YYYYMMDD)", pattern=r"^\d{8}$")
    # ny_fed: bool = Field(False, description="是否獲取 NY Fed 數據") # NY Fed data fetch is slow

class DataFetchResponse(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict, description="獲取到的數據，鍵為數據源名稱")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="獲取數據過程中發生的錯誤，鍵為數據源名稱")

@router.post("/fetch", response_model=DataFetchResponse) # Changed from /data/fetch to /fetch
async def fetch_data_endpoint(request: DataFetchRequest = Body(...)):
    '''
    根據請求參數從不同來源 (yfinance, FRED) 獲取外部數據。
    '''
    logger.info(f"API CALL: POST /api/data/fetch with params: {request.model_dump(exclude_none=True)}")

    response_data: Dict[str, Any] = {}
    response_errors: Dict[str, List[str]] = {}

    try:
        # Validate start and end dates (basic check, more can be added)
        if request.startDate > request.endDate:
            logger.error("無效的日期範圍：開始日期不能晚於結束日期。")
            # This error should ideally be part of the response_errors,
            # or a 400 HTTPException if it's a validation failure before processing.
            # For now, let's make it a general error in the response.
            response_errors.setdefault("validation", []).append("無效的日期範圍：開始日期不能晚於結束日期。")
            return DataFetchResponse(data=response_data, errors=response_errors) # Return early

        # Fetch YFinance data
        if request.yfinance:
            logger.info(f"正在獲取 YFinance 數據: Tickers='{request.yfinance.tickers}', Interval='{request.yfinance.interval}'")
            try:
                yf_data, yf_errors = await data_fetchers.fetch_yfinance_data(
                    tickers_str=request.yfinance.tickers,
                    start_date_str=request.startDate,
                    end_date_str=request.endDate,
                    interval=request.yfinance.interval
                )
                # Convert DataFrame to JSON serializable format (e.g., records)
                response_data["yfinance"] = {ticker: df.to_dict(orient="records") for ticker, df in yf_data.items()}
                if yf_errors: # yf_errors is already a list of strings
                    response_errors.setdefault("yfinance", []).extend(yf_errors)
                logger.info(f"YFinance 數據獲取完成。數據鍵: {list(response_data.get('yfinance', {}).keys())}, 錯誤數: {len(yf_errors)}")
            except Exception as e:
                logger.error(f"獲取 YFinance 數據時發生未預期錯誤: {e}", exc_info=True)
                response_errors.setdefault("yfinance", []).append(f"處理 YFinance 請求時發生內部錯誤: {str(e)}")

        # Fetch FRED data
        if request.fred:
            logger.info(f"正在獲取 FRED 數據: SeriesIDs='{request.fred.seriesIds}'")
            if not FRED_API_KEY:
                logger.warning("FRED API 金鑰未設定，跳過 FRED 數據獲取。")
                response_errors.setdefault("fred", []).append("FRED API 金鑰未在後端設定。")
            else:
                try:
                    # api_key is no longer passed as it's handled by fetch_fred_data internally via settings
                    fred_data, fred_errors = await data_fetchers.fetch_fred_data(
                        series_ids_str=request.fred.seriesIds,
                        start_date_str=request.startDate,
                        end_date_str=request.endDate
                    )
                    # Convert DataFrame to JSON serializable format
                    response_data["fred"] = {sid: df.to_dict(orient="records") for sid, df in fred_data.items()}
                    if fred_errors: # fred_errors is already a list of strings
                        response_errors.setdefault("fred", []).extend(fred_errors)
                    logger.info(f"FRED 數據獲取完成。數據鍵: {list(response_data.get('fred', {}).keys())}, 錯誤數: {len(fred_errors)}")
                except Exception as e:
                    logger.error(f"獲取 FRED 數據時發生未預期錯誤: {e}", exc_info=True)
                    response_errors.setdefault("fred", []).append(f"處理 FRED 請求時發生內部錯誤: {str(e)}")

        # Note: NY Fed data fetching is excluded for this version as per comments in original code.

        if not request.yfinance and not request.fred: # Check if any specific data source was requested
            logger.info("沒有請求特定的數據源 (yfinance, fred)。")
            # Optionally add a general message if no specific data was requested
            # response_errors.setdefault("general", []).append("請指定至少一個數據源 (yfinance 或 fred) 進行獲取。")
            # Or, it's also fine to return empty data/errors if no sources were in the request.
            # The current logic handles this by just returning empty response_data/response_errors if nothing is processed.

    except Exception as e_global: # Catch any other unexpected error during request handling
        logger.error(f"處理 /api/data/fetch 請求時發生全局錯誤: {e_global}", exc_info=True)
        # This ensures a 500 error is not raised directly, but reported in the JSON response.
        # However, for certain validation errors (like date pattern from Pydantic), FastAPI might raise 422 directly.
        response_errors.setdefault("global", []).append(f"處理請求時發生意外的內部錯誤: {str(e_global)}")


    return DataFetchResponse(data=response_data, errors=response_errors)
