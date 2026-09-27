"""Web retrieval policy for Teranga AI V3.3."""
from __future__ import annotations

SOURCE_FILTERS = {
    "weather": ("anacim.sn", "gov.sn", "who.int"),
    "society": ("ansd.sn", "gov.sn", "who.int", "worldbank.org"),
    "economy": ("ansd.sn", "gov.sn", "worldbank.org"),
    "agriculture": ("ansd.sn", "agriculture.gouv.sn", "gov.sn", "fao.org"),
    "territory": ("ansd.sn", "gov.sn", "tourisme.gouv.sn"),
    "travel": ("tourisme.gouv.sn", "ansd.sn", "unesco.org", "gov.sn"),
    "culture": ("unesco.org", "tourisme.gouv.sn", "gov.sn"),
    "environment": ("tourisme.gouv.sn", "unesco.org", "gov.sn", "who.int"),
    "administration": ("diplomatie.gouv.sn", "interieur.gouv.sn", "gov.sn"),
    "transport": ("transports.gouv.sn", "gov.sn", "ansd.sn"),
    "diaspora": ("diplomatie.gouv.sn", "gov.sn", "ansd.sn"),
}

def preferred_domains(domain: str) -> tuple[str, ...]:
    return SOURCE_FILTERS.get(str(domain or ""), ())

def search_context_size(domain: str, planner: bool = False) -> str:
    return "medium" if planner or domain in {"administration", "society", "economy"} else "low"

def reasoning_effort(use_web: bool, planner: bool) -> str:
    if planner:
        return "low"
    if use_web:
        return "low"
    return "none"
