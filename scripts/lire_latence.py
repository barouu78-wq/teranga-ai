"""Médiane, p95 et nombre de requêtes par route, à partir des lignes « latence » des journaux.

Colle (ou redirige) des lignes de journal sur l'entrée standard : seules celles qui contiennent
`latence route=…` comptent, le reste est ignoré (journaux Gunicorn, horodatages Render, export JSON…).

    python scripts/lire_latence.py < export.txt
    python scripts/lire_latence.py --tout < export.txt                 # garde aussi secours, erreurs, abandons…
    python scripts/lire_latence.py --garder modele=… --garder mode=flux < export.txt

Par défaut seules les requêtes au statut « ok » entrent dans les médianes et les p95 : une erreur
rapide ou un secours ne doivent pas faire croire que le chat va vite. Le nombre de lignes de chaque
statut reste affiché. Le chat est séparé selon `cache=oui|non` : une réponse du cache n'a rien à voir
avec un appel au modèle. Les réponses prêtes (`pret=oui` : servies par Teranga sans le modèle) forment un
groupe à part, « chat, réponse prête ».

Méthodes (refaisables à la main, voir docs/MESURE-LATENCE.md) :
  - médiane : valeur du milieu des valeurs triées (moyenne des deux du milieu s'il y en a un nombre pair) ;
  - p95 « rang le plus proche » : valeur de rang ceil(0,95 × n) dans les valeurs triées.
Aucun objectif chiffré n'est fixé ici : il se fixe après la première mesure réelle.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from collections.abc import Iterable
from typing import TextIO

METRICS = ("total_ms", "contexte_ms", "recherche_ms", "premier_mot_ms", "fournisseur_ms")
MIN_FOR_P95 = 20  # en dessous, le p95 n'est que la valeur la plus lente ou presque : on le dit

_LINE = re.compile(r"\blatence\s+(route=[^\s\",}]+(?:\s+[a-z_]+=[^\s\",}]+)*)")
_PAIR = re.compile(r"([a-z_]+)=([^\s\",}]+)")


def parse_line(text: str) -> dict[str, str] | None:
    """{'route': 'chat', 'total_ms': '2310.4', …} si la ligne contient `latence route=…`, sinon None."""
    found = _LINE.search(text)
    if not found:
        return None
    return dict(_PAIR.findall(found.group(1)))


def number(value: str | None) -> float | None:
    """Millisecondes lues, ou None pour « - » (sans objet) et pour tout ce qui n'est pas un nombre fini."""
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def percentile(values: list[float], pct: int) -> float:
    """Percentile « rang le plus proche » : valeur de rang ceil(pct/100 × n), calcul en entiers (pas d'arrondi flottant)."""
    ordered = sorted(values)
    rank = max(1, -(-pct * len(ordered) // 100))
    return ordered[rank - 1]


def group_name(record: dict[str, str]) -> str:
    route = record.get("route", "?")
    if route != "chat":
        return route
    # Réponse prête (sans le modèle) : un groupe à part, pour compter ce que Teranga sert seul.
    if record.get("pret") == "oui":
        return "chat, réponse prête"
    return f"{route}, cache={record.get('cache', '-')}"


def read_records(lines: Iterable[str]) -> list[dict[str, str]]:
    return [record for record in map(parse_line, lines) if record]


def summarize(records: list[dict[str, str]], *, keep_all: bool = False, filters: dict[str, str] | None = None) -> list[dict]:
    """Un résumé par groupe (route, et cache pour le chat), dans l'ordre alphabétique."""
    filters = filters or {}
    selected = [r for r in records if all(r.get(key) == value for key, value in filters.items())]
    groups: dict[str, list[dict[str, str]]] = {}
    for record in selected:
        groups.setdefault(group_name(record), []).append(record)
    summaries = []
    for name, members in sorted(groups.items()):
        kept = members if keep_all else [r for r in members if r.get("statut") == "ok"]
        metrics = {}
        for metric in METRICS:
            values = [v for v in (number(r.get(metric)) for r in kept) if v is not None]
            if values:
                metrics[metric] = {"n": len(values), "mediane": median(values), "p95": percentile(values, 95)}
        summaries.append({
            "groupe": name,
            "lues": len(members),
            "gardees": len(kept),
            "statuts": Counter(r.get("statut", "?") for r in members),
            "metriques": metrics,
        })
    return summaries


def render(summaries: list[dict], *, total: int, keep_all: bool, filters: dict[str, str]) -> str:
    out = [f"Lignes « latence » lues : {total}"]
    if filters:
        out.append("Filtres : " + ", ".join(f"{k}={v}" for k, v in filters.items()))
    out.append("Statuts gardés : " + ("tous" if keep_all else "ok seulement (--tout pour tout garder)"))
    for item in summaries:
        statuts = ", ".join(f"{k}={v}" for k, v in sorted(item["statuts"].items()))
        out += ["", f"{item['groupe']} : {item['gardees']} requête(s) gardée(s) sur {item['lues']} ({statuts})"]
        if not item["metriques"]:
            out.append("  (aucune durée à calculer)")
            continue
        for metric in METRICS:
            stats = item["metriques"].get(metric)
            if stats:
                out.append(f"  {metric:<15} n={stats['n']:<5} médiane={stats['mediane']:<10.1f} p95={stats['p95']:.1f}")
        if item["gardees"] < MIN_FOR_P95:
            out.append(f"  Attention : moins de {MIN_FOR_P95} requêtes, le p95 est peu fiable.")
    return "\n".join(out) + "\n"


def _filter(text: str) -> tuple[str, str]:
    key, separator, value = text.partition("=")
    if not separator or not key or not value:
        raise argparse.ArgumentTypeError("attendu : CLE=VALEUR, par exemple modele=nom-du-modele")
    return key, value


def main(argv: list[str] | None = None, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Médiane, p95 et nombre de requêtes par route, depuis les lignes « latence ».")
    parser.add_argument("--tout", action="store_true", help="garder tous les statuts (par défaut : ok seulement)")
    parser.add_argument("--garder", action="append", type=_filter, default=[], metavar="CLE=VALEUR",
                        help="ne garder que les lignes où CLE vaut VALEUR (répétable), par exemple mode=flux")
    args = parser.parse_args(argv)
    if stdin is None:
        stdin = sys.stdin
        if hasattr(stdin, "reconfigure"):
            stdin.reconfigure(errors="replace")  # un export peut contenir des octets invalides : on les remplace, on ne s'arrête pas
    stdout = stdout or sys.stdout
    records = read_records(stdin)
    if not records:
        print("Aucune ligne « latence route=… » trouvée dans l'entrée.", file=sys.stderr)
        return 1
    filters = dict(args.garder)
    summaries = summarize(records, keep_all=args.tout, filters=filters)
    stdout.write(render(summaries, total=len(records), keep_all=args.tout, filters=filters))
    return 0


if __name__ == "__main__":
    sys.exit(main())
