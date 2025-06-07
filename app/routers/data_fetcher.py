from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.data_fetcher_schemas import DataFetchRequest, DataFetchResponse
from app.services.external_data_service import fetch_fred_data, ExternalDataError
from app.db.database import get_cached_data, set_cached_data
from app.core.dependencies import get_current_user
from app.schemas.auth_schemas import User # For type hint
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/data", # Router prefix
    tags=["Data Fetching"]
)

@router.post(
    '/fetch',
    response_model=DataFetchResponse,
    summary='Fetch external data (e.g., from FRED) with caching.',
    description='Allows fetching data from supported external sources like FRED. '
                'The data is cached in the database to reduce external API calls.'
)
async def fetch_data_endpoint(
    request_data: DataFetchRequest,
    current_user: User = Depends(get_current_user) # Protected endpoint
):
    source = request_data.source # Already validated and lowercased by Pydantic model
    params = request_data.parameters

    logger.info(
        'Data fetch request received.',
        source=source,
        params=params,
        user_id=current_user.id
    )

    # 1. Try to get data from cache
    cached_data = get_cached_data(source=source, params=params)
    if cached_data is not None:
        logger.info(
            'Data retrieved from cache.',
            source=source,
            params=params,
            user_id=current_user.id
        )
        return DataFetchResponse(
            source=source,
            parameters=params,
            data=cached_data,
            message='Data retrieved from cache.',
            is_cached=True
        )

    logger.info(
        'Data not in cache, fetching from external source.',
        source=source,
        params=params,
        user_id=current_user.id
    )

    # 2. If not in cache, fetch from external source
    fetched_data = None
    try:
        if source == 'fred':
            symbol = params.get('symbol')
            if not isinstance(symbol, str) or not symbol:
                logger.warn("Missing or invalid 'symbol' in parameters for FRED source.", params=params)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Missing or invalid "symbol" (string) in parameters for FRED source.'
                )

            # Pass through other parameters (e.g., observation_start, observation_end)
            fred_api_params = {k: v for k, v in params.items() if k != 'symbol'}
            fetched_data = fetch_fred_data(symbol=symbol, parameters=fred_api_params)
        else:
            # This case should ideally not be reached if Pydantic model validator for source is exhaustive
            logger.error("Encountered unsupported data source post-validation. This should not happen.", source=source)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f'Unsupported data source: {source}')

        # 3. If fetched successfully, store in cache
        if fetched_data is not None:
            # Using default TTL from set_cached_data (1 hour)
            set_cached_data(source=source, params=params, data=fetched_data)
            logger.info(
                'Data fetched from external source and cached successfully.',
                source=source,
                params=params,
                user_id=current_user.id
            )
            return DataFetchResponse(
                source=source,
                parameters=params,
                data=fetched_data,
                message='Data fetched successfully from external source and cached.',
                is_cached=False # Data was fetched now, not from a pre-existing cache entry for this request
            )
        else:
            # This case implies fetch_fred_data (or other future fetchers) returned None without raising an error.
            # This shouldn't happen if the fetcher functions are implemented to always return data or raise.
            logger.error(
                'Fetched data is unexpectedly None without an explicit error raised by the service.',
                source=source,
                params=params,
                user_id=current_user.id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Data fetcher service returned no data and no error.'
            )

    except ExternalDataError as ede:
        logger.warn(
            'ExternalDataError during data fetching.',
            source=source,
            error_message=str(ede),
            status_code_from_error=ede.status_code,
            user_id=current_user.id
        )
        # Map ExternalDataError to appropriate HTTP response
        # If external service gave a specific client/server error status, we might reflect it,
        # or use a generic one like 502 Bad Gateway / 503 Service Unavailable.
        http_status_code = status.HTTP_502_BAD_GATEWAY # Default for "external service failed"
        if ede.status_code: # If ExternalDataError carries a status_code from the external API
            if 400 <= ede.status_code < 500: # Client-side error from external API (e.g., bad symbol for FRED)
                 http_status_code = status.HTTP_400_BAD_REQUEST # Or map to 502 if preferred not to expose external 4xx
            # Other mappings could be added here

        raise HTTPException(
            status_code=http_status_code,
            detail=f'Failed to fetch data from {source}: {str(ede)}'
        )
    except HTTPException:
        # Re-raise HTTPExceptions that were already raised (e.g., 400 for bad symbol)
        raise
    except Exception as e:
        # Catch-all for other unexpected errors within this endpoint logic
        logger.error(
            'Unexpected error during data fetching endpoint.',
            source=source,
            params=params,
            error_details=str(e),
            user_id=current_user.id,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'An unexpected internal error occurred: {str(e)}'
        )
