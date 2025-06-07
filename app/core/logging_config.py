import logging
import sys
import structlog
from structlog.types import Processor
from app.core.config import settings # 假設 settings.LOG_LEVEL 存在
import logging.config # Explicit import for clarity

def setup_logging():
    # --- structlog processors ---
    # These processors are executed by structlog in the order they are defined
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt='iso'), # ISO 8601 timestamp
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # --- Development logging (human-readable) ---
    # If we are in development, we want to log to the console with colors
    # For production, we want to log in JSON format
    if settings.LOG_LEVEL.upper() == 'DEBUG': # Assuming a way to detect dev mode, e.g. via LOG_LEVEL or specific env var
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(), # Pretty prints in development
        ]
    else: # --- Production logging (JSON) ---
        processors = shared_processors + [
            structlog.processors.dict_tracebacks, # Render tracebacks as dicts for JSON
            structlog.processors.JSONRenderer(), # Renders the log entry as JSON
        ]

    # --- Standard library logging integration ---
    # Configure the standard library logging to use structlog's processors
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False, # Keep existing loggers (e.g., uvicorn)
        'formatters': {
            'json_formatter': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.processors.JSONRenderer(),
                'foreign_pre_chain': shared_processors, # Apply shared processors to stdlib logs
            },
            'console_formatter': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.dev.ConsoleRenderer(),
                'foreign_pre_chain': shared_processors, # Apply shared processors to stdlib logs
            },
        },
        'handlers': {
            'default': {
                'level': settings.LOG_LEVEL.upper(),
                'class': 'logging.StreamHandler',
                'formatter': 'json_formatter' if settings.LOG_LEVEL.upper() != 'DEBUG' else 'console_formatter',
                'stream': sys.stdout, # Or sys.stderr
            },
        },
        'loggers': {
            '': { # Root logger
                'handlers': ['default'],
                'level': settings.LOG_LEVEL.upper(),
                'propagate': True,
            },
            'uvicorn.error': {
                'handlers': ['default'], # Route uvicorn errors through structlog
                'level': settings.LOG_LEVEL.upper(),
                'propagate': False,
            },
            'uvicorn.access': {
                'handlers': ['default'], # Route uvicorn access logs through structlog
                'level': settings.LOG_LEVEL.upper(),
                'propagate': False,
            },
            # Example of configuring another library's logger
            # 'httpx': {
            # 'handlers': ['default'],
            # 'level': 'INFO', # Or settings.LOG_LEVEL.upper()
            # 'propagate': False,
            # },
        }
    })

    # --- Configure structlog itself ---
    structlog.configure(
        processors=processors, # These are for structlog's own loggers
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger, # Standard library compatible logger
        cache_logger_on_first_use=True,
    )

    # Optional: Log a message to confirm setup
    # logger = structlog.get_logger('app.startup')
    # logger.info('Logging configured', log_level=settings.LOG_LEVEL, mode='DEBUG' if settings.LOG_LEVEL.upper() == 'DEBUG' else 'PRODUCTION')
