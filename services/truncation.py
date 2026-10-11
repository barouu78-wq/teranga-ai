"""Réponse coupée par la limite de longueur : le dire à l'utilisateur et lui permettre de continuer.

`max_output_tokens` (services/model_params.py) compte aussi le raisonnement du modèle. Quand la limite est atteinte,
l'API répond `status == "incomplete"` (événement `response.incomplete` en flux) ; Claude, `stop_reason == "max_tokens"`
(traduit de la même façon par services/backup_ai.py). Le client (static/home.js) n'affiche que le texte des
événements `d` : il ignore tout autre champ. La mention est donc ajoutée au texte lui-même, à la fin, en français
ou en anglais.

« Continue » ne marche que si le modèle voit la fin de sa réponse coupée : `prepare_cut_history` garde cette fin
(l'historique est sinon limité aux 1400 premiers caractères de chaque tour) et retire la mention, pour que le modèle
ne la recopie pas dans ses réponses suivantes.
"""

from __future__ import annotations

from typing import Any

CUT_NOTICES = {
    "fr": "Réponse coupée : écris « continue » pour avoir la suite.",
    "en": "Answer cut short: type “continue” to get the rest.",
}
_NOTICES = tuple(CUT_NOTICES.values())
# Raisons d'arrêt qui sont une limite de longueur (OpenAI : max_output_tokens ; Claude : max_tokens). Une raison
# absente compte aussi : Claude, via backup_ai, n'en donne pas. « content_filter » n'en est pas une : « continue »
# n'y changerait rien.
_LENGTH_REASONS = frozenset({"", "max_output_tokens", "max_tokens", "length"})
_GAP = " […] "


def cut_notice(language: str = "fr") -> str:
    """La mention, en anglais pour « en », en français sinon (wolof et peul compris)."""
    return CUT_NOTICES["en" if language == "en" else "fr"]


def ends_with_cut_notice(text: object) -> bool:
    return str(text or "").rstrip().endswith(_NOTICES)


def strip_cut_notice(text: object) -> str:
    """Le texte sans la mention finale (inchangé s'il n'en a pas)."""
    value = str(text or "").rstrip()
    for notice in _NOTICES:
        if value.endswith(notice):
            return value[: -len(notice)].rstrip()
    return str(text or "")


def with_cut_notice(text: object, language: str = "fr") -> str:
    """Le texte coupé, une ligne vide, puis la mention. Texte vide ou déjà muni de la mention : inchangé."""
    value = str(text or "")
    if not value.strip() or ends_with_cut_notice(value):
        return value
    return value.rstrip() + "\n\n" + cut_notice(language)


def _field(node: Any, name: str) -> Any:
    if isinstance(node, dict):
        return node.get(name)
    return getattr(node, name, None)


def is_cut_by_length(response: Any) -> bool:
    """Vrai si la réponse (objet ou dict de l'API) s'est arrêtée à la limite de longueur."""
    if response is None or _field(response, "status") != "incomplete":
        return False
    reason = _field(_field(response, "incomplete_details"), "reason")
    return str(reason or "").strip().lower() in _LENGTH_REASONS


def mark_incomplete(payload: dict, response: Any) -> bool:
    """Note sur la requête qu'une réponse n'est pas allée au bout (jamais mise en cache) et, si c'est la limite de
    longueur, qu'il faut le dire (`reply_cut`). Renvoie ce dernier point."""
    if _field(response, "status") == "incomplete":
        payload["reply_incomplete"] = True
    cut = is_cut_by_length(response)
    if cut:
        payload["reply_cut"] = True
    return cut


def prepare_cut_history(history: Any, max_item_length: int) -> tuple[Any, bool]:
    """Historique à donner au modèle, et vrai si sa dernière réponse a été coupée.

    La mention est retirée de tous les tours de l'assistant. Pour le dernier tour coupé trop long pour tenir dans
    `max_item_length`, on garde le début et surtout la fin, afin que « continue » reprenne où la réponse s'est
    arrêtée (sans cela, le modèle ne verrait que ses 1400 premiers caractères et se répéterait)."""
    if not isinstance(history, list):
        return history, False
    last = max(
        (i for i, item in enumerate(history) if isinstance(item, dict) and str(item.get("role", "")).lower() == "assistant"),
        default=-1,
    )
    cut_last = False
    result = []
    for index, item in enumerate(history):
        if not (isinstance(item, dict) and str(item.get("role", "")).lower() == "assistant" and ends_with_cut_notice(item.get("content"))):
            result.append(item)
            continue
        content = strip_cut_notice(item.get("content"))
        if index == last:
            cut_last = True
            if len(content) > max_item_length:
                head = max_item_length // 3
                content = content[:head].rstrip() + _GAP + content[-(max_item_length - head - len(_GAP)):].lstrip()
        result.append({**item, "content": content})
    return result, cut_last
