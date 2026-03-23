from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import os
import random
import time
from collections import deque
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QEvent, QEasingCurve, QMetaObject, QPoint, QPropertyAnimation, QRect, QSequentialAnimationGroup, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.models import Track
from app.common import get_logger
from app.ui.theme import get_theme
from app.ui.widgets import BoldSelectedItemDelegate, ClickableLabel, GradientSelectedTextDelegate
from app.core.storage import (
    APP_DATA_DIR,
    init_database,
    load_playlists,
    load_playlists_db,
    load_settings,
    load_settings_db,
    load_tracks_cache,
    load_tracks_db,
    migrate_json_to_db,
    save_playlists,
    save_playlists_db,
    save_settings,
    save_settings_db,
    save_tracks_cache,
    save_tracks_db,
)

try:
    from mutagen import File as MutagenFile
except Exception:  # pragma: no cover - fallback path when mutagen backends are unavailable
    MutagenFile = None

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    _scan_result_ready = Signal(int, object)
    _backdrop_result_ready = Signal(int, str, object)
    _cover_result_ready = Signal(int, str, str, object)

    def __init__(self, container) -> None:
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Zune Offline")
        self._drag_offset: QPoint | None = None
        
        # Store DI container and services
        self._container = container
        self._library_service = container.get_library_service()
        self._playback_service = container.get_playback_service()
        self._playlist_service = container.get_playlist_service()

        # Initialize database
        init_database()
        try:
            migrate_json_to_db()
        except Exception:
            pass  # Migration may fail if data already migrated

        self.settings = load_settings_db()
        self.playlists = load_playlists_db()
        self.theme_name = "dark"
        self.settings["theme"] = "dark"

        self.tracks: list[Track] = []
        self.filtered_tracks: list[Track] = []
        self.current_index = -1
        self.repeat_mode = "off"
        self.shuffle_enabled = False
        self.current_track_id = ""
        self._backdrop_dirty = True
        self._backdrop_phase = 0
        self._backdrop_cache_key = ""
        self._backdrop_cache_pixmap: QPixmap | None = None
        self._track_list_index_by_id: dict[str, int] = {}
        self._now_queue_index_by_id: dict[str, int] = {}
        self._last_artist_selection = ""
        self._album_art_cache: dict[str, QPixmap] = {}
        self._album_release_cache: dict[str, float] = {}
        self._is_seeking = False
        self._seek_total_seconds = 0
        self._next_position_slider_update = 0.0
        self._next_position_label_update = 0.0
        self._is_window_fitted = False
        self._restore_geometry: QRect | None = None
        self._lock_full_size = True
        self._seek_visual_resume_timer = QTimer(self)
        self._seek_visual_resume_timer.setSingleShot(True)

        # Separate thread pools: playback is highest priority (isolated), UI lower priority
        cpu = os.cpu_count() or 4
        self._playback_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="zune-playback",
        )
        self._scan_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="zune-scan",
        )
        self._backdrop_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, min(2, cpu // 2)),
            thread_name_prefix="zune-backdrop",
        )
        
        # Filter debounce timer: avoid blocking on every keystroke
        self._filter_debounce_timer = QTimer(self)
        self._filter_debounce_timer.setSingleShot(True)
        self._filter_debounce_timer.setInterval(300)  # 300ms debounce
        self._filter_debounce_timer.timeout.connect(self._apply_filter_deferred)
        self._scan_job_id = 0
        
        # Lightweight position polling to keep playback thread responsive (prevents audio stutter on UI updates)
        self._position_poll_timer = QTimer(self)
        self._position_poll_timer.setInterval(300)  # Poll every 300ms
        self._position_poll_timer.timeout.connect(self._keep_playback_responsive)
        self._position_poll_timer.start()
        
        self._scan_result_ready.connect(self._apply_scan_result)
        
        # Store current filter state for debounce
        self._pending_filter_query = ""
        self._pending_filter_artist = ""
        self._pending_filter_album = ""

        # Use PlaybackService from DI container instead of old AudioPlayer
        # self.player = AudioPlayer() - REMOVED: use self._playback_service instead
        self._track_anim_refs: list[QPropertyAnimation] = []

        self._build_ui()
        self._apply_theme()
        self._wire_events()
        self._load_playlists_ui()
        self._load_cached_library()
        self._scan_library()

        # Set initial volume via service
        self._playback_service.set_volume(int(self.settings.get("volume", 85)))
        self.volume_slider.setValue(int(self.settings.get("volume", 85)))
        self.np_volume_slider.setValue(int(self.settings.get("volume", 85)))

        self._set_play_pause_visual(False)
        self._sync_mode_buttons()
        self._switch_view(0, animate=False)
        QTimer.singleShot(0, self._apply_launch_full_size_lock)

        self._intro_animation = QPropertyAnimation(self, b"windowOpacity")
        self._intro_animation.setDuration(260)
        self._intro_animation.setStartValue(0.2)
        self._intro_animation.setEndValue(1.0)
        self._intro_animation.start()

    def _apply_launch_full_size_lock(self) -> None:
        if not self._lock_full_size:
            return
        self._apply_fitted_geometry()
        self.setMinimumSize(self.size())
        self.setMaximumSize(self.size())
        self._is_window_fitted = True
        self.max_btn.setText("O")
        self.np_max_btn.setText("O")

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        shell = QVBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.top_accent = QFrame()
        self.top_accent.setObjectName("topAccent")
        self.top_accent.setFixedHeight(5)
        shell.addWidget(self.top_accent)

        self.top_region = QWidget()
        self.top_region.setObjectName("topRegion")
        top_layout = QHBoxLayout(self.top_region)
        top_layout.setContentsMargins(20, 10, 10, 10)
        top_layout.setSpacing(10)

        self.library_view_btn = self._make_menu_button("Library", "menuTabButton", active=True)
        self.now_view_btn = self._make_menu_button("Now Playing", "menuTabButton", active=False)
        self.settings_view_btn = self._make_menu_button("Settings", "menuTabButton", active=False)

        top_layout.addWidget(self.now_view_btn)
        top_layout.addWidget(self.library_view_btn)
        top_layout.addWidget(self.settings_view_btn)
        top_layout.addStretch(1)

        self.min_btn = QPushButton("_")
        self.min_btn.setObjectName("winControl")
        self.max_btn = QPushButton("[]")
        self.max_btn.setObjectName("winControl")
        self.close_btn = QPushButton("X")
        self.close_btn.setObjectName("winClose")
        top_layout.addWidget(self.min_btn)
        top_layout.addWidget(self.max_btn)
        top_layout.addWidget(self.close_btn)

        shell.addWidget(self.top_region)

        self.main_stack = QStackedWidget()
        self.main_stack.addWidget(self._build_library_page())
        self.main_stack.addWidget(self._build_now_playing_page())
        self.main_stack.addWidget(self._build_settings_page())
        shell.addWidget(self.main_stack, 1)

        self._refresh_folders_label()

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(12)

        heading = QLabel("Settings")
        heading.setObjectName("settingsHeading")
        details = QLabel("Library folders and playback preferences")
        details.setObjectName("settingsSubheading")

        panel = QWidget()
        panel.setObjectName("frostPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(10)
        panel_layout.addWidget(QLabel("Library folders"))
        self.settings_folders_list = QListWidget()
        self.settings_folders_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.settings_folders_list.setFrameShape(QFrame.NoFrame)
        self.settings_folders_list.setFocusPolicy(Qt.NoFocus)
        self.settings_folders_list.setMinimumHeight(180)
        panel_layout.addWidget(self.settings_folders_list, 1)
        self.settings_scan_btn = QPushButton("Rescan")
        self.settings_add_folder_btn = QPushButton("Add Folder")
        self.settings_remove_folder_btn = QPushButton("Remove Selected Folder")
        self.settings_clear_folders_btn = QPushButton("Clear All Folders")
        panel_layout.addWidget(self.settings_scan_btn)
        panel_layout.addWidget(self.settings_add_folder_btn)
        panel_layout.addWidget(self.settings_remove_folder_btn)
        panel_layout.addWidget(self.settings_clear_folders_btn)
        panel_layout.addStretch(1)

        layout.addWidget(heading)
        layout.addWidget(details)
        layout.addWidget(panel, 1)
        return page

    def _build_library_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("libraryPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 16, 26, 18)
        layout.setSpacing(14)

        command_row = QWidget()
        command_row.setObjectName("frostPanel")
        command_layout = QHBoxLayout(command_row)
        command_layout.setContentsMargins(10, 10, 10, 10)
        command_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search artists, albums, songs")
        self.search_input.setMinimumWidth(320)

        command_layout.addWidget(self.search_input, 1)
        layout.addWidget(command_row)

        self.scope_buttons = []

        columns = QSplitter(Qt.Horizontal)
        columns.setObjectName("libraryColumns")

        artists_col = QWidget()
        artists_layout = QVBoxLayout(artists_col)
        artists_layout.setContentsMargins(0, 0, 0, 0)
        artists_layout.setSpacing(6)
        artists_header = QHBoxLayout()
        self.artists_count_label = QPushButton("0 ARTISTS")
        self.artists_count_label.setObjectName("columnTitleButton")
        self.artist_sort_btn = QPushButton("A-Z")
        self.artist_sort_btn.setObjectName("sortInlineButton")
        artists_header.addWidget(self.artists_count_label)
        artists_header.addWidget(self.artist_sort_btn)
        artists_header.addStretch(1)
        self.artist_list = QListWidget()
        self.artist_list.setObjectName("artistList")
        self.artist_list.setUniformItemSizes(True)
        self.artist_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.artist_list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.artist_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.artist_list.setFrameShape(QFrame.NoFrame)
        self.artist_list.setFocusPolicy(Qt.NoFocus)
        self.artist_list.setItemDelegate(BoldSelectedItemDelegate(self.artist_list))
        artists_layout.addLayout(artists_header)
        artists_layout.addWidget(self.artist_list, 1)

        albums_col = QWidget()
        albums_layout = QVBoxLayout(albums_col)
        albums_layout.setContentsMargins(0, 0, 0, 0)
        albums_layout.setSpacing(6)
        albums_header = QHBoxLayout()
        self.albums_count_label = QPushButton("0 ALBUMS")
        self.albums_count_label.setObjectName("columnTitleButton")
        self.album_sort_btn = QPushButton("A-Z")
        self.album_sort_btn.setObjectName("sortInlineButton")
        albums_header.addWidget(self.albums_count_label)
        albums_header.addWidget(self.album_sort_btn)
        albums_header.addStretch(1)
        self.album_list = QListWidget()
        self.album_list.setObjectName("albumList")
        self.album_list.setUniformItemSizes(True)
        self.album_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.album_list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.album_list.setViewMode(QListView.IconMode)
        self.album_list.setResizeMode(QListView.Adjust)
        self.album_list.setMovement(QListView.Static)
        self.album_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.album_list.setFrameShape(QFrame.NoFrame)
        self.album_list.setFocusPolicy(Qt.NoFocus)
        self.album_list.setWrapping(True)
        self.album_list.setSpacing(10)
        self.album_list.setIconSize(QSize(92, 92))
        self.album_list.setGridSize(QSize(126, 138))
        albums_layout.addLayout(albums_header)
        albums_layout.addWidget(self.album_list, 1)

        songs_col = QWidget()
        songs_layout = QVBoxLayout(songs_col)
        songs_layout.setContentsMargins(0, 0, 0, 0)
        songs_layout.setSpacing(6)
        songs_header = QHBoxLayout()
        self.songs_count_label = QPushButton("0 SONGS")
        self.songs_count_label.setObjectName("columnTitleButton")
        self.song_sort_btn = QPushButton("A-Z")
        self.song_sort_btn.setObjectName("sortInlineButton")
        songs_header.addWidget(self.songs_count_label)
        songs_header.addWidget(self.song_sort_btn)
        songs_header.addStretch(1)
        self.track_list = QListWidget()
        self.track_list.setObjectName("trackList")
        self.track_list.setUniformItemSizes(True)
        self.track_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.track_list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.track_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.track_list.setFrameShape(QFrame.NoFrame)
        self.track_list.setFocusPolicy(Qt.NoFocus)
        self.track_list.setItemDelegate(BoldSelectedItemDelegate(self.track_list))
        songs_layout.addLayout(songs_header)
        songs_layout.addWidget(self.track_list, 1)

        columns.addWidget(artists_col)
        columns.addWidget(albums_col)
        columns.addWidget(songs_col)
        columns.setStretchFactor(0, 1)
        columns.setStretchFactor(1, 2)
        columns.setStretchFactor(2, 2)

        layout.addWidget(columns, 1)

        transport = QWidget()
        transport.setObjectName("libraryTransport")
        transport_layout = QGridLayout(transport)
        transport_layout.setContentsMargins(12, 12, 12, 10)
        transport_layout.setHorizontalSpacing(12)
        transport_layout.setVerticalSpacing(7)
        transport_layout.setColumnStretch(1, 1)

        self.now_playing_label = ClickableLabel("Nothing playing")
        self.now_playing_label.setObjectName("libraryTrackTitle")
        self.now_playing_label.setCursor(Qt.PointingHandCursor)
        self.now_meta_label = ClickableLabel("-")
        self.now_meta_label.setObjectName("libraryTrackMeta")
        self.now_meta_label.setCursor(Qt.PointingHandCursor)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setObjectName("roundProgressSlider")
        self.position_slider.setRange(0, 1000)
        self.position_label = QLabel("00:00 / 00:00")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.repeat_btn = self._make_icon_button("repeat", hero=True)
        self.prev_btn = self._make_icon_button("prev", hero=True)
        self.play_pause_btn = self._make_icon_button("play", hero=True, primary=True)
        self.next_btn = self._make_icon_button("next", hero=True)
        self.shuffle_btn = self._make_icon_button("shuffle", hero=True)
        self.shuffle_btn.setToolTip("Shuffle")
        self.repeat_btn.setToolTip("Repeat")
        controls_widget = QWidget()
        controls_widget_layout = QHBoxLayout(controls_widget)
        controls_widget_layout.setContentsMargins(0, 0, 0, 0)
        controls_widget_layout.setSpacing(8)
        controls_widget_layout.addWidget(self.repeat_btn)
        controls_widget_layout.addWidget(self.prev_btn)
        controls_widget_layout.addWidget(self.play_pause_btn)
        controls_widget_layout.addWidget(self.next_btn)
        controls_widget_layout.addWidget(self.shuffle_btn)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("roundVolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(85)
        self.volume_slider.setFixedWidth(130)
        vol_label = QLabel("VOL")
        self.lib_mini_cover_label = QLabel()
        self.lib_mini_cover_label.setObjectName("libMiniCover")
        self.lib_mini_cover_label.setFixedSize(40, 40)
        self.lib_mini_cover_label.setScaledContents(True)

        controls.addStretch(1)
        controls.addWidget(controls_widget)
        controls.addStretch(1)
        controls.addWidget(vol_label)
        controls.addWidget(self.volume_slider)

        transport_layout.addWidget(self.lib_mini_cover_label, 0, 0, 2, 1)
        transport_layout.addWidget(self.now_playing_label, 0, 1)
        transport_layout.addWidget(self.now_meta_label, 1, 1)
        transport_layout.addWidget(self.position_slider, 2, 0, 1, 2)
        transport_layout.addWidget(self.position_label, 2, 2)
        transport_layout.addLayout(controls, 3, 0, 1, 3)
        layout.addWidget(transport)

        self.folders_label = QLabel()
        self.folders_label.setWordWrap(True)
        self.playlist_list = QListWidget()
        return page

    def _build_now_playing_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("nowPlayingPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        canvas = QWidget()
        canvas_layout = QGridLayout(canvas)
        canvas_layout.setContentsMargins(0, 0, 0, 0)

        self.now_bg_label = QLabel()
        self.now_bg_label.setScaledContents(True)
        canvas_layout.addWidget(self.now_bg_label, 0, 0)

        self.now_bg_prev_label = QLabel()
        self.now_bg_prev_label.setScaledContents(True)
        self.now_bg_prev_label.hide()
        canvas_layout.addWidget(self.now_bg_prev_label, 0, 0)

        self._now_bg_prev_effect = QGraphicsOpacityEffect(self.now_bg_prev_label)
        self.now_bg_prev_label.setGraphicsEffect(self._now_bg_prev_effect)
        self._bg_crossfade_anim: QPropertyAnimation | None = None

        overlay = QWidget()
        overlay.setObjectName("nowOverlay")
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(28, 20, 28, 18)
        overlay_layout.setSpacing(18)

        top_row = QHBoxLayout()
        self.now_back_btn = QPushButton("< Back")
        self.now_back_btn.setObjectName("nowBackButton")
        top_row.addWidget(self.now_back_btn)
        top_row.addStretch(1)
        self.np_min_btn = QPushButton("_")
        self.np_min_btn.setObjectName("winControl")
        self.np_max_btn = QPushButton("[]")
        self.np_max_btn.setObjectName("winControl")
        self.np_close_btn = QPushButton("X")
        self.np_close_btn.setObjectName("winClose")
        top_row.addWidget(self.np_min_btn)
        top_row.addWidget(self.np_max_btn)
        top_row.addWidget(self.np_close_btn)
        overlay_layout.addLayout(top_row)

        overlay_layout.addSpacing(8)

        # Add stretch to push content to bottom
        overlay_layout.addStretch(1)

        # Main content area: album art (left) + queue list (right) side by side
        content_area = QHBoxLayout()
        content_area.setSpacing(18)
        content_area.setContentsMargins(0, 0, 0, 0)

        # Left side: album cover + info
        cover_info_row = QHBoxLayout()
        cover_info_row.setSpacing(16)
        cover_info_row.setContentsMargins(0, 0, 0, 0)

        self.np_cover_label = QLabel()
        self.np_cover_label.setObjectName("npCover")
        self.np_cover_label.setFixedSize(170, 170)
        cover_info_row.addWidget(self.np_cover_label, 0, Qt.AlignTop)

        # Info text next to album cover (top-aligned)
        info_stack = QVBoxLayout()
        info_stack.setSpacing(0)
        info_stack.setContentsMargins(8, 0, 0, 0)

        # Create info labels (artist, title, album)
        self.np_artist_label = QLabel("UNKNOWN ARTIST")
        self.np_artist_label.setObjectName("npArtist")
        self.np_title_label = QLabel("Nothing Playing")
        self.np_title_label.setObjectName("npTitle")
        self.np_title_label.setWordWrap(True)
        self.np_album_label = QLabel("UNKNOWN ALBUM")
        self.np_album_label.setObjectName("npAlbum")

        info_stack.addWidget(self.np_artist_label)
        info_stack.addWidget(self.np_title_label)
        info_stack.addWidget(self.np_album_label)
        cover_info_row.addLayout(info_stack)
        
        # Wrap album + text and bottom-align them so they don't stretch to queue height
        left_section = QWidget()
        left_section.setLayout(cover_info_row)
        content_area.addWidget(left_section, 0, Qt.AlignBottom)

        # Right side: queue list
        self.now_queue_list = QListWidget()
        self.now_queue_list.setObjectName("nowQueueList")
        self.now_queue_list.setUniformItemSizes(True)
        self.now_queue_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.now_queue_list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.now_queue_list.setSpacing(6)
        self.now_queue_list.setContentsMargins(0, 0, 0, 0)
        self.now_queue_list.setViewportMargins(0, 0, 0, 0)
        self.now_queue_list.setItemDelegate(GradientSelectedTextDelegate(self.now_queue_list))
        self.now_queue_list.setFrameShape(QFrame.NoFrame)
        self.now_queue_list.setFocusPolicy(Qt.NoFocus)
        self.now_queue_list.setMinimumWidth(260)
        self.now_queue_list.setMaximumWidth(450)
        self.now_queue_list.setMinimumHeight(500)
        self.now_queue_list.setMaximumHeight(500)
        content_area.addWidget(self.now_queue_list, 0)

        # Wrap content_area in a widget so stretch factor works properly
        content_wrapper = QWidget()
        content_wrapper.setLayout(content_area)
        overlay_layout.addWidget(content_wrapper, 0)

        # Bottom section: media controls
        bottom_section = QWidget()
        bottom_section_layout = QVBoxLayout(bottom_section)
        bottom_section_layout.setContentsMargins(0, 0, 0, 0)
        bottom_section_layout.setSpacing(0)

        # Media controls below
        transport = QWidget()
        transport.setObjectName("npTransport")
        transport_layout = QVBoxLayout(transport)
        transport_layout.setContentsMargins(0, 12, 0, 12)
        transport_layout.setSpacing(10)

        seek_row = QHBoxLayout()
        self.np_position_slider = QSlider(Qt.Horizontal)
        self.np_position_slider.setObjectName("roundProgressSlider")
        self.np_position_slider.setRange(0, 1000)
        self.np_position_label = QLabel("00:00 / 00:00")
        self.np_position_label.setObjectName("npPositionLabel")
        seek_row.addWidget(self.np_position_slider, 1)
        seek_row.addWidget(self.np_position_label)
        transport_layout.addLayout(seek_row)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        self.np_repeat_btn = self._make_icon_button("repeat", hero=True)
        self.np_prev_btn = self._make_icon_button("prev", hero=True)
        self.np_play_pause_btn = self._make_icon_button("play", hero=True, primary=True)
        self.np_next_btn = self._make_icon_button("next", hero=True)
        self.np_shuffle_btn = self._make_icon_button("shuffle", hero=True)
        np_controls_widget = QWidget()
        np_controls_layout = QHBoxLayout(np_controls_widget)
        np_controls_layout.setContentsMargins(0, 0, 0, 0)
        np_controls_layout.setSpacing(10)
        np_controls_layout.addWidget(self.np_repeat_btn)
        np_controls_layout.addWidget(self.np_prev_btn)
        np_controls_layout.addWidget(self.np_play_pause_btn)
        np_controls_layout.addWidget(self.np_next_btn)
        np_controls_layout.addWidget(self.np_shuffle_btn)

        np_vol_label = QLabel("VOL")
        self.np_volume_slider = QSlider(Qt.Horizontal)
        self.np_volume_slider.setObjectName("roundVolumeSlider")
        self.np_volume_slider.setRange(0, 100)
        self.np_volume_slider.setFixedWidth(140)

        controls.addStretch(1)
        controls.addWidget(np_controls_widget)
        controls.addStretch(1)
        controls.addWidget(np_vol_label)
        controls.addWidget(self.np_volume_slider)

        transport_layout.addLayout(controls)
        bottom_section_layout.addWidget(transport)

        overlay_layout.addWidget(bottom_section)

        canvas_layout.addWidget(overlay, 0, 0)
        page_layout.addWidget(canvas, 1)
        return page

    def _wire_events(self) -> None:
        self.settings_scan_btn.clicked.connect(self._scan_library)
        self.settings_add_folder_btn.clicked.connect(self._add_folder)
        self.settings_remove_folder_btn.clicked.connect(self._remove_selected_folder)
        self.settings_clear_folders_btn.clicked.connect(self._clear_folders)
        # Debounce text input to avoid blocking on every keystroke
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.artists_count_label.clicked.connect(lambda: self._reset_library_selection("artists"))
        self.albums_count_label.clicked.connect(lambda: self._reset_library_selection("albums"))
        self.songs_count_label.clicked.connect(lambda: self._reset_library_selection("songs"))
        self.artist_sort_btn.clicked.connect(lambda: self._cycle_sort_mode("artist"))
        self.album_sort_btn.clicked.connect(lambda: self._cycle_sort_mode("album"))
        self.song_sort_btn.clicked.connect(lambda: self._cycle_sort_mode("song"))

        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self._toggle_max_restore)
        self.close_btn.clicked.connect(self.close)
        self.np_min_btn.clicked.connect(self.showMinimized)
        self.np_max_btn.clicked.connect(self._toggle_max_restore)
        self.np_close_btn.clicked.connect(self.close)

        # Debounce artist/album selection changes as well
        self.artist_list.itemSelectionChanged.connect(self._on_artist_selected)
        self.album_list.itemSelectionChanged.connect(self._on_album_selected)
        self.track_list.itemClicked.connect(self._on_track_clicked)
        self.now_queue_list.itemClicked.connect(self._on_now_queue_clicked)

        self.prev_btn.clicked.connect(self._play_previous)
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.next_btn.clicked.connect(self._play_next)
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        self.repeat_btn.clicked.connect(self._toggle_repeat)

        self.np_prev_btn.clicked.connect(self._play_previous)
        self.np_play_pause_btn.clicked.connect(self._toggle_play_pause)
        self.np_next_btn.clicked.connect(self._play_next)
        self.np_shuffle_btn.clicked.connect(self._toggle_shuffle)
        self.np_repeat_btn.clicked.connect(self._toggle_repeat)

        self.position_slider.sliderReleased.connect(self._seek)
        self.np_position_slider.sliderReleased.connect(self._seek)
        self.position_slider.sliderPressed.connect(self._on_seek_pressed)
        self.np_position_slider.sliderPressed.connect(self._on_seek_pressed)
        self.position_slider.sliderMoved.connect(self._on_seek_moved)
        self.np_position_slider.sliderMoved.connect(self._on_seek_moved)
        self.volume_slider.valueChanged.connect(self._set_volume)
        self.np_volume_slider.valueChanged.connect(self._set_volume)

        self.now_back_btn.clicked.connect(lambda: self._switch_view(0, animate=True))
        self.library_view_btn.clicked.connect(lambda: self._switch_view(0, animate=True))
        self.now_view_btn.clicked.connect(lambda: self._switch_view(1, animate=False))
        self.settings_view_btn.clicked.connect(lambda: self._switch_view(2, animate=True))

    def _clear_scope_selection(self, scope: str) -> None:
        if scope == "artists":
            self._clear_list_selection(self.artist_list)
            self._clear_list_selection(self.album_list)
            self._clear_list_selection(self.track_list)
        elif scope == "albums":
            self._clear_list_selection(self.album_list)
            self._clear_list_selection(self.track_list)
        else:
            self._clear_list_selection(self.track_list)

        self.scope_artists_btn.setProperty("active", scope == "artists")
        self.scope_albums_btn.setProperty("active", scope == "albums")
        self.scope_songs_btn.setProperty("active", scope == "songs")
        self._refresh_scope_style()
        self._apply_filter()

    @staticmethod
    def _clear_list_selection(widget: QListWidget) -> None:
        widget.blockSignals(True)
        widget.clearSelection()
        widget.setCurrentItem(None)
        widget.setCurrentRow(-1)
        widget.clearFocus()
        widget.blockSignals(False)

    def _toggle_theme(self) -> None:
        self.theme_name = "dark"
        self.settings["theme"] = self.theme_name
        self._apply_theme()

    def _toggle_max_restore(self) -> None:
        if self._lock_full_size:
            self._apply_launch_full_size_lock()
            return
        if self._is_window_fitted:
            if self._restore_geometry is not None:
                self.setGeometry(self._restore_geometry)
            self._is_window_fitted = False
            self.max_btn.setText("[]")
            self.np_max_btn.setText("[]")
            return

        self._restore_geometry = self.geometry()
        center = self.frameGeometry().center()
        screen = QGuiApplication.screenAt(center)
        if screen is None and self.windowHandle() is not None:
            screen = self.windowHandle().screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return

        # availableGeometry excludes taskbar/work-area reservations.
        self._apply_fitted_geometry(screen)
        self._is_window_fitted = True
        self.max_btn.setText("O")
        self.np_max_btn.setText("O")

    def _apply_fitted_geometry(self, screen=None) -> None:
        target_screen = screen
        if target_screen is None:
            center = self.frameGeometry().center()
            target_screen = QGuiApplication.screenAt(center)
        if target_screen is None and self.windowHandle() is not None:
            target_screen = self.windowHandle().screen()
        if target_screen is None:
            target_screen = QGuiApplication.primaryScreen()
        if target_screen is None:
            return
        self.setGeometry(target_screen.availableGeometry())

    def _enforce_non_fullscreen(self) -> None:
        if self._lock_full_size:
            self._apply_launch_full_size_lock()
            return
        state = self.windowState()
        forbidden = Qt.WindowMaximized | Qt.WindowFullScreen
        if state & forbidden:
            self.setWindowState(state & ~forbidden)
            self.showNormal()
            if self._is_window_fitted:
                self._apply_fitted_geometry()

    def _apply_theme(self) -> None:
        self.theme_name = "dark"
        self.settings["theme"] = "dark"
        self.setStyleSheet(get_theme("dark"))
        self._refresh_icon_set()

    def _refresh_icon_set(self) -> None:
        active = QColor("#ffffff") if self.theme_name == "dark" else QColor("#1f2127")
        self.prev_btn.setIcon(self._make_icon("prev", active))
        self.next_btn.setIcon(self._make_icon("next", active))
        self.shuffle_btn.setIcon(self._make_icon("shuffle", active))
        self.repeat_btn.setIcon(self._make_icon("repeat", active))

        np_active = QColor("#ffffff")
        self.np_prev_btn.setIcon(self._make_icon("prev", np_active))
        self.np_next_btn.setIcon(self._make_icon("next", np_active))
        self.np_shuffle_btn.setIcon(self._make_icon("shuffle", np_active))
        self.np_repeat_btn.setIcon(self._make_icon("repeat", np_active))

        self._set_play_pause_visual(self._playback_service.state.is_playing)
        self._sync_mode_buttons()

    def _switch_view(self, index: int, animate: bool) -> None:
        if index == 1:
            self._enforce_non_fullscreen()
        if self.main_stack.currentIndex() == index:
            return

        current = self.main_stack.currentWidget()

        def _apply_target() -> None:
            self.main_stack.setCurrentIndex(index)
            now_playing = index == 1
            self.top_region.setVisible(not now_playing)
            self.top_accent.setVisible(not now_playing)
            self.library_view_btn.setVisible(not now_playing)
            self.now_view_btn.setVisible(not now_playing)
            self.settings_view_btn.setVisible(not now_playing)
            self.library_view_btn.setProperty("active", index == 0)
            self.now_view_btn.setProperty("active", index == 1)
            self.settings_view_btn.setProperty("active", index == 2)
            self._refresh_toggle_style()
            if index == 1:
                if self.current_track_id:
                    self._sync_now_queue_selection(self.current_track_id)

        if not animate:
            _apply_target()
            return

        out_effect = current.graphicsEffect()
        if not isinstance(out_effect, QGraphicsOpacityEffect):
            out_effect = QGraphicsOpacityEffect(current)
            current.setGraphicsEffect(out_effect)

        out_anim = QPropertyAnimation(out_effect, b"opacity", self)
        out_anim.setDuration(180)
        out_anim.setEasingCurve(QEasingCurve.InOutCubic)
        out_anim.setStartValue(1.0)
        out_anim.setEndValue(0.0)

        def _switch_and_fade_in() -> None:
            _apply_target()
            target = self.main_stack.currentWidget()
            in_effect = target.graphicsEffect()
            if not isinstance(in_effect, QGraphicsOpacityEffect):
                in_effect = QGraphicsOpacityEffect(target)
                target.setGraphicsEffect(in_effect)

            in_anim = QPropertyAnimation(in_effect, b"opacity", self)
            in_anim.setDuration(240)
            in_anim.setEasingCurve(QEasingCurve.InOutCubic)
            in_anim.setStartValue(0.0)
            in_anim.setEndValue(1.0)

            def _cleanup() -> None:
                target.setGraphicsEffect(None)
                current.setGraphicsEffect(None)

            in_anim.finished.connect(_cleanup)
            self._page_fade = in_anim
            in_anim.start()

        out_anim.finished.connect(_switch_and_fade_in)
        self._page_fade = out_anim
        out_anim.start()

    def _refresh_toggle_style(self) -> None:
        self.library_view_btn.style().unpolish(self.library_view_btn)
        self.library_view_btn.style().polish(self.library_view_btn)
        self.now_view_btn.style().unpolish(self.now_view_btn)
        self.now_view_btn.style().polish(self.now_view_btn)
        self.settings_view_btn.style().unpolish(self.settings_view_btn)
        self.settings_view_btn.style().polish(self.settings_view_btn)

    def _refresh_scope_style(self) -> None:
        for btn in self.scope_buttons:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _fade_widgets(self, widgets: list[QWidget]) -> None:
        for widget in widgets:
            effect = widget.graphicsEffect()
            if not isinstance(effect, QGraphicsOpacityEffect):
                effect = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(effect)

            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(170)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(0.32)
            anim.setEndValue(1.0)

            def _cleanup(w: QWidget = widget, a: QPropertyAnimation = anim) -> None:
                w.setGraphicsEffect(None)
                if a in self._track_anim_refs:
                    self._track_anim_refs.remove(a)

            self._track_anim_refs.append(anim)
            anim.finished.connect(_cleanup)
            anim.start()

    def _scan_library(self) -> None:
        folders = self.settings.get("scan_folders", [])
        self._scan_job_id += 1
        job_id = self._scan_job_id

        def _on_done(future: concurrent.futures.Future) -> None:
            self._scan_result_ready.emit(job_id, future)

        future = self._scan_executor.submit(self._library_service.scan_folders, folders)
        future.add_done_callback(_on_done)

    def _get_backdrop_render_size(self) -> tuple[int, int]:
        """Get screen size for backdrop generation."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            size = screen.geometry().size()
            return (max(640, size.width()), max(380, size.height()))
        return (1920, 1080)  # Fallback to common fullscreen size

    def _apply_scan_result(self, job_id: int, future: concurrent.futures.Future) -> None:
        if job_id != self._scan_job_id:
            return

        try:
            tracks = future.result()
        except Exception:
            tracks = []

        self.tracks = tracks
        if tracks:
            save_tracks_db(tracks)
        self._album_art_cache.clear()
        self._album_release_cache.clear()
        self._apply_filter()

    def _load_cached_library(self) -> None:
        cached = load_tracks_db()
        if not cached:
            return
        self.tracks = cached
        self._apply_filter()

    def _on_search_text_changed(self) -> None:
        """Debounce search input to avoid blocking on every keystroke."""
        self._filter_debounce_timer.stop()
        self._filter_debounce_timer.start()
    
    def _on_artist_selected(self) -> None:
        """Debounce artist selection changes."""
        self._filter_debounce_timer.stop()
        self._filter_debounce_timer.start()
    
    def _on_album_selected(self) -> None:
        """Debounce album selection changes."""
        self._filter_debounce_timer.stop()
        self._filter_debounce_timer.start()

    def _apply_filter_deferred(self) -> None:
        """Apply filter after debounce period (deferred to avoid blocking UI)."""
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        previous_artist = self.artist_list.currentItem().text() if self.artist_list.currentItem() else ""
        selected_album = self.album_list.currentItem().data(Qt.UserRole) if self.album_list.currentItem() else ""

        if not query:
            base_tracks = list(self.tracks)
        else:
            base_tracks = [
                t
                for t in self.tracks
                if query in t.title.lower() or query in t.artist.lower() or query in t.album.lower()
            ]

        artists = self._sort_artists(list({t.artist for t in base_tracks if t.artist}))
        self._refresh_simple_list(self.artist_list, artists, previous_artist)

        selected_artist = self.artist_list.currentItem().text() if self.artist_list.currentItem() else ""
        if selected_artist != self._last_artist_selection:
            selected_album = ""
        self._last_artist_selection = selected_artist

        artist_tracks = [t for t in base_tracks if not selected_artist or t.artist == selected_artist]
        albums = self._sort_albums(list({t.album for t in artist_tracks if t.album}), artist_tracks)
        self._refresh_album_list(albums, selected_album, artist_tracks)

        selected_album = self.album_list.currentItem().data(Qt.UserRole) if self.album_list.currentItem() else ""

        filtered_tracks = [
            t
            for t in artist_tracks
            if not selected_album or t.album == selected_album
        ]
        self.filtered_tracks = self._sort_tracks(filtered_tracks)

        self.artists_count_label.setText(f"{len(artists)} ARTISTS A-Z")
        self.albums_count_label.setText(f"{len(albums)} ALBUMS")
        self.songs_count_label.setText(f"{len(self.filtered_tracks)} SONGS")

        self.track_list.setUpdatesEnabled(False)
        self.track_list.blockSignals(True)
        self.track_list.clear()
        self._track_list_index_by_id.clear()
        for row_index, track in enumerate(self.filtered_tracks):
            row = QListWidgetItem(f"{track.title}    |    {track.artist}    |    {track.duration_label}")
            row.setData(Qt.UserRole, track.track_id)
            self.track_list.addItem(row)
            self._track_list_index_by_id[track.track_id] = row_index
        self.track_list.blockSignals(False)
        self.track_list.setUpdatesEnabled(True)

        if self.current_track_id:
            self._sync_library_track_selection(self.current_track_id)

        self._populate_now_queue()

    def _refresh_simple_list(self, list_widget: QListWidget, values: list[str], selected: str) -> None:
        list_widget.blockSignals(True)
        list_widget.clear()
        for value in values:
            list_widget.addItem(value)

        if selected:
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.text() == selected:
                    list_widget.setCurrentItem(item)
                    break

        list_widget.blockSignals(False)

    def _refresh_album_list(self, albums: list[str], selected: str, source_tracks: list[Track]) -> None:
        album_tracks: dict[str, list[Track]] = {}
        for track in source_tracks:
            album_tracks.setdefault(track.album, []).append(track)

        self.album_list.blockSignals(True)
        self.album_list.clear()

        for name in albums:
            item = QListWidgetItem(self._album_icon(name, album_tracks.get(name, [])), name)
            item.setData(Qt.UserRole, name)
            self.album_list.addItem(item)

        if selected:
            for i in range(self.album_list.count()):
                item = self.album_list.item(i)
                if item.data(Qt.UserRole) == selected:
                    self.album_list.setCurrentItem(item)
                    break

        self.album_list.blockSignals(False)

    def _album_icon(self, name: str, tracks: list[Track] | None = None) -> QIcon:
        used_tracks = tracks or []
        key = self._album_art_cache_key(name, used_tracks, 92)
        if key in self._album_art_cache:
            return QIcon(self._album_art_cache[key])

        art = self._album_art_pixmap(name, used_tracks, 92)
        self._album_art_cache[key] = art
        return QIcon(art)

    @staticmethod
    def _album_art_cache_key(name: str, tracks: list[Track], size: int) -> str:
        if tracks:
            normalized = sorted(str(t.path).lower() for t in tracks)
            lead = "|".join(normalized[:4])
            return f"{name.lower().strip()}::{size}::{lead}::{len(normalized)}"
        return f"{name.lower().strip()}::{size}::fallback"

    def _album_art_pixmap(self, name: str, tracks: list[Track], size: int) -> QPixmap:
        # Without tracks, use gradient fallback only
        if not tracks:
            digest = hashlib.md5(name.encode("utf-8")).digest()
            pix = QPixmap(size, size)
            painter = QPainter(pix)
            grad = QLinearGradient(0, 0, size, size)
            grad.setColorAt(0.0, QColor(70 + digest[0] % 90, 16 + digest[1] % 35, 65 + digest[2] % 85))
            grad.setColorAt(0.5, QColor(138 + digest[3] % 60, 30 + digest[4] % 90, 118 + digest[5] % 80))
            grad.setColorAt(1.0, QColor(240, 108 + digest[6] % 55, 65 + digest[7] % 80))
            painter.fillRect(0, 0, size, size, grad)
            painter.fillRect(0, 0, size, size, QColor(0, 0, 0, 32))
            painter.setPen(QPen(QColor(255, 255, 255, 190), 1))
            painter.drawRect(0, 0, size - 1, size - 1)
            painter.end()
            return pix

        # Try embedded covers first (most album-specific)
        for track in tracks:
            embedded = self._extract_embedded_cover(track.path, size)
            if embedded is not None:
                return embedded

        # Try folder-level covers, checking each track's directories
        for track in tracks:
            # Check track's immediate parent (album folder)
            folder_art = self._find_folder_cover(track.path.parent)
            if folder_art is not None:
                return folder_art.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Check parent directory (often artist folder)
            parent_parent = track.path.parent.parent
            if parent_parent != track.path.parent:
                folder_art = self._find_folder_cover(parent_parent)
                if folder_art is not None:
                    return folder_art.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        # Fallback to gradient if no art found
        digest = hashlib.md5(name.encode("utf-8")).digest()
        pix = QPixmap(size, size)
        painter = QPainter(pix)
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(70 + digest[0] % 90, 16 + digest[1] % 35, 65 + digest[2] % 85))
        grad.setColorAt(0.5, QColor(138 + digest[3] % 60, 30 + digest[4] % 90, 118 + digest[5] % 80))
        grad.setColorAt(1.0, QColor(240, 108 + digest[6] % 55, 65 + digest[7] % 80))
        painter.fillRect(0, 0, size, size, grad)
        painter.fillRect(0, 0, size, size, QColor(0, 0, 0, 32))
        painter.setPen(QPen(QColor(255, 255, 255, 190), 1))
        painter.drawRect(0, 0, size - 1, size - 1)
        painter.end()
        return pix

    @staticmethod
    def _find_folder_cover(folder: Path) -> QPixmap | None:
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        prioritized_names = ["cover", "folder", "front", "album", "art", "thumb"]

        try:
            files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts]
        except OSError:
            logger.debug(f"Cannot read folder for covers: {folder}")
            return None

        if not files:
            return None

        def rank(path: Path) -> tuple[int, str]:
            lower = path.stem.lower()
            score = 50
            for i, name in enumerate(prioritized_names):
                if lower == name:
                    score = i
                    break
                if lower.startswith(name):
                    score = i + 8
                    break
                if name in lower:
                    score = i + 16
                    break
            return score, lower

        for candidate in sorted(files, key=rank):
            pix = QPixmap(str(candidate))
            if not pix.isNull():
                logger.debug(f"Found folder cover: {candidate}")
                return pix
        return None

    @staticmethod
    def _extract_embedded_cover(path: Path, size: int) -> QPixmap | None:
        if MutagenFile is None:
            return None

        try:
            audio = MutagenFile(path)
        except Exception:
            return None

        if audio is None:
            return None

        payload: bytes | None = None
        pictures = getattr(audio, "pictures", None)
        if pictures:
            for picture in pictures:
                data = getattr(picture, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    payload = bytes(data)
                    break

        tags = getattr(audio, "tags", None)
        if payload is None and tags is not None:
            for key in ("covr", "metadata_block_picture", "METADATA_BLOCK_PICTURE"):
                if key not in tags:
                    continue
                values = tags[key]
                if not isinstance(values, (list, tuple)):
                    values = [values]
                for entry in values:
                    if isinstance(entry, (bytes, bytearray)):
                        payload = bytes(entry)
                        break
                    if isinstance(entry, str):
                        try:
                            decoded = base64.b64decode(entry)
                        except Exception:
                            decoded = b""
                        if decoded:
                            payload = decoded
                            break
                if payload:
                    break

        # ASF/WMA stores pictures in WM/Picture binary blobs.
        if payload is None and tags is not None:
            for key in ("WM/Picture", "wm/picture"):
                if key not in tags:
                    continue
                values = tags[key]
                if not isinstance(values, (list, tuple)):
                    values = [values]
                for entry in values:
                    data = getattr(entry, "value", entry)
                    if isinstance(data, (bytes, bytearray)):
                        parsed = MainWindow._parse_asf_picture_blob(bytes(data))
                        if parsed:
                            payload = parsed
                            break
                if payload:
                    break

        if payload is None and tags is not None:
            for key, value in getattr(tags, "items", lambda: [])():
                if not str(key).upper().startswith("APIC"):
                    continue
                if isinstance(value, list):
                    for entry in value:
                        data = getattr(entry, "data", None)
                        if isinstance(data, (bytes, bytearray)):
                            payload = bytes(data)
                            break
                    if payload:
                        break
                data = getattr(value, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    payload = bytes(data)
                    break

        if payload is None and tags is not None:
            for value in getattr(tags, "values", lambda: [])():
                data = getattr(value, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    payload = bytes(data)
                    break

        if not payload:
            return None

        pix = QPixmap()
        if not pix.loadFromData(payload):
            return None
        return pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    @staticmethod
    def _parse_asf_picture_blob(blob: bytes) -> bytes | None:
        if len(blob) < 8:
            return None
        try:
            pos = 0
            pos += 1
            data_len = int.from_bytes(blob[pos:pos + 4], "little", signed=False)
            pos += 4

            # Skip MIME (UTF-16LE, null-terminated).
            while pos + 1 < len(blob):
                if blob[pos] == 0 and blob[pos + 1] == 0:
                    pos += 2
                    break
                pos += 2

            # Skip description (UTF-16LE, null-terminated).
            while pos + 1 < len(blob):
                if blob[pos] == 0 and blob[pos + 1] == 0:
                    pos += 2
                    break
                pos += 2

            if pos >= len(blob):
                return None

            data = blob[pos:pos + data_len]
            if data and len(data) >= 8:
                return data
        except Exception:
            return None
        return None

    def _play_at_index(self, index: int) -> None:
        if index < 0 or index >= len(self.filtered_tracks):
            return

        self.current_index = index
        track = self.filtered_tracks[index]
        self._sync_library_track_selection(track.track_id)
        self._sync_now_queue_selection(track.track_id)
        self.current_track_id = track.track_id
        try:
            self._playback_service.load_playlist([track])
            self._playback_service.play(0)
        except Exception as e:
            logger.error(f"Failed to play track: {e}")
        self._set_play_pause_visual(True)
        
        self.now_playing_label.setText(track.title)
        self.now_meta_label.setText(f"{track.artist} - {track.album}")
        self.settings["last_track"] = track.track_id

        self._update_now_playing_screen(track)

    def _sync_library_track_selection(self, track_id: str) -> None:
        row = self._track_list_index_by_id.get(track_id, -1)
        if row < 0 or row >= self.track_list.count():
            self.track_list.blockSignals(True)
            self.track_list.clearSelection()
            self.track_list.setCurrentRow(-1)
            self.track_list.blockSignals(False)
            return

        item = self.track_list.item(row)
        if item is None:
            return
        self.track_list.setCurrentItem(item)
        item_rect = self.track_list.visualItemRect(item)
        if not self.track_list.viewport().rect().contains(item_rect):
            self.track_list.scrollToItem(item, QAbstractItemView.EnsureVisible)

    def _sync_now_queue_selection(self, track_id: str) -> None:
        row = self._now_queue_index_by_id.get(track_id, -1)
        if row < 0 or row >= self.now_queue_list.count():
            return
        item = self.now_queue_list.item(row)
        if item is None:
            return
        self.now_queue_list.setCurrentItem(item)
        item_rect = self.now_queue_list.visualItemRect(item)
        if not self.now_queue_list.viewport().rect().contains(item_rect):
            self.now_queue_list.scrollToItem(item, QAbstractItemView.EnsureVisible)

    def _toggle_play_pause(self) -> None:
        if self.current_index < 0 and self.filtered_tracks:
            self._play_at_index(0)
            return

        try:
            if self._playback_service.state.is_playing:
                logger.info(f"[PAUSE] Pause clicked, current position: {self._playback_service.state.position_ms}ms")
                self._playback_service.pause()
                self._set_play_pause_visual(False)
            else:
                logger.info(f"[PAUSE] Resume clicked, current position: {self._playback_service.state.position_ms}ms")
                self._playback_service.resume()
                self._set_play_pause_visual(True)
        except Exception as e:
            logger.error(f"Failed to toggle playback: {e}")

    def _play_previous(self) -> None:
        if not self.filtered_tracks:
            return
        idx = self.current_index - 1 if self.current_index > 0 else len(self.filtered_tracks) - 1
        self._play_at_index(idx)

    def _play_next(self) -> None:
        if not self.filtered_tracks:
            return

        if self.shuffle_enabled:
            self._play_at_index(random.randrange(0, len(self.filtered_tracks)))
            return

        idx = self.current_index + 1
        if idx >= len(self.filtered_tracks):
            idx = 0
        self._play_at_index(idx)

    def _toggle_shuffle(self) -> None:
        self.shuffle_enabled = not self.shuffle_enabled
        self._sync_mode_buttons()

    def _toggle_repeat(self) -> None:
        modes = ["off", "single", "selection"]
        current = modes.index(self.repeat_mode)
        self.repeat_mode = modes[(current + 1) % len(modes)]
        self._sync_mode_buttons()

    def _sync_mode_buttons(self) -> None:
        shuffle_tip = "Shuffle: On" if self.shuffle_enabled else "Shuffle: Off"
        repeat_tip = {
            "off": "Repeat: Off",
            "single": "Repeat: Single Song",
            "selection": "Repeat: Selection",
        }[self.repeat_mode]

        self.shuffle_btn.setToolTip(shuffle_tip)
        self.np_shuffle_btn.setToolTip(shuffle_tip)
        self.repeat_btn.setToolTip(repeat_tip)
        self.np_repeat_btn.setToolTip(repeat_tip)

        shuffle_active = "true" if self.shuffle_enabled else "false"
        repeat_active = "true" if self.repeat_mode != "off" else "false"

        for btn in (self.shuffle_btn, self.np_shuffle_btn):
            btn.setProperty("active", shuffle_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        for btn in (self.repeat_btn, self.np_repeat_btn):
            btn.setProperty("active", repeat_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_play_pause_visual(self, playing: bool) -> None:
        color_main = QColor("#ffffff") if self.theme_name == "dark" else QColor("#1f2127")
        color_np = QColor("#ffffff")

        self.play_pause_btn.setIcon(self._make_icon("pause" if playing else "play", color_main))
        self.np_play_pause_btn.setIcon(self._make_icon("pause" if playing else "play", color_np))

        self.play_pause_btn.setToolTip("Pause" if playing else "Play")
        self.np_play_pause_btn.setToolTip("Pause" if playing else "Play")

    def _active_seek_slider(self):
        sender = self.sender()
        if sender is self.np_position_slider:
            return self.np_position_slider
        return self.position_slider

    def _sync_seek_slider_values(self, ratio: float) -> None:
        """Update seek sliders without blocking main thread during playback."""
        clamped = max(0.0, min(1.0, ratio))
        value = int(clamped * 1000)
        
        # Update sliders only if significantly changed (avoid excessive updates)
        current_value = self.position_slider.value()
        logger.debug(f"[SYNC] ratio={ratio:.3f}, new_value={value}, current_value={current_value}")
        if abs(current_value - value) < 5:  # Don't update if less than 0.5% change
            return
        
        self.position_slider.blockSignals(True)
        self.np_position_slider.blockSignals(True)
        self.position_slider.setValue(value)
        self.np_position_slider.setValue(value)
        self.position_slider.blockSignals(False)
        self.np_position_slider.blockSignals(False)
        logger.debug(f"[SYNC] Updated slider from {current_value} to {value}")

    def _set_seek_labels(self, ratio: float) -> None:
        clamped = max(0.0, min(1.0, ratio))
        total = self._seek_total_seconds if self._seek_total_seconds > 0 else max(0, int(self._playback_service.state.duration_ms / 1000))
        current = int(total * clamped)
        text = f"{self._to_mmss(current)} / {self._to_mmss(total)}"
        self.position_label.setText(text)
        self.np_position_label.setText(text)

    def _seek(self) -> None:
        """Seek to slider position - direct VLC set_time() call."""
        slider = self._active_seek_slider()
        ratio = max(0.0, min(1.0, slider.value() / 1000.0))
        
        try:
            duration_ms = self._playback_service.state.duration_ms
            position_ms = ratio * duration_ms
            self._playback_service.seek(position_ms)
            logger.info(f"[SEEK] Direct seek to {position_ms:.0f}ms")
        except Exception as e:
            logger.error(f"[SEEK] Failed: {e}", exc_info=True)

    def _on_seek_pressed(self) -> None:
        """User started dragging seek slider."""
        pass  # No special handling needed

    def _on_seek_moved(self, value: int) -> None:
        """Update time label during seek drag."""
        ratio = max(0.0, min(1.0, value / 1000.0))
        self._set_seek_labels(ratio)

    def _keep_playback_responsive(self) -> None:
        """Keep playback thread synchronized."""
        try:
            _ = self._playback_service.state.is_playing
        except Exception:
            pass

    def _set_volume(self, value: int) -> None:
        try:
            self._playback_service.set_volume(value)
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
        self.settings["volume"] = int(value)

        if self.sender() is self.volume_slider and self.np_volume_slider.value() != value:
            self.np_volume_slider.blockSignals(True)
            self.np_volume_slider.setValue(value)
            self.np_volume_slider.blockSignals(False)
        elif self.sender() is self.np_volume_slider and self.volume_slider.value() != value:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(value)
            self.volume_slider.blockSignals(False)

    def _on_track_finished(self) -> None:
        if self.repeat_mode == "single" and self.current_index >= 0:
            self._play_at_index(self.current_index)
            return

        if self.repeat_mode == "selection" or self.current_index < len(self.filtered_tracks) - 1 or self.shuffle_enabled:
            self._play_next()
            return

        self._set_play_pause_visual(False)

    def _on_track_clicked(self, item: QListWidgetItem) -> None:
        track_id = item.data(Qt.UserRole)
        for i, track in enumerate(self.filtered_tracks):
            if track.track_id == track_id:
                self._play_at_index(i)
                break

    def _on_now_queue_clicked(self, item: QListWidgetItem) -> None:
        track_id = item.data(Qt.UserRole)
        for i, track in enumerate(self.filtered_tracks):
            if track.track_id == track_id:
                self._play_at_index(i)
                break

    def _populate_now_queue(self) -> None:
        self.now_queue_list.setUpdatesEnabled(False)
        self.now_queue_list.blockSignals(True)
        self.now_queue_list.clear()
        self._now_queue_index_by_id.clear()
        source = self.filtered_tracks if self.filtered_tracks else self.tracks
        for row_index, track in enumerate(source):
            row = QListWidgetItem(track.title)
            row.setData(Qt.UserRole, track.track_id)
            row.setData(Qt.UserRole + 1, track.artist)
            row.setToolTip(f"{track.artist} - {track.album}")
            self.now_queue_list.addItem(row)
            self._now_queue_index_by_id[track.track_id] = row_index
        self.now_queue_list.blockSignals(False)
        self.now_queue_list.setUpdatesEnabled(True)

    def _update_now_playing_screen(self, track: Track) -> None:
        self.np_artist_label.setText(track.artist.upper())
        self.np_title_label.setText(track.title)
        self.np_album_label.setText(track.album.upper())
        cover = self._cover_pixmap(track)
        self.np_cover_label.setPixmap(cover)
        self.lib_mini_cover_label.setPixmap(
            cover.scaled(self.lib_mini_cover_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )

    def _cover_pixmap(self, track: Track) -> QPixmap:
        size = max(self.np_cover_label.width(), self.np_cover_label.height())
        key = self._album_art_cache_key(f"{track.artist}::{track.album}", [track], size)
        pix = self._album_art_cache.get(key)
        if pix is None:
            # Always pass the track for accurate cover extraction, even during playback.
            # The extraction will check embedded covers first, which is fast.
            pix = self._album_art_pixmap(track.album, [track], size)
            self._album_art_cache[key] = pix
        return pix.scaled(self.np_cover_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def _cycle_sort_mode(self, kind: str) -> None:
        if kind == "artist":
            modes = ["A-Z", "Z-A"]
            current = self.artist_sort_btn.text()
            self.artist_sort_btn.setText(modes[(modes.index(current) + 1) % len(modes)] if current in modes else modes[0])
        elif kind == "album":
            modes = ["A-Z", "Release Date", "Z-A"]
            current = self.album_sort_btn.text()
            self.album_sort_btn.setText(modes[(modes.index(current) + 1) % len(modes)] if current in modes else modes[0])
        else:
            modes = ["A-Z", "Z-A"]
            current = self.song_sort_btn.text()
            self.song_sort_btn.setText(modes[(modes.index(current) + 1) % len(modes)] if current in modes else modes[0])

        self._apply_filter()

    def _reset_library_selection(self, kind: str) -> None:
        if kind == "artists":
            self._clear_list_selection(self.artist_list)
            self._clear_list_selection(self.album_list)
            self._clear_list_selection(self.track_list)
        elif kind == "albums":
            self._clear_list_selection(self.album_list)
            self._clear_list_selection(self.track_list)
        else:
            self._clear_list_selection(self.track_list)

        self._apply_filter()

    def _sort_artists(self, artists: list[str]) -> list[str]:
        mode = self.artist_sort_btn.text() if hasattr(self, "artist_sort_btn") else "A-Z"
        reverse = mode == "Z-A"
        return sorted(artists, key=lambda a: a.lower(), reverse=reverse)

    def _sort_albums(self, albums: list[str], source_tracks: list[Track]) -> list[str]:
        mode = self.album_sort_btn.text() if hasattr(self, "album_sort_btn") else "A-Z"
        if mode == "Z-A":
            return sorted(albums, key=lambda a: a.lower(), reverse=True)

        if mode == "Release Date":
            by_album: dict[str, list[Track]] = {}
            for track in source_tracks:
                by_album.setdefault(track.album, []).append(track)

            def release_key(album: str) -> float:
                cache_key = album.lower().strip()
                if cache_key in self._album_release_cache:
                    return self._album_release_cache[cache_key]

                mtimes: list[float] = []
                for track in by_album.get(album, []):
                    try:
                        mtimes.append(track.path.stat().st_mtime)
                    except OSError:
                        continue

                value = max(mtimes) if mtimes else 0.0
                self._album_release_cache[cache_key] = value
                return value

            return sorted(albums, key=lambda a: (release_key(a), a.lower()), reverse=True)

        return sorted(albums, key=lambda a: a.lower())

    def _sort_tracks(self, tracks: list[Track]) -> list[Track]:
        mode = self.song_sort_btn.text() if hasattr(self, "song_sort_btn") else "A-Z"
        reverse = mode == "Z-A"
        return sorted(tracks, key=lambda t: (t.title.lower(), t.artist.lower()), reverse=reverse)

    def _animate_track_transition(self, widget: QWidget) -> None:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(230)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(0.15)
        anim.setEndValue(1.0)
        self._track_anim_refs.append(anim)

        def _cleanup() -> None:
            if anim in self._track_anim_refs:
                self._track_anim_refs.remove(anim)

        anim.finished.connect(_cleanup)
        anim.start()

    def _make_icon_button(self, kind: str, hero: bool = False, primary: bool = False) -> QPushButton:
        btn = QPushButton()
        if primary:
            btn.setObjectName("primaryControlButton")
            size = 62
        else:
            btn.setObjectName("heroIconButton" if hero else "iconButton")
            size = 46 if hero else 36
        btn.setFixedSize(size, size)
        if primary:
            btn.setIconSize(QSize(26, 26))
        else:
            btn.setIconSize(QSize(20, 20) if hero else QSize(16, 16))
        btn.setProperty("kind", kind)
        return btn

    @staticmethod
    def _make_menu_button(text: str, object_name: str, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(object_name)
        btn.setProperty("active", active)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _make_icon(self, kind: str, color: QColor) -> QIcon:
        size = 22
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)

        pen = QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(color)

        if kind == "play":
            p.drawPolygon(QPolygon([QPoint(7, 5), QPoint(17, 11), QPoint(7, 17)]))
        elif kind == "pause":
            p.fillRect(6, 5, 4, 12, color)
            p.fillRect(12, 5, 4, 12, color)
        elif kind == "next":
            p.drawPolygon(QPolygon([QPoint(5, 5), QPoint(12, 11), QPoint(5, 17)]))
            p.drawPolygon(QPolygon([QPoint(12, 5), QPoint(19, 11), QPoint(12, 17)]))
        elif kind == "prev":
            p.drawPolygon(QPolygon([QPoint(17, 5), QPoint(10, 11), QPoint(17, 17)]))
            p.drawPolygon(QPolygon([QPoint(10, 5), QPoint(3, 11), QPoint(10, 17)]))
        elif kind == "shuffle":
            path = QPainterPath()
            path.moveTo(3, 6)
            path.cubicTo(8, 6, 10, 16, 15, 16)
            path.lineTo(19, 16)
            p.drawPath(path)
            p.drawLine(16, 13, 19, 16)
            p.drawLine(16, 19, 19, 16)

            path2 = QPainterPath()
            path2.moveTo(3, 16)
            path2.cubicTo(7, 16, 10, 6, 14, 6)
            path2.lineTo(19, 6)
            p.drawPath(path2)
            p.drawLine(16, 3, 19, 6)
            p.drawLine(16, 9, 19, 6)
        elif kind == "repeat":
            p.setBrush(Qt.NoBrush)
            repeat_pen = QPen(color, 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(repeat_pen)

            top = QPainterPath()
            top.moveTo(4.0, 7.0)
            top.cubicTo(8.0, 7.0, 10.3, 5.0, 13.4, 5.0)
            top.lineTo(17.4, 5.0)
            p.drawPath(top)
            p.drawLine(17.4, 5.0, 15.2, 2.8)
            p.drawLine(17.4, 5.0, 15.2, 7.2)

            bottom = QPainterPath()
            bottom.moveTo(18.0, 15.0)
            bottom.cubicTo(13.6, 15.0, 11.4, 17.0, 8.4, 17.0)
            bottom.lineTo(4.6, 17.0)
            p.drawPath(bottom)
            p.drawLine(4.6, 17.0, 6.8, 14.8)
            p.drawLine(4.6, 17.0, 6.8, 19.2)

        p.end()
        return QIcon(pix)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if not folder:
            return

        folders = self.settings.get("scan_folders", [])
        if folder not in folders:
            folders.append(folder)
            self.settings["scan_folders"] = folders
            self._refresh_folders_label()

    def _remove_selected_folder(self) -> None:
        item = self.settings_folders_list.currentItem()
        if item is None:
            return

        value = item.text().strip()
        folders = [f for f in self.settings.get("scan_folders", []) if f != value]
        self.settings["scan_folders"] = folders
        self._refresh_folders_label()

    def _clear_folders(self) -> None:
        self.settings["scan_folders"] = []
        self._refresh_folders_label()

    def _refresh_folders_label(self) -> None:
        folders = self.settings.get("scan_folders", [])
        pretty = "\n".join(f"- {p}" for p in folders) if folders else "No folders configured"
        self.folders_label.setText(pretty)
        if hasattr(self, "settings_folders_list"):
            self.settings_folders_list.clear()
            self.settings_folders_list.addItems(folders)

    def _load_playlists_ui(self) -> None:
        self.playlist_list.clear()
        for name in sorted(self.playlists.keys()):
            self.playlist_list.addItem(name)

    def _create_playlist(self) -> None:
        base = "New Playlist"
        name = base
        i = 1
        while name in self.playlists:
            i += 1
            name = f"{base} {i}"
        self.playlists[name] = []
        self._load_playlists_ui()

    def _add_selected_to_playlist(self) -> None:
        track_item = self.track_list.currentItem()
        if track_item is None:
            QMessageBox.information(self, "Select Song", "Choose one song first.")
            return

        if self.playlist_list.count() == 0:
            QMessageBox.information(self, "No Playlist", "Create a playlist first.")
            return

        playlist_item = self.playlist_list.currentItem() or self.playlist_list.item(0)
        if playlist_item is None:
            return

        track_id = track_item.data(Qt.UserRole)
        playlist_name = playlist_item.text()
        bucket = self.playlists.setdefault(playlist_name, [])
        if track_id not in bucket:
            bucket.append(track_id)

    def closeEvent(self, event) -> None:  # noqa: N802
        save_playlists_db(self.playlists)
        save_settings_db(self.settings)
        self._backdrop_rotate_timer.stop()
        self._backdrop_render_timer.stop()
        self._scan_executor.shutdown(wait=False, cancel_futures=True)
        self._playback_executor.shutdown(wait=False, cancel_futures=True)
        self._backdrop_executor.shutdown(wait=False, cancel_futures=True)
        self._backdrop_worker_thread.quit()
        self._backdrop_worker_thread.wait(timeout=5000)
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._enforce_non_fullscreen()
        super().resizeEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.WindowStateChange:
            self._enforce_non_fullscreen()
        super().changeEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._lock_full_size:
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton and event.position().y() <= self.top_region.height() + 5:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._lock_full_size:
            super().mouseMoveEvent(event)
            return
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    @staticmethod
    def _to_mmss(total_seconds: int) -> str:
        total_seconds = max(0, int(total_seconds))
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02}:{seconds:02}"
