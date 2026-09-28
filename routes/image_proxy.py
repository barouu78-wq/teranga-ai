"""Image proxy route registration."""

from flask import Response, request


def register_image_proxy_route(app, deps):
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    abuse_blocked = deps["abuse_blocked"]
    allowed_request = deps["allowed_request"]
    record_abuse = deps["record_abuse"]
    image_request_log = deps["image_request_log"]
    IMAGE_RATE_LIMIT = deps["IMAGE_RATE_LIMIT"]
    IMAGE_RATE_WINDOW = deps["IMAGE_RATE_WINDOW"]
    usable_wiki_image = deps["usable_wiki_image"]
    allowed_image_url = deps["allowed_image_url"]
    safe_image_fetch = deps["safe_image_fetch"]
    MAX_IMAGE_BYTES = deps["MAX_IMAGE_BYTES"]
    OUTBOUND_TIMEOUT = deps["OUTBOUND_TIMEOUT"]
    safe_image_opener = deps["safe_image_opener"]

    @app.get("/image-proxy")
    def image_proxy():
        ip = client_ip()
        identity = abuse_key(ip)
        if abuse_blocked(ip) or abuse_blocked(identity):
            return Response(
                "Trop de demandes. Réessaie dans quelques minutes.",
                status=429,
                mimetype="text/plain",
                headers={"Retry-After": "120"},
            )
        if (
            not allowed_request(
                ip,
                image_request_log[ip],
                IMAGE_RATE_LIMIT,
                IMAGE_RATE_WINDOW,
                "image",
            )
            or not allowed_request(
                identity,
                image_request_log[identity],
                IMAGE_RATE_LIMIT,
                IMAGE_RATE_WINDOW,
                "image_identity",
            )
        ):
            record_abuse(ip, "image_rate", 1)
            record_abuse(identity, "image_identity_rate", 1)
            return Response(
                "Trop de demandes d'images. Réessaie dans un instant.",
                status=429,
                mimetype="text/plain",
                headers={"Retry-After": "10"},
            )

        src = usable_wiki_image(request.args.get("url", ""))
        if not src:
            return Response("Image invalide", status=400, mimetype="text/plain")
        if not allowed_image_url(src):
            return Response(
                "Source image non autorisée",
                status=403,
                mimetype="text/plain",
            )

        try:
            content_type, data = safe_image_fetch(
                src,
                MAX_IMAGE_BYTES,
                OUTBOUND_TIMEOUT,
                opener=safe_image_opener,
            )
            return Response(
                data,
                mimetype=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception:
            app.logger.exception("Erreur proxy image Wikimedia")
            return Response(
                "Image indisponible",
                status=502,
                mimetype="text/plain",
            )
