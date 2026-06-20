from __future__ import annotations

"""Release metadata shared by the app, docs, and release tooling.

This module intentionally avoids importing GUI / conversion modules so release
tooling can read public version information without triggering heavy optional
dependencies.
"""

APP_VERSION = '1.5.0'
PUBLIC_VERSION = APP_VERSION
PREVIOUS_PUBLIC_VERSION = '1.4.2'
PUBLIC_DISTRIBUTION_FLAVOR = 'public'
PUBLIC_DISTRIBUTION_LABEL = 'Public'
FULL_DISTRIBUTION_FLAVOR = 'full'
PUBLIC_VERSION_TAG = PUBLIC_VERSION
RELEASE_NOTES_FILE = f'docs/release_notes/RELEASE_NOTES_v{PUBLIC_VERSION.replace(".", "_")}.md'
RELEASE_ZIP_FILE_NAME = f'tategaki-xtc-gui-studio_v{PUBLIC_VERSION}-{PUBLIC_DISTRIBUTION_FLAVOR}.zip'
SOURCE_ONLY_ZIP_FILE_NAME = f'tategaki-xtc-gui-studio_v{PUBLIC_VERSION}-{PUBLIC_DISTRIBUTION_FLAVOR}-source-only.zip'
FULL_ZIP_FILE_NAME = f'tategaki-xtc-gui-studio_v{PUBLIC_VERSION}-{FULL_DISTRIBUTION_FLAVOR}.zip'
RELEASE_VERIFY_ZIP_FILE_NAME = RELEASE_ZIP_FILE_NAME

__all__ = [
    'APP_VERSION',
    'PUBLIC_VERSION',
    'PREVIOUS_PUBLIC_VERSION',
    'PUBLIC_DISTRIBUTION_FLAVOR',
    'PUBLIC_DISTRIBUTION_LABEL',
    'FULL_DISTRIBUTION_FLAVOR',
    'PUBLIC_VERSION_TAG',
    'RELEASE_NOTES_FILE',
    'RELEASE_ZIP_FILE_NAME',
    'SOURCE_ONLY_ZIP_FILE_NAME',
    'FULL_ZIP_FILE_NAME',
    'RELEASE_VERIFY_ZIP_FILE_NAME',
]
