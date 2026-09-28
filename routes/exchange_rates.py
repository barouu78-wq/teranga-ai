"""Exchange-rate route registration."""

import time

from flask import jsonify


def register_exchange_rates_route(app, deps):
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    allowed_request = deps["allowed_request"]
    record_abuse = deps["record_abuse"]
    fx_request_log = deps["fx_request_log"]
    FX_RATE_LIMIT = deps["FX_RATE_LIMIT"]
    FX_RATE_WINDOW = deps["FX_RATE_WINDOW"]
    fetch_bceao_rates = deps["fetch_bceao_rates"]

    @app.get("/exchange-rates")
    def exchange_rates():
        ip = client_ip()
        identity = abuse_key(ip)
        if (
            not allowed_request(
                ip, fx_request_log[ip], FX_RATE_LIMIT, FX_RATE_WINDOW, "fx"
            )
            or not allowed_request(
                identity,
                fx_request_log[identity],
                FX_RATE_LIMIT,
                FX_RATE_WINDOW,
                "fx_identity",
            )
        ):
            record_abuse(ip, "fx_rate", 1)
            record_abuse(identity, "fx_identity_rate", 1)
            return (
                jsonify({"error": "Trop de demandes de taux. Réessaie dans un instant."}),
                429,
                {"Retry-After": "15"},
            )
        data = fetch_bceao_rates()
        return jsonify(
            {
                "source": "BCEAO",
                "date": data["date"],
                "rates": data["rates"],
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
