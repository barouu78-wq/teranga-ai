"""Pytest configuration for repository-local imports."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import socket

import pytest

import os
from urllib.parse import urlsplit

_real_connect = socket.socket.connect
# Un proxy HTTP local (environnement cloud) servirait de porte de sortie : bloqué aussi.
_PROXIES = set()
for _name in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
    _url = urlsplit(os.environ.get(_name, ""))
    if _url.hostname and _url.port:
        _PROXIES.add((_url.hostname, _url.port))


def _guarded_connect(sock, address, *args, **kwargs):
    host = address[0] if isinstance(address, tuple) and address else address
    port = address[1] if isinstance(address, tuple) and len(address) > 1 else None
    if host not in ("127.0.0.1", "::1", "localhost") or (host, port) in _PROXIES:
        raise RuntimeError(f"Accès réseau interdit pendant les tests : {address!r}. Simule l'appel externe.")
    return _real_connect(sock, address, *args, **kwargs)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Un test qui atteint Internet réussit ou échoue selon la machine : on l'interdit."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)


@pytest.fixture(autouse=True)
def _fresh_answer_cache():
    """Le cache de réponses ne doit jamais faire dépendre un test d'un autre."""
    module = sys.modules.get("app")
    cache = getattr(module, "ANSWER_CACHE", None) if module else None
    if cache is not None:
        cache._memory.clear()
    yield
    if cache is not None:
        cache._memory.clear()
