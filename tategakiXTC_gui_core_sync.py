"""
tategakiXTC_gui_core_sync.py — split module monkey-patch synchronization helper

Split modules mirror selected globals from ``tategakiXTC_gui_core`` so legacy
callers and tests that monkey-patch the core module keep working. This helper
attaches a tiny version counter to the core module so repeated refresh calls can
return in O(1) unless a core attribute was actually reassigned.
"""
from __future__ import annotations

from types import ModuleType
from typing import Final

_CORE_SYNC_VERSION_ATTR: Final[str] = '_split_module_sync_version'


class _TrackedCoreModule(ModuleType):
    """Module subclass that bumps a version whenever globals are reassigned."""

    def __setattr__(self, name: str, value: object) -> None:
        ModuleType.__setattr__(self, name, value)
        if name != _CORE_SYNC_VERSION_ATTR:
            current = int(getattr(self, _CORE_SYNC_VERSION_ATTR, 0))
            ModuleType.__setattr__(self, _CORE_SYNC_VERSION_ATTR, current + 1)

    def __delattr__(self, name: str) -> None:
        ModuleType.__delattr__(self, name)
        if name != _CORE_SYNC_VERSION_ATTR:
            current = int(getattr(self, _CORE_SYNC_VERSION_ATTR, 0))
            ModuleType.__setattr__(self, _CORE_SYNC_VERSION_ATTR, current + 1)


def install_core_sync_tracker(core_module: ModuleType) -> int:
    """Install the version tracker on ``tategakiXTC_gui_core`` if needed."""
    current = int(getattr(core_module, _CORE_SYNC_VERSION_ATTR, 0))
    if not isinstance(core_module, _TrackedCoreModule):
        core_module.__class__ = _TrackedCoreModule
        ModuleType.__setattr__(core_module, _CORE_SYNC_VERSION_ATTR, current)
    return current


def core_sync_version(core_module: ModuleType) -> int:
    """Return the current core monkey-patch synchronization version."""
    return int(getattr(core_module, _CORE_SYNC_VERSION_ATTR, 0))
