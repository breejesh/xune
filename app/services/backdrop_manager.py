"""Backdrop generation and caching service."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal, QMetaObject, Qt
from PySide6.QtGui import QImage, QPixmap

from app.common import get_logger
from app.ui.backdrop import compose_backdrop_image
from app.workers.backdrop_generator import BackdropGeneratorWorker

logger = get_logger(__name__)


class BackdropManager(QObject):
    """Manages backdrop generation, caching, and lifecycle."""

    # Signals
    backdrop_ready = Signal(str, QPixmap)  # cache_key, pixmap
    error = Signal(str)

    def __init__(self, backdrop_cache_dir: Path | None = None, max_age_ms: int = 1200000) -> None:
        super().__init__()
        self._backdrop_cache_dir = backdrop_cache_dir or Path.home() / ".cache" / "zune" / "backdrops"
        self._backdrop_cache_dir.mkdir(parents=True, exist_ok=True)
        self._backdrop_max_age_ms = max_age_ms  # 20 minutes in milliseconds

        # Worker thread
        self._worker_thread = QThread()
        self._worker = BackdropGeneratorWorker(self._backdrop_cache_dir)
        self._worker.moveToThread(self._worker_thread)

        # Cache: {cache_key -> QPixmap}
        self._memory_cache: dict[str, QPixmap] = {}

        # Connect signals
        self._worker.backdrop_ready.connect(self._on_backdrop_ready)
        self._worker.error.connect(self.error.emit)
        self._worker_thread.start()

    def generate_backdrops(
        self,
        width: int,
        height: int,
        pil_image_pool: list[Image.Image],
        seed_base: int,
        theme_name: str,
        count: int = 2,
        max_pool_size: int = 5,
    ) -> list[str]:
        """
        Queue backdrop generation tasks only if we have fewer than max_pool_size recent files.

        Args:
            width: Backdrop width
            height: Backdrop height
            pil_image_pool: List of PIL Images (pre-built on main thread)
            seed_base: Base seed for deterministic generation
            theme_name: 'dark' or 'light'
            count: Number of backdrops to generate
            max_pool_size: Don't generate if we already have this many recent files

        Returns list of cache keys for tracking.
        """
        # Check if we already have enough recent backdrops
        recent_count = self.count_recent_backdrops()
        if recent_count >= max_pool_size:
            logger.info(f"Already have {recent_count} recent backdrops (>= max {max_pool_size}), skipping generation")
            return []
        
        cache_keys = []
        for phase in range(count):
            seed = seed_base + phase
            cache_key = self._worker.add_task_with_images(
                width=width,
                height=height,
                image_pool=pil_image_pool,
                seed=seed,
                theme_name=theme_name,
                phase=phase,
            )
            cache_keys.append(cache_key)

        # Schedule processing on worker thread (thread-safe invocation)
        if cache_keys:
            logger.info(f"Queued {len(cache_keys)} backdrop tasks, scheduling worker processing")
            QMetaObject.invokeMethod(
                self._worker, 
                "process_queue", 
                Qt.ConnectionType.QueuedConnection
            )

        return cache_keys

    def get_backdrop(self, cache_key: str) -> QPixmap | None:
        """
        Get a backdrop from memory cache (if generated).

        Returns QPixmap or None if not yet available.
        """
        return self._memory_cache.get(cache_key)

    def _on_backdrop_ready(self, cache_key: str, qimage: QImage) -> None:
        """Worker emitted a generated backdrop."""
        try:
            pixmap = QPixmap.fromImage(qimage)
            if pixmap.isNull():
                logger.error("Generated backdrop QImage was null")
                return

            # Cache in memory for immediate access
            self._memory_cache[cache_key] = pixmap
            
            # Also save to disk (QPixmap format)
            cache_path = self._backdrop_cache_dir / f"{cache_key}.png"
            if not pixmap.save(str(cache_path)):
                logger.error(f"Failed to save pixmap backdrop to {cache_path}")
            else:
                logger.info(f"Backdrop cached: {cache_key} -> {cache_path}")

            # Emit signal with ready-to-use QPixmap
            self.backdrop_ready.emit(cache_key, pixmap)
        except Exception as e:
            logger.error(f"Failed to process backdrop: {e}", exc_info=True)

    def load_backdrops_from_disk(self, cache_base_key: str, count: int = 2) -> dict[int, QPixmap]:
        """
        Load cached backdrops from disk by base key.

        Returns dict[phase -> QPixmap] of loaded backdrops.
        """
        result = {}
        for i in range(count):
            cache_key = f"{cache_base_key}-{i}"
            cache_path = self._backdrop_cache_dir / f"{cache_key}.png"
            if not cache_path.exists():
                continue

            pixmap = QPixmap(str(cache_path))
            if pixmap.isNull():
                logger.warning(f"Cached backdrop at {cache_path} failed to load")
                continue

            self._memory_cache[cache_key] = pixmap
            result[i] = pixmap
            logger.info(f"Loaded backdrop from disk: {cache_key}")

        return result

    def count_recent_backdrops(self) -> int:
        """Count backdrop files in cache that are newer than max_age.
        
        Returns the count of PNG files (excluding last.png) that are younger than the age threshold.
        """
        if not self._backdrop_cache_dir.exists():
            return 0
        
        now = time.time()
        max_age_seconds = self._backdrop_max_age_ms / 1000  # Convert ms to seconds
        recent_count = 0
        
        try:
            for file in self._backdrop_cache_dir.glob("*.png"):
                # Skip the display cache file
                if file.name == "last.png":
                    continue
                
                try:
                    file_age = now - file.stat().st_mtime
                    if file_age < max_age_seconds:
                        recent_count += 1
                except Exception:
                    pass
        except Exception:
            pass
        
        return recent_count

    def clear_cache(self) -> None:
        """Clear memory cache."""
        self._memory_cache.clear()

    def shutdown(self) -> None:
        """Clean shutdown."""
        self._worker_thread.quit()
        self._worker_thread.wait()
