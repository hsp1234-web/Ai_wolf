from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import health, auth, db_management, data_fetcher, chat # Add chat router import
from app.core.logging_config import setup_logging
from app.core.middlewares import RequestContextLogMiddleware
from app.core.exceptions import global_exception_handler, APIBaseException, api_base_exception_handler
from app.db.database import initialize_db
import structlog # Ensure structlog is imported

# Configure logging
setup_logging()

app = FastAPI(title='Ai_wolf Backend', version='0.1.0')

@app.on_event("startup")
async def on_startup():
    logger = structlog.get_logger("app.startup")
    try:
        initialize_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database during startup.", error=str(e), exc_info=True)
        # Depending on severity, you might want to prevent app startup here
        # For now, just logging the error.

# Add exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(APIBaseException, api_base_exception_handler)

# Add middlewares
app.add_middleware(RequestContextLogMiddleware)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(db_management.router, prefix="/api")
app.include_router(data_fetcher.router, prefix="/api")
app.include_router(chat.router, prefix="/api") # chat.router has prefix="/chat", so full is /api/chat

@app.get('/')
async def root():
    return {'message': 'Welcome to Ai_wolf Backend. Visit /docs for API documentation.'}
