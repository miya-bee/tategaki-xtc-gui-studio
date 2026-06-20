"""Stylesheet helpers for TategakiXTC GUI Studio.

This module keeps the large Qt stylesheet strings out of the MainWindow class.
It intentionally contains no GUI state and should remain behavior-preserving.
"""

from __future__ import annotations

from tategakiXTC_gui_studio_constants import (
    SPIN_DOWN_ICON,
    SPIN_DOWN_ICON_DARK,
    SPIN_UP_ICON,
    SPIN_UP_ICON_DARK,
)


def light_stylesheet() -> str:
    stylesheet = """
    /* ── ベース ── */
    QMainWindow, QWidget {
        background: #F4F7FB;
        color: #243648;
        font-family: 'Meiryo', 'Yu Gothic UI', sans-serif;
        font-size: 15px;
    }

    /* ── トップバー ── */
    QFrame#topBar {
        background: #FFFFFF;
        border: none;
    }
    QFrame#vSep { background: #D5E0EB; }
    QFrame#topSep { background: #DDE6EF; border: none; max-height: 1px; }
    QFrame#leftSettingsBottomSep { background: #DDE6EF; border: none; max-height: 1px; }
    QFrame#bottomPanelSep { background: #DDE6EF; border: none; max-height: 1px; }

    QLabel#appVersionSubtle {
        background: transparent;
        border: none;
        padding: 0px 2px;
        font-size: 12px;
        font-weight: 600;
        color: #5A7794;
        letter-spacing: 0px;
    }

    QLineEdit#targetEdit {
        background: #FFFFFF;
        border: 1px solid #C9D6E3;
        border-radius: 8px;
        padding: 6px 10px;
        color: #2B4056;
    }
    QLineEdit#targetEdit:focus { border-color: #77AEEB; }

    QPushButton#topBtn {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        padding: 5px 10px;
        color: #335A82;
        font-size: 14px;
    }
    QPushButton#topBtn:hover { background: #EEF5FC; }

    QPushButton#runBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #4F8FEF, stop:1 #69B8FF);
        border: none;
        border-radius: 8px;
        color: #F9FCFF;
        font-weight: 700;
        font-size: 15px;
        letter-spacing: 0.3px;
    }
    QPushButton#runBtn:hover { background: #5B9CF4; }
    QPushButton#runBtn:disabled { background: #D5DEE8; color: #7C8B99; }

    QPushButton#stopBtn {
        background: #FFF5F2;
        border: 1px solid #EDC2BA;
        border-radius: 8px;
        color: #C15A48;
        font-size: 14px;
    }
    QPushButton#stopBtn:hover { background: #FFEAE4; }
    QPushButton#stopBtn:disabled {
        background: #EEF2F6;
        color: #9AA7B3;
        border-color: #D6DEE6;
    }

    QPushButton#iconBtn {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        color: #7B95AC;
        font-size: 18px;
        font-weight: 700;
    }
    QPushButton#iconBtn:hover { background: #EEF5FC; color: #3E607F; }

    /* ── 設定パネル ── */
    QScrollBar:vertical {
        background: #E9EFF5;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #C6D4E2;
        min-height: 24px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover { background: #B5C7D8; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QGroupBox#settingsSection {
        background: #FFFFFF;
        border: 1px solid #D6E0EA;
        border-radius: 10px;
        margin-top: 0;
        padding-top: 14px;
        font-size: 14px;
        font-weight: 700;
        color: #6D89A6;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    QGroupBox#settingsSection::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        top: 6px;
        background: #FFFFFF;
    }

    QLabel#dimLabel { color: #5E7893; font-size: 14px; }
    QLabel#hintLabel { color: #788FA4; font-size: 13px; }
    QLabel#resultsPlaceholderLabel { color: #9BAABB; font-size: 13px; }
    QLabel#resultsPlaceholderLabel[placeholderState="empty"] { color: #AAB7C4; }
    QLabel#resultsPlaceholderLabel[placeholderState="content"] { color: #24577E; font-size: 13px; font-weight: 600; }
    QFrame#resultsActionRow { background: #EEF6FC; border: 1px solid #C9DDED; border-radius: 8px; }
    QPushButton#resultsActionButton { background: #FFFFFF; border: 1px solid #9CBAD4; border-radius: 8px; padding: 4px 10px; color: #234D70; font-weight: 700; }
    QPushButton#resultsActionButton:hover { background: #F6FBFF; border-color: #6F9FC8; }
    QPushButton#resultsActionButton:disabled { color: #A5B4C1; border-color: #D5E0E8; background: #F6F8FA; }
    QFrame#conversionCompletionCard { background: #FFF9E8; border: 1px solid #F0CF76; border-radius: 10px; margin: 6px 8px 0 8px; }
    QLabel#conversionCompletionTitle { color: #6F4B00; font-size: 15px; font-weight: 800; background: transparent; }
    QLabel#conversionCompletionMessage { color: #4A3A12; font-size: 13px; background: transparent; }
    QPushButton#conversionCompletionActionButton, QPushButton#conversionCompletionCloseButton { background: #FFFFFF; border: 1px solid #D8B95D; border-radius: 8px; padding: 4px 10px; color: #6F4B00; font-weight: 700; }
    QPushButton#conversionCompletionActionButton:hover, QPushButton#conversionCompletionCloseButton:hover { background: #FFF3CC; border-color: #C99D2E; }
    QPushButton#conversionCompletionActionButton:disabled { color: #B6A77E; border-color: #E8DBB1; background: #F8F4E8; }
    QLabel#presetSummaryLabel { color: #275C9A; font-size: 15px; font-weight: 400; }
    QLabel#subNoteLabel { color: #4F6982; font-size: 12px; line-height: 1.35em; }
    QLabel#flowGuideTitle { color: #1F3D5A; font-size: 13px; font-weight: 700; }
    QLabel#flowGuideText { color: #3E5771; font-size: 12px; }
    QLabel#viewRoleLabel { color: #163B63; font-size: 13px; font-weight: 700; }
    QPushButton#miniHelpBtn { background: #EAF3FB; color: #1C4D7C; border: 1px solid #8FB0CD; border-radius: 10px; font-size: 12px; font-weight: 700; padding: 0; }
    QPushButton#miniHelpBtn:hover { background: #DCECF9; border-color: #6F96BB; }
    QPushButton#miniHelpBtn:pressed { background: #CFE3F4; }

    /* ── 左ペインの密度調整 ── */
    QWidget#leftSettingsContainer QGroupBox#settingsSection {
        border-radius: 9px;
        padding-top: 12px;
    }
    QWidget#leftSettingsContainer QGroupBox#settingsSection::title {
        left: 8px;
        top: 5px;
        padding: 0 6px;
    }
    QWidget#leftSettingsContainer QLabel#dimLabel { font-size: 13px; }
    QWidget#leftSettingsContainer QLabel#hintLabel { font-size: 12px; }
    QWidget#leftSettingsContainer QLabel#subNoteLabel { font-size: 11px; }
    QWidget#leftSettingsContainer QLabel#flowGuideTitle { font-size: 12px; }
    QWidget#leftSettingsContainer QLabel#flowGuideText { font-size: 11px; }
    QFrame#flowGuide { background: #EDF4FB; border: 1px solid #C7D8E8; border-radius: 10px; }
    QWidget#viewRoleBox { background: transparent; }
    QWidget#leftSettingsContainer QLabel#presetSummaryLabel { font-size: 14px; font-weight: 400; }
    QWidget#leftSettingsContainer QComboBox,
    QWidget#leftSettingsContainer QSpinBox,
    QWidget#leftSettingsContainer QLineEdit {
        padding: 3px 7px;
        min-height: 18px;
        border-radius: 7px;
    }
    QWidget#leftSettingsContainer QComboBox::drop-down { width: 18px; }
    QWidget#leftSettingsContainer QSpinBox[compactField="true"] {
        padding: 2px 6px;
        min-height: 16px;
        max-height: 24px;
        border-radius: 6px;
    }
    QWidget#leftSettingsContainer QCheckBox { spacing: 4px; }
    QWidget#leftSettingsContainer QCheckBox::indicator { width: 14px; height: 14px; }
    QWidget#leftSettingsContainer QPushButton#smallBtn {
        padding: 3px 10px;
        min-height: 18px;
        border-radius: 7px;
    }
    QWidget#leftSettingsContainer QPushButton#stepBtn {
        border-radius: 5px;
        font-size: 15px;
    }

    QComboBox {
        background: #FFFFFF;
        border: 1px solid #C9D6E3;
        border-radius: 8px;
        padding: 5px 8px;
        color: #2B4056;
    }
    QComboBox:hover { border-color: #9ABFE4; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #6B86A0;
    }
    QComboBox QAbstractItemView {
        background: #FFFFFF;
        border: 1px solid #C9D6E3;
        selection-background-color: #DCEBFA;
        color: #2B4056;
    }

    QSpinBox {
        background: #FFFFFF;
        border: 1px solid #C9D6E3;
        border-radius: 8px;
        padding: 5px 8px;
        color: #2B4056;
        min-height: 22px;
    }
    QSpinBox:hover { border-color: #9ABFE4; }
    QSpinBox:focus { border-color: #77AEEB; }
    QSpinBox::up-button, QSpinBox::down-button { width: 0; }
    QSpinBox[showSpinButtons="true"] {
        padding-right: 23px;
        border-color: #7D9FBE;
    }
    QSpinBox[showSpinButtons="true"]::up-button,
    QSpinBox[showSpinButtons="true"]::down-button {
        width: 24px;
        background: #E5EEF8;
        border-left: 1px solid #6F93B6;
        border-right: 1px solid #AEC6DD;
    }
    QSpinBox[showSpinButtons="true"]::up-button:hover,
    QSpinBox[showSpinButtons="true"]::down-button:hover {
        background: #D6E5F5;
    }
    QSpinBox[showSpinButtons="true"]::up-button:pressed,
    QSpinBox[showSpinButtons="true"]::down-button:pressed {
        background: #C8DCF1;
    }
    QSpinBox[showSpinButtons="true"]::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        border-top-right-radius: 7px;
        border-bottom: 1px solid #6F93B6;
    }
    QSpinBox[showSpinButtons="true"]::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        border-bottom-right-radius: 7px;
    }
    QSpinBox[showSpinButtons="true"]::up-arrow {
        image: url({SPIN_UP_ICON});
        width: 14px;
        height: 10px;
    }
    QSpinBox[showSpinButtons="true"]::down-arrow {
        image: url({SPIN_DOWN_ICON});
        width: 14px;
        height: 10px;
    }
    QSpinBox[miniSpinButtons="true"] {
        padding-right: 12px;
    }
    QSpinBox[miniSpinButtons="true"]::up-button,
    QSpinBox[miniSpinButtons="true"]::down-button {
        width: 12px;
    }
    QSpinBox[miniSpinButtons="true"]::up-arrow,
    QSpinBox[miniSpinButtons="true"]::down-arrow {
        width: 7px;
        height: 5px;
    }

    QCheckBox { color: #35506A; spacing: 6px; }
    QLabel#checkboxTextLabel { color: #35506A; }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #AFC1D2;
        border-radius: 4px;
        background: #FFFFFF;
    }
    QCheckBox::indicator:hover { border-color: #77AEEB; }
    QCheckBox::indicator:checked {
        background-color: #5B9BED;
        border: 1px solid #4C8FE3;
    }

    QPushButton#smallBtn {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        padding: 5px 12px;
        color: #355A80;
        font-size: 14px;
        min-height: 20px;
    }
    QPushButton#smallBtn:hover { background: #EEF5FC; }
    QPushButton#smallBtn[previewState="pending"] {
        background: #FFF1DF;
        border: 1px solid #F0A84F;
        color: #8A4D00;
        font-weight: 700;
    }
    QPushButton#smallBtn[previewState="pending"]:hover { background: #FFE5C2; }
    QPushButton#smallBtn[previewState="refreshing"],
    QPushButton#smallBtn[previewState="refreshing"]:disabled {
        background: #F59E0B;
        border: 1px solid #D97706;
        color: #FFFFFF;
        font-weight: 700;
    }
    QPushButton#smallBtn[previewState="viewer"],
    QPushButton#smallBtn[previewState="viewer"]:disabled {
        background: #EEF2F6;
        border: 1px solid #CAD6E2;
        color: #6F8294;
        font-weight: 700;
    }

    QPushButton#stepBtn {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 6px;
        color: #5D7EA0;
        font-size: 16px;
        font-weight: 700;
    }
    QPushButton#stepBtn:hover { background: #EEF5FC; }

    QLineEdit {
        background: #FFFFFF;
        border: 1px solid #C9D6E3;
        border-radius: 8px;
        padding: 5px 9px;
        color: #2B4056;
    }
    QLineEdit:focus { border-color: #77AEEB; }

    /* ── プレビューパネル ── */
    QFrame#viewToggleBar {
        background: #F5F8FC;
        border: none;
    }
    QPushButton#viewToggleBtn {
        background: transparent;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        padding: 6px 16px;
        color: #6C86A0;
        font-size: 15px;
    }
    QPushButton#viewToggleBtn:hover { background: #EEF4FB; color: #37597C; }
    QPushButton#previewToolbarButton {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        padding: 5px 10px;
        color: #335A82;
        font-size: 14px;
    }
    QPushButton#previewToolbarButton:hover { background: #EEF5FC; color: #23435F; }
    QPushButton#previewToolbarButton:pressed { background: #DCEBFA; }

    QPushButton#viewToggleBtn:checked {
        background: #E8F1FD;
        border: 1px solid #C3D7EE;
        color: #23435F;
        font-weight: 700;
    }

    /* ── ナビゲーションバー ── */
    QFrame#navBar {
        background: #F5F8FC;
        border: none;
        border-top: 1px solid #DCE5EE;
    }
    QPushButton#navBtn {
        background: #FFFFFF;
        border: 1px solid #C8D6E5;
        border-radius: 8px;
        padding: 5px 14px;
        color: #355A80;
        font-size: 14px;
    }
    QPushButton#navBtn:hover { background: #EEF5FC; }
    QPushButton#navBtn:disabled { color: #A4B3C0; border-color: #D6DFE8; }
    QFrame#navSectionSep {
        color: #D2DEE9;
        background: transparent;
    }
    QCheckBox#navToggle, QCheckBox#previewToolbarToggle {
        color: #35506A;
        spacing: 6px;
        padding-right: 4px;
    }
    QCheckBox#navToggle::indicator, QCheckBox#previewToolbarToggle::indicator {
        width: 34px;
        height: 18px;
        border: 1px solid #AFC1D2;
        border-radius: 9px;
        background: #FFFFFF;
    }
    QCheckBox#navToggle::indicator:hover, QCheckBox#previewToolbarToggle::indicator:hover { border-color: #77AEEB; }
    QCheckBox#navToggle::indicator:checked, QCheckBox#previewToolbarToggle::indicator:checked {
        background: #5B9BED;
        border: 1px solid #4C8FE3;
    }

    /* ── 下部パネル ── */
    QFrame#bottomPanel { background: #F6F9FC; border: none; }
    QFrame#bottomPanel QTabBar::tab { min-height: 24px; padding: 4px 10px; }
    QFrame#statusStrip { background: #FAFCFE; border: none; }

    QLabel#badge {
        background: #EDF3F8;
        border: 1px solid #D4DFEA;
        border-radius: 10px;
        padding: 3px 10px;
        font-size: 13px;
        font-weight: 700;
        color: #627E99;
    }

    QProgressBar {
        background: #E7EEF5;
        border: none;
        border-radius: 3px;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #4F8FEF, stop:1 #67C0FF);
        border-radius: 3px;
    }

    QTabWidget::pane {
        background: #F6F9FC;
        border: none;
        border-top: 1px solid #DCE5EE;
    }
    QTabBar::tab {
        background: #F6F9FC;
        border: none;
        border-top: 2px solid transparent;
        padding: 7px 18px;
        color: #708BA6;
        font-size: 14px;
    }
    QTabBar::tab:selected {
        color: #25435F;
        border-top: 2px solid #6FA7E7;
        background: #FFFFFF;
    }
    QTabBar::tab:hover { color: #4D6F90; }

    QListWidget {
        background: #FFFFFF;
        border: none;
        border-radius: 6px;
        color: #35506A;
        font-size: 14px;
    }
    QListWidget::item:hover { background: #EEF5FC; }
    QListWidget::item:selected { background: #DCEBFA; }

    QTextEdit {
        background: #FFFFFF;
        border: 1px solid #E0E7EF;
        border-radius: 6px;
        color: #5D7892;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        padding: 6px;
    }

    /* ── スプリッタ ── */
    QSplitter::handle { background: #DCE5EE; }
    QSplitter::handle:horizontal {
        width: 6px;
        margin: 0 2px;
    }
    QSplitter::handle:vertical {
        height: 6px;
        margin: 2px 0;
    }

    /* ── ポップアップメニュー ── */
    QMenu#gearPopupMenu {
        background: #FFFFFF;
        color: #24415C;
        border: 1px solid #C8D5E1;
        padding: 6px;
        border-radius: 8px;
    }
    QMenu#gearPopupMenu::item {
        padding: 7px 28px 7px 12px;
        border-radius: 6px;
        font-size: 14px;
    }
    QMenu#gearPopupMenu::item:selected { background: #EAF4FF; }
    QMenu#gearPopupMenu::indicator { width: 14px; height: 14px; }
    QMenu#gearPopupMenu::separator { height: 1px; background: #D7E1EA; margin: 6px 4px; }

    /* ── ステータスバー ── */
    QStatusBar { background: #F6F9FC; color: #5F7992; font-size: 13px; }
    """
    return (stylesheet
            .replace("{SPIN_UP_ICON}", SPIN_UP_ICON)
            .replace("{SPIN_DOWN_ICON}", SPIN_DOWN_ICON))

