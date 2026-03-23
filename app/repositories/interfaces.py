"""Repository abstractions for data persistence."""
from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from app.core.models import Playlist, Setting, Track


@runtime_checkable
class TrackRepository(Protocol):
    """Interface for track persistence."""

    @abstractmethod
    def get_by_id(self, track_id: str) -> Track | None:
        """Get track by ID."""
        pass

    @abstractmethod
    def get_all(self) -> list[Track]:
        """Get all tracks."""
        pass

    @abstractmethod
    def save(self, track: Track) -> None:
        """Save a track."""
        pass

    @abstractmethod
    def delete(self, track_id: str) -> None:
        """Delete a track."""
        pass

    @abstractmethod
    def exists(self, track_id: str) -> bool:
        """Check if track exists."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close repository resources."""
        pass


@runtime_checkable
class PlaylistRepository(Protocol):
    """Interface for playlist persistence."""

    @abstractmethod
    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Get playlist by ID."""
        pass

    @abstractmethod
    def get_all(self) -> list[Playlist]:
        """Get all playlists."""
        pass

    @abstractmethod
    def save(self, playlist: Playlist) -> Playlist:
        """Save a playlist."""
        pass

    @abstractmethod
    def delete(self, playlist_id: int) -> None:
        """Delete a playlist."""
        pass

    @abstractmethod
    def add_track(self, playlist_id: int, track: Track) -> None:
        """Add track to playlist."""
        pass

    @abstractmethod
    def remove_track(self, playlist_id: int, track_id: str) -> None:
        """Remove track from playlist."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close repository resources."""
        pass


@runtime_checkable
class SettingRepository(Protocol):
    """Interface for setting persistence."""

    @abstractmethod
    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a setting."""
        pass

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Set a setting."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a setting."""
        pass

    @abstractmethod
    def get_all(self) -> dict[str, str]:
        """Get all settings."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close repository resources."""
        pass
