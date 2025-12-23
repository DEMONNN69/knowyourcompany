"""
Structured logging configuration for the application.
Uses JSON format for organized, machine-readable logs.
"""

import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(log_level=logging.INFO):
    """
    Configure structured JSON logging for the application.
    
    Args:
        log_level: Logging level (default: INFO)
    """
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # JSON formatter for structured logs
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(levelname)s %(name)s %(message)s',
        timestamp=True
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # App-specific logger
    app_logger = logging.getLogger("backend")
    app_logger.setLevel(log_level)
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)
