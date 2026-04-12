"""
tategakiXTC_gui_studio.py — GUI 本体

PySide6 ベースの縦書き XTC 変換ツール。
変換ロジックは tategakiXTC_gui_core.py に分離されています。
"""

import base64
import ctypes
import importlib
import struct
import sys
from io import BytesIO
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

_RUNTIME_DEPENDENCIES = [
    ('PySide6', 'PySide6'),
    ('Pillow', 'PIL'),
    ('ebooklib', 'ebooklib'),
    ('beautifulsoup4', 'bs4'),
    ('patool', 'patoolib'),
    ('tqdm', 'tqdm'),
]

def _collect_missing_runtime_dependencies():
    missing = []
    for package_name, module_name in _RUNTIME_DEPENDENCIES:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(package_name)
    return missing

def _show_startup_dependency_alert(missing_packages):
    install_line = 'pip install ' + ' '.join(missing_packages)
    message = (
        '次のライブラリが不足しているか、読み込みに失敗しました。\n\n'
        + '\n'.join(f'- {name}' for name in missing_packages)
        + '\n\nインストール例:\n'
        + install_line
        + '\nまたは\n'
        + 'pip install -r requirements.txt'
    )
    title = 'ライブラリ不足'
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return
        except Exception:
            pass
    print(f'{title}\n{message}', file=sys.stderr)

_missing_runtime_packages = _collect_missing_runtime_dependencies()
if _missing_runtime_packages:
    _show_startup_dependency_alert(_missing_runtime_packages)
    sys.exit(1)

from PIL import Image

from PySide6.QtCore import Qt, QObject, QThread, Signal, QSize, QSettings, QRectF, QTimer, QEvent, QPoint
from PySide6.QtGui import QActionGroup, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QSpinBox,
    QStyle,
    QStyleOptionSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import tategakiXTC_gui_core as core
from tategakiXTC_gui_core import ConversionArgs

APP_BASE_NAME = '縦書きXTC Studio'
APP_VERSION = '1.0.0'
APP_NAME = f'{APP_BASE_NAME} {APP_VERSION}'
SETTINGS_FILE = Path(__file__).with_suffix('.ini')
DEFAULT_WINDOW_WIDTH = 1600
DEFAULT_WINDOW_HEIGHT = 1000
DEFAULT_LEFT_PANEL_WIDTH = 430
DEFAULT_LEFT_SPLITTER_TOP = 760
DEFAULT_LEFT_SPLITTER_BOTTOM = 140
RESULT_TAB_INDEX = 0
LOG_TAB_INDEX = 1
SUPPORTED_INPUT_SUFFIXES = core.SUPPORTED_INPUT_SUFFIXES
UI_ASSETS_DIR = Path(__file__).resolve().parent / 'ui_assets'
SPIN_UP_ICON = (UI_ASSETS_DIR / 'spin_up.svg').as_posix()
SPIN_DOWN_ICON = (UI_ASSETS_DIR / 'spin_down.svg').as_posix()
SPIN_UP_ICON_DARK = (UI_ASSETS_DIR / 'spin_up_dark.svg').as_posix()
SPIN_DOWN_ICON_DARK = (UI_ASSETS_DIR / 'spin_down_dark.svg').as_posix()

TEXT_OR_MARKDOWN_LABEL = 'TXT / Markdown（簡易対応）'
PROCESSOR_BY_SUFFIX = {
    '.epub': core.process_epub,
    '.txt': core.process_text_file,
    '.md': core.process_markdown_file,
    '.markdown': core.process_markdown_file,
}


# ─────────────────────────────────────────────────────────
# データクラス
# ─────────────────────────────────────────────────────────

