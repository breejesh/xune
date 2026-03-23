"""Core module containing domain models, database, and business logic."""
from app.core.db import Base, get_session, get_session_factory, init_db, close_db
from app.core.db_models import TrackModel, PlaylistModel, SettingModel, BackdropModel
from app.core.models import Playlist, PlaybackState, Setting, Track
from app.core.storage import (
    load_tracks_cache, save_tracks_cache,
    load_settings, save_settings,
    load_playlists, save_playlists,
    init_database, load_tracks_db, save_tracks_db,
    load_settings_db, save_settings_db,
    load_playlists_db, save_playlists_db,
)

__all__ = [
    # Domain models
    "Track",
    "Playlist",
    "Setting",
    "PlaybackState",
    # Database
    "Base",
    "init_db",
    "get_session",
    "get_session_factory",
    "close_db",
    # ORM models
    "TrackModel",
    "PlaylistModel",
    "SettingModel",
    "BackdropModel",
    # Storage functions
    "load_tracks_cache",
    "save_tracks_cache",
    "load_settings",
    "save_settings",
    "load_playlists",
    "save_playlists",
    "init_database",
    "load_tracks_db",
    "save_tracks_db",
    "load_settings_db",
    "save_settings_db",
    "load_playlists_db",
    "save_playlists_db",
]
