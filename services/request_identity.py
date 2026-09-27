"""HTTP client identity primitives for Teranga AI."""

from __future__ import annotations


def client_ip(remote_addr: object) -> str:
    """Return the proxy-normalized client address with a bounded length."""
    return str(remote_addr or "unknown")[:64]
