"""Configuration helpers for Teranga AI.

Keep environment parsing in one place so deployment configuration behaves
consistently across local development and production.
"""

import os


_TRUE_VALUES = frozenset({"1", "true", "yes", "y", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "n", "off", ""})


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable with common spellings."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return default


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable as trimmed values."""
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
