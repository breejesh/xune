"""Dependency injection module."""
from app.di.container import DIContainer, get_container, init_container

__all__ = [
    "DIContainer",
    "get_container",
    "init_container",
]
