"""Playlist management service."""
from __future__ import annotations

from app.common import DatabaseError, get_logger
from app.core.models import Playlist, Track
from app.repositories import PlaylistRepository, TrackRepository

logger = get_logger(__name__)


class PlaylistService:
    """Service for managing playlists."""

    def __init__(
        self,
        playlist_repository: PlaylistRepository,
        track_repository: TrackRepository,
    ) -> None:
        """Initialize service.
        
        Args:
            playlist_repository: Repository for playlist persistence.
            track_repository: Repository for track persistence.
        """
        self._playlist_repo = playlist_repository
        self._track_repo = track_repository

    def create_playlist(self, name: str) -> Playlist:
        """Create a new playlist.
        
        Args:
            name: Playlist name.
            
        Returns:
            Created playlist.
        """
        try:
            playlist = Playlist(id=None, name=name)
            saved = self._playlist_repo.save(playlist)
            logger.info(f"Created playlist: {name}")
            return saved
        except Exception as e:
            logger.error(f"Failed to create playlist {name}: {e}")
            raise DatabaseError(f"Failed to create playlist: {e}") from e

    def get_playlist(self, playlist_id: int) -> Playlist | None:
        """Get playlist by ID.
        
        Args:
            playlist_id: Playlist ID.
            
        Returns:
            Playlist or None if not found.
        """
        return self._playlist_repo.get_by_id(playlist_id)

    def get_all_playlists(self) -> list[Playlist]:
        """Get all playlists.
        
        Returns:
            List of all playlists.
        """
        return self._playlist_repo.get_all()

    def delete_playlist(self, playlist_id: int) -> None:
        """Delete a playlist.
        
        Args:
            playlist_id: Playlist ID.
        """
        try:
            self._playlist_repo.delete(playlist_id)
            logger.info(f"Deleted playlist: {playlist_id}")
        except Exception as e:
            logger.error(f"Failed to delete playlist {playlist_id}: {e}")
            raise DatabaseError(f"Failed to delete playlist: {e}") from e

    def add_track_to_playlist(self, playlist_id: int, track_id: str) -> None:
        """Add track to playlist.
        
        Args:
            playlist_id: Playlist ID.
            track_id: Track ID.
        """
        try:
            track = self._track_repo.get_by_id(track_id)
            if not track:
                raise DatabaseError(f"Track {track_id} not found")
            self._playlist_repo.add_track(playlist_id, track)
            logger.debug(f"Added track {track_id} to playlist {playlist_id}")
        except Exception as e:
            logger.error(f"Failed to add track to playlist: {e}")
            raise DatabaseError(f"Failed to add track to playlist: {e}") from e

    def remove_track_from_playlist(self, playlist_id: int, track_id: str) -> None:
        """Remove track from playlist.
        
        Args:
            playlist_id: Playlist ID.
            track_id: Track ID.
        """
        try:
            self._playlist_repo.remove_track(playlist_id, track_id)
            logger.debug(f"Removed track {track_id} from playlist {playlist_id}")
        except Exception as e:
            logger.error(f"Failed to remove track from playlist: {e}")
            raise DatabaseError(f"Failed to remove track from playlist: {e}") from e

    def rename_playlist(self, playlist_id: int, new_name: str) -> None:
        """Rename a playlist.
        
        Args:
            playlist_id: Playlist ID.
            new_name: New playlist name.
        """
        try:
            playlist = self.get_playlist(playlist_id)
            if not playlist:
                raise DatabaseError(f"Playlist {playlist_id} not found")
            playlist.name = new_name
            self._playlist_repo.save(playlist)
            logger.info(f"Renamed playlist {playlist_id} to {new_name}")
        except Exception as e:
            logger.error(f"Failed to rename playlist: {e}")
            raise DatabaseError(f"Failed to rename playlist: {e}") from e
