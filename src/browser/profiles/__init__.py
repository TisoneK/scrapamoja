"""Persistent browser profiles — see :mod:`src.browser.profiles.manager`."""

from .manager import ProfileError, ProfileInUse, ProfileManager, default_root
from .models import ProfileMeta

__all__ = ["ProfileManager", "ProfileMeta", "ProfileError", "ProfileInUse", "default_root"]
