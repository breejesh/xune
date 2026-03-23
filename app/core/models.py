"""Core domain models."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Track:
    """Domain model for a music track."""

    track_id: str
    path: Path | str
    title: str = "Unknown"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration_seconds: float = 0.0
    track_number: int = 0
    genre: str = ""
    year: int = 0

    def __post_init__(self) -> None:
        """Convert path to Path object if it's a string."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        if self.title != "Unknown" and self.artist != "Unknown Artist":
            return f"{self.artist} - {self.title}"
        return self.title

    @property
    def duration_label(self) -> str:
        """Get formatted duration label (MM:SS)."""
        total_seconds = int(self.duration_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def __hash__(self) -> int:
        """Make Track hashable by track_id."""
        return hash(self.track_id)


@dataclass
class Playlist:
    """Domain model for a playlist."""

    id: int | None
    name: str
    tracks: list[Track] | None = None

    def __post_init__(self) -> None:
        if self.tracks is None:
            self.tracks = []


@dataclass
class Setting:
    """Domain model for a setting."""

    key: str
    value: str

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {"key": self.key, "value": self.value}


@dataclass
class PlaybackState:
    """Current playback state."""

    track: Track | None = None
    is_playing: bool = False
    position_ms: float = 0.0
    duration_ms: float = 0.0
    current_index: int = -1
    repeat_mode: str = "off"
    shuffle_enabled: bool = False

    @property
    def progress_percent(self) -> float:
        """Get playback progress as percentage."""
        if self.duration_ms <= 0:
            return 0.0
        return (self.position_ms / self.duration_ms) * 100
