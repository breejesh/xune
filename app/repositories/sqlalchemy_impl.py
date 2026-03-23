"""SQLAlchemy implementations of repositories."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.common import DatabaseError, get_logger
from app.core.models import Playlist, Setting, Track
from app.core.db import get_session
from app.core.db_models import PlaylistModel, SettingModel, TrackModel
from app.repositories.interfaces import PlaylistRepository, SettingRepository, TrackRepository

logger = get_logger(__name__)


class SQLAlchemyTrackRepository(TrackRepository):
    """SQLAlchemy implementation of TrackRepository."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository.
        
        Args:
            session: SQLAlchemy session. If None, creates a new one.
        """
        self._session = session or get_session()
        self._owns_session = session is None

    def get_by_id(self, track_id: str) -> Track | None:
        """Get track by ID."""
        try:
            model = self._session.query(TrackModel).filter_by(track_id=track_id).first()
            return model.to_domain() if model else None
        except Exception as e:
            logger.error(f"Error getting track {track_id}: {e}")
            raise DatabaseError(f"Failed to get track: {e}") from e

    def get_all(self) -> list[Track]:
        """Get all tracks."""
        try:
            models = self._session.query(TrackModel).all()
            return [model.to_domain() for model in models]
        except Exception as e:
            logger.error(f"Error getting all tracks: {e}")
            raise DatabaseError(f"Failed to get tracks: {e}") from e

    def save(self, track: Track) -> None:
        """Save a track."""
        try:
            existing = self._session.query(TrackModel).filter_by(track_id=track.track_id).first()
            if existing:
                existing.path = track.path
                existing.title = track.title
                existing.artist = track.artist
                existing.album = track.album
                existing.duration_seconds = track.duration_seconds
                existing.track_number = track.track_number
            else:
                model = TrackModel.from_domain(track)
                self._session.add(model)
            self._session.commit()
            logger.debug(f"Saved track: {track.track_id}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error saving track {track.track_id}: {e}")
            raise DatabaseError(f"Failed to save track: {e}") from e

    def delete(self, track_id: str) -> None:
        """Delete a track."""
        try:
            model = self._session.query(TrackModel).filter_by(track_id=track_id).first()
            if model:
                self._session.delete(model)
                self._session.commit()
                logger.debug(f"Deleted track: {track_id}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error deleting track {track_id}: {e}")
            raise DatabaseError(f"Failed to delete track: {e}") from e

    def exists(self, track_id: str) -> bool:
        """Check if track exists."""
        try:
            return self._session.query(TrackModel).filter_by(track_id=track_id).first() is not None
        except Exception as e:
            logger.error(f"Error checking track existence {track_id}: {e}")
            raise DatabaseError(f"Failed to check track existence: {e}") from e

    def close(self) -> None:
        """Close the session."""
        if self._owns_session and self._session:
            self._session.close()
            logger.debug("Track repository session closed")


class SQLAlchemyPlaylistRepository(PlaylistRepository):
    """SQLAlchemy implementation of PlaylistRepository."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository.
        
        Args:
            session: SQLAlchemy session. If None, creates a new one.
        """
        self._session = session or get_session()
        self._owns_session = session is None

    def get_by_id(self, playlist_id: int) -> Playlist | None:
        """Get playlist by ID."""
        try:
            model = self._session.query(PlaylistModel).filter_by(id=playlist_id).first()
            return model.to_domain() if model else None
        except Exception as e:
            logger.error(f"Error getting playlist {playlist_id}: {e}")
            raise DatabaseError(f"Failed to get playlist: {e}") from e

    def get_all(self) -> list[Playlist]:
        """Get all playlists."""
        try:
            models = self._session.query(PlaylistModel).all()
            return [model.to_domain() for model in models]
        except Exception as e:
            logger.error(f"Error getting all playlists: {e}")
            raise DatabaseError(f"Failed to get playlists: {e}") from e

    def save(self, playlist: Playlist) -> Playlist:
        """Save a playlist."""
        try:
            if playlist.id:
                model = self._session.query(PlaylistModel).filter_by(id=playlist.id).first()
                if model:
                    model.name = playlist.name
                else:
                    raise DatabaseError(f"Playlist {playlist.id} not found")
            else:
                model = PlaylistModel.from_domain(playlist)
                self._session.add(model)
            self._session.commit()
            self._session.refresh(model)
            logger.debug(f"Saved playlist: {playlist.name}")
            return model.to_domain()
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error saving playlist {playlist.name}: {e}")
            raise DatabaseError(f"Failed to save playlist: {e}") from e

    def delete(self, playlist_id: int) -> None:
        """Delete a playlist."""
        try:
            model = self._session.query(PlaylistModel).filter_by(id=playlist_id).first()
            if model:
                self._session.delete(model)
                self._session.commit()
                logger.debug(f"Deleted playlist: {playlist_id}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error deleting playlist {playlist_id}: {e}")
            raise DatabaseError(f"Failed to delete playlist: {e}") from e

    def add_track(self, playlist_id: int, track: Track) -> None:
        """Add track to playlist."""
        try:
            playlist = self._session.query(PlaylistModel).filter_by(id=playlist_id).first()
            track_model = self._session.query(TrackModel).filter_by(track_id=track.track_id).first()
            if not playlist:
                raise DatabaseError(f"Playlist {playlist_id} not found")
            if not track_model:
                track_model = TrackModel.from_domain(track)
                self._session.add(track_model)
            if track_model not in playlist.tracks:
                playlist.tracks.append(track_model)
                self._session.commit()
                logger.debug(f"Added track {track.track_id} to playlist {playlist_id}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error adding track to playlist: {e}")
            raise DatabaseError(f"Failed to add track to playlist: {e}") from e

    def remove_track(self, playlist_id: int, track_id: str) -> None:
        """Remove track from playlist."""
        try:
            playlist = self._session.query(PlaylistModel).filter_by(id=playlist_id).first()
            if not playlist:
                raise DatabaseError(f"Playlist {playlist_id} not found")
            playlist.tracks = [t for t in playlist.tracks if t.track_id != track_id]
            self._session.commit()
            logger.debug(f"Removed track {track_id} from playlist {playlist_id}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error removing track from playlist: {e}")
            raise DatabaseError(f"Failed to remove track from playlist: {e}") from e

    def close(self) -> None:
        """Close the session."""
        if self._owns_session and self._session:
            self._session.close()
            logger.debug("Playlist repository session closed")


class SQLAlchemySettingRepository(SettingRepository):
    """SQLAlchemy implementation of SettingRepository."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository.
        
        Args:
            session: SQLAlchemy session. If None, creates a new one.
        """
        self._session = session or get_session()
        self._owns_session = session is None

    def get(self, key: str, default: str | None = None) -> str | None:
        """Get a setting."""
        try:
            model = self._session.query(SettingModel).filter_by(key=key).first()
            return model.value if model else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            raise DatabaseError(f"Failed to get setting: {e}") from e

    def set(self, key: str, value: str) -> None:
        """Set a setting."""
        try:
            model = self._session.query(SettingModel).filter_by(key=key).first()
            if model:
                model.value = value
            else:
                model = SettingModel(key=key, value=value)
                self._session.add(model)
            self._session.commit()
            logger.debug(f"Set setting: {key}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error setting {key}: {e}")
            raise DatabaseError(f"Failed to set setting: {e}") from e

    def delete(self, key: str) -> None:
        """Delete a setting."""
        try:
            model = self._session.query(SettingModel).filter_by(key=key).first()
            if model:
                self._session.delete(model)
                self._session.commit()
                logger.debug(f"Deleted setting: {key}")
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error deleting setting {key}: {e}")
            raise DatabaseError(f"Failed to delete setting: {e}") from e

    def get_all(self) -> dict[str, str]:
        """Get all settings."""
        try:
            models = self._session.query(SettingModel).all()
            return {model.key: model.value for model in models}
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            raise DatabaseError(f"Failed to get settings: {e}") from e

    def close(self) -> None:
        """Close the session."""
        if self._owns_session and self._session:
            self._session.close()
            logger.debug("Setting repository session closed")
