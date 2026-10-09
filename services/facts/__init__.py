"""Repères pratiques par thème : un fichier par sujet, chargés automatiquement.

Pour ajouter un sujet, créer `services/facts/<theme>.py` qui définit :

    TOPICS = (("nom", r"déclencheurs sur le texte sans accents", ("repère 1", "repère 2")),)
    SPECIFIC_FIRST = ("nom",)   # facultatif : sujet précis, prioritaire quand la limite de 3 coupe

Aucune ligne à modifier ailleurs (les agents peuvent travailler en parallèle sans conflit de fusion).
Les fichiers sont chargés par ordre alphabétique, après les sujets de `services/practical_facts.py`.
Un module ne doit pas importer `services.practical_facts` (import circulaire).
"""

from __future__ import annotations

import importlib
import pkgutil


def _collect(modules) -> tuple[tuple, tuple]:
    topics: list = []
    specific: list = []
    for module in modules:
        topics.extend(getattr(module, "TOPICS", ()))
        specific.extend(getattr(module, "SPECIFIC_FIRST", ()))
    return tuple(topics), tuple(specific)


def load_topics() -> tuple[tuple, tuple]:
    """(sujets, noms des sujets prioritaires) de tous les fichiers du dossier, par ordre alphabétique."""
    names = sorted(info.name for info in pkgutil.iter_modules(__path__) if not info.name.startswith("_"))
    return _collect(importlib.import_module(f"{__name__}.{name}") for name in names)
