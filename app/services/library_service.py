"""Library service for scanning and managing music files."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from mutagen import File as MutagenFile

from app.common import LibraryError, get_logger
from app.core.models import Track
from app.repositories import TrackRepository

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".aiff",
    ".aif",
    ".ape",
    ".wv",
    ".alac",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
    ".m4b",
}


class LibraryService:
    """Service for managing music library."""

    def __init__(self, track_repository: TrackRepository) -> None:
        """Initialize service.
        
        Args:
            track_repository: Repository for track persistence.
        """
        self._track_repo = track_repository
        self._supported_extensions = SUPPORTED_EXTENSIONS

    def scan_folders(
        self,
        folders: list[str],
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> list[Track]:
        """Scan folders for audio files.
        
        Args:
            folders: List of folder paths to scan.
            progress_callback: Optional callback(file_path, total_count) for progress.
            
        Returns:
            List of discovered tracks.
            
        Raises:
            LibraryError: If scan fails.
        """
        logger.info(f"Starting scan of {len(folders)} folder(s)")
        tracks: list[Track] = []
        scanned = set()

        try:
            for folder_path in folders:
                folder = Path(folder_path)
                if not folder.exists():
                    logger.warning(f"Scan folder does not exist: {folder_path}")
                    continue

                for file_path in folder.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in self._supported_extensions:
                        if file_path in scanned:
                            continue

                        try:
                            track = self._extract_track_metadata(file_path)
                            if track:
                                tracks.append(track)
                                scanned.add(file_path)
                                if progress_callback:
                                    progress_callback(str(file_path), len(tracks))
                        except Exception as e:
                            logger.warning(f"Failed to extract metadata for {file_path}: {e}")
                            continue

            logger.info(f"Scan completed. Found {len(tracks)} tracks")
            return tracks
        except Exception as e:
            logger.error(f"Library scan failed: {e}")
            raise LibraryError(f"Failed to scan library: {e}") from e

    def _extract_track_metadata(self, file_path: Path) -> Track | None:
        """Extract metadata from audio file.
        
        Args:
            file_path: Path to audio file.
            
        Returns:
            Track object with metadata, or None if extraction fails.
        """
        try:
            audio = MutagenFile(file_path)
            if audio is None:
                return None

            # Generate unique track ID based on file path
            track_id = hashlib.md5(str(file_path).encode()).hexdigest()

            # Extract metadata - handle different tag formats (ID3, Vorbis, MP4, ASF/WMA)
            title = self._get_metadata_value(audio, ["TIT2", "TITLE", "Title", "\xa9nam"])
            artist = self._get_metadata_value(audio, ["TPE1", "ARTIST", "Artist", "\xa9ART", "Author"])
            album = self._get_metadata_value(audio, ["TALB", "ALBUM", "Album", "\xa9alb", "WM/AlbumTitle"])
            genre = self._get_metadata_value(audio, ["TCON", "GENRE", "Genre", "\xa9gen", "WM/Genre"]) or ""
            year_str = self._get_metadata_value(audio, ["TDRC", "DATE", "Year", "\xa9day", "WM/Year"])
            track_num = self._get_metadata_value(audio, ["TRCK", "TRACKNUMBER", "TrackNumber", "WM/TrackNumber", "WM/TrackNumberAndCount"])

            try:
                track_number = int(str(track_num).split("/")[0]) if track_num else 0
            except (ValueError, AttributeError):
                track_number = 0
            
            try:
                year = int(str(year_str).split("-")[0]) if year_str else 0
            except (ValueError, AttributeError):
                year = 0

            # Get duration
            duration = 0.0
            if hasattr(audio, "info") and hasattr(audio.info, "length"):
                duration = float(audio.info.length)

            return Track(
                track_id=track_id,
                path=str(file_path),
                title=str(title) if title else "Unknown",
                artist=str(artist) if artist else "Unknown Artist",
                album=str(album) if album else "Unknown Album",
                duration_seconds=duration,
                track_number=track_number,
                genre=str(genre) if genre else "",
                year=year,
            )
        except Exception as e:
            logger.debug(f"Failed to extract metadata from {file_path}: {e}")
            return None

    def _extract_frame_value(self, frame_obj: object) -> str | None:
        """Extract text value from a Mutagen frame object.
        
        Handles ID3 frames (TIT2, TXXX, etc.) which have a .text attribute.
        
        Args:
            frame_obj: Mutagen frame object or raw value.
            
        Returns:
            Extracted text value, or None if empty.
        """
        # Check for Mutagen frame's .text attribute (ID3v2 frames)
        if hasattr(frame_obj, "text"):
            text_list = frame_obj.text
            if isinstance(text_list, (list, tuple)) and text_list:
                # Join list elements for multi-value frames
                result = str(text_list[0]).strip()
                if result:
                    return result
        
        # Fallback: direct string conversion for other types
        if frame_obj:
            result = str(frame_obj).strip()
            if result:
                return result
        
        return None

    def _get_metadata_value(self, audio: object, tag_keys: list[str]) -> str | None:
        """Extract metadata value from audio file.
        
        Handles multiple tag formats: ID3v2, Vorbis, MP4, etc.
        
        Args:
            audio: Mutagen audio object.
            tag_keys: List of possible tag keys to try (in order).
            
        Returns:
            Tag value as string, or None if not found.
        """
        # First try: standard dictionary access to tags
        if hasattr(audio, "tags") and audio.tags is not None:
            for key in tag_keys:
                try:
                    value = audio.tags.get(key) if hasattr(audio.tags, "get") else audio.tags[key]
                    if value:
                        # Handle various Mutagen return types
                        if isinstance(value, (list, tuple)):
                            val = value[0] if value else None
                        else:
                            val = value
                        
                        if val:
                            # Use frame value extractor for proper handling
                            result = self._extract_frame_value(val)
                            if result:
                                return result
                except (AttributeError, TypeError, KeyError, IndexError):
                    pass
        
        # Second try: direct dictionary-style access (for MP4 and others)
        try:
            for key in tag_keys:
                if key in audio:
                    value = audio[key]
                    if value:
                        if isinstance(value, (list, tuple)):
                            val = value[0] if value else None
                        else:
                            val = value
                        
                        if val:
                            # Use frame value extractor for proper handling
                            result = self._extract_frame_value(val)
                            if result:
                                return result
        except (TypeError, KeyError):
            pass
        
        return None

    def import_tracks(self, tracks: list[Track]) -> None:
        """Import tracks into the repository.
        
        Args:
            tracks: List of tracks to import.
            
        Raises:
            LibraryError: If import fails.
        """
        try:
            for track in tracks:
                if not self._track_repo.exists(track.track_id):
                    self._track_repo.save(track)
                    logger.debug(f"Imported track: {track.display_name}")
            logger.info(f"Imported {len(tracks)} tracks")
        except Exception as e:
            logger.error(f"Failed to import tracks: {e}")
            raise LibraryError(f"Failed to import tracks: {e}") from e

    def get_all_tracks(self) -> list[Track]:
        """Get all tracks from repository.
        
        Returns:
            List of all tracks.
        """
        return self._track_repo.get_all()
