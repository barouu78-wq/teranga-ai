"""Banc V3 : 100 questions sénégalaises envoyées à la vraie route /chat, sans IA ni réseau.

Ce banc mesure le ROUTAGE réel de Teranga (réponse prête, recherche web, modèle choisi, taille du contexte,
temps de préparation), pas la justesse des réponses : l'IA est simulée (aucun coût, aucune clé) et tout accès
réseau est coupé (météo, images, recherche externe échouent tout de suite, comme dans les tests).

La colonne « attendu » est le jugement de l'audit V3 (docs/audit-v3/03-benchmark-teranga.md) :
  prete    réponse exacte sans IA (calcul, conversion, date connue, numéro d'urgence, présentation)
  web      l'information change (actualité, prix du jour, horaires, offres) : il faut chercher
  base     connaissance stable : base vérifiée du site + modèle, sans recherche web
  service  service dédié (météo)
  precis   question ambiguë : demander une précision, ne rien chercher
  inconnu  hors du champ ou invérifiable : le dire honnêtement, sans inventer

Usage : OPENAI_API_KEY=test-key python scripts/banc_v3.py [--json sortie.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# (thème, langue, question, attendu)
QUESTIONS: list[tuple[str, str, str, str]] = [
    # 1. Vie quotidienne et démarches
    ("demarches", "fr", "Comment refaire ma carte d'identité au Sénégal ?", "base"),
    ("demarches", "fr", "Quels documents faut-il pour un passeport sénégalais ?", "base"),
    ("demarches", "fr", "Comment payer ma facture Senelec ?", "base"),
    ("demarches", "fr", "Comment déclarer une naissance à Dakar ?", "base"),
    ("demarches", "fr", "Où faire légaliser un document à Dakar ?", "base"),
    ("demarches", "fr", "Comment obtenir un extrait de casier judiciaire ?", "base"),
    ("demarches", "fr", "Quel est le prix actuel du sac de riz à Dakar ?", "web"),
    ("demarches", "fr", "Comment ouvrir un compte Wave ?", "base"),
    ("demarches", "fr", "Quels sont les jours fériés au Sénégal ?", "base"),
    ("demarches", "fr", "Quelle pharmacie est de garde à Dakar ce soir ?", "web"),
    # 2. Transport et mobilité
    ("transport", "fr", "Comment aller de l'aéroport AIBD à Dakar ?", "base"),
    ("transport", "fr", "Combien coûte un taxi de l'AIBD au Plateau ?", "base"),
    ("transport", "fr", "Le TER circule-t-il normalement aujourd'hui ?", "web"),
    ("transport", "fr", "Quels sont les horaires du BRT de Dakar ?", "web"),
    ("transport", "fr", "Comment aller à Saint-Louis depuis Dakar ?", "base"),
    ("transport", "fr", "Comment prendre la chaloupe pour Gorée ?", "base"),
    ("transport", "fr", "Y a-t-il un bateau Dakar–Ziguinchor cette semaine ?", "web"),
    ("transport", "fr", "C'est quoi un car rapide ?", "base"),
    ("transport", "fr", "Combien de temps de route entre Dakar et Touba ?", "base"),
    ("transport", "en", "How do I get from Dakar airport to the city centre?", "base"),
    # 3. Tourisme et patrimoine
    ("tourisme", "fr", "Que visiter à Dakar en deux jours ?", "base"),
    ("tourisme", "fr", "C'est quoi le Lac Rose ?", "base"),
    ("tourisme", "fr", "Raconte-moi l'histoire de l'île de Gorée", "base"),
    ("tourisme", "fr", "Que faire en Casamance ?", "base"),
    ("tourisme", "en", "What is the best time to visit Senegal?", "base"),
    ("tourisme", "fr", "Visiter le parc du Niokolo-Koba", "base"),
    ("tourisme", "fr", "Que voir à Saint-Louis ?", "base"),
    ("tourisme", "fr", "Prépare-moi un séjour de 5 jours au Sénégal", "base"),
    ("tourisme", "fr", "Quels sites sont classés à l'UNESCO au Sénégal ?", "base"),
    ("tourisme", "fr", "Quel est le prix d'une nuit à l'hôtel Terrou-Bi ce soir ?", "web"),
    # 4. Langues locales
    ("langues", "fr", "Comment dire merci en wolof ?", "base"),
    ("langues", "wo", "Nanga def ?", "base"),
    ("langues", "wo", "Lan mooy thiéboudienne ?", "prete"),
    ("langues", "fr", "Traduis « combien ça coûte » en wolof", "base"),
    ("langues", "fr", "Que veut dire teranga ?", "base"),
    ("langues", "wo", "Dama bëgg dem Ndakaaru, naka laa def ?", "base"),
    ("langues", "fr", "Apprends-moi à compter en wolof", "base"),
    ("langues", "fr", "Comment saluer un aîné en wolof ?", "base"),
    ("langues", "wo", "Ana yoonu Tubaa ?", "base"),
    ("langues", "fr", "Dama bëgg jënd mburu, ñaata la ?", "precis"),
    # 5. Emploi et formation
    ("emploi", "fr", "Comment trouver un emploi à Dakar ?", "base"),
    ("emploi", "fr", "Aide-moi à préparer mon CV", "base"),
    ("emploi", "fr", "Quelles offres d'emploi pour un comptable à Dakar en ce moment ?", "web"),
    ("emploi", "fr", "Quelles sont les dates d'inscription à l'université Cheikh Anta Diop cette année ?", "web"),
    ("emploi", "fr", "Quelles formations gratuites en informatique au Sénégal ?", "web"),
    ("emploi", "fr", "Prépare-moi à un entretien d'embauche", "base"),
    ("emploi", "fr", "Quel est le SMIG au Sénégal ?", "base"),
    ("emploi", "fr", "Comment devenir enseignant au Sénégal ?", "base"),
    ("emploi", "fr", "Quelles bourses pour étudier en France cette année ?", "web"),
    ("emploi", "fr", "C'est quoi l'ANPEJ ?", "base"),
    # 6. Commerce, entrepreneuriat et argent
    ("commerce", "fr", "Combien font 100 euros en FCFA ?", "prete"),
    ("commerce", "fr", "Convertis 50 000 FCFA en euros", "prete"),
    ("commerce", "fr", "Comment créer une entreprise au Sénégal ?", "base"),
    ("commerce", "fr", "Je veux vendre du jus naturel à Thiès, par où commencer ?", "base"),
    ("commerce", "fr", "Combien coûte aujourd'hui l'immatriculation d'une SARL à l'APIX ?", "web"),
    ("commerce", "fr", "Comment obtenir un microcrédit au Sénégal ?", "base"),
    ("commerce", "fr", "J'achète à 1 500 FCFA et je revends à 2 000 FCFA : quelle est ma marge ?", "prete"),
    ("commerce", "fr", "Comment négocier au marché Sandaga ?", "base"),
    ("commerce", "fr", "Quel est le taux de TVA au Sénégal ?", "base"),
    ("commerce", "fr", "Fais-moi un budget mensuel pour une famille à Dakar avec 250 000 FCFA", "base"),
    # 7. Informations qui changent
    ("dynamique", "fr", "Quel temps fera-t-il à Dakar demain ?", "service"),
    ("dynamique", "fr", "Quelles sont les dernières nouvelles au Sénégal ?", "web"),
    ("dynamique", "fr", "Quel est le résultat du dernier match des Lions du Sénégal ?", "web"),
    ("dynamique", "fr", "Combien vaut le dollar en FCFA aujourd'hui ?", "web"),
    ("dynamique", "fr", "Quel est le prix de l'essence au Sénégal ce mois-ci ?", "web"),
    ("dynamique", "fr", "Y a-t-il des coupures d'électricité à Dakar aujourd'hui ?", "web"),
    ("dynamique", "fr", "C'est quand la Tabaski cette année ?", "prete"),
    ("dynamique", "fr", "Quand est le prochain Magal de Touba ?", "prete"),
    ("dynamique", "fr", "Quels concerts à Dakar ce week-end ?", "web"),
    ("dynamique", "fr", "Qui est l'actuel ministre de la Santé du Sénégal ?", "web"),
    # 8. Santé et urgences
    ("sante", "fr", "Quel est le numéro des pompiers au Sénégal ?", "prete"),
    ("sante", "fr", "Quels sont les numéros d'urgence au Sénégal ?", "prete"),
    ("sante", "fr", "J'ai de la fièvre depuis trois jours, que faire ?", "base"),
    ("sante", "fr", "Quels vaccins pour voyager au Sénégal ?", "base"),
    ("sante", "fr", "Où trouver un hôpital à Saint-Louis ?", "base"),
    ("sante", "fr", "Comment fonctionne la CMU au Sénégal ?", "base"),
    ("sante", "fr", "Paludisme : comment se protéger ?", "base"),
    ("sante", "fr", "Mon enfant a avalé un produit ménager, que faire ?", "base"),
    ("sante", "fr", "Le SAMU, c'est quel numéro au Sénégal ?", "prete"),
    ("sante", "fr", "Faut-il un test Covid pour entrer au Sénégal en ce moment ?", "web"),
    # 9. Diaspora
    ("diaspora", "fr", "Comment envoyer de l'argent de France au Sénégal ?", "base"),
    ("diaspora", "en", "Do I need a visa to visit Senegal?", "base"),
    ("diaspora", "fr", "Comment acheter un terrain au Sénégal depuis la France ?", "base"),
    ("diaspora", "fr", "Comment renouveler mon passeport sénégalais en France ?", "base"),
    ("diaspora", "fr", "Quels frais pour envoyer 200 euros avec Wave aujourd'hui ?", "web"),
    ("diaspora", "fr", "Comment voter depuis l'étranger à la prochaine élection ?", "web"),
    ("diaspora", "fr", "Rapatriement d'un corps vers le Sénégal : quelles démarches ?", "base"),
    ("diaspora", "fr", "Comment investir au Sénégal depuis la diaspora ?", "base"),
    ("diaspora", "fr", "Peut-on avoir la double nationalité sénégalaise ?", "base"),
    ("diaspora", "fr", "Combien font 300 euros en francs CFA ?", "prete"),
    # 10. Questions ambiguës, inconnues ou hors du champ
    ("ambigu", "fr", "Combien ?", "precis"),
    ("ambigu", "fr", "Et là-bas ?", "precis"),
    ("ambigu", "fr", "Quel est le meilleur logiciel de comptabilité pour mon garage ?", "inconnu"),
    ("ambigu", "fr", "Donne-moi le numéro de téléphone du chef de village de Ndiaganiao", "inconnu"),
    ("ambigu", "fr", "Qui va gagner la prochaine élection présidentielle ?", "inconnu"),
    ("ambigu", "fr", "Écris un petit poème sur le baobab", "base"),
    ("ambigu", "fr", "Bonjour", "prete"),
    ("ambigu", "fr", "Qui es-tu ?", "prete"),
    ("ambigu", "en", "What can you do?", "prete"),
    ("ambigu", "fr", "C'est combien le kilo ?", "precis"),
]

_LINE = re.compile(r"latence route=chat (?P<rest>.*)")


def _block_network() -> None:
    """Comme tests/conftest.py : aucune connexion sortante, les appels externes échouent tout de suite."""

    def refuse(sock, address, *args, **kwargs):
        raise RuntimeError("réseau coupé pendant le banc")

    socket.socket.connect = refuse  # type: ignore[assignment]


def _fake_stream(text: str):
    yield SimpleNamespace(type="response.output_text.delta", delta=text)
    yield SimpleNamespace(type="response.completed", response=SimpleNamespace(
        status="completed", incomplete_details=None, output_text=text, output=[],
        usage=SimpleNamespace(input_tokens=0, output_tokens=0)))


def run() -> list[dict]:
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    for name in ("ANTHROPIC_API_KEY", "AI_PRINCIPALE"):
        os.environ.pop(name, None)  # routage OpenAI : le même pour tous, sans clé ni coût
    _block_network()
    import app as app_module
    from services.latency import LOGGER_NAME

    lines: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record):
            lines.append(record.getMessage())

    logging.getLogger(LOGGER_NAME).addHandler(Capture())
    calls: list[dict] = []

    def create(**kwargs):
        tools = kwargs.get("tools") or []
        calls.append({
            "model": kwargs.get("model"),
            "web_tool": any("web_search" in str(t.get("type", "")) for t in tools if isinstance(t, dict)),
            "input_chars": len(json.dumps(kwargs.get("input", ""), ensure_ascii=False)),
            "instructions_chars": len(str(kwargs.get("instructions") or "")),
            "max_output_tokens": kwargs.get("max_output_tokens"),
            "reasoning": (kwargs.get("reasoning") or {}).get("effort") if isinstance(kwargs.get("reasoning"), dict) else None,
        })
        text = "Réponse simulée du banc."
        if kwargs.get("stream"):
            return _fake_stream(text)
        return SimpleNamespace(status="completed", incomplete_details=None, output_text=text, output=[])

    app_module.client.responses.create = create
    results = []
    base = "https://teranga-ai.fr"
    for index, (theme, lang, question, expected) in enumerate(QUESTIONS, 1):
        client = app_module.app.test_client()
        token = client.get("/csrf", base_url=base).get_json()["token"]
        client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
        before_calls, before_lines = len(calls), len(lines)
        started = time.perf_counter()
        response = client.post(
            "/chat",
            json={"message": question, "language": lang, "history": [{"role": "user", "content": question}]},
            headers={"X-CSRF-Token": token, "Origin": base},
            base_url=base,
            environ_base={"REMOTE_ADDR": f"10.{index // 250}.{index % 250}.7"},
        )
        body = response.get_data(as_text=True)
        response.close()  # la ligne « latence » s'écrit à la fermeture de la réponse, comme sous Gunicorn
        elapsed_ms = (time.perf_counter() - started) * 1000
        events = [json.loads(line) for line in body.splitlines() if line.strip()]
        text = "".join(e.get("d", "") for e in events if isinstance(e, dict))
        fields = {}
        for line in lines[before_lines:]:
            match = _LINE.search(line)
            if match:
                fields = dict(pair.split("=", 1) for pair in match.group("rest").split() if "=" in pair)
        call = calls[before_calls] if len(calls) > before_calls else None
        if fields.get("pret") == "oui" or (call is None and text and "Réponse simulée" not in text):
            observed = "prete"
        elif call is None:
            observed = "aucune"
        elif call["web_tool"]:
            observed = "web"
        else:
            observed = "modele"
        results.append({
            "n": index, "theme": theme, "lang": lang, "question": question, "attendu": expected,
            "observe": observed, "http": response.status_code, "modele": (call or {}).get("model") or fields.get("modele"),
            "web_outil": bool(call and call["web_tool"]), "contexte_caracteres": (call or {}).get("input_chars"),
            "consignes_caracteres": (call or {}).get("instructions_chars"),
            "max_output_tokens": (call or {}).get("max_output_tokens"), "raisonnement": (call or {}).get("reasoning"),
            "contexte_ms": _number(fields.get("contexte_ms")), "total_ms_local": round(elapsed_ms, 1),
            "erreur": any("error" in e for e in events if isinstance(e, dict)),
        })
    return results


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _agrees(expected: str, observed: str) -> bool:
    if expected == "prete":
        return observed == "prete"
    if expected == "web":
        return observed == "web"
    if expected == "service":
        return observed in ("modele", "prete")  # météo : donnée du service dans le contexte, pas de recherche web
    return observed in ("modele", "prete")  # base, precis, inconnu : surtout pas de recherche web inutile


def summary(results: list[dict]) -> str:
    out = ["| Thème | Questions | Accord avec l'attendu | Prêtes | Outil web proposé | Modèle sans web | Contexte envoyé, médiane (caractères) | Préparation serveur, médiane (ms) |",
           "|---|---|---|---|---|---|---|---|"]
    by_theme = defaultdict(list)
    for row in results:
        by_theme[row["theme"]].append(row)
    for theme, rows in list(by_theme.items()) + [("TOTAL", results)]:
        counts = Counter(r["observe"] for r in rows)
        sizes = [r["contexte_caracteres"] + (r["consignes_caracteres"] or 0) for r in rows if r["contexte_caracteres"]]
        prep = [r["contexte_ms"] for r in rows if r["contexte_ms"] is not None]
        agree = sum(_agrees(r["attendu"], r["observe"]) for r in rows)
        out.append(f"| {theme} | {len(rows)} | {agree}/{len(rows)} | {counts['prete']} | {counts['web']} | {counts['modele']} | "
                   f"{int(statistics.median(sizes)) if sizes else '-'} | {round(statistics.median(prep), 1) if prep else '-'} |")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="fichier où écrire le détail des 100 questions")
    args = parser.parse_args()
    results = run()
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(summary(results))
    print()
    for row in results:
        if not _agrees(row["attendu"], row["observe"]):
            print(f"désaccord n°{row['n']} [{row['theme']}] attendu={row['attendu']} observé={row['observe']} : {row['question']}")


if __name__ == "__main__":
    main()