class VisibleArrowSpinBox(QSpinBox):
    """Windows環境でも上下三角が確実に見えるよう、スピンボタン上に矢印を自前描画する。"""

    def paintEvent(self, event):
        super().paintEvent(event)
        if not bool(self.property('showSpinButtons')):
            return

        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        style = self.style()
        up_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxUp, self)
        down_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, self)
        if not up_rect.isValid() or not down_rect.isValid():
            return

        theme = self.property('uiTheme') or 'light'
        fill = QColor('#0B3E78') if theme != 'dark' else QColor('#F5FAFF')
        outline = QColor('#06294D') if theme != 'dark' else QColor('#BFD8EE')

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(outline, 1.2))
        painter.setBrush(fill)

        def triangle(rect, up=True):
            cx = rect.center().x()
            cy = rect.center().y()
            half_w = max(5, min(7, rect.width() // 3))
            half_h = max(3, min(5, rect.height() // 4))
            if up:
                return QPolygon([
                    QPoint(cx, cy - half_h),
                    QPoint(cx - half_w, cy + half_h),
                    QPoint(cx + half_w, cy + half_h),
                ])
            return QPolygon([
                QPoint(cx - half_w, cy - half_h),
                QPoint(cx + half_w, cy - half_h),
                QPoint(cx, cy + half_h),
            ])

        painter.drawPolygon(triangle(up_rect, up=True))
        painter.drawPolygon(triangle(down_rect, up=False))


@dataclass
class DeviceProfile:
    key: str
    name: str
    width_px: int
    height_px: int
    ppi: float
    body_w_mm: float
    body_h_mm: float
    screen_w_mm: float
    screen_h_mm: float
    accent: str
    tagline: str


DEVICE_PROFILES = {
    'x4': DeviceProfile(
        key='x4', name='Xteink X4', width_px=480, height_px=800, ppi=220.0,
        body_w_mm=69.0, body_h_mm=114.0, screen_w_mm=55.42, screen_h_mm=92.36,
        accent='#5DA9FF', tagline='',
    ),
    'x3': DeviceProfile(
        # X3 の解像度は 横528 × 縦792 に設定
        key='x3', name='Xteink X3', width_px=528, height_px=792, ppi=252.0,
        body_w_mm=64.0, body_h_mm=98.0, screen_w_mm=48.38, screen_h_mm=80.63,
        accent='#9B80FF', tagline='',
    ),
    'custom': DeviceProfile(
        key='custom', name='Custom', width_px=480, height_px=800, ppi=220.0,
        body_w_mm=69.0, body_h_mm=114.0, screen_w_mm=55.42, screen_h_mm=92.36,
        accent='#38C172', tagline='任意サイズで確認',
    ),
}


# ─────────────────────────────────────────────────────────
# プリセット定義
# ─────────────────────────────────────────────────────────

def _make_preset(n: int, font_size: int = 20, ruby_size: int = 11, line_spacing: int = 35) -> dict:
    """プリセット辞書を生成するファクトリ関数。"""
    return {
        'button_text': f'プリセット{n}',
        'name': f'プリセット{n}',
        'profile': 'x4',
        'width': 480,
        'height': 800,
        'font_file': 'NotoSansJP-SemiBold.ttf',
        'font_size': font_size,
        'ruby_size': ruby_size,
        'line_spacing': line_spacing,
        'margin_t': 12,
        'margin_b': 14,
        'margin_r': 12,
        'margin_l': 12,
        'night_mode': False,
        'dither': False,
        'kinsoku_mode': 'standard',
        'output_format': 'xtc',
    }


DEFAULT_PRESET_DEFINITIONS = {
    'preset_1':  _make_preset(1,  font_size=20, ruby_size=11, line_spacing=35),
    'preset_2':  _make_preset(2,  font_size=22, ruby_size=11, line_spacing=37),
    'preset_3':  _make_preset(3,  font_size=24, ruby_size=12, line_spacing=41),
    'preset_4':  _make_preset(4,  font_size=26, ruby_size=12, line_spacing=41),
    'preset_5':  _make_preset(5,  font_size=27, ruby_size=12, line_spacing=41),
    'preset_6':  _make_preset(6,  font_size=28, ruby_size=12, line_spacing=44),
    'preset_7':  _make_preset(7,  font_size=29, ruby_size=12, line_spacing=44),
    'preset_8':  _make_preset(8,  font_size=30, ruby_size=13, line_spacing=44),
    'preset_9':  _make_preset(9,  font_size=31, ruby_size=13, line_spacing=44),
    'preset_10': _make_preset(10, font_size=32, ruby_size=13, line_spacing=44),
}

PRESET_FIELDS = [
    'profile', 'width', 'height', 'font_file',
    'font_size', 'ruby_size', 'line_spacing',
    'margin_t', 'margin_b', 'margin_r', 'margin_l',
    'night_mode', 'dither', 'kinsoku_mode', 'output_format',
]

KINSOKU_MODE_OPTIONS = [
    ('off', 'オフ'),
    ('simple', '簡易'),
    ('standard', '標準'),
]
KINSOKU_MODE_LABELS = {key: label for key, label in KINSOKU_MODE_OPTIONS}
OUTPUT_FORMAT_OPTIONS = [
    ('xtc', 'XTC'),
    ('xtch', 'XTCH'),
]
OUTPUT_FORMAT_LABELS = {key: label for key, label in OUTPUT_FORMAT_OPTIONS}


@dataclass
class XtcPage:
    offset: int
    length: int
    width: int
    height: int


# ─────────────────────────────────────────────────────────
# 実機プレビューウィジェット
# ─────────────────────────────────────────────────────────

class XtcViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 560)
        self.profile = DEVICE_PROFILES['x4']
        self.actual_size = False
        self.show_guides = True
        self.calibration = 1.0
        self.page_image: Optional[QImage] = None
        self.ui_theme = 'light'
        self.setFocusPolicy(Qt.StrongFocus)

    def set_ui_theme(self, theme: str):
        self.ui_theme = 'dark' if theme == 'dark' else 'light'
        self.update()

    def set_profile(self, profile: DeviceProfile):
        self.profile = profile
        self.updateGeometry()
        self.update()

    def set_actual_size(self, enabled: bool):
        self.actual_size = enabled
        self.updateGeometry()
        self.update()

    def set_show_guides(self, enabled: bool):
        self.show_guides = enabled
        self.update()

    def set_calibration(self, value: float):
        self.calibration = value
        self.updateGeometry()
        self.update()

    def set_page_image(self, image: Optional[QImage]):
        self.page_image = image
        self.update()

    def clear_page(self):
        self.page_image = None
        self.update()

    def _px_per_mm(self) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96
        return max(1.0, dpi / 25.4) * self.calibration

    def sizeHint(self) -> QSize:
        margin = 48
        if self.actual_size:
            px = self._px_per_mm()
            return QSize(
                int(self.profile.body_w_mm * px) + margin * 2,
                int(self.profile.body_h_mm * px) + margin * 2,
            )
        return QSize(
            max(360, int(660 * self.calibration)),
            max(480, int(860 * self.calibration)),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        dark = self.ui_theme == 'dark'
        outer_bg = QColor('#0D1520') if dark else QColor('#F3F6FA')
        body_fill = QColor('#132131') if dark else QColor('#FCFEFF')
        title_color = QColor('#DDEAF7') if dark else QColor('#1E3650')
        sub_color = QColor('#8EA8BF') if dark else QColor('#6E8193')
        screen_fill = QColor('#DDE4E8') if dark else QColor('#E8EEF0')
        screen_border = QColor('#6D8295') if dark else QColor('#94A3B3')
        empty_color = QColor('#93A7B9') if dark else QColor('#7E8B98')
        guide_color = QColor(114, 173, 255, 120) if dark else QColor(75, 152, 255, 110)
        guide_text = QColor('#8CA6BC') if dark else QColor('#73879A')

        painter.fillRect(self.rect(), outer_bg)
        body_rect, screen_rect = self._calculate_rects()
        if body_rect.width() <= 0 or body_rect.height() <= 0:
            return

        shadow = QPainterPath()
        shadow.addRoundedRect(body_rect.adjusted(-8, -8, 8, 8), 30, 30)
        painter.fillPath(shadow, QColor(0, 0, 0, 28))

        body = QPainterPath()
        body.addRoundedRect(body_rect, 26, 26)
        painter.fillPath(body, body_fill)
        painter.setPen(QPen(QColor(self.profile.accent), 2.2))
        painter.drawPath(body)

        band = body_rect.adjusted(18, 16, -18, -(body_rect.height() - 52))
        painter.fillRect(band.toRect(), QColor(0, 0, 0, 6))

        f = QFont('Meiryo', 11)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(title_color)
        painter.drawText(body_rect.adjusted(0, 10, 0, 0), Qt.AlignTop | Qt.AlignHCenter, self.profile.name)
        painter.setFont(QFont('Meiryo', 10))
        painter.setPen(sub_color)
        painter.drawText(
            body_rect.adjusted(12, 28, -12, 0),
            Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap,
            self.profile.tagline,
        )

        sp = QPainterPath()
        sp.addRoundedRect(screen_rect, 16, 16)
        painter.fillPath(sp, screen_fill)
        painter.setPen(QPen(screen_border, 1.0))
        painter.drawPath(sp)

        page_rect = screen_rect.adjusted(7, 7, -7, -7)
        if self.page_image and not self.page_image.isNull():
            pix = QPixmap.fromImage(self.page_image)
            scaled = pix.scaled(page_rect.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            ix = int(page_rect.x() + (page_rect.width() - scaled.width()) / 2)
            iy = int(page_rect.y() + (page_rect.height() - scaled.height()) / 2)
            painter.drawPixmap(ix, iy, scaled)
        else:
            painter.setPen(empty_color)
            painter.setFont(QFont('Meiryo', 14))
            painter.drawText(
                page_rect.toRect(), Qt.AlignCenter,
                'XTCを読み込むと\nここに実機風プレビューを表示します',
            )

        if self.show_guides:
            painter.setPen(QPen(guide_color, 1, Qt.DashLine))
            painter.drawRect(page_rect.toRect())
            painter.setFont(QFont('Meiryo', 10))
            painter.setPen(guide_text)
            info = (
                f'{self.profile.width_px}×{self.profile.height_px}px'
                f' / {self.profile.screen_w_mm:.1f}×{self.profile.screen_h_mm:.1f}mm'
            )
            painter.drawText(
                screen_rect.adjusted(0, 0, 0, -8).toRect(),
                Qt.AlignBottom | Qt.AlignHCenter,
                info,
            )

    def _calculate_rects(self):
        margin = 34
        c = self.rect().adjusted(margin, margin, -margin, -margin)
        if self.actual_size:
            px = self._px_per_mm()
            body_w = int(self.profile.body_w_mm * px)
            body_h = int(self.profile.body_h_mm * px)
        else:
            scale = min(c.width() / self.profile.body_w_mm, c.height() / self.profile.body_h_mm)
            body_w = int(self.profile.body_w_mm * scale)
            body_h = int(self.profile.body_h_mm * scale)
            px = scale
        x = c.x() + max(0, (c.width() - body_w) // 2)
        y = c.y() + max(0, (c.height() - body_h) // 2)
        body_rect = QRectF(x, y, body_w, body_h)
        sw = int(self.profile.screen_w_mm * px)
        sh = int(self.profile.screen_h_mm * px)
        sx = body_rect.x() + (body_rect.width() - sw) / 2
        vertical_bezel = max(0.0, body_rect.height() - sh)
        top_bezel_ratio = 0.34
        sy = body_rect.y() + vertical_bezel * top_bezel_ratio
        return body_rect, QRectF(sx, sy, sw, sh)


# ─────────────────────────────────────────────────────────
# 変換ワーカー
# ─────────────────────────────────────────────────────────

class ConversionWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, settings_dict: dict):
        super().__init__()
        self.settings_dict = settings_dict
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        try:
            self.finished.emit(self._convert())
        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _build_args(cfg: dict) -> ConversionArgs:
        return ConversionArgs(
            width=int(cfg.get('width', 480)),
            height=int(cfg.get('height', 800)),
            font_size=int(cfg.get('font_size', 26)),
            ruby_size=int(cfg.get('ruby_size', 12)),
            line_spacing=int(cfg.get('line_spacing', 44)),
            margin_t=int(cfg.get('margin_t', 12)),
            margin_b=int(cfg.get('margin_b', 14)),
            margin_r=int(cfg.get('margin_r', 12)),
            margin_l=int(cfg.get('margin_l', 12)),
            dither=bool(cfg.get('dither', False)),
            night_mode=bool(cfg.get('night_mode', False)),
            threshold=int(cfg.get('threshold', 128)),
            kinsoku_mode=str(cfg.get('kinsoku_mode', 'standard')),
            output_format=str(cfg.get('output_format', 'xtc')),
        )

    @staticmethod
    def _resolve_supported_targets(tp: Path):
        all_targets = core.iter_conversion_targets(tp)
        targets = [p for p in all_targets if not core.should_skip_conversion_target(p)]
        return [p for p in targets if p.suffix.lower() in SUPPORTED_INPUT_SUFFIXES]

    @staticmethod
    def _sanitize_output_stem(name: str) -> str:
        return Path(Path(name).name).stem.strip()

    def _output_path_for_target(self, path: Path, args, requested_name: str, supported_count: int):
        use_custom = bool(requested_name) and supported_count == 1
        if requested_name and not use_custom:
            self.log.emit('出力名の指定は単一ファイル変換時のみ使用します。今回は自動命名にします。')
        if use_custom:
            stem = self._sanitize_output_stem(requested_name)
            if not stem:
                raise RuntimeError('出力ファイル名が不正です。')
            ext = '.xtch' if str(getattr(args, 'output_format', 'xtc')).strip().lower() == 'xtch' else '.xtc'
            return core.make_unique_output_path(path.parent / f'{stem}{ext}')
        desired = core.get_output_path_for_target(path, getattr(args, 'output_format', 'xtc'))
        if not desired:
            return None
        return core.make_unique_output_path(desired)

    def _process_target(self, path: Path, font_path: Path, args, out_path: Path):
        suffix = path.suffix.lower()
        processor = PROCESSOR_BY_SUFFIX.get(suffix)
        if processor is not None:
            return processor(path, str(font_path), args, output_path=out_path)
        return core.process_archive(path, args, output_path=out_path)

    def _convert(self) -> dict:
        cfg = self.settings_dict
        target_raw = str(cfg.get('target', '')).strip()
        if not target_raw:
            raise RuntimeError('変換対象ファイルまたはフォルダを指定してください。')
        tp = Path(target_raw)
        if not tp.exists():
            raise RuntimeError(f'指定したパスが見つかりません: {tp}')

        font_path = core.resolve_font_path(cfg.get('font_file', ''))
        if not font_path or not Path(font_path).exists():
            raise RuntimeError(f'フォントが見つかりません: {cfg.get("font_file", "") or font_path}')

        args = self._build_args(cfg)
        supported = self._resolve_supported_targets(tp)
        if not supported:
            raise RuntimeError(f'変換対象の EPUB / ZIP / RAR / CBZ / CBR / {TEXT_OR_MARKDOWN_LABEL} が見つかりませんでした。')

        requested_name = str(cfg.get('output_name', '')).strip()
        converted, stopped = [], False
        total = len(supported)
        for idx, path in enumerate(supported, 1):
            if self._stop_requested:
                stopped = True
                self.log.emit('停止要求を受け付けました。')
                break
            self.log.emit(f'[{idx}/{total}] 変換中: {path.name}')
            out_path = self._output_path_for_target(path, args, requested_name, total)
            if not out_path:
                continue
            saved = self._process_target(path, font_path, args, out_path)
            converted.append(str(saved))
            self.log.emit(f'保存: {Path(saved).name}')
            if self._stop_requested:
                stopped = True
                self.log.emit('停止しました。')
                break

        if cfg.get('open_folder', True):
            try:
                tgt = tp.parent if tp.is_file() else tp
                if sys.platform.startswith('win'):
                    import os
                    os.startfile(tgt)
            except Exception:
                pass

        msg = (
            f'変換を停止しました。({len(converted)} 件を保存)'
            if stopped
            else f'変換完了しました。({len(converted)} 件)'
        )
        self.log.emit(msg)
        return {'message': msg, 'converted_files': converted, 'stopped': stopped}


# ─────────────────────────────────────────────────────────
# メインウィンドウ
# ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    # ── 初期化 ────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.settings_store = QSettings(str(SETTINGS_FILE), QSettings.IniFormat)
        self.preset_definitions = self._load_preset_definitions()
        self.setWindowTitle(APP_NAME)
        initial_size = self._default_window_size()
        self.resize(initial_size.width(), initial_size.height())

        self.current_profile_key = 'x4'
        self.current_preview_mode = 'text'
        self.preview_image_data_url = None
        self.xtc_bytes: Optional[bytes] = None
        self.xtc_pages: List[XtcPage] = []
        self.current_page_index = 0
        self.nav_buttons_reversed = False
        self.current_ui_theme = 'light'
        self.panel_button_visible = True
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[ConversionWorker] = None
        self._startup_pending = True
        self._pending_left_panel_width: Optional[int] = None
        self._initialized = False  # 初期化完了前の save_ui_state を抑制

        self._build_ui()
        QApplication.instance().installEventFilter(self)
        self._setup_global_navigation_shortcuts()
        self._apply_styles()
        self._restore_settings()
        self.refresh_preview()
        self._initialized = True

    def _default_window_size(self) -> QSize:
        width = max(1100, self.settings_store.value('window_width', DEFAULT_WINDOW_WIDTH, type=int))
        height = max(760, self.settings_store.value('window_height', DEFAULT_WINDOW_HEIGHT, type=int))
        return QSize(width, height)

    def _default_left_splitter_sizes(self) -> list[int]:
        top = max(280, self.settings_store.value('left_splitter_top', DEFAULT_LEFT_SPLITTER_TOP, type=int))
        bottom = max(92, self.settings_store.value('left_splitter_bottom', DEFAULT_LEFT_SPLITTER_BOTTOM, type=int))
        return [top, bottom]

    def showEvent(self, event):
        super().showEvent(event)
        if self._startup_pending:
            self._startup_pending = False
            QTimer.singleShot(0, self._apply_initial_sizes)
            QTimer.singleShot(0, self.refresh_preview)
        else:
            QTimer.singleShot(0, self._sync_preview_size)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'preview_label') and hasattr(self, 'viewer_widget'):
            self._sync_preview_size()

    def closeEvent(self, event):
        self.save_ui_state()
        super().closeEvent(event)

    def _setup_global_navigation_shortcuts(self):
        # 左右キーは eventFilter 側で一元処理する。
        # 以前は QShortcut と KeyPress の両方で反応し、1回の押下で2ページ送られることがあった。
        self.left_arrow_shortcut = None
        self.right_arrow_shortcut = None

    def eventFilter(self, obj, event):
        # 実機ビューのページ送り：左右矢印キー対応
        if event.type() == QEvent.ShortcutOverride:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right) and self._can_handle_device_view_arrow_key():
                event.accept()
                return True
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right):
                if self._handle_device_view_arrow_key(key):
                    event.accept()
                    return True
        return super().eventFilter(obj, event)

    def _can_handle_device_view_arrow_key(self) -> bool:
        if getattr(self, 'main_view_mode', 'font') != 'device':
            return False
        if not getattr(self, 'xtc_pages', None):
            return False

        fw = QApplication.focusWidget()
        # 入力・選択系ウィジェットでは矢印キー本来の挙動を優先
        if fw is not None:
            from PySide6.QtWidgets import QLineEdit, QTextEdit, QSpinBox, QComboBox, QListWidget
            if isinstance(fw, (QLineEdit, QTextEdit, QSpinBox, QComboBox, QListWidget)):
                return False
        return True

    def _handle_device_view_arrow_key(self, key: int) -> bool:
        if not self._can_handle_device_view_arrow_key():
            return False

        if hasattr(self, 'viewer_widget'):
            self.viewer_widget.setFocus(Qt.ShortcutFocusReason)

        logical_delta = -1 if key == Qt.Key_Left else 1
        delta = -logical_delta if self.nav_buttons_reversed else logical_delta
        self.change_page(delta)
        return True

    def _apply_initial_sizes(self):
        if self._pending_left_panel_width is not None:
            self._apply_left_panel_width(self._pending_left_panel_width)
            self._pending_left_panel_width = None
        if not self.settings_store.contains('left_splitter_state'):
            self.left_splitter.setSizes(self._default_left_splitter_sizes())
        self._sync_preview_size()

    # ── UI 構築 ────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName('topSep')
        root.addWidget(sep)

        self.left_panel = self._build_left_settings()
        self.left_panel.setMinimumWidth(380)

        right = self._build_right_preview()

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        root.addWidget(self.main_splitter, 1)
        self.main_view_mode = 'font'
        self.statusBar().showMessage('準備完了')

    # ── トップバー ─────────────────────────────────────────

    def _build_top_bar(self):
        bar = QFrame()
        bar.setObjectName('topBar')
        bar.setFixedHeight(56)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(10)

        title = QLabel(APP_NAME)
        title.setObjectName('appTitle')
        lay.addWidget(title)
        lay.addWidget(self._v_sep())

        btn_file = QPushButton('ファイル')
        btn_file.setObjectName('topBtn')
        btn_file.setFixedWidth(72)
        btn_file.clicked.connect(lambda: self.select_target_path(True))

        btn_folder = QPushButton('フォルダ')
        btn_folder.setObjectName('topBtn')
        btn_folder.setFixedWidth(72)
        btn_folder.clicked.connect(lambda: self.select_target_path(False))

        lay.addWidget(btn_file)
        lay.addWidget(btn_folder)

        self.target_edit = QLineEdit()
        self.target_edit.setObjectName('targetEdit')
        self.target_edit.setPlaceholderText('EPUB / ZIP / CBZ / CBR / RAR / TXT またはフォルダ')
        self.target_edit.editingFinished.connect(self._update_top_status)
        self.target_edit.editingFinished.connect(self.refresh_preview)
        lay.addWidget(self.target_edit, 1)
        lay.addWidget(self._v_sep())

        self.run_btn = QPushButton('▶  変換実行')
        self.run_btn.setObjectName('runBtn')
        self.run_btn.setFixedWidth(130)
        self.run_btn.clicked.connect(self.start_conversion)
        lay.addWidget(self.run_btn)

        self.stop_btn = QPushButton('■  停止')
        self.stop_btn.setObjectName('stopBtn')
        self.stop_btn.setFixedWidth(90)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_conversion)
        lay.addWidget(self.stop_btn)
        lay.addWidget(self._v_sep())

        self.panel_btn = QPushButton('≡')
        self.panel_btn.setObjectName('iconBtn')
        self.panel_btn.setFocusPolicy(Qt.NoFocus)
        self.panel_btn.setFixedSize(36, 36)
        self.panel_btn.setToolTip('左パネルの表示/非表示')
        self.panel_btn.clicked.connect(self.toggle_left_panel)
        lay.addWidget(self.panel_btn)

        help_btn = QPushButton('?')
        help_btn.setObjectName('iconBtn')
        help_btn.setFocusPolicy(Qt.NoFocus)
        help_btn.setFixedSize(36, 36)
        help_btn.setToolTip('使い方の流れ')
        help_btn.clicked.connect(self.show_help_dialog)
        lay.addWidget(help_btn)

        self.settings_btn = QPushButton('⚙')
        self.settings_btn.setObjectName('iconBtn')
        self.settings_btn.setFocusPolicy(Qt.NoFocus)
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip('表示設定')
        self.settings_btn.clicked.connect(self.show_display_settings_popup)
        lay.addWidget(self.settings_btn)

        return bar

    @staticmethod
    def _v_sep():
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setObjectName('vSep')
        line.setFixedWidth(1)
        return line

    # ── 左設定パネル ──────────────────────────────────────

    def _build_left_settings(self):
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(False)
        self.left_splitter.setHandleWidth(5)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName('leftSettingsContainer')
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 9, 10, 9)
        lay.setSpacing(5)
        self._ensure_behavior_controls()
        lay.addWidget(self._section_font())
        lay.addWidget(self._section_display())
        lay.addWidget(self._section_image())
        lay.addWidget(self._section_preset())
        lay.addStretch(1)
        scroll.setWidget(container)

        self.bottom_panel = self._build_bottom_panel()
        self.bottom_panel.setMinimumHeight(92)

        self.left_splitter.addWidget(scroll)
        self.left_splitter.addWidget(self.bottom_panel)
        self.left_splitter.setStretchFactor(0, 3)
        self.left_splitter.setStretchFactor(1, 1)
        self.left_splitter.setSizes(self._default_left_splitter_sizes())
        return self.left_splitter

    # ── 設定セクション：フォントと組版 ────────────────────

    def _section_font(self):
        box = self._make_section('フォントと組版')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 12, 8, 7)
        lay.setSpacing(6)

        font_row = QHBoxLayout()
        self.font_combo = QComboBox()
        for f in self._available_font_names():
            self.font_combo.addItem(f)
        self._apply_default_font_selection()
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        font_row.addWidget(self.font_combo, 1)
        browse_btn = QPushButton('参照')
        browse_btn.setObjectName('smallBtn')
        browse_btn.clicked.connect(self.select_font_file)
        font_row.addWidget(browse_btn)
        lay.addLayout(font_row)

        self.font_size_spin = self._spin(18, 72, 26, compact=True, buttons=True)
        self.ruby_size_spin = self._spin(8, 32, 12, compact=True, buttons=True)
        self.line_spacing_spin = self._spin(24, 80, 44, compact=True, buttons=True)
        lay.addLayout(self._spin_row([
            ('本文', self.font_size_spin),
            ('ルビ', self.ruby_size_spin),
            ('行間', self.line_spacing_spin),
        ]))

        self.margin_t_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        self.margin_b_spin = self._spin(0, 80, 14, compact=True, buttons=True)
        self.margin_r_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        self.margin_l_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        lay.addWidget(self._build_margin_rows())

        format_row = QHBoxLayout()
        format_row.addWidget(self._dim_label('出力形式'))
        self.output_format_combo = QComboBox()
        for key, label in OUTPUT_FORMAT_LABELS.items():
            self.output_format_combo.addItem(label, key)
        self.output_format_combo.currentIndexChanged.connect(self.refresh_preview)
        self.output_format_combo.currentIndexChanged.connect(lambda _i, self=self: self.save_ui_state())
        format_row.addWidget(self.output_format_combo)
        format_row.addStretch(1)
        lay.addLayout(format_row)

        self._ensure_behavior_controls()
        kinsoku_row = QHBoxLayout()
        kinsoku_row.addWidget(self._dim_label('禁則処理'))
        kinsoku_row.addWidget(self.kinsoku_mode_combo)
        kinsoku_row.addSpacing(6)
        kinsoku_row.addWidget(self._help_icon_button('オフ: 禁則処理を行わず機械的に流し込みます。簡易: 行頭禁則・行末禁則・句読点のぶら下げのみ行います。標準: 連続約物や閉じ括弧＋句読点のまとまりも含めて、現在の禁則処理を有効にします。'))
        kinsoku_row.addStretch(1)
        lay.addLayout(kinsoku_row)

        for w in [
            self.font_size_spin, self.ruby_size_spin, self.line_spacing_spin,
            self.margin_t_spin, self.margin_b_spin, self.margin_r_spin, self.margin_l_spin,
        ]:
            w.valueChanged.connect(self.refresh_preview)
            w.valueChanged.connect(lambda _v, self=self: self.save_ui_state())
        return box

    def _build_margin_rows(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        row1 = QHBoxLayout()
        row1.addWidget(self._dim_label('上余白'))
        row1.addWidget(self.margin_t_spin)
        row1.addSpacing(16)
        row1.addWidget(self._dim_label('下余白'))
        row1.addWidget(self.margin_b_spin)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        row2.addWidget(self._dim_label('右余白'))
        row2.addWidget(self.margin_r_spin)
        row2.addSpacing(16)
        row2.addWidget(self._dim_label('左余白'))
        row2.addWidget(self.margin_l_spin)
        row2.addStretch(1)

        lay.addLayout(row1)
        lay.addLayout(row2)
        return w

    # ── 設定セクション：表示と実機 ────────────────────────

    def _section_display(self):
        box = self._make_section('表示と実機')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(self._dim_label('機種'))
        self.profile_combo = QComboBox()
        self.profile_combo.addItem('Xteink X4', 'x4')
        self.profile_combo.addItem('Xteink X3', 'x3')
        self.profile_combo.addItem('Custom', 'custom')
        self.profile_combo.setMinimumWidth(130)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        row1.addWidget(self.profile_combo)
        row1.addSpacing(16)
        self.night_check = QCheckBox('白黒反転')
        self.night_check.toggled.connect(self.refresh_preview)
        row1.addWidget(self.night_check)
        row1.addStretch(1)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.actual_size_check = QCheckBox('実寸近似')
        self.actual_size_check.toggled.connect(self.on_actual_size_toggled)
        self.guides_check = QCheckBox('ガイド')
        self.guides_check.setChecked(True)
        row2.addWidget(self.actual_size_check)
        row2.addWidget(self.guides_check)
        row2.addSpacing(16)
        row2.addWidget(self._dim_label('実寸補正'))
        self.calib_down_btn = QPushButton('−')
        self.calib_down_btn.setObjectName('stepBtn')
        self.calib_down_btn.setFixedSize(24, 24)
        row2.addWidget(self.calib_down_btn)
        self.calib_spin = QSpinBox()
        self.calib_spin.setRange(50, 300)
        self.calib_spin.setSingleStep(5)
        self.calib_spin.setAccelerated(True)
        self.calib_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.calib_spin.setValue(100)
        self.calib_spin.setSuffix('%')
        self.calib_spin.setFixedWidth(62)
        self.calib_spin.valueChanged.connect(self.on_calibration_changed)
        row2.addWidget(self.calib_spin)
        self.calib_up_btn = QPushButton('+')
        self.calib_up_btn.setObjectName('stepBtn')
        self.calib_up_btn.setFixedSize(24, 24)
        row2.addWidget(self.calib_up_btn)
        row2.addSpacing(6)
        row2.addWidget(self._help_icon_button('実寸補正: 実機の見え方に合わせて全体の大きさを微調整します。白黒反転: 白と黒を入れ替えて見え方を確認します。変換時は出力ファイルにも反映されます。'))
        row2.addStretch(1)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        self.width_spin = self._spin(240, 2000, 480)
        self.height_spin = self._spin(240, 2000, 800)
        self.custom_size_row = QWidget()
        self.custom_size_row.setVisible(False)
        cs_lay = QHBoxLayout(self.custom_size_row)
        cs_lay.setContentsMargins(0, 0, 0, 0)
        cs_lay.addWidget(self._dim_label('幅'))
        cs_lay.addWidget(self.width_spin)
        cs_lay.addSpacing(8)
        cs_lay.addWidget(self._dim_label('高さ'))
        cs_lay.addWidget(self.height_spin)
        row3.addWidget(self.custom_size_row)
        row3.addStretch(1)
        self.open_xtc_btn = QPushButton('XTC/XTCHを開く')
        self.open_xtc_btn.setObjectName('smallBtn')
        self.open_xtc_btn.clicked.connect(self.open_xtc_file)
        row3.addWidget(self.open_xtc_btn)
        lay.addLayout(row3)

        self.profile_hint = QLabel(DEVICE_PROFILES['x4'].tagline)
        self.profile_hint.setObjectName('hintLabel')
        self.profile_hint.setVisible(bool(DEVICE_PROFILES['x4'].tagline))
        lay.addWidget(self.profile_hint)

        self.guides_check.toggled.connect(lambda v: self.viewer_widget.set_show_guides(v))
        self.calib_down_btn.clicked.connect(lambda: self.calib_spin.stepBy(-1))
        self.calib_up_btn.clicked.connect(lambda: self.calib_spin.stepBy(1))
        self.width_spin.valueChanged.connect(self.refresh_preview)
        self.height_spin.valueChanged.connect(self.refresh_preview)
        return box

    # ── 設定セクション：画像処理 ──────────────────────────

    def _section_image(self):
        box = self._make_section('画像処理')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 12, 8, 7)
        lay.setSpacing(5)

        row = QHBoxLayout()
        self.dither_check = QCheckBox('ディザリング')
        self.dither_check.setChecked(False)
        self.dither_check.toggled.connect(self.on_dither_toggled)
        row.addWidget(self.dither_check)
        row.addSpacing(16)
        row.addWidget(self._dim_label('しきい値'))
        self.threshold_spin = self._spin(0, 255, 128, compact=True)
        self.threshold_spin.setEnabled(False)
        self.threshold_spin.valueChanged.connect(self.refresh_preview)
        row.addWidget(self.threshold_spin)
        row.addSpacing(6)
        row.addWidget(self._help_icon_button('しきい値: 白と黒の分かれ目を調整します。ディザリング: 粒状感と引き換えに濃淡感を残します。'))
        row.addStretch(1)
        lay.addLayout(row)
        return box

    # ── 設定セクション：プリセット ────────────────────────

    def _section_preset(self):
        box = self._make_section('プリセット')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(6)

        row = QHBoxLayout()
        self.preset_combo = QComboBox()
        for key, p in self.preset_definitions.items():
            self.preset_combo.addItem(p['button_text'], key)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selection_changed)
        row.addWidget(self.preset_combo, 1)

        apply_btn = QPushButton('適用')
        apply_btn.setObjectName('smallBtn')
        apply_btn.clicked.connect(self.apply_selected_preset)
        row.addWidget(apply_btn)

        save_btn = QPushButton('保存')
        save_btn.setObjectName('smallBtn')
        save_btn.setToolTip('現在の設定をこのプリセットへ上書き保存')
        save_btn.clicked.connect(self.save_selected_preset)
        row.addWidget(save_btn)
        lay.addLayout(row)

        self.preset_summary_label = QLabel('')
        self.preset_summary_label.setObjectName('presetSummaryLabel')
        self.preset_summary_label.setWordWrap(True)
        lay.addWidget(self.preset_summary_label)
        return box

    def _ensure_behavior_controls(self):
        if hasattr(self, 'open_folder_check'):
            return
        self.open_folder_check = QCheckBox('完了後フォルダを開く')
        self.open_folder_check.setChecked(True)
        self.open_folder_check.toggled.connect(self.save_ui_state)

        self.kinsoku_mode_combo = QComboBox()
        for key, label in KINSOKU_MODE_OPTIONS:
            self.kinsoku_mode_combo.addItem(label, key)
        self.kinsoku_mode_combo.currentIndexChanged.connect(self._on_kinsoku_mode_changed)

    # ── 設定セクション：その他オプション ────────────────────────

    def _section_behavior(self):
        box = self._make_section('その他オプション')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(6)

        self._ensure_behavior_controls()

        row1 = QHBoxLayout()
        row1.addWidget(self.open_folder_check)
        row1.addStretch(1)
        lay.addLayout(row1)
        return box

    # ── 右プレビューパネル ────────────────────────────────

    def _build_right_preview(self):
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._build_view_toggle_bar())

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName('topSep')
        lay.addWidget(sep)

        self.preview_stack = QStackedWidget()

        font_page = QWidget()
        fl = QVBoxLayout(font_page)
        fl.setContentsMargins(8, 8, 8, 8)
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(False)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(360, 600)
        self.preview_label.setWordWrap(True)
        self.preview_scroll.setWidget(self.preview_label)
        fl.addWidget(self.preview_scroll)
        self.preview_stack.addWidget(font_page)

        device_page = QWidget()
        dl = QVBoxLayout(device_page)
        dl.setContentsMargins(8, 8, 8, 8)
        self.viewer_scroll = QScrollArea()
        self.viewer_scroll.setWidgetResizable(False)
        self.viewer_scroll.setAlignment(Qt.AlignCenter)
        self.viewer_scroll.setFrameShape(QFrame.NoFrame)
        self.viewer_scroll.setFocusPolicy(Qt.StrongFocus)
        self.viewer_widget = XtcViewerWidget()
        self.viewer_widget.setMinimumSize(360, 600)
        self.viewer_scroll.setWidget(self.viewer_widget)
        dl.addWidget(self.viewer_scroll)
        self.preview_stack.addWidget(device_page)

        lay.addWidget(self.preview_stack, 1)
        lay.addWidget(self._build_nav_bar())

        self.preview_stack.setCurrentIndex(0)
        self._sync_preview_size()
        return panel

    def _build_view_toggle_bar(self):
        bar = QFrame()
        bar.setObjectName('viewToggleBar')
        bar.setFixedHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(6)

        self.font_view_btn = QPushButton('フォントビュー')
        self.font_view_btn.setObjectName('viewToggleBtn')
        self.font_view_btn.setCheckable(True)
        self.font_view_btn.setChecked(True)
        self.font_view_btn.setFocusPolicy(Qt.NoFocus)
        self.font_view_btn.clicked.connect(lambda: self.set_main_view_mode('font'))

        self.device_view_btn = QPushButton('実機ビュー')
        self.device_view_btn.setObjectName('viewToggleBtn')
        self.device_view_btn.setCheckable(True)
        self.device_view_btn.setFocusPolicy(Qt.NoFocus)
        self.device_view_btn.clicked.connect(lambda: self.set_main_view_mode('device'))

        lay.addWidget(self.font_view_btn)
        lay.addWidget(self.device_view_btn)
        lay.addStretch(1)

        self.view_help_btn = self._help_icon_button('フォントビュー: 文字サイズ・余白・ルビの見え方を調整するときに使います。')
        lay.addWidget(self.view_help_btn)
        return bar

    def _build_nav_bar(self):
        bar = QFrame()
        bar.setObjectName('navBar')
        bar.setFixedHeight(48)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        self.current_xtc_label = QLabel('表示中: なし')
        self.current_xtc_label.setObjectName('hintLabel')
        lay.addWidget(self.current_xtc_label, 1)

        self.nav_reverse_check = QCheckBox('反転')
        self.nav_reverse_check.setObjectName('navToggle')
        self.nav_reverse_check.setFocusPolicy(Qt.NoFocus)
        self.nav_reverse_check.toggled.connect(self.on_nav_reverse_toggled)
        lay.addWidget(self.nav_reverse_check)

        self.prev_btn = QPushButton('前')
        self.prev_btn.setObjectName('navBtn')
        self.prev_btn.setFocusPolicy(Qt.NoFocus)
        self.prev_btn.clicked.connect(lambda: self.on_nav_button_clicked(-1))
        lay.addWidget(self.prev_btn)

        lay.addWidget(self._dim_label('ページ'))
        self.page_input = QSpinBox()
        self.page_input.setRange(0, 0)
        self.page_input.setButtonSymbols(QSpinBox.NoButtons)
        self.page_input.setKeyboardTracking(False)
        self.page_input.setFixedWidth(60)
        self.page_input.valueChanged.connect(self.on_page_input_changed)
        lay.addWidget(self.page_input)

        self.page_total_label = QLabel('/ 0')
        self.page_total_label.setObjectName('hintLabel')
        lay.addWidget(self.page_total_label)

        self.next_btn = QPushButton('次')
        self.next_btn.setObjectName('navBtn')
        self.next_btn.setFocusPolicy(Qt.NoFocus)
        self.next_btn.clicked.connect(lambda: self.on_nav_button_clicked(1))
        lay.addWidget(self.next_btn)

        self._update_nav_button_texts()
        return bar

    # ── 下部パネル（ステータス + 結果/ログ）────────────────

    def _build_bottom_panel(self):
        panel = QFrame()
        panel.setObjectName('bottomPanel')
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        strip = QFrame()
        strip.setObjectName('statusStrip')
        strip.setFixedHeight(34)
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(14, 0, 14, 0)
        sl.setSpacing(10)

        self.busy_badge = QLabel('待機中')
        self.busy_badge.setObjectName('badge')
        sl.addWidget(self.busy_badge)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setMaximumWidth(200)
        sl.addWidget(self.progress_bar)

        self.progress_label = QLabel('変換を開始すると進行状況を表示します。')
        self.progress_label.setObjectName('hintLabel')
        sl.addWidget(self.progress_label, 1)

        lay.addWidget(strip)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName('topSep')
        lay.addWidget(sep)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self._build_results_tab(), '変換結果')
        self.bottom_tabs.addTab(self._build_log_tab(), 'ログ')
        lay.addWidget(self.bottom_tabs, 1)
        return panel

    def _build_results_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.SingleSelection)
        self.results_list.itemClicked.connect(self.on_result_item_clicked)
        self.results_list.itemActivated.connect(self.on_result_item_clicked)
        lay.addWidget(self.results_list, 1)
        return w

    def _build_log_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        lay.addWidget(self.log_edit)
        return w

    # ── ヘルパー ───────────────────────────────────────────

    @staticmethod
    def _make_section(title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName('settingsSection')
        return box

    @staticmethod
    def _dim_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName('dimLabel')
        return lbl


    @staticmethod
    def _note_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName('subNoteLabel')
        lbl.setWordWrap(True)
        return lbl

    def _help_icon_button(self, text: str, *, tooltip: Optional[str] = None) -> QPushButton:
        btn = QPushButton('?')
        btn.setObjectName('miniHelpBtn')
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(20, 20)
        tip = tooltip if tooltip is not None else text
        btn.setToolTip(tip)
        btn.setProperty('helpText', tip)
        btn.clicked.connect(lambda _checked=False, b=btn: self._show_inline_help(b))
        return btn

    def _show_inline_help(self, button: QPushButton):
        text = str(button.property('helpText') or '').strip()
        if not text:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle('説明')
        msg.setIcon(QMessageBox.Information)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.exec()

    def _build_flow_guide(self) -> QFrame:
        box = QFrame()
        box.setObjectName('flowGuide')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        title = QLabel('使い方')
        title.setObjectName('flowGuideTitle')
        title_row.addWidget(title)
        title_row.addWidget(self._help_icon_button('1. ファイルを開く → 2. プリセットを選ぶ → 3. 必要なら微調整 → 4. 変換実行 → 5. 実機ビューで確認'))
        title_row.addStretch(1)
        lay.addLayout(title_row)
        return box

    def _spin(self, minimum: int, maximum: int, value: int, *, compact: bool = False, buttons: bool = False) -> QSpinBox:
        s = VisibleArrowSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setAccelerated(True)
        s.setProperty('showSpinButtons', buttons)
        s.setProperty('uiTheme', self.current_ui_theme)
        if buttons:
            s.setButtonSymbols(QSpinBox.UpDownArrows)
            s.setFixedWidth(78 if compact else 84)
        else:
            s.setButtonSymbols(QSpinBox.NoButtons)
            s.setFixedWidth(56)
        if compact:
            s.setProperty('compactField', True)
            s.setFixedHeight(24)
        return s

    @staticmethod
    def _spin_row(pairs: list) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(3)
        for i, (label, widget) in enumerate(pairs):
            if i > 0:
                row.addSpacing(6)
            lbl = QLabel(label)
            lbl.setObjectName('dimLabel')
            row.addWidget(lbl)
            row.addWidget(widget)
        row.addStretch(1)
        return row

    # ── スタイルシート ─────────────────────────────────────

    def _apply_styles(self):
        stylesheet = self._dark_stylesheet() if self.current_ui_theme == 'dark' else self._light_stylesheet()
        for s in self.findChildren(QSpinBox):
            s.setProperty('uiTheme', self.current_ui_theme)
            s.style().unpolish(s)
            s.style().polish(s)
            s.update()
        self.setStyleSheet(stylesheet)
        if hasattr(self, 'viewer_widget'):
            self.viewer_widget.set_ui_theme(self.current_ui_theme)

    def _light_stylesheet(self) -> str:
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

        QLabel#appTitle {
            font-size: 17px;
            font-weight: 700;
            color: #1F3A56;
            letter-spacing: 0.5px;
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
            padding-right: 26px;
            border-color: #7D9FBE;
        }
        QSpinBox[showSpinButtons="true"]::up-button,
        QSpinBox[showSpinButtons="true"]::down-button {
            width: 28px;
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
            width: 16px;
            height: 12px;
        }
        QSpinBox[showSpinButtons="true"]::down-arrow {
            image: url({SPIN_DOWN_ICON});
            width: 16px;
            height: 12px;
        }

        QCheckBox { color: #35506A; spacing: 6px; }
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
        QCheckBox#navToggle {
            color: #35506A;
            spacing: 6px;
            padding-right: 4px;
        }
        QCheckBox#navToggle::indicator {
            width: 34px;
            height: 18px;
            border: 1px solid #AFC1D2;
            border-radius: 9px;
            background: #FFFFFF;
        }
        QCheckBox#navToggle::indicator:hover { border-color: #77AEEB; }
        QCheckBox#navToggle::indicator:checked {
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

    def _dark_stylesheet(self) -> str:
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

        QLabel#appTitle {
            font-size: 17px;
            font-weight: 700;
            color: #E8F6FF;
            letter-spacing: 0.5px;
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
            padding-right: 26px;
            border-color: #6D88A4;
        }
        QSpinBox[showSpinButtons="true"]::up-button,
        QSpinBox[showSpinButtons="true"]::down-button {
            width: 28px;
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
            width: 16px;
            height: 12px;
        }
        QSpinBox[showSpinButtons="true"]::down-arrow {
            image: url({SPIN_DOWN_ICON_DARK});
            width: 16px;
            height: 12px;
        }

        QCheckBox { color: #A8C8E0; spacing: 6px; }
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
        QCheckBox#navToggle {
            color: #A8C8E0;
            spacing: 6px;
            padding-right: 4px;
        }
        QCheckBox#navToggle::indicator {
            width: 34px;
            height: 18px;
            border: 1px solid #2A4A60;
            border-radius: 9px;
            background: #0A1520;
        }
        QCheckBox#navToggle::indicator:hover { border-color: #3A6A9A; }
        QCheckBox#navToggle::indicator:checked {
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

    # ── ビュー切替 ────────────────────────────────────────

    def set_main_view_mode(self, mode: str, initial: bool = False):
        self.main_view_mode = mode
        is_font = mode == 'font'
        self.preview_stack.setCurrentIndex(0 if is_font else 1)
        self.font_view_btn.setChecked(is_font)
        self.device_view_btn.setChecked(not is_font)
        view_tip = 'フォントビュー: 文字サイズ・余白・ルビの見え方を調整するときに使います。' if is_font else '実機ビュー: 変換後のXTCをページ送りしながら実機に近い形で確認します。'
        self.view_help_btn.setToolTip(view_tip)
        self.view_help_btn.setProperty('helpText', view_tip)
        self.update_navigation_ui()
        if not is_font and hasattr(self, 'viewer_widget'):
            QTimer.singleShot(0, lambda: self.viewer_widget.setFocus(Qt.OtherFocusReason))
        if not initial:
            self.statusBar().showMessage(
                'フォントビューに切り替えました。' if is_font else '実機ビューに切り替えました。', 2000
            )

    def toggle_left_panel(self):
        vis = not self.left_panel.isVisible()
        self.left_panel.setVisible(vis)
        if vis:
            self._apply_left_panel_width(430)
        self.statusBar().showMessage(
            '設定パネルを表示しました。' if vis else '設定パネルを非表示にしました。', 2000
        )

    def set_ui_theme(self, theme: str, persist: bool = True):
        normalized = 'dark' if theme == 'dark' else 'light'
        if self.current_ui_theme == normalized and hasattr(self, 'viewer_widget'):
            self.viewer_widget.set_ui_theme(normalized)
            if persist:
                self.settings_store.setValue('ui_theme', normalized)
                self.settings_store.sync()
            return

        self.current_ui_theme = normalized
        self._apply_styles()
        if persist:
            self.settings_store.setValue('ui_theme', normalized)
            self.settings_store.sync()
            self.statusBar().showMessage(
                '外観をダークに切り替えました。' if normalized == 'dark' else '外観を白基調に切り替えました。',
                2000,
            )

    def set_panel_button_visible(self, visible: bool, persist: bool = True):
        self.panel_button_visible = bool(visible)
        if hasattr(self, 'panel_btn'):
            self.panel_btn.setVisible(self.panel_button_visible)
        if persist:
            self.statusBar().showMessage(
                '三本線ボタンを表示しました。' if self.panel_button_visible else '三本線ボタンを非表示にしました。',
                2000,
            )

    def show_display_settings_popup(self):
        menu = QMenu(self)
        menu.setObjectName('gearPopupMenu')
        menu.setToolTipsVisible(True)
        menu.addSection('外観')

        theme_group = QActionGroup(menu)
        theme_group.setExclusive(True)

        light_action = menu.addAction('白基調')
        light_action.setCheckable(True)
        light_action.setChecked(self.current_ui_theme != 'dark')
        light_action.triggered.connect(lambda checked: checked and self.set_ui_theme('light'))
        theme_group.addAction(light_action)

        dark_action = menu.addAction('ダーク')
        dark_action.setCheckable(True)
        dark_action.setChecked(self.current_ui_theme == 'dark')
        dark_action.triggered.connect(lambda checked: checked and self.set_ui_theme('dark'))
        theme_group.addAction(dark_action)

        menu.addSeparator()
        menu.addSection('その他オプション')

        open_folder_action = menu.addAction('完了後フォルダを開く')
        open_folder_action.setCheckable(True)
        open_folder_action.setChecked(self.open_folder_check.isChecked())
        open_folder_action.toggled.connect(lambda checked: self.open_folder_check.setChecked(bool(checked)))

        menu_size = menu.sizeHint()
        button_global = self.settings_btn.mapToGlobal(QPoint(0, 0))
        x = button_global.x() + self.settings_btn.width() - menu_size.width()
        y = button_global.y() + self.settings_btn.height()

        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = max(available.left(), min(x, available.right() - menu_size.width() + 1))
            y = max(available.top(), min(y, available.bottom() - menu_size.height() + 1))

        menu.exec(QPoint(x, y))

    def _apply_left_panel_width(self, width: int):
        """main_splitter の左パネル幅を確実にセットする。"""
        total = self.main_splitter.width()
        if total <= 0:
            QTimer.singleShot(50, lambda: self._apply_left_panel_width(width))
            return
        if width <= 0:
            return
        left = max(380, min(width, total - 200))
        self.main_splitter.setSizes([left, max(200, total - left)])

    # ── プレビュー ─────────────────────────────────────────

    def refresh_preview(self):
        try:
            data = {
                'mode': self.current_preview_mode,
                'file_b64': self.preview_image_data_url,
                'font_file': self.font_combo.currentText(),
                'font_size': self.font_size_spin.value(),
                'ruby_size': self.ruby_size_spin.value(),
                'line_spacing': self.line_spacing_spin.value(),
                'margin_t': self.margin_t_spin.value(),
                'margin_b': self.margin_b_spin.value(),
                'margin_r': self.margin_r_spin.value(),
                'margin_l': self.margin_l_spin.value(),
                'dither': 'true' if self.dither_check.isChecked() else 'false',
                'threshold': self.threshold_spin.value(),
                'night_mode': 'true' if self.night_check.isChecked() else 'false',
                'kinsoku_mode': self.current_kinsoku_mode(),
                'output_format': self.current_output_format(),
                'width': self.width_spin.value(),
                'height': self.height_spin.value(),
            }
            img_b64 = core.generate_preview_base64(data)
            if not img_b64:
                self.preview_label.setText('プレビューを生成できませんでした')
                return
            raw = base64.b64decode(img_b64)
            pix = QPixmap.fromImage(QImage.fromData(raw, 'PNG'))
            target = self._font_preview_target_size()
            if target.width() < 10 or target.height() < 10:
                target = QSize(480, 720)
            scaled = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.resize(scaled.size())
            self.preview_label.setMinimumSize(scaled.size())
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText('')
            self._update_top_status()
        except Exception as exc:
            self.preview_label.setText(f'プレビュー生成エラー\n{exc}')

    def _font_preview_target_size(self) -> QSize:
        profile = DEVICE_PROFILES[self.current_profile_key]
        if self.actual_size_check.isChecked():
            px = self._preview_px_per_mm()
            return QSize(max(180, int(profile.screen_w_mm * px)), max(240, int(profile.screen_h_mm * px)))
        if hasattr(self, 'preview_scroll'):
            vp = self.preview_scroll.viewport().size()
            if vp.width() >= 10 and vp.height() >= 10:
                return vp
        return QSize(480, 720)

    def _preview_px_per_mm(self) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96
        return max(1.0, dpi / 25.4) * (self.calib_spin.value() / 100.0)

    def _sync_preview_size(self):
        self._sync_viewer_size()
        if not hasattr(self, 'preview_label'):
            return
        target = self._font_preview_target_size()
        self.preview_label.resize(target)
        self.preview_label.setMinimumSize(target)
        self.preview_label.updateGeometry()

    def _sync_viewer_size(self):
        hint = self.viewer_widget.sizeHint()
        w = max(360, hint.width())
        h = max(600, hint.height())
        self.viewer_widget.resize(w, h)
        self.viewer_widget.setMinimumSize(w, h)
        self.viewer_widget.updateGeometry()
        self.viewer_widget.update()

    # ── ナビゲーション ─────────────────────────────────────

    def _update_nav_button_texts(self):
        if not hasattr(self, 'prev_btn') or not hasattr(self, 'next_btn'):
            return
        if self.nav_buttons_reversed:
            self.prev_btn.setText('次')
            self.next_btn.setText('前')
        else:
            self.prev_btn.setText('前')
            self.next_btn.setText('次')

    def on_nav_reverse_toggled(self, checked):
        self.nav_buttons_reversed = bool(checked)
        self._update_nav_button_texts()
        self.save_ui_state()

    def on_nav_button_clicked(self, logical_step: int):
        delta = -logical_step if self.nav_buttons_reversed else logical_step
        self.change_page(delta)

    def update_navigation_ui(self):
        if not hasattr(self, 'prev_btn'):
            return
        active = self.main_view_mode == 'device' and bool(self.xtc_pages)
        total = len(self.xtc_pages)
        can_go_prev = active and self.current_page_index > 0
        can_go_next = active and self.current_page_index < max(0, total - 1)
        if self.nav_buttons_reversed:
            self.prev_btn.setEnabled(can_go_next)
            self.next_btn.setEnabled(can_go_prev)
        else:
            self.prev_btn.setEnabled(can_go_prev)
            self.next_btn.setEnabled(can_go_next)
        self.page_input.setEnabled(active)
        self.page_total_label.setText(f'/ {total}')
        if total == 0:
            self.page_input.blockSignals(True)
            self.page_input.setRange(0, 0)
            self.page_input.setValue(0)
            self.page_input.blockSignals(False)

    def on_page_input_changed(self, value):
        if self.xtc_pages and 1 <= value <= len(self.xtc_pages):
            new_idx = value - 1
            if new_idx != self.current_page_index:
                self.current_page_index = new_idx
                self.render_current_page()
        self.update_navigation_ui()

    def change_page(self, delta: int):
        if not self.xtc_pages:
            return
        new_idx = max(0, min(len(self.xtc_pages) - 1, self.current_page_index + delta))
        if new_idx != self.current_page_index:
            self.current_page_index = new_idx
            self.render_current_page()

    # ── プロファイル・設定変更ハンドラ ─────────────────────

    def on_profile_changed(self):
        key = self.profile_combo.currentData() or 'x4'
        self.current_profile_key = key
        profile = DEVICE_PROFILES[key]
        self.viewer_widget.set_profile(profile)
        self._sync_preview_size()
        is_custom = key == 'custom'
        self.custom_size_row.setVisible(is_custom)
        if not is_custom:
            self.width_spin.setValue(profile.width_px)
            self.height_spin.setValue(profile.height_px)
        self.profile_hint.setText(profile.tagline)
        self.profile_hint.setVisible(bool(profile.tagline))
        self._update_top_status()
        self.save_ui_state()
        self.refresh_preview()

    def on_actual_size_toggled(self, checked):
        self.viewer_widget.set_actual_size(checked)
        self._sync_preview_size()
        self.refresh_preview()
        self.save_ui_state()

    def on_calibration_changed(self, value):
        self.viewer_widget.set_calibration(value / 100.0)
        self._sync_preview_size()
        self.save_ui_state()
        self.refresh_preview()

    def on_dither_toggled(self, checked):
        self.threshold_spin.setEnabled(not checked)
        self.refresh_preview()
        self.save_ui_state()

    def _on_kinsoku_mode_changed(self):
        self.refresh_preview()
        self.save_ui_state()

    def current_kinsoku_mode(self) -> str:
        if not hasattr(self, 'kinsoku_mode_combo'):
            return 'standard'
        value = str(self.kinsoku_mode_combo.currentData() or 'standard').strip().lower()
        return value if value in KINSOKU_MODE_LABELS else 'standard'

    def current_output_format(self) -> str:
        if not hasattr(self, 'output_format_combo'):
            return 'xtc'
        value = str(self.output_format_combo.currentData() or 'xtc').strip().lower()
        return value if value in OUTPUT_FORMAT_LABELS else 'xtc'

    def on_font_changed(self, _value):
        self.save_ui_state()
        self.refresh_preview()

    # ── プリセット ─────────────────────────────────────────

    def on_preset_selection_changed(self):
        self._refresh_preset_ui()
        key = self.selected_preset_key()
        p = self.preset_definitions.get(key) if key else None
        if p:
            self.statusBar().showMessage(f"{p['button_text']} の詳細表示を更新しました。適用する場合は［適用］を押してください。", 2500)
        self.save_ui_state()

    def selected_preset_key(self) -> Optional[str]:
        if not hasattr(self, 'preset_combo'):
            return None
        key = self.preset_combo.currentData()
        if key:
            return str(key)
        idx = self.preset_combo.currentIndex()
        if idx >= 0:
            data = self.preset_combo.itemData(idx)
            if data:
                return str(data)
            text = self.preset_combo.itemText(idx).strip()
            if text.startswith('プリセット'):
                suffix = text.replace('プリセット', '').strip()
                if suffix.isdigit():
                    return f'preset_{suffix}'
        return None

    def apply_selected_preset(self):
        key = self.selected_preset_key()
        if key:
            self.apply_preset(key)

    def save_selected_preset(self):
        key = self.selected_preset_key()
        if key:
            self.save_preset(key)

    def _preset_settings_prefix(self, key: str) -> str:
        return f'presets/{key}'

    def _load_preset_definitions(self) -> dict:
        presets = deepcopy(DEFAULT_PRESET_DEFINITIONS)
        stored_font = self.settings_store.value('font_file', self._default_font_name(), type=str)
        stored_night = self.settings_store.value('night_mode', False, type=bool)
        stored_dither = self.settings_store.value('dither', False, type=bool)
        stored_kinsoku_mode = str(self.settings_store.value('kinsoku_mode', 'standard', type=str)).strip().lower()
        if stored_kinsoku_mode not in KINSOKU_MODE_LABELS:
            stored_kinsoku_mode = 'standard'
        for key, preset in presets.items():
            prefix = self._preset_settings_prefix(key)
            for field in PRESET_FIELDS:
                sk = f'{prefix}/{field}'
                if self.settings_store.contains(sk):
                    dv = preset.get(field)
                    preset[field] = self.settings_store.value(
                        sk, dv, type=type(dv) if dv is not None else str
                    )
            if not preset.get('font_file'):
                preset['font_file'] = stored_font
            preset['night_mode'] = bool(preset.get('night_mode', stored_night))
            preset['dither'] = bool(preset.get('dither', stored_dither))
            preset_mode = str(preset.get('kinsoku_mode', stored_kinsoku_mode)).strip().lower()
            preset['kinsoku_mode'] = preset_mode if preset_mode in KINSOKU_MODE_LABELS else 'standard'
            preset_fmt = str(preset.get('output_format', 'xtc')).strip().lower()
            preset['output_format'] = preset_fmt if preset_fmt in OUTPUT_FORMAT_LABELS else 'xtc'
        return presets


    def _preset_display_name(self, p: dict) -> str:
        button_text = str(p.get('button_text') or '').strip()
        name = str(p.get('name') or '').strip()
        if button_text and name:
            return button_text if button_text == name else f"{button_text} / {name}"
        return button_text or name or 'プリセット'

    def _preset_summary_text(self, p: dict) -> str:
        font_text = Path(str(p.get('font_file') or self._default_font_name())).name
        night_text = 'ON' if bool(p.get('night_mode', False)) else 'OFF'
        dither_text = 'ON' if bool(p.get('dither', False)) else 'OFF'
        profile_text = str(p.get('profile', 'x4')).upper()
        kinsoku_mode = str(p.get('kinsoku_mode', 'standard')).strip().lower()
        if kinsoku_mode not in KINSOKU_MODE_LABELS:
            kinsoku_mode = 'standard'
        kinsoku_text = KINSOKU_MODE_LABELS.get(kinsoku_mode, '標準')
        out_fmt = str(p.get('output_format', 'xtc')).strip().lower()
        if out_fmt not in OUTPUT_FORMAT_LABELS:
            out_fmt = 'xtc'
        preset_name = self._preset_display_name(p)
        return (
            f"{preset_name}<br>"
            f"機種: {profile_text}　フォント: {font_text}<br>"
            f"本文: {p['font_size']}　ルビ: {p['ruby_size']}　行間: {p['line_spacing']}<br>"
            f"余白: 上 {p['margin_t']} / 下 {p['margin_b']} / 右 {p['margin_r']} / 左 {p['margin_l']}<br>"
            f"白黒反転: {night_text}　ディザリング: {dither_text}　禁則: {kinsoku_text}"
        )

    def _refresh_preset_ui(self):
        if not hasattr(self, 'preset_combo'):
            return
        current_key = self.preset_combo.currentData()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for key, p in self.preset_definitions.items():
            self.preset_combo.addItem(p['button_text'], key)
        if current_key:
            idx = self.preset_combo.findData(current_key)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)
        key = self.selected_preset_key()
        if not key:
            self.preset_summary_label.setText('')
            return
        p = self.preset_definitions.get(key, DEFAULT_PRESET_DEFINITIONS[key])
        summary = self._preset_summary_text(p)
        self.preset_summary_label.setText(summary)
        self.preset_combo.setToolTip(summary)

    def current_preset_payload(self) -> dict:
        return {
            'profile': self.profile_combo.currentData(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'font_file': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'ruby_size': self.ruby_size_spin.value(),
            'line_spacing': self.line_spacing_spin.value(),
            'margin_t': self.margin_t_spin.value(),
            'margin_b': self.margin_b_spin.value(),
            'margin_r': self.margin_r_spin.value(),
            'margin_l': self.margin_l_spin.value(),
            'night_mode': self.night_check.isChecked(),
            'dither': self.dither_check.isChecked(),
            'kinsoku_mode': self.current_kinsoku_mode(),
            'output_format': self.current_output_format(),
        }

    def save_preset(self, key: str):
        p = self.preset_definitions.get(key)
        if not p:
            return
        payload = self.current_preset_payload()
        summary = self._preset_summary_text({**p, **payload})
        ans = QMessageBox.question(
            self, 'プリセット保存',
            f"現在の設定を {self._preset_display_name(p)} へ保存しますか？\n\n{summary}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if ans != QMessageBox.Yes:
            return
        updated = deepcopy(p)
        updated.update(payload)
        self.preset_definitions[key] = updated
        prefix = self._preset_settings_prefix(key)
        for field, value in payload.items():
            self.settings_store.setValue(f'{prefix}/{field}', value)
        self.settings_store.sync()
        self._refresh_preset_ui()
        self.statusBar().showMessage(f"{self._preset_display_name(p)} を保存しました", 4000)

    def apply_preset(self, key: str):
        p = self.preset_definitions.get(key)
        if not p:
            self.statusBar().showMessage('適用するプリセットが見つかりませんでした。', 3000)
            return
        idx = self.preset_combo.findData(key)
        if idx < 0 and key.startswith('preset_'):
            try:
                idx = self.preset_combo.findText(f"プリセット{int(key.split('_')[-1])}")
            except Exception:
                idx = -1
        if idx >= 0 and self.preset_combo.currentIndex() != idx:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(idx)
            self.preset_combo.blockSignals(False)

        widgets_to_block = [
            self.profile_combo, self.width_spin, self.height_spin, self.font_combo,
            self.font_size_spin, self.ruby_size_spin, self.line_spacing_spin,
            self.margin_t_spin, self.margin_b_spin, self.margin_r_spin, self.margin_l_spin,
            self.night_check, self.dither_check, self.kinsoku_mode_combo, self.output_format_combo,
        ]
        for w in widgets_to_block:
            try:
                w.blockSignals(True)
            except Exception:
                pass
        try:
            profile_key = str(p.get('profile', 'x4'))
            profile_idx = self.profile_combo.findData(profile_key)
            if profile_idx >= 0:
                self.profile_combo.setCurrentIndex(profile_idx)
            self.current_profile_key = profile_key if profile_key in DEVICE_PROFILES else 'x4'

            if p.get('font_file'):
                font_name = str(p['font_file'])
                if self.font_combo.findText(font_name) < 0:
                    self.font_combo.addItem(font_name)
                self.font_combo.setCurrentText(font_name)

            self.font_size_spin.setValue(int(p.get('font_size', self.font_size_spin.value())))
            self.ruby_size_spin.setValue(int(p.get('ruby_size', self.ruby_size_spin.value())))
            self.line_spacing_spin.setValue(int(p.get('line_spacing', self.line_spacing_spin.value())))
            self.margin_t_spin.setValue(int(p.get('margin_t', self.margin_t_spin.value())))
            self.margin_b_spin.setValue(int(p.get('margin_b', self.margin_b_spin.value())))
            self.margin_r_spin.setValue(int(p.get('margin_r', self.margin_r_spin.value())))
            self.margin_l_spin.setValue(int(p.get('margin_l', self.margin_l_spin.value())))
            self.night_check.setChecked(bool(p.get('night_mode', False)))
            self.dither_check.setChecked(bool(p.get('dither', False)))
            kinsoku_mode = str(p.get('kinsoku_mode', 'standard')).strip().lower()
            combo_idx = self.kinsoku_mode_combo.findData(kinsoku_mode if kinsoku_mode in KINSOKU_MODE_LABELS else 'standard')
            if combo_idx >= 0:
                self.kinsoku_mode_combo.setCurrentIndex(combo_idx)
            out_fmt = str(p.get('output_format', 'xtc')).strip().lower()
            fmt_idx = self.output_format_combo.findData(out_fmt if out_fmt in OUTPUT_FORMAT_LABELS else 'xtc')
            if fmt_idx >= 0:
                self.output_format_combo.setCurrentIndex(fmt_idx)

            if profile_key == 'custom':
                self.width_spin.setValue(int(p.get('width', self.width_spin.value())))
                self.height_spin.setValue(int(p.get('height', self.height_spin.value())))
            else:
                profile = DEVICE_PROFILES.get(profile_key, DEVICE_PROFILES['x4'])
                self.width_spin.setValue(int(p.get('width', profile.width_px)))
                self.height_spin.setValue(int(p.get('height', profile.height_px)))
        finally:
            for w in widgets_to_block:
                try:
                    w.blockSignals(False)
                except Exception:
                    pass

        self.on_profile_changed()
        self.on_font_changed(None)
        self._refresh_preset_ui()
        self.save_ui_state()
        self.refresh_preview()
        self.statusBar().showMessage(f"{self._preset_display_name(p)} を適用しました。", 3000)

    # ── ファイル選択 ───────────────────────────────────────

    def select_target_path(self, as_file: bool):
        current = self.target_edit.text().strip() or str(Path.home())
        if as_file:
            path, _ = QFileDialog.getOpenFileName(
                self, '変換対象を選択', current,
                'Supported (*.epub *.zip *.rar *.cbz *.cbr *.txt *.md *.markdown);;All Files (*.*)',
            )
        else:
            path = QFileDialog.getExistingDirectory(self, '変換対象フォルダを選択', current)
        if path:
            self.target_edit.setText(path)
            self._update_top_status()
            self.save_ui_state()
            self.refresh_preview()

    def select_font_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'フォントファイルを選択', str(Path.home()),
            'Fonts (*.ttf *.ttc *.otf);;All Files (*.*)',
        )
        if path:
            if self.font_combo.findText(path) < 0:
                self.font_combo.addItem(path)
            self.font_combo.setCurrentText(path)
            self.save_ui_state()
            self.refresh_preview()

    def _available_font_names(self) -> list[str]:
        fonts = []
        for f in core.get_font_list():
            lower = str(f).lower()
            if any(t in lower for t in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
                continue
            fonts.append(str(f))

        def sort_key(name: str):
            base = Path(name).name.lower()
            family_priority = 0 if 'notosansjp' in base else 1
            if 'regular' in base:
                weight_priority = 0
            elif 'medium' in base:
                weight_priority = 1
            elif 'semibold' in base or 'semi-bold' in base:
                weight_priority = 2
            elif 'bold' in base:
                weight_priority = 3
            else:
                weight_priority = 9
            return (family_priority, weight_priority, base)

        return sorted(fonts, key=sort_key)

    def _default_font_name(self) -> str:
        preferred = ['NotoSansJP-SemiBold.ttf', 'NotoSansJP-SemiBold.otf', 'NotoSansJP-SemiBold.ttc']
        available = self._available_font_names()
        for name in preferred:
            if name in available:
                return name
        for name in available:
            if 'semibold' in name.lower():
                return name
        return available[0] if available else ''

    def _apply_default_font_selection(self):
        name = self._default_font_name()
        if name:
            idx = self.font_combo.findText(name)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)

    def _update_top_status(self):
        target = self.target_edit.text().strip()
        if not target:
            self.statusBar().showMessage('変換対象を選択してください。')
            return
        p = Path(target)
        kind = 'フォルダ' if p.is_dir() else 'ファイル'
        msg = f'{kind}: {p.name}'
        profile = DEVICE_PROFILES[self.current_profile_key]
        msg += f'  |  {profile.name} / 本文{self.font_size_spin.value()} / 行間{self.line_spacing_spin.value()}'
        self.statusBar().showMessage(msg)

    # ── 変換 ──────────────────────────────────────────────

    def current_settings_dict(self) -> dict:
        return {
            'target': self.target_edit.text().strip(),
            'font_file': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'ruby_size': self.ruby_size_spin.value(),
            'line_spacing': self.line_spacing_spin.value(),
            'margin_t': self.margin_t_spin.value(),
            'margin_b': self.margin_b_spin.value(),
            'margin_r': self.margin_r_spin.value(),
            'margin_l': self.margin_l_spin.value(),
            'dither': self.dither_check.isChecked(),
            'threshold': self.threshold_spin.value(),
            'night_mode': self.night_check.isChecked(),
            'kinsoku_mode': self.current_kinsoku_mode(),
            'output_format': self.current_output_format(),
            'open_folder': self.open_folder_check.isChecked(),
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
        }

    def _supported_targets_for_path(self, target_raw: str) -> List[Path]:
        target_raw = str(target_raw).strip()
        if not target_raw:
            return []
        tp = Path(target_raw)
        if not tp.exists():
            return []
        return ConversionWorker._resolve_supported_targets(tp)

    def _default_output_name_for_target(self, path: Path) -> str:
        desired = core.get_output_path_for_target(path, self.current_output_format())
        if desired:
            return Path(desired).stem
        return path.stem

    def _prepare_conversion_settings(self) -> Optional[dict]:
        cfg = self.current_settings_dict()
        supported = self._supported_targets_for_path(cfg.get('target', ''))
        if len(supported) != 1:
            return cfg

        current_name = str(self.settings_store.value('last_output_name', '')).strip()
        suggested = current_name or self._default_output_name_for_target(supported[0])
        new_name, ok = QInputDialog.getText(
            self, '出力ファイル名', '保存する .xtc / .xtch のファイル名を入力してください', text=suggested,
        )
        if not ok:
            self.statusBar().showMessage('変換をキャンセルしました。', 3000)
            return None

        sanitized = ConversionWorker._sanitize_output_stem(new_name)
        if not sanitized:
            QMessageBox.warning(self, '出力ファイル名', '空の名前は使えません。')
            return None

        cfg['output_name'] = sanitized
        self.settings_store.setValue('last_output_name', sanitized)
        self.settings_store.sync()
        return cfg

    def start_conversion(self):
        cfg = self._prepare_conversion_settings()
        if not cfg:
            return
        self.run_btn.setEnabled(False)
        self.run_btn.setText('変換中…')
        self.stop_btn.setEnabled(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText('変換中です…')
        self.busy_badge.setText('変換中')
        self.append_log('変換を開始しました。')
        self.bottom_tabs.setCurrentIndex(LOG_TAB_INDEX)

        self.worker_thread = QThread(self)
        self.worker = ConversionWorker(cfg)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.error.connect(self.on_conversion_error)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.cleanup_worker)
        self.worker_thread.start()

    def stop_conversion(self):
        if not self.worker:
            return
        self.worker.stop()
        self.stop_btn.setEnabled(False)
        self.append_log('停止要求を送りました。現在の変換単位が終わりしだい停止します。')

    def cleanup_worker(self):
        self.run_btn.setEnabled(True)
        self.run_btn.setText('▶  変換実行')
        self.stop_btn.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None

    def on_conversion_finished(self, result: dict):
        msg = result.get('message', '変換完了しました。')
        stopped = result.get('stopped', False)
        self.progress_label.setText(msg)
        self.busy_badge.setText('停止' if stopped else '完了')
        self.statusBar().showMessage(msg)
        self.populate_results(result.get('converted_files', []))
        if result.get('converted_files'):
            self.load_xtc_from_path(result['converted_files'][0])
        self.bottom_tabs.setCurrentIndex(RESULT_TAB_INDEX)

    def on_conversion_error(self, message: str):
        QMessageBox.critical(self, '変換エラー', message)
        self.append_log(f'エラー: {message}')
        self.progress_label.setText(f'エラー: {message}')
        self.busy_badge.setText('エラー')
        self.statusBar().showMessage(message)
        self.bottom_tabs.setCurrentIndex(LOG_TAB_INDEX)

    def append_log(self, text: str):
        self.log_edit.append(text)
        self.progress_label.setText(text)
        self.statusBar().showMessage(text, 5000)

    def populate_results(self, paths: List[str]):
        self.results_list.clear()
        for path in paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.UserRole, path)
            self.results_list.addItem(item)
        if paths:
            self.results_list.setCurrentRow(0)

    def on_result_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            self.load_xtc_from_path(path)

    def load_selected_result(self):
        selected = self.results_list.selectedItems()
        if selected:
            item = selected[0]
        elif self.results_list.currentItem() is not None:
            item = self.results_list.currentItem()
        elif self.results_list.count() == 1:
            item = self.results_list.item(0)
        else:
            item = None

        if not item:
            QMessageBox.information(self, '実機ビュー', '表示する変換結果を選択してください。')
            return
        path = item.data(Qt.UserRole)
        if not path:
            QMessageBox.warning(self, '実機ビュー', '選択した項目のファイルパスを取得できませんでした。')
            return
        self.results_list.setCurrentItem(item)
        self.load_xtc_from_path(path)

    # ── XTCビューア ───────────────────────────────────────

    def open_xtc_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'XTC/XTCHを開く', str(Path.home()), 'XTC / XTCH Files (*.xtc *.xtch)')
        if path:
            self.load_xtc_from_path(path)

    def load_xtc_from_path(self, path: str):
        try:
            raw = Path(path).read_bytes()
            self.load_xtc_from_bytes(raw)
            self.append_log(f'XTC/XTCH読込: {path}')
            self.current_xtc_label.setText(f'表示中: {Path(path).name}')
            self.set_main_view_mode('device')
        except Exception as exc:
            QMessageBox.critical(self, 'XTC読込エラー', str(exc))

    def load_xtc_from_bytes(self, data: bytes):
        self.xtc_bytes = data
        self.xtc_pages = parse_xtc_pages(data)
        self.current_page_index = 0
        if not self.xtc_pages:
            raise RuntimeError('XTC内にページがありません。')
        self.page_input.blockSignals(True)
        self.page_input.setRange(1, len(self.xtc_pages))
        self.page_input.setValue(1)
        self.page_input.blockSignals(False)
        self.render_current_page()

    def render_current_page(self):
        if not self.xtc_bytes or not self.xtc_pages:
            self.viewer_widget.clear_page()
            self.page_total_label.setText('/ 0')
            self.update_navigation_ui()
            return
        page = self.xtc_pages[self.current_page_index]
        blob = self.xtc_bytes[page.offset: page.offset + page.length]
        try:
            qi = xt_page_blob_to_qimage(blob)
            self.viewer_widget.set_page_image(qi)
        except Exception as exc:
            QMessageBox.critical(self, 'ページ表示エラー', str(exc))
            return
        self.page_input.blockSignals(True)
        self.page_input.setValue(self.current_page_index + 1)
        self.page_input.blockSignals(False)
        self.page_total_label.setText(f'/ {len(self.xtc_pages)}')
        self.update_navigation_ui()

    # ── 設定の保存 / 読み込み ──────────────────────────────

    def _restore_settings(self):
        if self.settings_store.contains('geometry'):
            self.restoreGeometry(self.settings_store.value('geometry'))
        else:
            initial_size = self._default_window_size()
            self.resize(initial_size.width(), initial_size.height())
        if self.settings_store.value('is_maximized', False, type=bool):
            self.showMaximized()

        left_w = self.settings_store.value('left_panel_width', DEFAULT_LEFT_PANEL_WIDTH, type=int)
        if self.settings_store.contains('left_splitter_state'):
            self.left_splitter.restoreState(self.settings_store.value('left_splitter_state'))
        else:
            self.left_splitter.setSizes(self._default_left_splitter_sizes())

        saved_profile = self.settings_store.value('profile', 'x4')
        self.profile_combo.setCurrentIndex(max(0, self.profile_combo.findData(saved_profile)))

        self.actual_size_check.setChecked(self.settings_store.value('actual_size', False, type=bool))
        self.guides_check.setChecked(self.settings_store.value('show_guides', True, type=bool))
        self.calib_spin.setValue(self.settings_store.value('calibration_pct', 100, type=int))
        self.nav_reverse_check.setChecked(self.settings_store.value('nav_buttons_reversed', False, type=bool))

        for key, widget, default in [
            ('font_size', self.font_size_spin, 26),
            ('ruby_size', self.ruby_size_spin, 12),
            ('line_spacing', self.line_spacing_spin, 44),
            ('margin_t', self.margin_t_spin, 12),
            ('margin_b', self.margin_b_spin, 14),
            ('margin_r', self.margin_r_spin, 12),
            ('margin_l', self.margin_l_spin, 12),
            ('threshold', self.threshold_spin, 128),
            ('width', self.width_spin, 480),
            ('height', self.height_spin, 800),
        ]:
            widget.setValue(self.settings_store.value(key, default, type=int))

        self.dither_check.setChecked(self.settings_store.value('dither', False, type=bool))
        self.night_check.setChecked(self.settings_store.value('night_mode', False, type=bool))
        self.open_folder_check.setChecked(self.settings_store.value('open_folder', True, type=bool))
        saved_kinsoku_mode = str(self.settings_store.value('kinsoku_mode', 'standard', type=str)).strip().lower()
        if saved_kinsoku_mode not in KINSOKU_MODE_LABELS:
            saved_kinsoku_mode = 'standard'
        kinsoku_idx = self.kinsoku_mode_combo.findData(saved_kinsoku_mode)
        if kinsoku_idx >= 0:
            self.kinsoku_mode_combo.setCurrentIndex(kinsoku_idx)

        font_value = self.settings_store.value('font_file', self._default_font_name())
        if font_value:
            lower = str(font_value).lower()
            if any(t in lower for t in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
                font_value = self._default_font_name()
            idx = self.font_combo.findText(font_value)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
            elif font_value:
                self.font_combo.addItem(font_value)
                self.font_combo.setCurrentIndex(self.font_combo.count() - 1)

        self.viewer_widget.set_show_guides(self.guides_check.isChecked())
        self.set_ui_theme(self.settings_store.value('ui_theme', 'light', type=str), persist=False)
        self.set_panel_button_visible(True, persist=False)
        self.on_profile_changed()
        self.on_dither_toggled(self.dither_check.isChecked())
        self.current_preview_mode = 'text'

        saved_view = self.settings_store.value('main_view_mode', 'font')
        if saved_view not in {'font', 'device'}:
            saved_view = 'font'
        self.set_main_view_mode(saved_view, initial=True)

        bt = self.settings_store.value('bottom_tab_index', 0, type=int)
        if 0 <= bt < self.bottom_tabs.count():
            self.bottom_tabs.setCurrentIndex(bt)

        pi = self.settings_store.value('preset_index', 0, type=int)
        if 0 <= pi < self.preset_combo.count():
            self.preset_combo.setCurrentIndex(pi)

        left_vis = self.settings_store.value('left_panel_visible', True, type=bool)
        self.left_panel.setVisible(bool(left_vis))
        self._pending_left_panel_width = left_w if bool(left_vis) else 0

        self._refresh_preset_ui()
        self._update_top_status()

    def save_ui_state(self):
        if not getattr(self, '_initialized', False):
            return
        if not self.isMaximized():
            self.settings_store.setValue('geometry', self.saveGeometry())
        normal_geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        self.settings_store.setValue('window_width', max(1100, normal_geom.width()))
        self.settings_store.setValue('window_height', max(760, normal_geom.height()))
        self.settings_store.setValue('is_maximized', self.isMaximized())
        sizes = self.main_splitter.sizes()
        if sizes and sizes[0] > 0:
            self.settings_store.setValue('left_panel_width', sizes[0])
        self.settings_store.setValue('left_splitter_state', self.left_splitter.saveState())
        left_splitter_sizes = self.left_splitter.sizes()
        if len(left_splitter_sizes) >= 2:
            self.settings_store.setValue('left_splitter_top', left_splitter_sizes[0])
            self.settings_store.setValue('left_splitter_bottom', left_splitter_sizes[1])
        self.settings_store.setValue('left_panel_visible', self.left_panel.isVisible())
        self.settings_store.setValue('bottom_tab_index', self.bottom_tabs.currentIndex())
        self.settings_store.setValue('main_view_mode', getattr(self, 'main_view_mode', 'font'))
        self.settings_store.setValue('ui_theme', self.current_ui_theme)
        self.settings_store.setValue('preset_index', self.preset_combo.currentIndex())
        self.settings_store.setValue('target', self.target_edit.text().strip())
        self.settings_store.setValue('profile', self.profile_combo.currentData())
        self.settings_store.setValue('actual_size', self.actual_size_check.isChecked())
        self.settings_store.setValue('show_guides', self.guides_check.isChecked())
        self.settings_store.setValue('calibration_pct', self.calib_spin.value())
        self.settings_store.setValue('nav_buttons_reversed', self.nav_reverse_check.isChecked())
        self.settings_store.setValue('font_file', self.font_combo.currentText())
        for key, widget in [
            ('font_size', self.font_size_spin),
            ('ruby_size', self.ruby_size_spin),
            ('line_spacing', self.line_spacing_spin),
            ('margin_t', self.margin_t_spin),
            ('margin_b', self.margin_b_spin),
            ('margin_r', self.margin_r_spin),
            ('margin_l', self.margin_l_spin),
            ('threshold', self.threshold_spin),
            ('width', self.width_spin),
            ('height', self.height_spin),
        ]:
            self.settings_store.setValue(key, widget.value())
        self.settings_store.setValue('dither', self.dither_check.isChecked())
        self.settings_store.setValue('night_mode', self.night_check.isChecked())
        self.settings_store.setValue('kinsoku_mode', self.current_kinsoku_mode())
        self.settings_store.setValue('output_format', self.current_output_format())
        self.settings_store.setValue('open_folder', self.open_folder_check.isChecked())
        self.settings_store.sync()

    # ── ヘルプ ─────────────────────────────────────────────

    def show_help_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('使い方')
        dlg.resize(640, 500)
        lay = QVBoxLayout(dlg)
        tv = QTextEdit(dlg)
        tv.setReadOnly(True)
        tv.setPlainText("""\
【基本的な流れ】
1. 上部の「ファイル」または「フォルダ」で変換対象を選びます。
2. 左側の設定を調整します。
3. 右側のフォントビューで文字の見え方を確認します。
4. 「▶ 変換実行」を押すと .xtc を保存します。
5. 変換後は実機ビューで XTC を確認できます。

【プレビュー】
・フォントビュー: 設定中の文字の見え方を確認します。
・実機ビュー: 変換後の XTC を X3/X4 の外形で確認します。
・ページ送りはナビゲーションバーの「前/次」ボタン、またはページ番号入力で行います。
・「反転」を ON にすると、前/次 ボタンの左右配置と動作感を入れ替えられます。

【表示と実機セクション】
・機種を選ぶと解像度が自動設定されます（Custom では手動指定）。
・実寸近似 ON で PC 画面上の実機サイズに近い表示になります。
・実寸補正は定規で実物と比較しながら調整してください。

【プリセット】
・コンボボックスで選択し「適用」で呼び出します。
・「保存」で現在の設定を上書きします。
・プリセットには禁則処理モードも保存されます。

【下部パネル】
・「変換結果」タブでファイルをクリックすると実機ビューへ読み込みます。
・「ログ」タブで変換の詳細を確認できます。

【表示設定】
・右上の歯車から、白基調 / ダーク の切替ができます。
・同じ画面で、三本線ボタンの表示 / 非表示も切り替えられます。

【補足】
・停止ボタンは変換中のみ有効です。
・同名ファイルがある場合は (1), (2) を付けて保存します。
""")
        lay.addWidget(tv)
        close_btn = QPushButton('閉じる')
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn)
        dlg.exec()


