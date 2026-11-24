"""Audit de sécurité du 1er novembre 2026 (constat 1) : teranga-ai.fr passe par Cloudflare.

Journaux Render du 1er novembre : le téléphone du propriétaire arrivait de 141.101.97.28 puis 141.101.97.29,
UptimeRobot de 162.158.110.82, Claude-User de 172.69.150.167, toutes des adresses de Cloudflare. ProxyFix
(x_for=1) retient le dernier saut, celui de Cloudflare : les limites par visiteur comptaient donc par point de
présence Cloudflare, partagé par toute une région.

L'adresse réelle vient de l'en-tête CF-Connecting-IP, mais seulement quand la requête arrive d'une adresse de
Cloudflare : sinon, quiconque joint Render directement pourrait l'écrire lui-même et contourner les limites.
"""

import os

import pytest

from services.request_identity import client_ip, from_cloudflare

VISITEUR = "41.82.10.5"


@pytest.mark.parametrize("edge", ["141.101.97.28", "141.101.97.29", "162.158.110.82", "172.69.150.167"])
def test_the_addresses_seen_in_production_belong_to_cloudflare(edge):
    assert from_cloudflare(edge)


@pytest.mark.parametrize("addr", ["203.0.113.10", "10.0.0.5", "127.0.0.1", "unknown", "", None, "2001:db8::1"])
def test_other_addresses_are_not_cloudflare(addr):
    assert not from_cloudflare(addr)


def test_the_real_visitor_is_used_behind_cloudflare():
    assert client_ip("141.101.97.28", VISITEUR) == VISITEUR
    assert client_ip("2a06:98c0::1", "2001:db8::5") == "2001:db8::5"  # Cloudflare en IPv6


def test_two_visitors_behind_the_same_cloudflare_edge_are_told_apart():
    assert client_ip("141.101.97.28", VISITEUR) != client_ip("141.101.97.28", "41.82.10.6")


def test_the_header_is_ignored_when_the_request_does_not_come_from_cloudflare():
    # Requête envoyée directement à Render avec un faux en-tête : on garde l'adresse qui se connecte.
    assert client_ip("203.0.113.10", VISITEUR) == "203.0.113.10"


@pytest.mark.parametrize("header", ["", "   ", "pas-une-adresse", "41.82.10.5, 1.2.3.4", "999.1.1.1", "x" * 200])
def test_an_invalid_header_keeps_the_connecting_address(header):
    assert client_ip("141.101.97.28", header) == "141.101.97.28"


def test_without_header_nothing_changes():
    assert client_ip("203.0.113.10") == "203.0.113.10"
    assert client_ip(None) == "unknown"
    assert len(client_ip("x" * 100)) == 64


def test_the_app_counts_the_real_visitor():
    """client_ip() de app.py, qui sert aux limites de débit et aux blocages pour abus."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    import app as app_module

    with app_module.app.test_request_context(
        "/", environ_base={"REMOTE_ADDR": "141.101.97.28"}, headers={"CF-Connecting-IP": VISITEUR}
    ):
        assert app_module.client_ip() == VISITEUR
    with app_module.app.test_request_context(
        "/", environ_base={"REMOTE_ADDR": "203.0.113.10"}, headers={"CF-Connecting-IP": VISITEUR}
    ):
        assert app_module.client_ip() == "203.0.113.10"
