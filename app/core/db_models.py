"""Database models for ORM."""
from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.models import Playlist as PlaylistDomain
from app.core.models import Setting as SettingDomain
from app.core.models import Track as TrackDomain
from app.core.db import Base

# Association table for many-to-many playlist-track relationship
playlist_track_association = Table(
    "playlist_track",
    Base.metadata,
    Column("playlist_id", Integer, ForeignKey("playlist.id"), primary_key=True),
    Column("track_id", Integer, ForeignKey("track.id"), primary_key=True),
    Column("position", Integer, default=0),
)


class TrackModel(Base):
    """SQLAlchemy model for Track data."""

    __tablename__ = "track"

    id = Column(Integer, primary_key=True)
    track_id = Column(String, unique=True, nullable=False, index=True)
    path = Column(String, nullable=False)
    title = Column(String, default="Unknown")
    artist = Column(String, default="Unknown Artist")
    album = Column(String, default="Unknown Album")
    genre = Column(String, default="")
    year = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    track_number = Column(Integer, default=0)
    playlists = relationship(
        "PlaylistModel",
        secondary=playlist_track_association,
        back_populates="tracks",
    )

    def to_domain(self) -> TrackDomain:
        """Convert ORM model to domain model."""
        return TrackDomain(
            track_id=self.track_id,
            path=self.path,
            title=self.title,
            artist=self.artist,
            album=self.album,
            duration_seconds=self.duration_seconds,
            track_number=self.track_number,
            genre=self.genre,
            year=self.year,
        )

    @staticmethod
    def from_domain(track: TrackDomain) -> TrackModel:
        """Create ORM model from domain model."""
        return TrackModel(
            track_id=track.track_id,
            path=track.path,
            title=track.title,
            artist=track.artist,
            album=track.album,
            duration_seconds=track.duration_seconds,
            track_number=track.track_number,
            genre=track.genre,
            year=track.year,
        )


class PlaylistModel(Base):
    """SQLAlchemy model for Playlist data."""

    __tablename__ = "playlist"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    tracks = relationship(
        "TrackModel",
        secondary=playlist_track_association,
        back_populates="playlists",
    )

    def to_domain(self) -> PlaylistDomain:
        """Convert ORM model to domain model."""
        tracks = [track.to_domain() for track in self.tracks] if self.tracks else []
        return PlaylistDomain(id=self.id, name=self.name, tracks=tracks)

    @staticmethod
    def from_domain(playlist: PlaylistDomain) -> PlaylistModel:
        """Create ORM model from domain model."""
        model = PlaylistModel(id=playlist.id, name=playlist.name)
        if playlist.tracks:
            model.tracks = [TrackModel.from_domain(t) for t in playlist.tracks]
        return model


class SettingModel(Base):
    """SQLAlchemy model for Settings data."""

    __tablename__ = "setting"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)

    def to_domain(self) -> SettingDomain:
        """Convert ORM model to domain model."""
        return SettingDomain(key=self.key, value=self.value)

    @staticmethod
    def from_domain(setting: SettingDomain) -> SettingModel:
        """Create ORM model from domain model."""
        return SettingModel(key=setting.key, value=setting.value)


class BackdropModel(Base):
    """SQLAlchemy model for cached backdrop metadata."""

    __tablename__ = "backdrop"
    __table_args__ = (UniqueConstraint("cache_key", name="_backdrop_cache_key_uc"),)

    id = Column(Integer, primary_key=True)
    cache_key = Column(String, nullable=False, index=True)
    phase = Column(Integer, default=0)
    seed = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    theme = Column(String, nullable=False)
    # Store as base64-encoded PNG data
    image_data = Column(String, nullable=True)
