"""Logging configuration for the application."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.DEBUG,
) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_dir: Directory for log files. If None, logs only to console.
        level: Logging level.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Standard formatter with context
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if directory provided)
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "zune.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Module name (typically __name__).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
