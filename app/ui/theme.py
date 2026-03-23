from __future__ import annotations

DARK_QSS = """
QMainWindow {
    background: #090a10;
}
QWidget {
    color: #f2f4fb;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    font-size: 13px;
}
QFrame#topAccent {
    background: transparent;
}
QWidget#topRegion {
    background: transparent;
}
QLabel#title {
    color: #f9fbff;
    font-size: 42px;
    font-weight: 200;
}
QPushButton {
    background: rgba(0, 0, 0, 1);
    border: 0px solid rgba(255, 255, 255, 0.08);
    color: #e8ecff;
    border-radius: 0;
    padding: 8px 14px;
}
QPushButton:hover {
    background: rgba(36, 42, 64, 0.74);
    border-color: rgba(255, 255, 255, 0.14);
}
QPushButton:pressed {
    background: rgba(22, 22, 22, 0.9);
}
QPushButton#ghostButton {
    background: transparent;
    border: 0px solid rgba(201, 214, 248, 0.35);
    color: #c8d2f8;
}
QPushButton#menuButton {
    border: 0;
    background: transparent;
    color: #9da8cf;
    font-size: 13px;
    letter-spacing: 1px;
    padding: 4px 8px;
}
QPushButton#menuButton[active="true"] {
    color: #ffffff;
    font-weight: 700;
}
QPushButton#menuTabButton {
    border: 0;
    background: transparent;
    color: #b7c2e7;
    font-size: 27px;
    font-weight: 300;
    padding: 2px 4px;
}
QPushButton#menuTabButton[active="true"] {
    color: #ffffff;
    font-weight: 700;
}
QPushButton#scopeMenuButton {
    border: 0;
    background: transparent;
    color: #a9b3d8;
    font-size: 13px;
    letter-spacing: 0.8px;
    padding: 5px 8px;
}
QPushButton#scopeMenuButton[active="true"] {
    color: #ffffff;
    font-weight: 700;
}
QPushButton#themeToggle {
    min-width: 70px;
    max-width: 90px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #f0f3ff;
}
QPushButton#themeToggle:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f9f9fb, stop:1 #d6dbe8);
    color: #1f2436;
}
QPushButton#winControl {
    min-width: 34px;
    max-width: 34px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    background: transparent;
    border: 0;
    color: #ffffff;
}
QPushButton#winControl:hover {
    background: transparent;
    color: #ffffff;
}
QPushButton#winClose {
    min-width: 34px;
    max-width: 34px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    background: transparent;
    border: 0;
    color: #ffffff;
}
QPushButton#winClose:hover {
    background: transparent;
    color: #ffffff;
}
QPushButton#viewToggle {
    border-radius: 0;
    padding: 7px 12px;
}
QPushButton#viewToggle[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #fd6a3e, stop:0.52 #ff56bb, stop:1 #b33fdb);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #ffffff;
    font-weight: 700;
}
QLineEdit {
    background: rgba(16, 16, 16, 0.9);
    border: 1px solid rgba(100, 100, 100, 1);
    border-radius: 0px;
    padding: 10px 14px;
    color: #f4f7ff;
    selection-background-color: rgba(255, 99, 197, 0.38);
    selection-color: #ffffff;
}
QLineEdit:focus {
    background: rgba(16, 16, 16, 0.9);
    border: 1px solid rgba(200, 200, 200, 1);
    outline: none;
}
QWidget#libraryPage {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #070707, stop:1 #141414);
}
QWidget#settingsPage {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #070707, stop:1 #141414);
}
QLabel#settingsHeading {
    font-size: 30px;
    font-weight: 300;
    color: #f8fbff;
}
QLabel#settingsSubheading {
    color: #b2bddf;
}
QWidget#frostPanel {
    background: rgba(18, 18, 18, 0.62);
}
QLabel#columnTitle {
    color: #eff2ff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.6px;
}
QPushButton#columnTitleButton {
    background: transparent;
    border: 0;
    color: #eff2ff;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.6px;
    padding: 0;
    text-align: left;
}
QPushButton#columnTitleButton:hover {
    color: #ffffff;
}
QPushButton#sortInlineButton {
    background: transparent;
    border: 0;
    color: #8f98b8;
    font-size: 12px;
    padding: 0;
    text-align: left;
}
QPushButton#sortInlineButton:hover {
    color: #bcc4de;
}
QSplitter::handle {
    background: rgba(255, 255, 255, 0.08);
    width: 1px;
}
QListWidget {
    background: rgba(18, 18, 18, 0.62);
    border: 0;
    border-radius: 0;
    padding: 10px;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 0;
    outline: none;
}
QListWidget::item:selected {
    background: rgba(255, 96, 187, 0.35);
    color: #ffffff;
    font-weight: 700;
    font-style: bold;
}
QListWidget#artistList::item:selected,
QListWidget#trackList::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8a44, stop:0.56 #ff63c5, stop:1 #b843dd);
    color: #ffffff;
        font-weight: 800;
}
QWidget#libraryTransport {
    background: rgba(14, 14, 14, 0.72);
    border: 0;
    border-radius: 0;
    padding: 10px;
}
QWidget#npTransport {
    background: transparent;
    border: 0;
    border-radius: 0;
}
QWidget#eqWidget {
    background: rgba(255, 255, 255, 0.05);
    border: 0;
    border-radius: 0;
}
QLabel#libraryTrackTitle {
    font-size: 18px;
    font-weight: 700;
    color: #f7f9ff;
}
QLabel#libraryTrackMeta {
    color: #a8b2d8;
}
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(194, 203, 233, 0.28);
    border-radius: 0;
}
QSlider::handle:horizontal {
    background: #ff60ba;
    width: 16px;
    margin: -6px 0;
    border-radius: 0;
}
QSlider#roundProgressSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#roundProgressSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8a44, stop:0.56 #ff63c5, stop:1 #b843dd);
    border-radius: 4px;
}
QSlider#roundProgressSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 0.16);
    border-radius: 4px;
}
QSlider#roundProgressSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider#roundVolumeSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#roundVolumeSlider::sub-page:horizontal {
    background: #ff63c5;
    border-radius: 4px;
}
QSlider#roundVolumeSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 0.22);
    border-radius: 4px;
}
QSlider#roundVolumeSlider::handle:horizontal {
    background: #f3f4f8;
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QPushButton#openNowButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9040, stop:0.55 #ff5ac0, stop:1 #ac3adc);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #ffffff;
    font-weight: 700;
}
QPushButton#iconButton {
    border-radius: 0;
    min-width: 36px;
    min-height: 36px;
    max-width: 36px;
    max-height: 36px;
    padding: 0;
    border: 0px solid rgba(255, 255, 255, 0);
}
QWidget#nowPlayingPage {
    background: #060209;
}
QWidget#nowOverlay {
    background: transparent;
}
QPushButton#nowBackButton {
    background: rgba(14, 12, 22, 0.65);
    border: 0;
    border-radius: 0;
    color: #ffffff;
    padding: 9px 14px;
}
QWidget#npInfoPanel {
    background: transparent;
    border: 0;
    border-radius: 0;
}
QLabel#npCover {
    border: 4px solid rgba(255, 255, 255, 0.92);
    border-radius: 0;
}
QLabel#libMiniCover {
    border: 0;
    border-radius: 0;
}
QLabel#npArtist {
    color: #d6d6dc;
    font-size: 12px;
    letter-spacing: 1px;
}
QLabel#npTitle {
    color: #ffffff;
    font-size: 38px;
    font-weight: 800;
}
QLabel#npAlbum {
    color: #ececf3;
    font-size: 22px;
}
QListWidget#nowQueueList {
    background: rgba(10, 10, 10, 0.8);
    border: 0;
    border-radius: 0;
    padding: 0;
    color: #ffffff;
    font-size: 15px;
}
QListWidget#nowQueueList::item {
    padding: 0;
    margin: 0;
    border: 0;
}
QListWidget#nowQueueList::item:selected {
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
    font-weight: 700;
}
QWidget#npTransport {
    background: transparent;
    border: 0;
    border-radius: 0;
}
QWidget#npTransport QSlider::groove:horizontal {
    background: rgba(255, 255, 255, 0.22);
}
QWidget#npTransport QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8a44, stop:0.56 #ff63c5, stop:1 #b843dd);
}
QWidget#npTransport QSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 0.16);
}
QWidget#npTransport QSlider::handle:horizontal {
    background: #ff66c4;
}
QSlider#npVolumeSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#npVolumeSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QPushButton#heroIconButton {
    border-radius: 23px;
    min-width: 46px;
    min-height: 46px;
    max-width: 46px;
    max-height: 46px;
    padding: 0;
    background: rgba(255, 255, 255, 0.1);
    border: 0px solid rgba(100, 100, 100, 1);
}
QPushButton#heroIconButton:hover {
    background: rgba(255, 255, 255, 0.22);
    border: 0px solid rgba(255, 255, 255, 0);
}
QPushButton#heroIconButton[active="true"] {
    background: rgba(255, 255, 255, 0.22);
    border: 0px solid rgba(255, 255, 255, 0);
}
QPushButton#primaryControlButton {
    border-radius: 31px;
    min-width: 62px;
    min-height: 62px;
    max-width: 62px;
    max-height: 62px;
    padding: 0;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8a44, stop:0.56 #ff63c5, stop:1 #b843dd);
    border: 0px solid rgba(255, 255, 255, 0.2);
}
QPushButton#primaryControlButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9d57, stop:0.56 #ff75ce, stop:1 #c153e4);
    border: 0px solid rgba(255, 255, 255, 0.26);
}
QLabel#npPositionLabel {
    color: #ffffff;
    font-weight: 700;
}
"""

