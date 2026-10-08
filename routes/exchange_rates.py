"""Exchange-rate route registration."""

import time

from flask import jsonify


def register_exchange_rates_route(app, deps):
    client_ip = deps["client_ip"]
    abuse_key = deps["abuse_key"]
    allowed_request = deps["allowed_request"]
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
            return (
                jsonify({"error": "Trop de demandes de taux. Réessaie dans un instant."}),
                429,
                {"Retry-After": "15"},
            )
        data = fetch_bceao_rates()
        return jsonify(
            {
                # Sans date, la BCEAO n'a pas pu être lue : les taux sont ceux du code, et c'est dit.
                "source": "BCEAO" if data["date"] else "indicatif",
                "live": bool(data["date"]),
                "date": data["date"],
                "rates": data["rates"],
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
