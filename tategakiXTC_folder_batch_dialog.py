from __future__ import annotations

"""Qt dialog skeleton for the folder batch conversion feature.

This file is intentionally self-contained and conservative.  It can be wired into
``tategakiXTC_gui_studio.py`` after the baseline release tree is available.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tategakiXTC_folder_batch_plan import (
    FolderBatchPlan,
    build_folder_batch_plan,
    describe_folder_batch_no_work,
    describe_folder_batch_partial_skip_notice,
    normalize_suffixes,
    summarize_folder_batch_plan,
)
import tategakiXTC_gui_studio_logic as studio_logic

from tategakiXTC_folder_batch_safety import (
    analyze_folder_batch_roots,
    format_folder_batch_safety_warnings,
)


@dataclass(frozen=True)
class FolderBatchDialogResult:
    input_root: Path
    output_root: Path
    include_subfolders: bool
    preserve_structure: bool
    existing_policy: str
    output_format: str
    plan: FolderBatchPlan


class FolderBatchDialog(QDialog):
    SUFFIX_LABELS = {
        '.txt': 'TXT',
        '.md': 'Markdown',
        '.markdown': 'Markdown',
        '.epub': 'EPUB',
        '.png': 'PNG',
        '.jpg': 'JPG',
        '.jpeg': 'JPEG',
        '.webp': 'WEBP',
    }
    POLICY_LABELS = (
        ('skip', 'スキップ'),
        ('overwrite', '上書き'),
        ('rename', '別名で保存'),
    )

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        output_format: str = 'xtc',
        input_root: str | Path = '',
        output_root: str | Path = '',
        include_subfolders: bool = True,
        preserve_structure: bool = True,
        existing_policy: str = 'skip',
        supported_suffixes: Iterable[str] | None = None,
        language: str = 'ja',
    ) -> None:
        super().__init__(parent)
        self.language = studio_logic.normalize_ui_language(language, 'ja')
        self.setWindowTitle(self._tr('フォルダ一括変換'))
        self.output_format = str(output_format or 'xtc').lower()
        self.supported_suffixes = tuple(supported_suffixes) if supported_suffixes is not None else None
        self._last_plan: FolderBatchPlan | None = None
        self._result: FolderBatchDialogResult | None = None
        self.input_edit = QLineEdit(str(input_root or ''))
        self.output_edit = QLineEdit(str(output_root or ''))
        self.input_browse_btn = QPushButton(self._tr('参照...'))
        self.output_browse_btn = QPushButton(self._tr('参照...'))
        self.include_subfolders_check = QCheckBox(self._tr('サブフォルダ内も対象にする'))
        self.include_subfolders_check.setChecked(bool(include_subfolders))
        self.preserve_structure_check = QCheckBox(self._tr('フォルダ構造を保持して出力する'))
        self.preserve_structure_check.setChecked(bool(preserve_structure))
        self.policy_combo = QComboBox()
        for value, label in self.POLICY_LABELS:
            self.policy_combo.addItem(self._tr(label), value)
        idx = self.policy_combo.findData(existing_policy)
        self.policy_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.summary_label = QLabel(self._tr('入力元フォルダと出力先フォルダを指定してください。'))
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setText(self._tr('変換開始'))
            ok_button.setEnabled(False)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        if cancel_button is not None:
            cancel_button.setText(self._tr('キャンセル'))
        self._build_layout()
        self._connect_signals()
        self.refresh_summary()

    def _tr(self, text: object) -> str:
        return studio_logic.translate_ui_text(text, self.language)

    def _tr_lines(self, lines: Iterable[object]) -> list[str]:
        return [self._tr(line) for line in lines]

    def _build_layout(self) -> None:
        root_layout = QVBoxLayout(self)
        form_group = QGroupBox(self._tr('フォルダ'))
        form = QFormLayout(form_group)
        input_row = QHBoxLayout()
        input_row.addWidget(self.input_edit, 1)
        input_row.addWidget(self.input_browse_btn)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(self.output_browse_btn)
        form.addRow(self._tr('入力元フォルダ:'), input_row)
        form.addRow(self._tr('出力先フォルダ:'), output_row)
        root_layout.addWidget(form_group)
        option_group = QGroupBox(self._tr('一括変換オプション'))
        option_layout = QGridLayout(option_group)
        option_layout.addWidget(self.include_subfolders_check, 0, 0, 1, 2)
        option_layout.addWidget(self.preserve_structure_check, 1, 0, 1, 2)
        option_layout.addWidget(QLabel(self._tr('既存ファイルがある場合:')), 2, 0)
        option_layout.addWidget(self.policy_combo, 2, 1)
        option_layout.addWidget(QLabel(self._tr('現在のメイン画面設定で変換します。')), 3, 0, 1, 2)
        option_layout.addWidget(QLabel(self._supported_suffixes_label()), 4, 0, 1, 2)
        root_layout.addWidget(option_group)
        summary_group = QGroupBox(self._tr('確認'))
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(self.summary_label)
        root_layout.addWidget(summary_group)
        root_layout.addWidget(self.button_box)

    def _supported_suffixes_label(self) -> str:
        labels: list[str] = []
        seen: set[str] = set()
        for suffix in normalize_suffixes(self.supported_suffixes):
            label = self.SUFFIX_LABELS.get(suffix, suffix.lstrip('.').upper())
            if label not in seen:
                labels.append(label)
                seen.add(label)
        return self._tr('対象形式: なし') if not labels else self._tr('対象形式: ') + ' / '.join(labels)

    def _connect_signals(self) -> None:
        self.input_browse_btn.clicked.connect(self.browse_input_root)
        self.output_browse_btn.clicked.connect(self.browse_output_root)
        self.input_edit.textChanged.connect(self.refresh_summary)
        self.output_edit.textChanged.connect(self.refresh_summary)
        self.include_subfolders_check.toggled.connect(self.refresh_summary)
        self.preserve_structure_check.toggled.connect(self.refresh_summary)
        self.policy_combo.currentIndexChanged.connect(self.refresh_summary)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def browse_input_root(self) -> None:
        current = self.input_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, self._tr('入力元フォルダを選択'), current)
        if selected:
            self.input_edit.setText(selected)

    def browse_output_root(self) -> None:
        current = self.output_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, self._tr('出力先フォルダを選択'), current)
        if selected:
            self.output_edit.setText(selected)

    def _selected_policy(self) -> str:
        return str(self.policy_combo.currentData() or 'skip')

    def build_current_plan(self) -> FolderBatchPlan:
        return build_folder_batch_plan(
            self.input_edit.text().strip(),
            self.output_edit.text().strip(),
            include_subfolders=self.include_subfolders_check.isChecked(),
            preserve_structure=self.preserve_structure_check.isChecked(),
            existing_policy=self._selected_policy(),
            output_format=self.output_format,
            supported_suffixes=self.supported_suffixes,
        )

    def refresh_summary(self) -> None:
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        try:
            plan = self.build_current_plan()
        except Exception as exc:
            self._last_plan = None
            self.summary_label.setText(self._tr(str(exc)))
            if ok_button is not None:
                ok_button.setEnabled(False)
            return
        self._last_plan = plan
        lines = self._tr_lines(summarize_folder_batch_plan(plan))
        safety = analyze_folder_batch_roots(plan.input_root, plan.output_root)
        if safety.has_warnings:
            lines.append('')
            lines.extend(self._tr_lines(format_folder_batch_safety_warnings(safety)))
        if plan.convert_count <= 0:
            no_work_message = describe_folder_batch_no_work(plan)
            if no_work_message:
                lines.append('')
                lines.extend(self._tr_lines(no_work_message.splitlines()))
        else:
            partial_skip_message = describe_folder_batch_partial_skip_notice(plan)
            if partial_skip_message:
                lines.append('')
                lines.extend(self._tr_lines(partial_skip_message.splitlines()))
        self.summary_label.setText('\n'.join(lines))
        if ok_button is not None:
            can_execute = plan.convert_count > 0
            ok_button.setEnabled(can_execute)
            ok_button.setToolTip('' if can_execute else self._tr('変換予定のファイルがないため開始できません。'))

    def accept(self) -> None:
        plan = self._last_plan or self.build_current_plan()
        if plan.convert_count <= 0:
            self.refresh_summary()
            return
        confirm_lines = self._tr_lines(summarize_folder_batch_plan(plan))
        safety = analyze_folder_batch_roots(plan.input_root, plan.output_root)
        if safety.has_warnings:
            confirm_lines.append('')
            confirm_lines.extend(self._tr_lines(format_folder_batch_safety_warnings(safety)))
        confirm_lines.append('')
        confirm_lines.append(self._tr('この内容で変換を開始しますか？'))
        title = self._tr('上書き確認' if plan.overwritten_count else 'フォルダ一括変換の確認')
        if plan.overwritten_count:
            confirm_lines.insert(0, self._tr('既存ファイルを上書きする設定です。'))
            confirm_lines.insert(1, '')
        ask = QMessageBox.warning if plan.overwritten_count else QMessageBox.question
        reply = ask(
            self,
            title,
            '\n'.join(confirm_lines),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._result = FolderBatchDialogResult(
            input_root=plan.input_root,
            output_root=plan.output_root,
            include_subfolders=plan.include_subfolders,
            preserve_structure=plan.preserve_structure,
            existing_policy=plan.existing_policy,
            output_format=plan.output_format,
            plan=plan,
        )
        super().accept()

    def result_options(self) -> FolderBatchDialogResult | None:
        return self._result
