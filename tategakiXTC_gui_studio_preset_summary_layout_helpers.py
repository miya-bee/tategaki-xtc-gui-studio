from __future__ import annotations

"""Preset summary label layout helpers for ``tategakiXTC_gui_studio``."""

from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic


def preset_summary_label_measurement_width(self: Any, label: object) -> int:
    """Return the best available real QLabel width for compact summary height."""
    candidate_widths: list[int] = []

    contents_rect_getter = getattr(label, 'contentsRect', None)
    if callable(contents_rect_getter):
        try:
            contents_width = int(contents_rect_getter().width())
            if contents_width > 0:
                candidate_widths.append(contents_width)
        except Exception:
            pass

    label_width_getter = getattr(label, 'width', None)
    if callable(label_width_getter):
        try:
            label_width = int(label_width_getter())
            if label_width > 0:
                candidate_widths.append(label_width)
        except Exception:
            pass

    parent_getter = getattr(label, 'parentWidget', None)
    parent = None
    if callable(parent_getter):
        try:
            parent = parent_getter()
        except Exception:
            parent = None
    parent_width_getter = getattr(parent, 'width', None)
    if callable(parent_width_getter):
        try:
            parent_width = int(parent_width_getter())
            if parent_width > 0:
                margin_total = 0
                layout_getter = getattr(parent, 'layout', None)
                layout = None
                if callable(layout_getter):
                    try:
                        layout = layout_getter()
                    except Exception:
                        layout = None
                margins_getter = getattr(layout, 'contentsMargins', None)
                if callable(margins_getter):
                    try:
                        margins = margins_getter()
                        margin_total = int(margins.left()) + int(margins.right())
                    except Exception:
                        margin_total = 0
                candidate_widths.append(max(1, parent_width - margin_total))
        except Exception:
            pass

    reliable_widths = [width for width in candidate_widths if width >= 240]
    if reliable_widths:
        return max(reliable_widths)
    if candidate_widths:
        return max(candidate_widths)
    return 320


def queue_preset_summary_label_layout_retry(self: Any, *, timer_class: Any) -> None:
    """Re-measure the preset summary after Qt has assigned the real label width."""
    if getattr(self, '_preset_summary_layout_retry_queued', False):
        return
    timer_single_shot = getattr(timer_class, 'singleShot', None)
    if not callable(timer_single_shot):
        return
    self._preset_summary_layout_retry_queued = True

    def _retry() -> None:
        self._preset_summary_layout_retry_queued = False
        self._update_preset_summary_label_layout(queue_retry=False)

    try:
        timer_single_shot(0, _retry)
    except Exception:
        self._preset_summary_layout_retry_queued = False