def dark_stylesheet() -> str:
    stylesheet = """
    /* ── ベース ── */
    QMainWindow, QWidget {
        background: #0D1520;
        color: #D8EAF8;
        font-family: 'Meiryo', 'Yu Gothic UI', sans-serif;
        font-size: 15px;
    }

    /* ── トップバー ── */
    QFrame#topBar {
        background: #111F2E;
        border: none;
    }
    QFrame#vSep { background: #1E3040; }
    QFrame#topSep { background: #1A2D3F; border: none; max-height: 1px; }
    QFrame#leftSettingsBottomSep { background: #1A2D3F; border: none; max-height: 1px; }
    QFrame#bottomPanelSep { background: #1A2D3F; border: none; max-height: 1px; }

    QLabel#appVersionSubtle {
        background: transparent;
        border: none;
        padding: 0px 2px;
        font-size: 12px;
        font-weight: 600;
        color: #7FA4C2;
        letter-spacing: 0px;
    }

    QLineEdit#targetEdit {
        background: #0A1520;
        border: 1px solid #1E3040;
        border-radius: 8px;
        padding: 6px 10px;
        color: #C8DFF0;
    }
    QLineEdit#targetEdit:focus { border-color: #3A6A9A; }

    QPushButton#topBtn {
        background: #182C3E;
        border: 1px solid #233D55;
        border-radius: 8px;
        padding: 5px 10px;
        color: #B8D4E8;
        font-size: 14px;
    }
    QPushButton#topBtn:hover { background: #1E3850; }

    QPushButton#runBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #2A6FCC, stop:1 #1A9AE0);
        border: none;
        border-radius: 8px;
        color: #F0F8FF;
        font-weight: 700;
        font-size: 15px;
        letter-spacing: 0.3px;
    }
    QPushButton#runBtn:hover { background: #3A80DD; }
    QPushButton#runBtn:disabled { background: #1A2D3F; color: #4A6070; }

    QPushButton#stopBtn {
        background: #2A1A1A;
        border: 1px solid #5A2A2A;
        border-radius: 8px;
        color: #E07060;
        font-size: 14px;
    }
    QPushButton#stopBtn:hover { background: #3A2020; }
    QPushButton#stopBtn:disabled {
        background: #161E26;
        color: #3A4A54;
        border-color: #1E2D3A;
    }

    QPushButton#iconBtn {
        background: #182C3E;
        border: 1px solid #233D55;
        border-radius: 8px;
        color: #88AABF;
        font-size: 18px;
        font-weight: 700;
    }
    QPushButton#iconBtn:hover { background: #1E3850; color: #C8E4F8; }

    /* ── 設定パネル ── */
    QScrollBar:vertical {
        background: #0A1520;
        width: 10px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #253D52;
        min-height: 24px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover { background: #3A5870; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QGroupBox#settingsSection {
        background: #101D2B;
        border: 1px solid #1A2E40;
        border-radius: 10px;
        margin-top: 0;
        padding-top: 14px;
        font-size: 14px;
        font-weight: 700;
        color: #6A9AB8;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    QGroupBox#settingsSection::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        top: 6px;
        background: #101D2B;
    }

    QLabel#dimLabel { color: #7A9BB2; font-size: 14px; }
    QLabel#hintLabel { color: #6485A0; font-size: 13px; }
    QFrame#conversionCompletionCard { background: #2A2414; border: 1px solid #8B6C21; border-radius: 10px; margin: 6px 8px 0 8px; }
    QLabel#conversionCompletionTitle { color: #FFD97A; font-size: 15px; font-weight: 800; background: transparent; }
    QLabel#conversionCompletionMessage { color: #F0E2BB; font-size: 13px; background: transparent; }
    QPushButton#conversionCompletionActionButton, QPushButton#conversionCompletionCloseButton { background: #172434; border: 1px solid #8B6C21; border-radius: 8px; padding: 4px 10px; color: #FFD97A; font-weight: 700; }
    QPushButton#conversionCompletionActionButton:hover, QPushButton#conversionCompletionCloseButton:hover { background: #24364A; border-color: #B98A28; }
    QPushButton#conversionCompletionActionButton:disabled { color: #827657; border-color: #4A3D1F; background: #1A1D20; }
    QLabel#presetSummaryLabel { color: #8BB6E8; font-size: 15px; font-weight: 400; }
    QLabel#subNoteLabel { color: #83A0BD; font-size: 12px; line-height: 1.35em; }
    QLabel#flowGuideTitle { color: #D6E6F6; font-size: 13px; font-weight: 700; }
    QLabel#flowGuideText { color: #A8C0D7; font-size: 12px; }
    QLabel#viewRoleLabel { color: #E2F0FF; font-size: 13px; font-weight: 700; }
    QPushButton#miniHelpBtn { background: #203749; color: #F1F7FE; border: 1px solid #5E7D99; border-radius: 10px; font-size: 12px; font-weight: 700; padding: 0; }
    QPushButton#miniHelpBtn:hover { background: #28455C; border-color: #7D9BB7; }
    QPushButton#miniHelpBtn:pressed { background: #31526D; }

    /* ── 左ペインの密度調整 ── */
    QWidget#leftSettingsContainer QGroupBox#settingsSection {
        border-radius: 9px;
        padding-top: 12px;
    }
    QWidget#leftSettingsContainer QGroupBox#settingsSection::title {
        left: 8px;
        top: 5px;
        padding: 0 6px;
    }
    QWidget#leftSettingsContainer QLabel#dimLabel { font-size: 13px; }
    QWidget#leftSettingsContainer QLabel#hintLabel { font-size: 12px; }
    QWidget#leftSettingsContainer QLabel#subNoteLabel { font-size: 11px; }
    QWidget#leftSettingsContainer QLabel#flowGuideTitle { font-size: 12px; }
    QWidget#leftSettingsContainer QLabel#flowGuideText { font-size: 11px; }
    QFrame#flowGuide { background: #14283B; border: 1px solid #314A62; border-radius: 10px; }
    QWidget#viewRoleBox { background: transparent; }
    QWidget#leftSettingsContainer QLabel#presetSummaryLabel { font-size: 14px; font-weight: 400; }
    QWidget#leftSettingsContainer QComboBox,
    QWidget#leftSettingsContainer QSpinBox,
    QWidget#leftSettingsContainer QLineEdit {
        padding: 3px 7px;
        min-height: 18px;
        border-radius: 7px;
    }
    QWidget#leftSettingsContainer QComboBox::drop-down { width: 18px; }
    QWidget#leftSettingsContainer QSpinBox[compactField="true"] {
        padding: 2px 6px;
        min-height: 16px;
        max-height: 24px;
        border-radius: 6px;
    }
    QWidget#leftSettingsContainer QCheckBox { spacing: 4px; }
    QWidget#leftSettingsContainer QCheckBox::indicator { width: 14px; height: 14px; }
    QWidget#leftSettingsContainer QPushButton#smallBtn {
        padding: 3px 10px;
        min-height: 18px;
        border-radius: 7px;
    }
    QWidget#leftSettingsContainer QPushButton#stepBtn {
        border-radius: 5px;
        font-size: 15px;
    }

    QComboBox {
        background: #0A1520;
        border: 1px solid #1E3040;
        border-radius: 8px;
        padding: 5px 8px;
        color: #C8DFF0;
    }
    QComboBox:hover { border-color: #2E5070; }
    QComboBox::drop-down { border: none; width: 22px; }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #7AA0BB;
    }
    QComboBox QAbstractItemView {
        background: #0F1E2C;
        border: 1px solid #1E3040;
        selection-background-color: #1A3D5A;
        color: #D8EAF8;
    }

    QSpinBox {
        background: #0A1520;
        border: 1px solid #1E3040;
        border-radius: 8px;
        padding: 5px 8px;
        color: #C8DFF0;
        min-height: 22px;
    }
    QSpinBox:hover { border-color: #2E5070; }
    QSpinBox:focus { border-color: #3A6A9A; }
    QSpinBox::up-button, QSpinBox::down-button { width: 0; }
    QSpinBox[showSpinButtons="true"] {
        padding-right: 23px;
        border-color: #6D88A4;
    }
    QSpinBox[showSpinButtons="true"]::up-button,
    QSpinBox[showSpinButtons="true"]::down-button {
        width: 24px;
        background: #22415E;
        border-left: 1px solid #88A7C4;
        border-right: 1px solid #35516E;
    }
    QSpinBox[showSpinButtons="true"]::up-button:hover,
    QSpinBox[showSpinButtons="true"]::down-button:hover {
        background: #2A4A69;
    }
    QSpinBox[showSpinButtons="true"]::up-button:pressed,
    QSpinBox[showSpinButtons="true"]::down-button:pressed {
        background: #31577A;
    }
    QSpinBox[showSpinButtons="true"]::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        border-top-right-radius: 7px;
        border-bottom: 1px solid #88A7C4;
    }
    QSpinBox[showSpinButtons="true"]::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        border-bottom-right-radius: 7px;
    }
    QSpinBox[showSpinButtons="true"]::up-arrow {
        image: url({SPIN_UP_ICON_DARK});
        width: 14px;
        height: 10px;
    }
    QSpinBox[showSpinButtons="true"]::down-arrow {
        image: url({SPIN_DOWN_ICON_DARK});
        width: 14px;
        height: 10px;
    }
    QSpinBox[miniSpinButtons="true"] {
        padding-right: 12px;
    }
    QSpinBox[miniSpinButtons="true"]::up-button,
    QSpinBox[miniSpinButtons="true"]::down-button {
        width: 12px;
    }
    QSpinBox[miniSpinButtons="true"]::up-arrow,
    QSpinBox[miniSpinButtons="true"]::down-arrow {
        width: 7px;
        height: 5px;
    }

    QCheckBox { color: #A8C8E0; spacing: 6px; }
    QLabel#checkboxTextLabel { color: #A8C8E0; }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #2A4A60;
        border-radius: 4px;
        background: #0A1520;
    }
    QCheckBox::indicator:hover { border-color: #3A6A9A; }
    QCheckBox::indicator:checked {
        background-color: #2A6FCC;
        border: 1px solid #3A80DD;
    }

    QPushButton#smallBtn {
        background: #182C3E;
        border: 1px solid #233D55;
        border-radius: 8px;
        padding: 5px 12px;
        color: #A8C8E0;
        font-size: 14px;
        min-height: 20px;
    }
    QPushButton#smallBtn:hover { background: #1E3850; }
    QPushButton#smallBtn[previewState="pending"] {
        background: #4A2B10;
        border: 1px solid #B7791F;
        color: #FFE1B8;
        font-weight: 700;
    }
    QPushButton#smallBtn[previewState="pending"]:hover { background: #5C3514; }
    QPushButton#smallBtn[previewState="refreshing"],
    QPushButton#smallBtn[previewState="refreshing"]:disabled {
        background: #A16207;
        border: 1px solid #D97706;
        color: #FFF7ED;
        font-weight: 700;
    }
    QPushButton#smallBtn[previewState="viewer"],
    QPushButton#smallBtn[previewState="viewer"]:disabled {
        background: #223244;
        border: 1px solid #3D5268;
        color: #9DB4C9;
        font-weight: 700;
    }

    QPushButton#stepBtn {
        background: #182C3E;
        border: 1px solid #233D55;
        border-radius: 6px;
        color: #88AACC;
        font-size: 16px;
        font-weight: 700;
    }
    QPushButton#stepBtn:hover { background: #1E3850; }

    QLineEdit {
        background: #0A1520;
        border: 1px solid #1E3040;
        border-radius: 8px;
        padding: 5px 9px;
        color: #C8DFF0;
    }
    QLineEdit:focus { border-color: #3A6A9A; }

    /* ── プレビューパネル ── */
    QFrame#viewToggleBar {
        background: #0F1C28;
        border: none;
    }
    QPushButton#viewToggleBtn {
        background: transparent;
        border: 1px solid #29455D;
        border-radius: 8px;
        padding: 6px 16px;
        color: #7EA4BE;
        font-size: 15px;
    }
    QPushButton#viewToggleBtn:hover { background: #14283A; color: #A8C8E0; }
    QPushButton#previewToolbarButton {
        background: #182C3E;
        border: 1px solid #29455D;
        border-radius: 8px;
        padding: 5px 10px;
        color: #A8C8E0;
        font-size: 14px;
    }
    QPushButton#previewToolbarButton:hover { background: #1E3850; color: #E0F2FF; }
    QPushButton#previewToolbarButton:pressed { background: #24425E; }

    QPushButton#viewToggleBtn:checked {
        background: #1A3550;
        border: 1px solid #2A5070;
        color: #E0F2FF;
        font-weight: 700;
    }

    /* ── ナビゲーションバー ── */
    QFrame#navBar {
        background: #0F1C28;
        border: none;
        border-top: 1px solid #1A2D3F;
    }
    QPushButton#navBtn {
        background: #182C3E;
        border: 1px solid #233D55;
        border-radius: 8px;
        padding: 5px 14px;
        color: #A8C8E0;
        font-size: 14px;
    }
    QPushButton#navBtn:hover { background: #1E3850; }
    QPushButton#navBtn:disabled { color: #4D6475; border-color: #172030; }
    QFrame#navSectionSep {
        color: #243C52;
        background: transparent;
    }
    QCheckBox#navToggle, QCheckBox#previewToolbarToggle {
        color: #A8C8E0;
        spacing: 6px;
        padding-right: 4px;
    }
    QCheckBox#navToggle::indicator, QCheckBox#previewToolbarToggle::indicator {
        width: 34px;
        height: 18px;
        border: 1px solid #2A4A60;
        border-radius: 9px;
        background: #0A1520;
    }
    QCheckBox#navToggle::indicator:hover, QCheckBox#previewToolbarToggle::indicator:hover { border-color: #3A6A9A; }
    QCheckBox#navToggle::indicator:checked, QCheckBox#previewToolbarToggle::indicator:checked {
        background: #215EA8;
        border: 1px solid #3A80DD;
    }

    /* ── 下部パネル ── */
    QFrame#bottomPanel { background: #0D1824; border: none; }
    QFrame#bottomPanel QTabBar::tab { min-height: 24px; padding: 4px 10px; }
    QFrame#statusStrip { background: #0F1C28; border: none; }

    QLabel#badge {
        background: #182C3E;
        border: 1px solid #1E3A50;
        border-radius: 10px;
        padding: 3px 10px;
        font-size: 13px;
        font-weight: 700;
        color: #7AAAC0;
    }

    QProgressBar {
        background: #0A1520;
        border: none;
        border-radius: 3px;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #2A6FCC, stop:1 #1ABBE0);
        border-radius: 3px;
    }

    QTabWidget::pane {
        background: #0D1824;
        border: none;
        border-top: 1px solid #1A2D3F;
    }
    QTabBar::tab {
        background: #0D1824;
        border: none;
        border-top: 2px solid transparent;
        padding: 7px 18px;
        color: #6A8CAA;
        font-size: 14px;
    }
    QTabBar::tab:selected {
        color: #A8D4F0;
        border-top: 2px solid #3A7AAA;
        background: #101E2C;
    }
    QTabBar::tab:hover { color: #80B0D0; }

    QListWidget {
        background: #0A1520;
        border: none;
        border-radius: 6px;
        color: #A8C8E0;
        font-size: 14px;
    }
    QListWidget::item:hover { background: #1A2E40; }
    QListWidget::item:selected { background: #1A3D5A; }

    QTextEdit {
        background: #080F18;
        border: 1px solid #152434;
        border-radius: 6px;
        color: #8EB1C8;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        padding: 6px;
    }

    /* ── スプリッタ ── */
    QSplitter::handle { background: #1A2D3F; }
    QSplitter::handle:horizontal {
        width: 6px;
        margin: 0 2px;
    }
    QSplitter::handle:vertical {
        height: 6px;
        margin: 2px 0;
    }
    QSplitter::handle:hover { background: #2A4560; }

    /* ── ポップアップメニュー ── */
    QMenu#gearPopupMenu {
        background: #10202F;
        color: #D7E7F5;
        border: 1px solid #29445C;
        padding: 6px;
        border-radius: 8px;
    }
    QMenu#gearPopupMenu::item {
        padding: 7px 28px 7px 12px;
        border-radius: 6px;
        font-size: 14px;
    }
    QMenu#gearPopupMenu::item:selected { background: #173249; }
    QMenu#gearPopupMenu::indicator { width: 14px; height: 14px; }
    QMenu#gearPopupMenu::separator { height: 1px; background: #29445C; margin: 6px 4px; }

    /* ── ステータスバー ── */
    QStatusBar { background: #0D1824; color: #6E92AD; font-size: 13px; }
    """
    return (stylesheet
            .replace("{SPIN_UP_ICON_DARK}", SPIN_UP_ICON_DARK)
            .replace("{SPIN_DOWN_ICON_DARK}", SPIN_DOWN_ICON_DARK))

