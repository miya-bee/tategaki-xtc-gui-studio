# Release checklist v1.5.0

## Version metadata

- [ ] `APP_VERSION` / `PUBLIC_VERSION` are `1.5.0`.
- [ ] `PREVIOUS_PUBLIC_VERSION` is `1.4.2`.
- [ ] `docs/release_notes/RELEASE_NOTES_v1_5_0.md` summarizes the public v1.5.0 release.
- [ ] `docs/publish_checklists/PUBLISH_CHECKLIST_v1_5_0.md` exists.
- [ ] `CHANGELOG.md` starts with a `v1.5.0` entry.
- [ ] `README.md` current version, Release tag, attachment names, and public-target section are aligned to v1.5.0 Public.
- [ ] `README.md` explains the difference from Full版 (`tategaki-xtc-gui-studio_v1.5.0-full.zip`) and notes that Full版 is distributed on note.

## Smoke checks

- [ ] `python -m compileall -q .` passes.
- [ ] `python tests/generate_golden_images.py --check` reports that golden images are current.
- [ ] `python -m pytest tests/ -q` passes on Windows, or any skipped/expected exclusions are recorded before release.
- [ ] `python -m mypy --config-file mypy.ini` passes on Windows.
- [ ] Japanese UI title shows `縦書きXTC Studio Public 1.5.0`.
- [ ] English UI title shows `TategakiXTC GUI Studio Public 1.5.0`.
- [ ] 上部バーに「青空文庫」ボタンが無いことを確認する。
- [ ] 上部バーに「クリップボード」ボタンが無いことを確認する。
- [ ] `https://example.com` / `www.example.com/path` が横組みされることを確認する。
- [ ] `https://` / `http://` / `www.` 単体が横組みされないことを確認する。
- [ ] 草枕TXTで欧文横組み、URL横組み、空行、会話行、短いルビ＋読点の見え方を確認する。
- [ ] 右ペイン上部の `XTCファイルを開く` から既存の .xtc / .xtch ファイルを読み込めることを確認する。
- [ ] 右ペイン上部の `PNG保存` で現在ページを保存できることを確認する。

## Build and packaging

- [ ] Source tree does not contain generated caches, logs, or local virtual environments.
- [ ] Source-only zip is built with `build_release_zip.py --source-only`.
- [ ] Release zip is built with `build_release_zip.py`.
- [ ] Both zips pass `build_release_zip.py --verify`.
- [ ] Release zip contains expected `Font/` payload when distributing the release build.

## GitHub Release

- [ ] Release tag: `v1.5.0`
- [ ] Release title: `v1.5.0 Public`
- [ ] Previous tag: `v1.4.2`
- [ ] Attachment: `tategaki-xtc-gui-studio_v1.5.0-public-source-only.zip`
- [ ] Attachment SHA256: `tategaki-xtc-gui-studio_v1.5.0-public-source-only.zip.sha256.txt`
- [ ] Release zip: `tategaki-xtc-gui-studio_v1.5.0-public.zip`
- [ ] Release zip SHA256: `tategaki-xtc-gui-studio_v1.5.0-public.zip.sha256.txt`
- [ ] Release body uses `docs/release_notes/RELEASE_NOTES_v1_5_0.md`.

## Verification commands

```bat
py -3.10 -m compileall -q .
py -3.10 tests\generate_golden_images.py --check
py -3.10 -m pytest tests -q -x
py -3.10 build_release_zip.py --source-only
py -3.10 build_release_zip.py
py -3.10 build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.5.0-public-source-only.zip
py -3.10 build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.5.0-public.zip
```

## v1.5.0 documents

- `docs/release_notes/RELEASE_NOTES_v1_5_0.md`
- `docs/publish_checklists/PUBLISH_CHECKLIST_v1_5_0.md`
