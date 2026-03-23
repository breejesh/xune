"""UI utilities and helpers for service integration."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from app.common import ZuneException, get_logger

logger = get_logger(__name__)


def handle_service_error(
    error: Exception,
    title: str = "Error",
    parent = None,
    log: bool = True,
) -> None:
    """Handle and display service errors.
    
    Args:
        error: Exception that occurred
        title: Dialog title
        parent: Parent widget for dialog
        log: Whether to log the error
    """
    if log:
        if isinstance(error, ZuneException):
            logger.warning(f"{title}: {error}")
        else:
            logger.exception(f"{title}: {error}")

    # Show user-friendly error dialog
    if isinstance(error, ZuneException):
        message = str(error)
    else:
        message = f"An unexpected error occurred. Please check the logs."

    QMessageBox.critical(parent, title, message)


def run_with_error_handling(
    func: Callable,
    error_title: str = "Error",
    parent = None,
) -> bool:
    """Run a function with error handling and display.
    
    Args:
        func: Function to run
        error_title: Title for error dialog
        parent: Parent widget
        
    Returns:
        True if function succeeded, False otherwise
    """
    try:
        func()
        return True
    except Exception as e:
        handle_service_error(e, error_title, parent)
        return False
