"""Configuration management for the application."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.common import ConfigurationError


@dataclass
class DatabaseConfig:
    """Database configuration."""

    db_path: Path
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    @property
    def connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return f"sqlite:///{self.db_path}"


@dataclass
class UIConfig:
    """UI configuration."""

    window_width: int = 1280
    window_height: int = 800
    theme: str = "dark"
    remember_position: bool = True


@dataclass
class LibraryConfig:
    """Library scanning configuration."""

    scan_folders: list[str] = field(default_factory=list)
    supported_extensions: set[str] = field(
        default_factory=lambda: {
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
    )
    scan_interval_seconds: int = 3600  # 1 hour


@dataclass
class PlaybackConfig:
    """Playback configuration."""

    poll_interval_ms: int = 300
    seek_settle_ms: int = 1200
    duration_probe_interval_s: float = 2.5
    post_seek_probe_delay_s: float = 1.2


@dataclass
class AppConfig:
    """Main application configuration."""

    app_name: str = "Zune Offline"
    version: str = "0.1.0"
    app_data_dir: Path = field(default_factory=lambda: Path.home() / ".zune")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".zune" / "logs")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".zune" / "cache")

    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        db_path=Path(__file__).parent.parent / "data" / "zune.db"
    ))
    ui: UIConfig = field(default_factory=UIConfig)
    library: LibraryConfig = field(default_factory=LibraryConfig)
    playback: PlaybackConfig = field(default_factory=PlaybackConfig)

    def __post_init__(self) -> None:
        """Validate configuration."""
        self._create_directories()
        self._set_default_scan_folders()

    def _create_directories(self) -> None:
        """Create necessary directories."""
        for directory in [self.app_data_dir, self.log_dir, self.cache_dir, self.database.db_path.parent]:
            directory.mkdir(parents=True, exist_ok=True)

    def _set_default_scan_folders(self) -> None:
        """Set default scan folders if not already configured."""
        if not self.library.scan_folders:
            home = Path.home()
            folders = []
            for folder in [home / "Desktop", home / "Music"]:
                if folder.exists():
                    folders.append(str(folder))
            self.library.scan_folders = folders

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as dictionary."""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "app_data_dir": str(self.app_data_dir),
            "log_dir": str(self.log_dir),
            "cache_dir": str(self.cache_dir),
            "database": {
                "db_path": str(self.database.db_path),
                "echo_sql": self.database.echo_sql,
                "pool_size": self.database.pool_size,
            },
            "ui": {
                "window_width": self.ui.window_width,
                "window_height": self.ui.window_height,
                "theme": self.ui.theme,
            },
            "library": {
                "scan_folders": self.library.scan_folders,
                "scan_interval_seconds": self.library.scan_interval_seconds,
            },
        }


_default_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance.
    
    Returns:
        Application configuration.
        
    Raises:
        ConfigurationError: If configuration hasn't been initialized.
    """
    if _default_config is None:
        raise ConfigurationError("Configuration not initialized. Call init_config() first.")
    return _default_config


def init_config(config: AppConfig | None = None) -> AppConfig:
    """Initialize the global configuration.
    
    Args:
        config: Configuration instance. If None, creates default.
        
    Returns:
        Initialized configuration.
    """
    global _default_config
    _default_config = config or AppConfig()
    return _default_config
