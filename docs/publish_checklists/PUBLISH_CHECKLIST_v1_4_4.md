# Publish checklist v1.4.4

- [ ] `APP_VERSION` / `PUBLIC_VERSION` are `1.4.4`.
- [ ] `PREVIOUS_PUBLIC_VERSION` is `1.4.3.43`.
- [ ] `docs/release_notes/RELEASE_NOTES_v1_4_4.md` exists and summarizes the v1.4.3.43 -> v1.4.4 changes.
- [ ] `CHANGELOG.md` starts with a `v1.4.4` entry.
- [ ] `README.md` current version, Release tag, and attachment names are aligned to v1.4.4.
- [ ] `REFACTORING_PLAN*.md` is not included in release/source-only zip artifacts.
- [ ] `python3 -m compileall -q .` passes.
- [ ] `python3 -m pytest tests/test_clipboard_and_share_export_regression.py -q` passes.
- [ ] Focused GUI layout / translation / split-module / worker regression tests pass.
- [ ] Full pytest passes with `tests/test_english_ui_widget_scan.py` excluded, or all target files pass in split runs if the single command times out in this environment.
- [ ] `python3 build_release_zip.py` succeeds.
- [ ] `python3 build_release_zip.py --source-only` succeeds.
- [ ] `python3 build_release_zip.py --verify dist/tategaki-xtc-gui-studio_v1.4.4-release.zip` succeeds.
- [ ] `python3 build_release_zip.py --verify dist/tategaki-xtc-gui-studio_v1.4.4-source-only.zip` succeeds.

## GitHub release

- [ ] Release tag: `v1.4.4`
- [ ] Release title: `v1.4.4`
- [ ] Attachment: `tategaki-xtc-gui-studio_v1.4.4-source-only.zip`
- [ ] Attachment: `tategaki-xtc-gui-studio_v1.4.4-release.zip`
- [ ] Release body uses `docs/release_notes/RELEASE_NOTES_v1_4_4.md`.