# ─────────────────────────────────────────────────────────
# XTC パーサ
# ─────────────────────────────────────────────────────────

def parse_xtc_pages(data: bytes) -> List[XtcPage]:
    if len(data) < 48 or data[:4] not in {b'XTC\x00', b'XTCH'}:
        raise RuntimeError('XTC/XTCHファイルのヘッダが不正です。')
    count = struct.unpack_from('<H', data, 6)[0]
    table_size = 48 + count * 16
    if table_size > len(data):
        raise RuntimeError('XTCページテーブルが途中で切れています。')

    pages = []
    for i in range(count):
        off = 48 + i * 16
        page = XtcPage(
            offset=struct.unpack_from('<Q', data, off)[0],
            length=struct.unpack_from('<I', data, off + 8)[0],
            width=struct.unpack_from('<H', data, off + 12)[0],
            height=struct.unpack_from('<H', data, off + 14)[0],
        )
        end = page.offset + page.length
        if page.offset < table_size or end > len(data):
            raise RuntimeError(f'XTCページ {i + 1} のオフセットまたは長さが不正です。')
        pages.append(page)
    return pages


def _pil_image_to_qimage(img: Image.Image) -> QImage:
    bio = BytesIO()
    img.save(bio, format='PNG')
    qimg = QImage.fromData(bio.getvalue(), 'PNG')
    if qimg.isNull():
        raise RuntimeError('画像データのQImage変換に失敗しました。')
    return qimg.copy()


