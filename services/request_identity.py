"""HTTP client identity primitives for Teranga AI."""

from __future__ import annotations

import ipaddress

# Plages publiques de Cloudflare, qui se place devant teranga-ai.fr (adresses vues dans les journaux Render du
# 1er novembre 2026). Liste officielle : https://www.cloudflare.com/ips/ (ips-v4 et ips-v6), relevée le
# 1er novembre 2026. Une plage absente n'ouvre aucune faille : la requête garde alors l'adresse de Cloudflare.
CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
    "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
    "2a06:98c0::/29", "2c0f:f248::/32",
))


def _address(value: object):
    try:
        return ipaddress.ip_address(str(value or "").strip())
    except ValueError:
        return None


def from_cloudflare(remote_addr: object) -> bool:
    """Vrai si l'adresse qui se connecte appartient à Cloudflare."""
    address = _address(remote_addr)
    return address is not None and any(address in network for network in CLOUDFLARE_NETWORKS)


def client_ip(remote_addr: object, cf_connecting_ip: object = None) -> str:
    """Adresse du visiteur, bornée en longueur.

    `remote_addr` est l'adresse normalisée par ProxyFix (dernier saut). Derrière Cloudflare, c'est celle de
    Cloudflare : l'adresse réelle est alors l'en-tête CF-Connecting-IP. Il n'est lu que si la requête arrive
    vraiment de Cloudflare (sinon n'importe qui pourrait l'écrire) et seulement s'il contient une adresse valide.
    """
    if cf_connecting_ip and from_cloudflare(remote_addr):
        visitor = _address(cf_connecting_ip)
        if visitor is not None:
            return str(visitor)[:64]
    return str(remote_addr or "unknown")[:64]
