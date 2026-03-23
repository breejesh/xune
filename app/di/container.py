"""Dependency injection container for application."""
from __future__ import annotations

from app.common import get_logger
from app.config import get_config
from app.core.db import init_db
from app.repositories import (
    SQLAlchemyPlaylistRepository,
    SQLAlchemySettingRepository,
    SQLAlchemyTrackRepository,
)
from app.services import LibraryService, PlaybackService, PlaylistService

logger = get_logger(__name__)


class DIContainer:
    """Dependency injection container."""

    def __init__(self) -> None:
        """Initialize container."""
        self._singletons: dict[str, object] = {}
        logger.debug("Initializing DI container")

    def initialize(self) -> None:
        """Initialize all services."""
        # Initialize database
        init_db()
        logger.info("DI container initialized")

    def get_track_repository(self):
        """Get track repository (singleton).
        
        Returns:
            TrackRepository instance.
        """
        if "track_repo" not in self._singletons:
            self._singletons["track_repo"] = SQLAlchemyTrackRepository()
        return self._singletons["track_repo"]

    def get_playlist_repository(self):
        """Get playlist repository (singleton).
        
        Returns:
            PlaylistRepository instance.
        """
        if "playlist_repo" not in self._singletons:
            self._singletons["playlist_repo"] = SQLAlchemyPlaylistRepository()
        return self._singletons["playlist_repo"]

    def get_setting_repository(self):
        """Get setting repository (singleton).
        
        Returns:
            SettingRepository instance.
        """
        if "setting_repo" not in self._singletons:
            self._singletons["setting_repo"] = SQLAlchemySettingRepository()
        return self._singletons["setting_repo"]

    def get_library_service(self) -> LibraryService:
        """Get library service (singleton).
        
        Returns:
            LibraryService instance.
        """
        if "library_service" not in self._singletons:
            track_repo = self.get_track_repository()
            self._singletons["library_service"] = LibraryService(track_repo)
        return self._singletons["library_service"]

    def get_playback_service(self) -> PlaybackService:
        """Get playback service (singleton).
        
        Returns:
            PlaybackService instance.
        """
        if "playback_service" not in self._singletons:
            config = get_config()
            self._singletons["playback_service"] = PlaybackService(
                poll_interval_ms=config.playback.poll_interval_ms
            )
        return self._singletons["playback_service"]

    def get_playlist_service(self) -> PlaylistService:
        """Get playlist service (singleton).
        
        Returns:
            PlaylistService instance.
        """
        if "playlist_service" not in self._singletons:
            playlist_repo = self.get_playlist_repository()
            track_repo = self.get_track_repository()
            self._singletons["playlist_service"] = PlaylistService(
                playlist_repo, track_repo
            )
        return self._singletons["playlist_service"]

    def shutdown(self) -> None:
        """Shutdown all services."""
        logger.debug("Shutting down DI container")
        
        # Shutdown services
        if "playback_service" in self._singletons:
            service = self._singletons["playback_service"]
            try:
                service.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down playback service: {e}")

        # Close repositories
        for repo_key in ["track_repo", "playlist_repo", "setting_repo"]:
            if repo_key in self._singletons:
                repo = self._singletons[repo_key]
                try:
                    repo.close()
                except Exception as e:
                    logger.warning(f"Error closing repository: {e}")

        self._singletons.clear()
        logger.info("DI container shut down")


# Global container instance
_container: DIContainer | None = None


def get_container() -> DIContainer:
    """Get global DI container.
    
    Returns:
        DIContainer instance.
    """
    global _container
    if _container is None:
        raise RuntimeError("Container not initialized. Call init_container() first.")
    return _container


def init_container() -> DIContainer:
    """Initialize global DI container.
    
    Returns:
        Initialized DIContainer instance.
    """
    global _container
    _container = DIContainer()
    _container.initialize()
    return _container