def update_preset_summary_label_layout(
    self: Any,
    *,
    queue_retry: bool = True,
    qt_namespace: Any,
    rect_class: Any,
) -> None:
    label = getattr(self, 'preset_summary_label', None)
    if label is None:
        return
    text = ''
    text_getter = getattr(label, 'text', None)
    if callable(text_getter):
        try:
            text = str(text_getter() or '')
        except Exception:
            text = ''
    compact_text = studio_logic.compact_multiline_label_text(text)
    if compact_text != text:
        set_text = getattr(label, 'setText', None)
        if callable(set_text):
            try:
                set_text(compact_text)
                text = compact_text
            except Exception:
                text = compact_text
        else:
            text = compact_text
    height = 0
    if text.strip():
        width_value = self._preset_summary_label_measurement_width(label)
        used_precise_metrics = False
        font_metrics_getter = getattr(label, 'fontMetrics', None)
        if callable(font_metrics_getter) and width_value > 0:
            try:
                metrics = font_metrics_getter()
                text_word_wrap = getattr(qt_namespace, 'TextWordWrap', 0)
                align_top = getattr(qt_namespace, 'AlignTop', 0)
                align_left = getattr(qt_namespace, 'AlignLeft', 0)
                flags = int(text_word_wrap) | int(align_top) | int(align_left)
                line_spacing_value = 0
                line_spacing_getter = getattr(metrics, 'lineSpacing', None)
                if callable(line_spacing_getter):
                    try:
                        line_spacing_value = max(1, int(line_spacing_getter()))
                    except Exception:
                        line_spacing_value = 0
                if line_spacing_value > 0:
                    measured_height = 0
                    for line in text.splitlines():
                        rect = metrics.boundingRect(rect_class(0, 0, width_value, 10000), flags, line)
                        measured_height += max(line_spacing_value, int(rect.height()))
                    if measured_height > 0:
                        height = measured_height
                        used_precise_metrics = True
                if height <= 0:
                    rect = metrics.boundingRect(rect_class(0, 0, width_value, 10000), flags, text)
                    height = int(rect.height())
                    if height > 0:
                        used_precise_metrics = True
            except Exception:
                height = 0
        if height <= 0:
            height_for_width = getattr(label, 'heightForWidth', None)
            if callable(height_for_width) and width_value > 0:
                try:
                    height = int(height_for_width(width_value))
                except Exception:
                    height = 0
        if height <= 0:
            size_hint = getattr(label, 'sizeHint', None)
            if callable(size_hint):
                try:
                    height = int(size_hint().height())
                except Exception:
                    height = 0
        if height > 0 and not used_precise_metrics:
            height = max(1, height - 2)
    fixed_height_applied = False
    if height > 0:
        set_fixed_height = getattr(label, 'setFixedHeight', None)
        if callable(set_fixed_height):
            try:
                set_fixed_height(height)
                fixed_height_applied = True
            except Exception:
                fixed_height_applied = False
        if not fixed_height_applied:
            for setter_name in ('setMinimumHeight', 'setMaximumHeight'):
                setter = getattr(label, setter_name, None)
                if callable(setter):
                    try:
                        setter(height)
                    except Exception:
                        pass
    update_geometry = getattr(label, 'updateGeometry', None)
    if callable(update_geometry):
        update_geometry()
    section_box = getattr(self, 'preset_section_box', None)
    if section_box is not None:
        try:
            section_box.setMinimumHeight(max(1, int(section_box.sizeHint().height()) + 14))
            section_box.updateGeometry()
        except Exception:
            pass
    if queue_retry:
        self._queue_preset_summary_label_layout_retry()

def sync_summary_payload(self: Any, payload: object | None, *, summary_tag: str = '') -> None:
    if not hasattr(self, 'preset_summary_label') or not hasattr(self, 'preset_combo'):
        return
    if not payload:
        return
    summary = self._preset_side_summary_text(
        self._preset_summary_plain_text(payload, summary_tag=summary_tag, include_name_line=False)
    )
    self.preset_summary_label.setText(summary)
    self.preset_combo.setToolTip(summary)
    self._update_preset_summary_label_layout()


def sync_current_settings_summary(self: Any, key: str | None = None) -> None:
    summary_payload = self._current_settings_summary_payload(key)
    if not summary_payload:
        return
    self._sync_summary_payload(summary_payload, summary_tag='（現在の設定）')


def sync_selected_preset_summary(self: Any, key: str | None = None) -> None:
    if not hasattr(self, 'preset_summary_label') or not hasattr(self, 'preset_combo'):
        return
    selected_key = key or self.selected_preset_key()
    preset = self.preset_definitions.get(selected_key) if selected_key else None
    if not preset:
        self.preset_summary_label.setText('')
        self.preset_combo.setToolTip('')
        return
    summary = self._preset_side_summary_text(
        self._preset_summary_plain_text(preset, include_name_line=False)
    )
    self.preset_summary_label.setText(summary)
    self.preset_combo.setToolTip(summary)
    adjust = getattr(self.preset_summary_label, 'adjustSize', None)
    if callable(adjust):
        adjust()
    update = getattr(self.preset_summary_label, 'update', None)
    if callable(update):
        update()
    self._update_preset_summary_label_layout()


def refresh_preset_ui(self: Any, *, bulk_block_signals: Any) -> None:
    if not hasattr(self, 'preset_combo'):
        return
    current_key = self.preset_combo.currentData()
    with bulk_block_signals(self.preset_combo):
        self.preset_combo.clear()
        for key, preset in self.preset_definitions.items():
            self.preset_combo.addItem(self._preset_display_name(preset), key)
        if current_key:
            idx = self.preset_combo.findData(current_key)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
    self._sync_selected_preset_summary()

