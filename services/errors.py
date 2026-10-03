"""Public-facing error messages for Teranga AI.

Keep provider/infrastructure details out of HTTP handlers while preserving
safe, user-facing diagnostics.
"""
from __future__ import annotations

import re


def public_error(exc: object) -> str:
    """Map an exception to a safe public-facing French error message."""
    text = f"{type(exc).__name__} {exc}".lower()
    text = re.sub(r"(sk-[a-z0-9_-]{8,})", "[redacted-key]", text)
    text = re.sub(r"(bearer\s+)[a-z0-9._-]{12,}", r"\1[redacted-token]", text)
    text = re.sub(
        r"([?&](?:key|api_key|token|access_token)=)[^&\s]+",
        r"\1[redacted]",
        text,
    )
    if "timeout" in text or "timed out" in text:
        return "La réponse a pris trop de temps. Réessaie."
    if "429" in text or "rate limit" in text or "quota" in text:
        return "Le service est très demandé. Réessaie dans un moment."
    if "401" in text or "403" in text or "api key" in text or "authentication" in text:
        return "Le service IA est momentanément indisponible. Réessaie dans quelques secondes."
    if "model" in text and (
        "not found" in text
        or "does not exist" in text
        or "not available" in text
        or "unsupported" in text
        or "not permitted" in text
    ):
        return "Le modèle IA configuré n'est pas disponible. Le modèle de secours va être essayé."
    if "web_search" in text or "web search" in text:
        return "La recherche web IA a échoué. Réessaie sans la recherche actuelle."
    if "badrequest" in text or "invalid" in text or "parameter" in text:
        return "La requête IA est refusée par le service. Vérifie le modèle ou les paramètres."
    if "connection" in text or "network" in text or "502" in text or "503" in text:
        return "Le service IA est momentanément inaccessible. Réessaie dans quelques secondes."
    return "Le service IA a rencontré une erreur inattendue. Réessaie dans quelques secondes."
