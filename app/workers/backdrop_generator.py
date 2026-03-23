"""Background worker for backdrop generation."""
from __future__ import annotations

import base64
import hashlib
import io
import random
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage

from app.common import get_logger
from app.ui.backdrop import compose_backdrop_image

logger = get_logger(__name__)


class BackdropGeneratorWorker(QObject):
    """Worker for generating backdrop images in background thread."""

    # Signals
    finished = Signal()
    error = Signal(str)
    backdrop_ready = Signal(str, QImage)  # cache_key, image

    def __init__(self, backdrop_cache_dir: Path | None = None) -> None:
        super().__init__()
        self._queue: list[dict] = []
        self._is_running = False
        self._current_task: Optional[dict] = None
        self._backdrop_cache_dir = backdrop_cache_dir or Path.home() / ".cache" / "zune" / "backdrops"

    def add_task(
        self,
        width: int,
        height: int,
        tracks: list,
        album_art_getter: Callable[[str, list], QImage],
        seed: int,
        theme_name: str,
        phase: int,
    ) -> str:
        """Legacy method - build image pool on main thread instead."""
        logger.warning("add_task(tracks) is deprecated - use add_task_with_images(image_pool) instead")
        return ""

    def add_task_with_images(
        self,
        width: int,
        height: int,
        image_pool: list[Image.Image],
        seed: int,
        theme_name: str,
        phase: int,
    ) -> str:
        """
        Add a backdrop generation task with pre-built PIL Image pool.
        
        Args:
            width: Backdrop width
            height: Backdrop height
            image_pool: List of PIL Images to use for backdrop generation
            seed: Random seed
            theme_name: 'dark' or 'light'
            phase: Phase (0-4)

        Returns the cache_key for tracking this task.
        """
        cache_key = self._compute_cache_key(width, height, seed, theme_name, phase)

        task = {
            "cache_key": cache_key,
            "width": width,
            "height": height,
            "image_pool": image_pool,
            "seed": seed,
            "theme_name": theme_name,
            "phase": phase,
        }
        self._queue.append(task)
        return cache_key

    @Slot()
    def process_queue(self) -> None:
        """Process all queued tasks."""
        if self._is_running:
            logger.warning("Already processing, skipping")
            return

        logger.info(f"Starting backdrop worker queue processing: {len(self._queue)} tasks")
        self._is_running = True
        try:
            while self._queue:
                self._current_task = self._queue.pop(0)
                logger.info(f"Processing task {len(self._queue)} remaining")
                self._process_task(self._current_task)
        except Exception as e:
            logger.error(f"Backdrop generation failed: {e}", exc_info=True)
            self.error.emit(f"Backdrop generation failed: {str(e)}")
        finally:
            self._is_running = False
            logger.info("Backdrop worker queue processing finished")
            self.finished.emit()

    def clear_queue(self) -> None:
        """Clear all pending tasks."""
        self._queue.clear()

    def _process_task(self, task: dict) -> None:
        """Generate backdrop for a single task."""
        try:
            logger.info(f"Worker processing backdrop task: {task['cache_key']}")
            
            # Get pre-built image pool from task (built on main thread)
            image_pool = task.get("image_pool", [])
            
            if not image_pool:
                logger.error("Image pool is empty in task")
                self.error.emit("Image pool is empty")
                return
            
            logger.info(f"Using pre-built image pool with {len(image_pool)} images")
            
            # Generate backdrop using pure PIL
            pil_image = compose_backdrop_image(
                width=task["width"],
                height=task["height"],
                image_pool=image_pool,
                seed=task["seed"],
                theme_name=task["theme_name"],
                phase=task["phase"],
            )
            
            logger.info(f"Generated PIL image: {pil_image.size}")
            
            # Worker saves to disk independently
            self._save_backdrop_to_disk(pil_image, task["cache_key"])
            
            # Worker converts PIL -> QImage for signal emission
            qimage = self._pil_to_qimage(pil_image)
            logger.info(f"Converted to QImage: {qimage.width()}x{qimage.height()}, emitting signal")
            self.backdrop_ready.emit(task["cache_key"], qimage)
        except Exception as e:
            logger.error(f"Failed to generate backdrop: {e}", exc_info=True)
            self.error.emit(f"Failed to generate backdrop: {str(e)}")

    def _save_backdrop_to_disk(self, pil_image: Image.Image, cache_key: str) -> None:
        """Save backdrop PIL Image to disk independently."""
        try:
            self._backdrop_cache_dir.mkdir(parents=True, exist_ok=True)
            save_path = self._backdrop_cache_dir / f"{cache_key}.png"
            logger.info(f"Saving backdrop to: {save_path}")
            pil_image.save(str(save_path), "PNG")
            logger.info(f"Backdrop saved successfully: {save_path}")
        except Exception as e:
            logger.error(f"Failed to save backdrop to {self._backdrop_cache_dir}: {e}", exc_info=True)

    @staticmethod
    def _qimage_to_pil(qimg: QImage) -> Image.Image:
        """Convert QImage to PIL Image."""
        width = qimg.width()
        height = qimg.height()
        ptr = qimg.bits()
        
        # Handle both old and new PySide6 versions
        if isinstance(ptr, memoryview):
            arr = bytes(ptr)
        else:
            arr = ptr.tobytes()
        
        # Convert from ARGB32 to RGBA
        pil_img = Image.frombytes('RGBA', (width, height), arr, 'raw', 'BGRA')
        return pil_img

    @staticmethod
    def _pil_to_qimage(pil_image: Image.Image) -> QImage:
        """Convert PIL Image to QImage."""
        width, height = pil_image.size
        rgba_img = pil_image.convert('RGBA')
        data = rgba_img.tobytes('raw', 'BGRA')
        qimg = QImage(data, width, height, width * 4, QImage.Format_ARGB32)
        return qimg

    @staticmethod
    def _compute_cache_key(
        width: int, height: int, seed: int, theme_name: str, phase: int
    ) -> str:
        """Compute cache key for backdrop."""
        key_str = f"{width}×{height}×{seed}×{theme_name}×{phase}"
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def save_image_as_base64(image: QImage) -> str:
        """Convert QImage to base64-encoded PNG."""
        buffer = io.BytesIO()
        image_copy = image.copy()
        # Qt doesn't directly save to Python file objects, use temporary conversion
        # instead save via PNG format in memory
        from PySide6.QtCore import QByteArray, QIODevice, QBuffer

        byte_array = QByteArray()
        buffer_qBuf = QBuffer(byte_array)
        buffer_qBuf.open(QIODevice.WriteOnly)
        image_copy.save(buffer_qBuf, "PNG")
        buffer_qBuf.close()

        return base64.b64encode(byte_array.data()).decode("utf-8")

    @staticmethod
    def load_image_from_base64(data: str) -> Optional[QImage]:
        """Convert base64-encoded PNG back to QImage."""
        try:
            from PySide6.QtCore import QByteArray

            byte_data = base64.b64decode(data)
            byte_array = QByteArray(byte_data)
            image = QImage()
            image.loadFromData(byte_array, "PNG")
            return image if not image.isNull() else None
        except Exception:
            return None

    @staticmethod
    def save_image_as_base64(image: QImage) -> str:
        """Convert QImage to base64-encoded PNG."""
        buffer = io.BytesIO()
        image_copy = image.copy()
        # Qt doesn't directly save to Python file objects, use temporary conversion
        # instead save via PNG format in memory
        from PySide6.QtCore import QByteArray, QIODevice, QBuffer

        byte_array = QByteArray()
        buffer_qBuf = QBuffer(byte_array)
        buffer_qBuf.open(QIODevice.WriteOnly)
        image_copy.save(buffer_qBuf, "PNG")
        buffer_qBuf.close()

        return base64.b64encode(byte_array.data()).decode("utf-8")

    @staticmethod
    def load_image_from_base64(data: str) -> Optional[QImage]:
        """Convert base64-encoded PNG back to QImage."""
        try:
            from PySide6.QtCore import QByteArray

            byte_data = base64.b64decode(data)
            byte_array = QByteArray(byte_data)
            image = QImage()
            image.loadFromData(byte_array, "PNG")
            return image if not image.isNull() else None
        except Exception:
            return None

    @staticmethod
    def save_image_as_base64(image: QImage) -> str:
        """Convert QImage to base64-encoded PNG."""
        buffer = io.BytesIO()
        image_copy = image.copy()
        # Qt doesn't directly save to Python file objects, use temporary conversion
        # instead save via PNG format in memory
        from PySide6.QtCore import QByteArray, QIODevice, QBuffer

        byte_array = QByteArray()
        buffer_qBuf = QBuffer(byte_array)
        buffer_qBuf.open(QIODevice.WriteOnly)
        image_copy.save(buffer_qBuf, "PNG")
        buffer_qBuf.close()

        return base64.b64encode(byte_array.data()).decode("utf-8")

    @staticmethod
    def load_image_from_base64(data: str) -> Optional[QImage]:
        """Convert base64-encoded PNG back to QImage."""
        try:
            from PySide6.QtCore import QByteArray

            byte_data = base64.b64decode(data)
            byte_array = QByteArray(byte_data)
            image = QImage()
            image.loadFromData(byte_array, "PNG")
            return image if not image.isNull() else None
        except Exception:
            return None
