"""Database module for persistent storage using SQLite."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.common import DatabaseError, get_logger
from app.config import get_config

# Global instances
Base = declarative_base()
_engine: Engine | None = None
_session_factory: sessionmaker | None = None

logger = get_logger(__name__)


def _get_engine() -> Engine:
    """Create and return database engine (singleton)."""
    global _engine
    if _engine is not None:
        return _engine

    config = get_config()
    try:
        logger.debug(f"Creating database engine at {config.database.db_path}")
        _engine = create_engine(
            config.database.connection_string,
            connect_args={"check_same_thread": False},
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            echo=config.database.echo_sql,
        )
        return _engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise DatabaseError(f"Failed to initialize database: {e}") from e


def init_db() -> None:
    """Initialize database tables."""
    try:
        engine = _get_engine()
        Base.metadata.create_all(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}") from e


def get_session_factory() -> sessionmaker:
    """Get SQLAlchemy session factory (singleton)."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = _get_engine()
    _session_factory = sessionmaker(bind=engine)
    return _session_factory


def get_session():
    """Create a new database session."""
    factory = get_session_factory()
    return factory()


def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")
