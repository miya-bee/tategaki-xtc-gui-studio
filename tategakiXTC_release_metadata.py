from __future__ import annotations

"""Release metadata shared by the app, docs, and release tooling.

This module intentionally avoids importing GUI / conversion modules so release
tooling can read public version information without triggering heavy optional
dependencies.
"""

APP_VERSION = '1.2.0'
PUBLIC_VERSION = APP_VERSION
PREVIOUS_PUBLIC_VERSION = '1.1.1.37'
PUBLIC_VERSION_TAG = PUBLIC_VERSION
RELEASE_NOTES_FILE = f'RELEASE_NOTES_v{PUBLIC_VERSION.replace(".", "_")}.md'
RELEASE_ZIP_FILE_NAME = f'tategaki-xtc-gui-studio_v{PUBLIC_VERSION}-release.zip'
RELEASE_VERIFY_ZIP_FILE_NAME = RELEASE_ZIP_FILE_NAME

__all__ = [
    'APP_VERSION',
    'PUBLIC_VERSION',
    'PREVIOUS_PUBLIC_VERSION',
    'PUBLIC_VERSION_TAG',
    'RELEASE_NOTES_FILE',
    'RELEASE_ZIP_FILE_NAME',
    'RELEASE_VERIFY_ZIP_FILE_NAME',
]
