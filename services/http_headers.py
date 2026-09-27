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
):
    script_src = f"'self' 'nonce-{nonce}'" if nonce else "'self' 'unsafe-inline'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=(self), payment=(), usb=(), "
        "accelerometer=(), gyroscope=(), magnetometer=()"
    )
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    response.headers["Origin-Agent-Cluster"] = "?1"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src {script_src} 'unsafe-eval' "
        "https://cse.google.com https://www.google.com https://www.gstatic.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https://upload.wikimedia.org "
        "https://thumb.wikimedia.org https://commons.wikimedia.org https:; "
        "connect-src 'self' https://cse.google.com https://www.google.com; "
        "media-src 'self' blob:; object-src 'none'; "
        "frame-src https://www.google.com https://cse.google.com https://maps.google.com; "
        "child-src https://www.google.com https://maps.google.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = (
        "public, max-age=86400" if path in CACHED_ASSETS else "no-store"
    )
    if is_secure or forwarded_proto == "https":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    response.headers.pop("Server", None)
    return response
