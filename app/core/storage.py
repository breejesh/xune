from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.models import Track
from app.core.db import get_session, init_db
from app.core.db_models import PlaylistModel, SettingModel, TrackModel

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SETTINGS_FILE = APP_DATA_DIR / "settings.json"
PLAYLISTS_FILE = APP_DATA_DIR / "playlists.json"
LIBRARY_CACHE_FILE = APP_DATA_DIR / "library_cache.json"


def _ensure_data_dir() -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, payload: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def default_scan_folders() -> list[str]:
    home = Path.home()
    desktop = home / "Desktop"
    music = home / "Music"
    folders: list[str] = []
    for folder in (desktop, music):
        if folder.exists():
            folders.append(str(folder))
    return folders


def load_settings() -> dict[str, Any]:
    default = {
        "scan_folders": default_scan_folders(),
        "window": {"width": 1280, "height": 800},
        "last_track": "",
        "volume": 85,
        "theme": "dark",
    }
    settings = load_json(SETTINGS_FILE, default)
    if "scan_folders" not in settings:
        settings["scan_folders"] = default_scan_folders()
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    save_json(SETTINGS_FILE, settings)


def load_playlists() -> dict[str, list[str]]:
    return load_json(PLAYLISTS_FILE, {"Favorites": []})


def save_playlists(playlists: dict[str, list[str]]) -> None:
    save_json(PLAYLISTS_FILE, playlists)


def load_tracks_cache() -> list[Track]:
    payload = load_json(LIBRARY_CACHE_FILE, [])
    if not isinstance(payload, list):
        return []

    tracks: list[Track] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        try:
            tracks.append(
                Track(
                    track_id=str(row.get("track_id", "")),
                    path=Path(str(row.get("path", ""))),
                    title=str(row.get("title", "Unknown")),
                    artist=str(row.get("artist", "Unknown Artist")),
                    album=str(row.get("album", "Unknown Album")),
                    duration_seconds=float(row.get("duration_seconds", 0.0) or 0.0),
                    track_number=int(row.get("track_number", 0) or 0),
                    genre=str(row.get("genre", "")),
                    year=int(row.get("year", 0) or 0),
                )
            )
        except Exception:
            continue
    return tracks


def save_tracks_cache(tracks: list[Track]) -> None:
    payload = [
        {
            "track_id": t.track_id,
            "path": str(t.path),
            "title": t.title,
            "artist": t.artist,
            "album": t.album,
            "duration_seconds": float(t.duration_seconds),
            "track_number": int(t.track_number),
            "genre": t.genre,
            "year": int(t.year),
        }
        for t in tracks
    ]
    save_json(LIBRARY_CACHE_FILE, payload)


# ==================== DATABASE FUNCTIONS ====================
# These functions provide SQLite-based storage with in-memory caching


def init_database() -> None:
    """Initialize the database schema."""
    init_db()


def get_db_session() -> Session:
    """Get a new database session."""
    return get_session()


def save_tracks_db(tracks: list[Track]) -> None:
    """Save tracks to database."""
    session = get_db_session()
    try:
        # Clear existing tracks
        session.query(TrackModel).delete()

        # Add new tracks
        for track in tracks:
            db_track = TrackModel(
                track_id=track.track_id,
                path=str(track.path),
                title=track.title,
                artist=track.artist,
                album=track.album,
                duration_seconds=track.duration_seconds,
                track_number=track.track_number,
                genre=track.genre,
                year=track.year,
            )
            session.add(db_track)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def load_tracks_db() -> list[Track]:
    """Load tracks from database."""
    session = get_db_session()
    try:
        db_tracks = session.query(TrackModel).all()
        return [track.to_domain() for track in db_tracks]
    finally:
        session.close()


def save_setting_db(key: str, value: str) -> None:
    """Save a single setting to database."""
    session = get_db_session()
    try:
        existing = session.query(SettingModel).filter_by(key=key).first()
        if existing:
            existing.value = value
        else:
            session.add(SettingModel(key=key, value=value))
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def load_setting_db(key: str, default: str = "") -> str:
    """Load a single setting from database."""
    session = get_db_session()
    try:
        setting = session.query(SettingModel).filter_by(key=key).first()
        return setting.value if setting else default
    finally:
        session.close()


def save_settings_db(settings: dict[str, Any]) -> None:
    """Save all settings to database."""
    session = get_db_session()
    try:
        # Store settings as JSON strings for complex types
        for key, value in settings.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            else:
                value = str(value)

            existing = session.query(SettingModel).filter_by(key=key).first()
            if existing:
                existing.value = value
            else:
                session.add(SettingModel(key=key, value=value))

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def load_settings_db() -> dict[str, Any]:
    """Load all settings from database."""
    session = get_db_session()
    try:
        default = {
            "scan_folders": default_scan_folders(),
            "window": {"width": 1280, "height": 800},
            "last_track": "",
            "volume": 85,
            "theme": "dark",
        }

        db_settings = session.query(SettingModel).all()
        settings = {}

        for setting in db_settings:
            try:
                # Try to parse as JSON for complex types
                settings[setting.key] = json.loads(setting.value)
            except (json.JSONDecodeError, ValueError):
                # Fall back to string value
                settings[setting.key] = setting.value

        # Merge with defaults
        for key, value in default.items():
            if key not in settings:
                settings[key] = value

        return settings
    finally:
        session.close()


def save_playlists_db(playlists: dict[str, list[str]]) -> None:
    """Save playlists to database."""
    session = get_db_session()
    try:
        # Clear existing playlists
        session.query(PlaylistModel).delete()

        # Get all tracks for mapping
        all_tracks = {t.track_id: t for t in session.query(TrackModel).all()}

        # Add new playlists with their tracks
        for playlist_name, track_ids in playlists.items():
            playlist = PlaylistModel(name=playlist_name)

            for i, track_id in enumerate(track_ids):
                if track_id in all_tracks:
                    playlist.tracks.append(all_tracks[track_id])

            session.add(playlist)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def load_playlists_db() -> dict[str, list[str]]:
    """Load playlists from database."""
    session = get_db_session()
    try:
        db_playlists = session.query(PlaylistModel).all()
        result = {}

        for playlist in db_playlists:
            result[playlist.name] = [t.track_id for t in playlist.tracks]

        # Ensure Favorites playlist exists
        if "Favorites" not in result:
            result["Favorites"] = []

        return result
    finally:
        session.close()


def migrate_json_to_db() -> None:
    """Migrate existing JSON data to SQLite database."""
    init_database()

    # Migrate tracks
    json_tracks = load_tracks_cache()
    if json_tracks:
        save_tracks_db(json_tracks)

    # Migrate settings
    json_settings = load_settings()
    save_settings_db(json_settings)

    # Migrate playlists
    json_playlists = load_playlists()
    save_playlists_db(json_playlists)
