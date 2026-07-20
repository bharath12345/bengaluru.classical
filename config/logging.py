import logging
import os

import structlog


def configure_logging():
    """Configure structured logging for production (JSON to stdout / Cloud Logging)."""
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    if os.getenv("K_SERVICE"):  # Cloud Run sets K_SERVICE
        import google.cloud.logging

        client = google.cloud.logging.Client()
        client.setup_logging()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
