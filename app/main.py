import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.bootstrap import ApplicationBootstrap
from app.common import get_logger
from app.ui.main_window import MainWindow

logger = get_logger(__name__)


def _configure_qt_logging() -> None:
    # Suppress noisy libpng iCCP profile warnings from third-party album-art PNG files.
    existing = os.environ.get("QT_LOGGING_RULES", "").strip()
    rule = "qt.gui.imageio.warning=false"
    if not existing:
        os.environ["QT_LOGGING_RULES"] = rule
        return
    if rule not in existing:
        os.environ["QT_LOGGING_RULES"] = f"{existing};{rule}"


def main() -> int:
    """Run the application.
    
    Returns:
        Application exit code.
    """
    try:
        # Bootstrap application
        config, container = ApplicationBootstrap.initialize()
        _configure_qt_logging()

        # Create and show main window
        app = QApplication(sys.argv)
        app.setApplicationName(config.app_name)
        app.setOrganizationName("Local")

        window = MainWindow(container)
        window.resize(config.ui.window_width, config.ui.window_height)
        window.show()

        exit_code = app.exec()
        return exit_code

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    finally:
        try:
            ApplicationBootstrap.shutdown()
        except Exception as e:
            logger.exception(f"Error during shutdown: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