LIGHT_QSS = """
QMainWindow {
    background: #f2f3f8;
}
QWidget {
    color: #202430;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    font-size: 13px;
}
QFrame#topAccent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff993c, stop:0.45 #ff6dc8, stop:1 #9e4ed6);
}
QWidget#topRegion {
    background: rgba(248, 249, 253, 0.94);
}
QLabel#title {
    color: #2a2f41;
    font-size: 42px;
    font-weight: 200;
}
QPushButton {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(40, 48, 70, 0.13);
    color: #2b3042;
    border-radius: 0;
    padding: 8px 14px;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.88);
    border-color: rgba(40, 48, 70, 0.2);
}
QPushButton#ghostButton {
    background: transparent;
    border: 1px solid rgba(88, 96, 135, 0.32);
    color: #586087;
}
QPushButton#menuButton {
    border: 0;
    background: transparent;
    color: #7c849f;
    font-size: 13px;
    letter-spacing: 1px;
    padding: 4px 8px;
}
QPushButton#menuButton[active="true"] {
    color: #1f253b;
    font-weight: 700;
}
QPushButton#menuTabButton {
    border: 0;
    background: transparent;
    color: #58617e;
    font-size: 27px;
    font-weight: 300;
    padding: 2px 4px;
}
QPushButton#menuTabButton[active="true"] {
    color: #1f253b;
    font-weight: 700;
}
QPushButton#scopeMenuButton {
    border: 0;
    background: transparent;
    color: #6c7696;
    font-size: 13px;
    letter-spacing: 0.8px;
    padding: 5px 8px;
}
QPushButton#scopeMenuButton[active="true"] {
    color: #1f253b;
    font-weight: 700;
}
QPushButton#themeToggle {
    min-width: 70px;
    max-width: 90px;
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.75);
    border: 1px solid rgba(40, 48, 70, 0.2);
    color: #263049;
}
QPushButton#themeToggle:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #202739, stop:1 #414b63);
    color: #f5f7ff;
}
QPushButton#winControl {
    min-width: 34px;
    max-width: 34px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    background: rgba(27, 33, 47, 0.09);
    border: 0;
    color: #273149;
}
QPushButton#winControl:hover {
    background: rgba(27, 33, 47, 0.18);
}
QPushButton#winClose {
    min-width: 34px;
    max-width: 34px;
    min-height: 30px;
    max-height: 30px;
    padding: 0;
    background: rgba(245, 65, 90, 0.16);
    border: 0;
    color: #6c1f2c;
}
QPushButton#winClose:hover {
    background: rgba(245, 65, 90, 0.46);
    color: #ffffff;
}
QPushButton#viewToggle {
    border-radius: 0;
    padding: 7px 12px;
}
QPushButton#viewToggle[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8e41, stop:0.52 #ff5dc3, stop:1 #9f48d7);
    border: 1px solid rgba(40, 48, 70, 0.15);
    color: #ffffff;
    font-weight: 700;
}
QLineEdit {
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(40, 48, 70, 0.16);
    border-radius: 0;
    padding: 10px 14px;
    color: #2a3042;
}
QWidget#libraryPage {
    background: #f2f3f8;
}
QWidget#settingsPage {
    background: #f2f3f8;
}
QLabel#settingsHeading {
    font-size: 30px;
    font-weight: 300;
    color: #2a2f41;
}
QLabel#settingsSubheading {
    color: #66708f;
}
QWidget#frostPanel {
    background: rgba(255, 255, 255, 0.54);
}
QLabel#columnTitle {
    color: #2f3447;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.6px;
}
QSplitter::handle {
    background: rgba(38, 45, 67, 0.14);
    width: 1px;
}
QListWidget {
    background: rgba(255, 255, 255, 0.7);
    border: 0;
    border-radius: 0;
    padding: 10px;
    outline: none;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 0;
    outline: none;
}
QListWidget::item:selected {
    background: rgba(255, 98, 189, 0.2);
    color: #202430;
    font-weight: 700;
    
}
QListWidget#trackList::item:selected {
    color: #202430;
    font-weight: 800;
}
    QListWidget#artistList::item:selected {
        color: #202430;
        font-weight: 800;
    }
QWidget#libraryTransport {
    background: rgba(255, 255, 255, 0.62);
    border: 0;
    border-radius: 0;
    padding: 10px;
}
QWidget#npTransport {
    background: rgba(255, 255, 255, 0.62);
    border: 0;
    border-radius: 0;
}
QLabel#libraryTrackTitle {
    font-size: 18px;
    font-weight: 700;
    color: #212538;
}
QLabel#libraryTrackMeta {
    color: #5f6782;
}
QSlider::groove:horizontal {
    height: 5px;
    background: rgba(28, 34, 50, 0.2);
    border-radius: 0;
}
QSlider::handle:horizontal {
    background: #ff5dbc;
    width: 16px;
    margin: -6px 0;
    border-radius: 0;
}
QSlider#roundProgressSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#roundProgressSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f38843, stop:0.56 #f85fbe, stop:1 #a643d5);
    border-radius: 4px;
}
QSlider#roundProgressSlider::add-page:horizontal {
    background: rgba(28, 34, 50, 0.12);
    border-radius: 4px;
}
QSlider#roundProgressSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QSlider#roundVolumeSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#roundVolumeSlider::sub-page:horizontal {
    background: rgba(28, 34, 50, 0.32);
    border-radius: 4px;
}
QSlider#roundVolumeSlider::add-page:horizontal {
    background: rgba(28, 34, 50, 0.14);
    border-radius: 4px;
}
QSlider#roundVolumeSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QWidget#eqWidget {
    background: rgba(24, 29, 46, 0.08);
    border: 0;
    border-radius: 0;
}
QPushButton#openNowButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9140, stop:0.55 #ff59bf, stop:1 #a043d6);
    border: 0;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#iconButton {
    border-radius: 0;
    min-width: 36px;
    min-height: 36px;
    max-width: 36px;
    max-height: 36px;
    padding: 0;
}
QWidget#nowPlayingPage {
    background: #f2f3f8;
}
QWidget#nowOverlay {
    background: transparent;
}
QPushButton#nowBackButton {
    background: rgba(255, 255, 255, 0.72);
    border: 0;
    border-radius: 0;
    color: #1f2538;
    padding: 9px 14px;
}
QWidget#npInfoPanel {
    background: transparent;
    border: 0;
    border-radius: 0;
}
QLabel#npCover {
    border: 4px solid rgba(255, 255, 255, 0.92);
    border-radius: 0;
}
QLabel#npArtist {
    color: #444d66;
    font-size: 12px;
    letter-spacing: 1px;
}
QLabel#npTitle {
    color: #ffffff;
    font-size: 38px;
    font-weight: 800;
    margin: 6px 0px;
}
QLabel#npAlbum {
    color: #ffffff;
    font-size: 22px;
}
QListWidget#nowQueueList {
    background: rgba(255, 255, 255, 0.58);
    border: 0;
    border-radius: 0;
    padding: 0;
    color: #23283a;
    font-size: 15px;
}
QListWidget#nowQueueList::item {
    padding: 0;
    margin: 0;
    border: 0;
}
QListWidget#nowQueueList::item:selected {
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
}
QWidget#npTransport {
    background: rgba(255, 255, 255, 0.64);
    border: 0;
    border-radius: 0;
}
QWidget#npTransport QSlider::groove:horizontal {
    background: rgba(28, 34, 50, 0.2);
}
QWidget#npTransport QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f38843, stop:0.56 #f85fbe, stop:1 #a643d5);
}
QWidget#npTransport QSlider::add-page:horizontal {
    background: rgba(28, 34, 50, 0.12);
}
QWidget#npTransport QSlider::handle:horizontal {
    background: #ff53ba;
}
QSlider#npVolumeSlider::groove:horizontal {
    height: 8px;
    border-radius: 4px;
}
QSlider#npVolumeSlider::handle:horizontal {
    width: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QPushButton#heroIconButton {
    border-radius: 23px;
    min-width: 46px;
    min-height: 46px;
    max-width: 46px;
    max-height: 46px;
    padding: 0;
    background: rgba(0, 0, 0, 1);
    border: 0px solid rgba(25, 30, 44, 0.24);
}
QPushButton#heroIconButton:hover {
    background: rgba(25, 30, 44, 0.18);
    border: 0px solid rgba(25, 30, 44, 0.3);
}
QPushButton#heroIconButton[active="true"] {
    background: rgba(25, 30, 44, 0.18);
    border: 0px solid rgba(25, 30, 44, 0.3);
}
QPushButton#primaryControlButton {
    border-radius: 31px;
    min-width: 62px;
    min-height: 62px;
    max-width: 62px;
    max-height: 62px;
    padding: 0;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f38843, stop:0.56 #f85fbe, stop:1 #a643d5);
    border: 0px solid rgba(28, 34, 50, 0.14);
}
QPushButton#primaryControlButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f79a57, stop:0.56 #fb73c5, stop:1 #b357de);
    border: 0px solid rgba(28, 34, 50, 0.2);
}
QLabel#npPositionLabel {
    color: #ffffff;
    font-weight: 700;
}
"""


def get_theme(name: str) -> str:
    return DARK_QSS
