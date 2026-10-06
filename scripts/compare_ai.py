"""Comparatif OpenAI / Claude sur les 50 questions du banc d'essai.

À lancer là où les deux clés sont définies (Render → Shell, ou ton ordinateur) :

    python scripts/compare_ai.py                 # les 50 questions
    python scripts/compare_ai.py --limite 5      # essai rapide
    python scripts/compare_ai.py --prix-openai 1.25,10 --prix-claude 5,25

Chaque question est posée aux deux IA avec exactement le même contexte que sur
le site (base de connaissances, consignes). Coûte de l'argent : environ
100 appels pour les 50 questions. Les prix sont en dollars par million de jetons
(entrée,sortie) ; sans eux, seul le nombre de jetons est affiché.

Résultat : comparatif-ia.md, avec pour chaque question les deux réponses côte à
côte, le temps de réponse, les faits attendus trouvés et les jetons utilisés.
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.backup_ai import claude_response  # noqa: E402


def load_bench():
    """Questions de tests/test_ai_bench.py, lues sans importer pytest."""
    tree = ast.parse((ROOT / "tests" / "test_ai_bench.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "BENCH" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("BENCH introuvable dans tests/test_ai_bench.py")


def prices(raw):
    if not raw:
        return None
    entry, out = (float(x) for x in raw.split(","))
    return entry, out


def tokens(response):
    usage = getattr(response, "usage", None)
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)


def ask(app_module, provider, lang, question):
    os.environ["AI_PRINCIPALE"] = provider
    with app_module.app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = app_module.parse_chat_payload()
    if error:
        return {"text": "(requête refusée)", "seconds": 0.0, "tokens": (0, 0), "sources": []}
    started = time.perf_counter()
    try:
        if provider == "claude":
            # Appel direct : un échec de Claude ne doit pas être masqué par le relais OpenAI.
            response = claude_response(
                payload.get("input_text") or question, system=payload.get("instructions", ""),
                max_tokens=4000, timeout=60.0, web=bool(payload.get("use_web")),
            )
        else:
            response = app_module.create_response(payload, stream=False)
        text = app_module.clean_answer(getattr(response, "output_text", "") or "")
        sources = app_module.extract_sources(response)
    except Exception as exc:  # noqa: BLE001 - on note l'échec et on continue
        response, text, sources = None, f"(échec : {type(exc).__name__})", []
    return {"text": text, "seconds": time.perf_counter() - started, "tokens": tokens(response), "sources": sources}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limite", type=int, default=0, help="nombre de questions (0 = toutes)")
    parser.add_argument("--prix-openai", default="", help="dollars par million de jetons : entrée,sortie")
    parser.add_argument("--prix-claude", default="", help="dollars par million de jetons : entrée,sortie")
    parser.add_argument("--sortie", default="comparatif-ia.md")
    args = parser.parse_args()
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Il faut OPENAI_API_KEY et ANTHROPIC_API_KEY.")

    import app as app_module

    bench = load_bench()[: args.limite or None]
    cost = {"openai": prices(args.prix_openai), "claude": prices(args.prix_claude)}
    totals = {p: {"seconds": 0.0, "facts": 0, "expected": 0, "in": 0, "out": 0, "fails": 0} for p in cost}
    rows = []
    for index, (lang, question, expected) in enumerate(bench, 1):
        print(f"[{index}/{len(bench)}] {question}", flush=True)
        row = {"lang": lang, "question": question}
        for provider in cost:
            result = ask(app_module, provider, lang, question)
            found = [fact for fact in expected if fact.lower() in result["text"].lower()]
            total = totals[provider]
            total["seconds"] += result["seconds"]
            total["facts"] += len(found)
            total["expected"] += len(expected)
            total["in"] += result["tokens"][0]
            total["out"] += result["tokens"][1]
            total["fails"] += result["text"].startswith("(échec")
            row[provider] = {**result, "found": found, "expected": expected}
        rows.append(row)

    def money(provider):
        if not cost[provider]:
            return "prix non fourni"
        t = totals[provider]
        dollars = t["in"] / 1e6 * cost[provider][0] + t["out"] / 1e6 * cost[provider][1]
        return f"{dollars:.2f} $ (≈ {dollars / max(1, len(rows)) * 1000:.2f} $ pour 1 000 questions)"

    lines = ["# Comparatif OpenAI / Claude", "", f"{len(rows)} questions du banc d'essai.", "",
             "| | OpenAI | Claude |", "|---|---|---|"]
    for label, key in (("Temps moyen", "seconds"),):
        lines.append(f"| {label} | " + " | ".join(f"{totals[p][key] / max(1, len(rows)):.1f} s" for p in cost) + " |")
    lines.append("| Faits attendus trouvés | " + " | ".join(f"{totals[p]['facts']} / {totals[p]['expected']}" for p in cost) + " |")
    lines.append("| Échecs | " + " | ".join(str(totals[p]["fails"]) for p in cost) + " |")
    lines.append("| Jetons (entrée / sortie) | " + " | ".join(f"{totals[p]['in']} / {totals[p]['out']}" for p in cost) + " |")
    lines.append("| Coût | " + " | ".join(money(p) for p in cost) + " |")
    lines += ["", "Les « faits attendus » sont un repère grossier : lis aussi les réponses ci-dessous.", ""]
    for index, row in enumerate(rows, 1):
        lines += [f"## {index}. {row['question']} ({row['lang']})", ""]
        for provider, title in (("openai", "OpenAI"), ("claude", "Claude")):
            result = row[provider]
            facts = f"{len(result['found'])}/{len(result['expected'])} faits" if result["expected"] else "pas de fait attendu"
            lines += [f"**{title}** · {result['seconds']:.1f} s · {facts}", ""]
            lines += ["> " + line if line else ">" for line in result["text"].splitlines()]
            if result["sources"]:
                lines.append("> Sources : " + ", ".join(s["url"] for s in result["sources"]))
            lines.append("")
    Path(args.sortie).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nRésultat écrit dans {args.sortie}")


if __name__ == "__main__":
    main()
