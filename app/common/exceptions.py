"""Custom exceptions for the Zune application."""
from __future__ import annotations


class ZuneException(Exception):
    """Base exception for all Zune application errors."""

    pass


class ConfigurationError(ZuneException):
    """Raised when configuration is invalid."""

    pass


class DatabaseError(ZuneException):
    """Raised when a database operation fails."""

    pass


class StorageError(ZuneException):
    """Raised when storage operations fail."""

    pass


class LibraryError(ZuneException):
    """Raised when library scanning fails."""

    pass


class PlaybackError(ZuneException):
    """Raised when playback operations fail."""

    pass


class ValidationError(ZuneException):
    """Raised when data validation fails."""

    pass
