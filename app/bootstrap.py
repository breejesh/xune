"""Application bootstrap utilities."""
from __future__ import annotations

from app.common import get_logger, setup_logging
from app.config import get_config, init_config
from app.di import get_container, init_container

logger = get_logger(__name__)


class ApplicationBootstrap:
    """Bootstrap application with all necessary initialization."""

    @staticmethod
    def initialize() -> tuple:
        """Initialize the entire application.
        
        Returns:
            Tuple of (config, container) for use in main application.
            
        Raises:
            Exception: If initialization fails.
        """
        logger.info("Starting application bootstrap...")

        try:
            # Setup logging first  
            setup_logging()
            logger.debug("Logging configured")

            # Initialize configuration
            config = init_config()
            logger.debug(f"Configuration initialized: {config.app_name}")

            # Initialize DI container
            container = init_container()
            logger.debug("Dependency injection container initialized")

            logger.info("Application bootstrap complete")
            return config, container

        except Exception as e:
            logger.critical(f"Application bootstrap failed: {e}")
            raise

    @staticmethod
    def shutdown() -> None:
        """Shutdown the application gracefully.
        
        Raises:
            Exception: If shutdown fails.
        """
        try:
            logger.info("Shutting down application...")
            container = get_container()
            container.shutdown()
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
