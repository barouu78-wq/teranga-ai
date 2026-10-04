"""HTTP response security and caching headers."""

from __future__ import annotations


CACHED_ASSETS = frozenset({
    "/icon.svg",
    "/og.svg",
    "/og.png",
    "/icon-192.png",
    "/icon-512.png",
    "/robots.txt",
    "/sitemap.xml",
    "/manifest.webmanifest",
})


def add_security_headers(
    response,
    *,
    path: str,
    nonce: str = "",
    is_secure: bool = False,
    forwarded_proto: str = "",
    extra_script_origins: tuple[str, ...] = (),
):
    script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self' 'unsafe-inline'"
    # Origines optionnelles (mesure d'audience) : autorisées pour le script et ses envois.
    extra = "".join(" " + origin for origin in extra_script_origins if origin)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=(self), payment=(), usb=(), "
        "accelerometer=(), gyroscope=(), magnetometer=()"
    )
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["X-DNS-Prefetch-Control"] = "off"
    response.headers["Origin-Agent-Cluster"] = "?1"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src {script_src} 'unsafe-eval' "
        "https://cse.google.com https://www.google.com https://www.gstatic.com" + extra + "; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https://upload.wikimedia.org "
        "https://thumb.wikimedia.org https://commons.wikimedia.org https:; "
        "connect-src 'self' https://cse.google.com https://www.google.com" + extra + "; "
        "media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; object-src 'none'; "
        "frame-src https://www.google.com https://cse.google.com https://maps.google.com https://www.openstreetmap.org; "
        "child-src https://www.google.com https://maps.google.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if path == "/image-proxy":
        # Contenu tiers relayé depuis notre origine : aucun script, document isolé.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Cache-Control"] = (
        "public, max-age=86400" if path in CACHED_ASSETS else "no-store"
    )
    if path == "/image-proxy" and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=86400"
    if is_secure or forwarded_proto == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    response.headers.pop("Server", None)
    return response
