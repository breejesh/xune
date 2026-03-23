"""Playback service for audio playback control."""
from __future__ import annotations

import time
from pathlib import Path

from app.common import PlaybackError, get_logger
from app.core.models import PlaybackState, Track
import vlc

logger = get_logger(__name__)

# VLC player configuration
VLC_INSTANCE_OPTIONS = (
    "--no-video",
    "--quiet",
    "--file-caching=1000",
    "--network-caching=1000",
    "--avcodec-fast",
)

MEDIA_OPTIONS = (
    ":input-fast-seek",
    ":no-video",
)


class PlaybackService:
    """Service for managing audio playback."""

    def __init__(self, poll_interval_ms: int = 300) -> None:
        """Initialize playback service.
        
        Args:
            poll_interval_ms: Interval for position polling in milliseconds.
        """
        try:
            self._vlc = vlc
            self._instance = vlc.Instance(*VLC_INSTANCE_OPTIONS)
            self._player = self._instance.media_list_player_new()
            self._media_list = vlc.MediaList()
            self._player.set_media_list(self._media_list)
            self._poll_interval_ms = poll_interval_ms
            self._current_index = -1
            self._playlist: list[Track] = []
            logger.info("Playback service initialized")
        except ImportError as e:
            logger.error("VLC Python bindings not available")
            raise PlaybackError("VLC not available") from e

    @property
    def state(self) -> PlaybackState:
        """Get current playback state.
        
        Returns:
            Current PlaybackState.
        """
        try:
            is_playing = self._player.is_playing()
            media_player = self._player.get_media_player()
            media = media_player.get_media()
            
            # Get position and duration
            position_ms = media_player.get_time() if is_playing or media else 0.0
            duration_ms = media.get_duration() if media else 0.0
            
            # Get current track
            track = self._playlist[self._current_index] if 0 <= self._current_index < len(self._playlist) else None
            
            state = PlaybackState(
                track=track,
                is_playing=is_playing,
                position_ms=position_ms,
                duration_ms=duration_ms,
                current_index=self._current_index,
            )
            
            return state
        except Exception as e:
            logger.debug(f"[STATE] Error reading playback state: {e}")
            return PlaybackState(
                track=None,
                is_playing=False,
                position_ms=0.0,
                duration_ms=0.0,
                current_index=self._current_index,
            )

    def load_playlist(self, tracks: list[Track]) -> None:
        """Load a playlist.
        
        Args:
            tracks: List of tracks to load.
        """
        try:
            self._playlist = tracks
            self._media_list.lock()
            # Remove all existing items from media list (VLC doesn't have clear())
            while self._media_list.count() > 0:
                self._media_list.remove_index(0)
            # Add new tracks to media list
            for track in tracks:
                media = self._instance.media_new(str(track.path))
                media.add_options(*MEDIA_OPTIONS)
                self._media_list.add_media(media)
            self._media_list.unlock()
            self._current_index = -1
            logger.debug(f"Loaded playlist with {len(tracks)} tracks")
        except Exception as e:
            logger.error(f"Failed to load playlist: {e}")
            raise PlaybackError(f"Failed to load playlist: {e}") from e

    def play(self, index: int = 0) -> None:
        """Play a track at index.
        
        Args:
            index: Track index in current playlist.
            
        Raises:
            PlaybackError: If index is invalid or playback fails.
        """
        if not (0 <= index < len(self._playlist)):
            raise PlaybackError(f"Invalid track index: {index}")

        try:
            track = self._playlist[index]
            logger.info(f"[PLAY] Starting playback of track {index}: {track.title}")
            self._current_index = index
            self._player.play_item_at_index(index)
            logger.info(f"[PLAY] play_item_at_index({index}) called")
        except Exception as e:
            logger.error(f"[PLAY] Failed to play track at index {index}: {e}")
            raise PlaybackError(f"Playback failed: {e}") from e

    def pause(self) -> None:
        """Pause playback."""
        try:
            was_playing = self._player.is_playing()
            logger.info(f"[PAUSE] Called (was_playing={was_playing})")
            self._player.pause()
            logger.debug(f"[PAUSE] Completed")
        except Exception as e:
            logger.error(f"[PAUSE] Failed: {e}")
            raise PlaybackError(f"Pause failed: {e}") from e

    def resume(self) -> None:
        """Resume playback."""
        try:
            was_playing = self._player.is_playing()
            logger.info(f"[RESUME] Called (was_playing={was_playing})")
            self._player.pause()  # Toggle pause
            logger.debug(f"[RESUME] Completed - toggled pause")
        except Exception as e:
            logger.error(f"[RESUME] Failed: {e}")
            raise PlaybackError(f"Resume failed: {e}") from e

    def stop(self) -> None:
        """Stop playback."""
        try:
            self._player.stop()
            self._current_index = -1
            logger.debug("Playback stopped")
        except Exception as e:
            logger.error(f"Failed to stop: {e}")
            raise PlaybackError(f"Stop failed: {e}") from e

    def seek(self, position_ms: float) -> None:
        """Seek to position.
        
        Args:
            position_ms: Position in milliseconds.
        """
        try:
            media_player = self._player.get_media_player()
            logger.info(f"[SEEK] Seeking to {position_ms:.0f}ms")
            media_player.set_time(int(position_ms))
        except Exception as e:
            logger.error(f"[SEEK] FAILED: {e}", exc_info=True)
            raise PlaybackError(f"Seek failed: {e}") from e

    def next(self) -> None:
        """Play next track."""
        try:
            self._player.next()
            self._current_index = min(self._current_index + 1, len(self._playlist) - 1)
            logger.debug("Skipped to next track")
        except Exception as e:
            logger.error(f"Failed to skip to next: {e}")
            raise PlaybackError(f"Skip failed: {e}") from e

    def previous(self) -> None:
        """Play previous track."""
        try:
            self._player.previous()
            self._current_index = max(self._current_index - 1, 0)
            logger.debug("Skipped to previous track")
        except Exception as e:
            logger.error(f"Failed to skip to previous: {e}")
            raise PlaybackError(f"Skip failed: {e}") from e

    def set_volume(self, volume: int) -> None:
        """Set volume (0-100).
        
        Args:
            volume: Volume level.
        """
        try:
            volume = max(0, min(100, volume))
            media_player = self._player.get_media_player()
            media_player.audio_set_volume(volume)
            logger.debug(f"Volume set to {volume}%")
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            raise PlaybackError(f"Volume control failed: {e}") from e

    def shutdown(self) -> None:
        """Shutdown playback service."""
        try:
            self.stop()
            logger.info("Playback service shut down")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
