"""Public-facing error messages for Teranga AI.

Keep provider/infrastructure details out of HTTP handlers while preserving
safe, user-facing diagnostics.
"""
from __future__ import annotations

import re


_UNAVAILABLE = "Le service IA est momentanément indisponible. Réessaie dans quelques secondes."
_UNAVAILABLE_EN = "The AI service is temporarily unavailable. Please try again in a few seconds."


def public_error(exc: object, language: str = "fr") -> str:
    """Map an exception to a safe public-facing French error message."""
    text = f"{type(exc).__name__} {exc}".lower()
    text = re.sub(r"(sk-[a-z0-9_-]{8,})", "[redacted-key]", text)
    text = re.sub(r"(bearer\s+)[a-z0-9._-]{12,}", r"\1[redacted-token]", text)
    text = re.sub(
        r"([?&](?:key|api_key|token|access_token)=)[^&\s]+",
        r"\1[redacted]",
        text,
    )
    fr = language != "en"
    if "timeout" in text or "timed out" in text:
        return "La réponse a pris trop de temps. Réessaie." if fr else "The answer took too long. Please try again."
    if "429" in text or "rate limit" in text or "quota" in text:
        return "Le service est très demandé. Réessaie dans un moment." if fr else "The service is very busy. Please try again in a moment."
    if "401" in text or "403" in text or "api key" in text or "authentication" in text:
        return _UNAVAILABLE if fr else _UNAVAILABLE_EN
    if "model" in text and (
        "not found" in text
        or "does not exist" in text
        or "not available" in text
        or "unsupported" in text
        or "not permitted" in text
    ):
        return (
            "Le modèle IA configuré est momentanément indisponible. Réessaie dans quelques secondes."
            if fr else "The AI model is temporarily unavailable. Please try again in a few seconds."
        )
    if "web_search" in text or "web search" in text:
        return (
            "La recherche web a échoué. Réessaie dans un instant."
            if fr else "The web search failed. Please try again in a moment."
        )
    if "badrequest" in text or "invalid" in text or "parameter" in text:
        # Pas de conseil technique (« vérifie le modèle ») : le visiteur n'y peut rien.
        return (
            "La requête IA n'a pas pu être traitée. Reformule ta question ou réessaie."
            if fr else "The AI request could not be processed. Rephrase your question or try again."
        )
    if "connection" in text or "network" in text or "502" in text or "503" in text:
        return (
            "Le service IA est momentanément inaccessible. Réessaie dans quelques secondes."
            if fr else "The AI service is temporarily unreachable. Please try again in a few seconds."
        )
    return (
        "Le service IA a rencontré une erreur inattendue. Réessaie dans quelques secondes."
        if fr else "The AI service hit an unexpected error. Please try again in a few seconds."
    )