def xtg_blob_to_qimage(blob: bytes) -> QImage:
    if len(blob) < 22 or blob[:4] != b'XTG\x00':
        raise RuntimeError('XTC/XTCH内ページデータが不正です。')
    width = struct.unpack_from('<H', blob, 4)[0]
    height = struct.unpack_from('<H', blob, 6)[0]
    if width <= 0 or height <= 0:
        raise RuntimeError('XTC内ページのサイズ情報が不正です。')
    row_bytes = (width + 7) // 8
    expected_payload_len = row_bytes * height
    payload = blob[22:22 + expected_payload_len]
    if len(payload) != expected_payload_len:
        raise RuntimeError('XTC内ページデータが途中で切れています。')

    img = Image.new('L', (width, height), 0)
    pixels = img.load()
    for y in range(height):
        row = payload[y * row_bytes:(y + 1) * row_bytes]
        for x in range(width):
            bi = x >> 3
            bit = (row[bi] >> (7 - (x & 7))) & 1
            pixels[x, y] = 255 if bit else 0
    return _pil_image_to_qimage(img)


def xth_blob_to_qimage(blob: bytes) -> QImage:
    if len(blob) < 22 or blob[:4] != b'XTH\x00':
        raise RuntimeError('XTCH内ページデータが不正です。')
    width = struct.unpack_from('<H', blob, 4)[0]
    height = struct.unpack_from('<H', blob, 6)[0]
    if width <= 0 or height <= 0:
        raise RuntimeError('XTCH内ページのサイズ情報が不正です。')
    plane_size = ((width * height) + 7) // 8
    expected_payload_len = plane_size * 2
    payload = blob[22:22 + expected_payload_len]
    if len(payload) != expected_payload_len:
        raise RuntimeError('XTCH内ページデータが途中で切れています。')
    plane1 = payload[:plane_size]
    plane2 = payload[plane_size:]
    img = Image.new('L', (width, height), 255)
    pixels = img.load()
    bit_index = 0
    shades = {0: 255, 1: 85, 2: 170, 3: 0}
    for x in range(width - 1, -1, -1):
        for y in range(height):
            byte_index = bit_index >> 3
            shift = 7 - (bit_index & 7)
            bit1 = (plane1[byte_index] >> shift) & 1
            bit2 = (plane2[byte_index] >> shift) & 1
            pixels[x, y] = shades[(bit1 << 1) | bit2]
            bit_index += 1
    return _pil_image_to_qimage(img)


def xt_page_blob_to_qimage(blob: bytes) -> QImage:
    mark = blob[:4] if len(blob) >= 4 else b''
    if mark == b'XTG\x00':
        return xtg_blob_to_qimage(blob)
    if mark == b'XTH\x00':
        return xth_blob_to_qimage(blob)
    raise RuntimeError('未対応のページ形式です。')


# ─────────────────────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
