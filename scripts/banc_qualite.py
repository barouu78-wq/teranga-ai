"""Banc qualité Teranga AI : 50 questions (tests/banc_qualite/questions.json), 10 catégories, note sur 100.

Trois usages, du gratuit au payant :

  1. hors-ligne (gratuit, sans clé ni réseau, lancé aussi par pytest) :
       OPENAI_API_KEY=test-key python scripts/banc_qualite.py hors-ligne
     Vérifie que la base vérifiée du site fournit les faits attendus (contexte envoyé à l'IA ou réponse prête), et
     contrôle les réponses prêtes (sans IA) contre les attendus et les interdits. Ne juge PAS les réponses de l'IA.

  2. reel (PAYANT : 50 questions envoyées à la vraie IA ; compte dans AI_PLAFOND_JOUR si --site) :
       python scripts/banc_qualite.py reel --site https://teranga-ai.fr     # le site en ligne, au rythme permis
       python scripts/banc_qualite.py reel --local                          # ce code, avec les clés du propriétaire
     Écrit banc-qualite-<date>.md (réponses, contrôles automatiques, temps) et banc-qualite-<date>.csv (fiche de
     notation humaine, à remplir). À lancer seulement par le propriétaire, ou avec son accord écrit.

  3. noter (gratuit) : python scripts/banc_qualite.py noter banc-qualite-<date>.csv
     Calcule la moyenne sur 100 (par catégorie et globale) et compte les hallucinations graves, à partir de la fiche
     remplie par un humain. Objectif : 85/100 de moyenne et zéro hallucination grave.

Grille par réponse : exactitude 25, compréhension 20, contexte Sénégal 20, utilité concrète 20, clarté 15.
Ce qui est automatique : faits attendus présents, affirmations interdites absentes (expressions régulières). Ce qui
demande un humain : les cinq notes, et la confirmation de chaque hallucination grave signalée par la machine.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_FILE = ROOT / "tests" / "banc_qualite" / "questions.json"
GRILLE = (("exactitude", 25), ("comprehension", 20), ("contexte_senegal", 20), ("utilite", 20), ("clarte", 15))
OBJECTIF = 85
# Limites du site (app.py) : 16 messages par minute et 120 par heure et par visiteur. 6 s entre deux questions
# reste sous la limite par minute ; 50 questions tiennent dans l'heure.
PAUSE_SITE = 6.0


def load(path: Path = QUESTIONS_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def body(question: dict) -> dict:
    data = {"message": question["question"], "language": question["langue"]}
    if question.get("historique"):
        data["history"] = question["historique"]
    return data


def check_answer(question: dict, answer: str) -> dict:
    """Contrôles automatiques d'une réponse : attendus manquants, interdits trouvés, hallucination grave probable."""
    missing = [p for p in question.get("attendus", []) if not re.search(p, answer, re.I)]
    found = [p for p in question.get("interdits", []) if re.search(p, answer, re.I)]
    return {"attendus_manquants": missing, "interdits_trouves": found,
            "hallucination_grave_auto": bool(found and question.get("critique"))}


# ---------------------------------------------------------------- hors ligne

def offline_material(app_module, question: dict) -> tuple[str, str]:
    """(contexte envoyé à l'IA, réponse prête éventuelle) pour cette question, sans IA ni réseau."""
    from services.quick_answers import quick_answer

    data = body(question)
    with app_module.app.test_request_context("/chat", method="POST", json=data):
        payload, error = app_module.parse_chat_payload()
        if error:
            return "", ""
        ready = quick_answer(payload, data) or {}
    context = "\n".join(str(payload.get(key) or "") for key in ("instructions", "input_text"))
    return context, str(ready.get("reply") or "")


def run_offline(app_module, data: dict) -> list[dict]:
    rows = []
    for question in data["questions"]:
        context, ready = offline_material(app_module, question)
        material = context + "\n" + ready
        row = {"id": question["id"], "question": question["question"], "pret": bool(ready),
               "contexte_manquant": [fact for fact in question.get("contexte", []) if fact not in material]}
        if ready:
            row.update(check_answer(question, ready))
        rows.append(row)
    return rows


def offline_report(rows: list[dict]) -> str:
    lines = ["Banc qualité, mode hors ligne (base vérifiée du site, sans IA) :"]
    for row in rows:
        flags = []
        if row["contexte_manquant"]:
            flags.append("fait absent du contexte : " + ", ".join(row["contexte_manquant"]))
        if row.get("attendus_manquants"):
            flags.append("réponse prête sans : " + ", ".join(row["attendus_manquants"]))
        if row.get("interdits_trouves"):
            flags.append("INTERDIT dans la réponse prête : " + ", ".join(row["interdits_trouves"]))
        status = "OK " if not flags else "KO "
        lines.append(f"{status} {row['id']:13} {'prête' if row['pret'] else 'IA   '}  {row['question']}"
                     + ("".join(f"\n      - {f}" for f in flags)))
    bad = sum(1 for row in rows if row["contexte_manquant"] or row.get("attendus_manquants") or row.get("interdits_trouves"))
    lines.append(f"\n{len(rows) - bad}/{len(rows)} questions sans défaut détecté hors ligne. "
                 "Les réponses de l'IA ne sont pas jugées ici (mode reel + fiche humaine).")
    return "\n".join(lines)


# ---------------------------------------------------------------- réel

def _read_stream(lines) -> tuple[str, dict]:
    """Texte et signaux d'un flux NDJSON de /chat ({"d": …}, {"st": "web"}, {"degraded": …}, {"error": …})."""
    text, info = [], {"web": False, "degraded": False, "error": ""}
    for raw in lines:
        raw = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            text.append(str(event.get("d") or ""))
            info["web"] |= event.get("st") == "web"
            info["degraded"] |= bool(event.get("degraded"))
            info["error"] = info["error"] or str(event.get("error") or "")
    return "".join(text), info


def ask_site(site: str, question: dict, opener) -> dict:
    """Une question au site en ligne, comme un navigateur : jeton CSRF, puis POST /chat en flux."""
    from urllib.request import Request

    site = site.rstrip("/")
    headers = {"User-Agent": "TerangaBancQualite/1 (banc du propriétaire)", "Accept": "application/json"}
    with opener.open(Request(site + "/csrf", headers=headers), timeout=30) as resp:  # nosec B310 - site choisi par le propriétaire
        token = json.loads(resp.read().decode("utf-8"))["token"]
    request = Request(site + "/chat", data=json.dumps(body(question)).encode("utf-8"), method="POST", headers={
        **headers, "Content-Type": "application/json", "Origin": site, "Referer": site + "/", "X-CSRF-Token": token})
    started = time.perf_counter()
    first = None
    chunks = []
    with opener.open(request, timeout=120) as resp:  # nosec B310 - site choisi par le propriétaire
        for line in resp:
            if first is None and b'"d"' in line:
                first = time.perf_counter() - started
            chunks.append(line)
    text, info = _read_stream(chunks)
    return {"texte": text, "premier_mot_s": first, "total_s": time.perf_counter() - started, **info}


def ask_local(app_module, question: dict, index: int) -> dict:
    """Une question à ce code (clés réelles dans l'environnement), par la vraie route /chat."""
    client = app_module.app.test_client()
    address = f"198.51.100.{index % 250 + 1}"  # une adresse par question : la limite de débit ne fausse pas le banc
    token = client.get("/csrf", environ_base={"REMOTE_ADDR": address}).get_json()["token"]
    started = time.perf_counter()
    response = client.post("/chat", json=body(question), buffered=False, environ_base={"REMOTE_ADDR": address},
                           headers={"Origin": app_module.SITE_URL, "X-CSRF-Token": token})
    first = None
    chunks = []
    for line in response.response:
        if first is None and b'"d"' in (line if isinstance(line, bytes) else line.encode()):
            first = time.perf_counter() - started
        chunks.append(line)
    text, info = _read_stream(chunks)
    if response.status_code != 200 and not text:
        info["error"] = info["error"] or f"HTTP {response.status_code}"
    return {"texte": text, "premier_mot_s": first, "total_s": time.perf_counter() - started, **info}


def run_real(data: dict, site: str = "", limit: int = 0) -> list[dict]:
    questions = data["questions"][: limit or None]
    rows = []
    if site:
        from http.cookiejar import CookieJar
        from urllib.request import HTTPCookieProcessor, build_opener

        opener = build_opener(HTTPCookieProcessor(CookieJar()))
    else:
        import app as app_module
    for index, question in enumerate(questions, 1):
        print(f"[{index}/{len(questions)}] {question['id']} {question['question']}", flush=True)
        try:
            result = ask_site(site, question, opener) if site else ask_local(app_module, question, index)
        except Exception as exc:  # noqa: BLE001 - on note l'échec et on continue
            result = {"texte": "", "premier_mot_s": None, "total_s": 0.0, "web": False, "degraded": False,
                      "error": f"{type(exc).__name__}"}
        rows.append({**question, **result, **check_answer(question, result["texte"])})
        if site and index < len(questions):
            time.sleep(PAUSE_SITE)
    return rows


def _seconds(value) -> str:
    return "—" if value is None else f"{value:.1f} s"


def real_report(rows: list[dict], source: str, categories: dict) -> str:
    graves = [r for r in rows if r["hallucination_grave_auto"]]
    lines = [f"# Banc qualité Teranga AI — {dt.date.today().isoformat()}", "",
             f"Source des réponses : {source}. {len(rows)} questions.", "",
             "Contrôles automatiques seulement : la note sur 100 vient de la fiche humaine (`noter`).", "",
             "| | Valeur |", "|---|---|",
             f"| Réponses en échec ou vides | {sum(1 for r in rows if r['error'] or not r['texte'])} |",
             f"| Réponses dégradées (secours sans IA) | {sum(1 for r in rows if r['degraded'])} |",
             f"| Recherche web utilisée | {sum(1 for r in rows if r['web'])} |",
             f"| Questions avec un attendu manquant | {sum(1 for r in rows if r['attendus_manquants'])} |",
             f"| Hallucinations graves probables (interdit trouvé, question critique) | {len(graves)} |"]
    firsts = sorted(r["premier_mot_s"] for r in rows if r["premier_mot_s"] is not None)
    totals = sorted(r["total_s"] for r in rows if r["texte"])
    if firsts:
        lines.append(f"| Premier mot (médiane, sur ce banc) | {firsts[len(firsts) // 2]:.1f} s |")
    if totals:
        lines.append(f"| Réponse complète (médiane, sur ce banc) | {totals[len(totals) // 2]:.1f} s |")
    lines.append("")
    for row in rows:
        lines += [f"## {row['id']} · {categories.get(row['categorie'], row['categorie'])}"
                  + (" · critique" if row.get("critique") else ""), "",
                  f"**Question ({row['langue']}) :** {row['question']}", ""]
        if row.get("historique"):
            lines += ["Historique : " + " / ".join(f"{t['role']} : {t['content']}" for t in row["historique"]), ""]
        lines += [f"Premier mot : {_seconds(row['premier_mot_s'])} · total : {_seconds(row['total_s'])}"
                  + (" · recherche web" if row["web"] else "") + (" · DÉGRADÉE" if row["degraded"] else "")
                  + (f" · ERREUR {row['error']}" if row["error"] else ""), ""]
        lines += ["> " + line if line else ">" for line in (row["texte"] or "(aucune réponse)").splitlines()]
        lines.append("")
        if row["attendus_manquants"]:
            lines.append("- Attendu manquant : " + ", ".join(f"`{p}`" for p in row["attendus_manquants"]))
        if row["interdits_trouves"]:
            lines.append("- **Interdit trouvé** : " + ", ".join(f"`{p}`" for p in row["interdits_trouves"]))
        lines += [f"- Repère pour la notation : {row.get('note', '')}", ""]
    return "\n".join(lines) + "\n"


def write_sheet(rows: list[dict], path: Path) -> None:
    """Fiche de notation (séparateur « ; » pour Excel en français). Les notes sont laissées vides : à un humain."""
    columns = ["id", "categorie", "critique", "question", "reponse", "attendus_manquants", "interdits_trouves"] + [
        f"{name}_{points}" for name, points in GRILLE] + ["hallucination_grave", "commentaire"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row["id"], row["categorie"], "oui" if row.get("critique") else "non", row["question"],
                             row["texte"], " | ".join(row["attendus_manquants"]), " | ".join(row["interdits_trouves"])]
                            + [""] * len(GRILLE)
                            + ["oui (auto, à confirmer)" if row["hallucination_grave_auto"] else "", ""])


# ---------------------------------------------------------------- notation

def score_sheet(path: Path) -> dict:
    """Moyennes à partir d'une fiche remplie. Une ligne sans ses cinq notes est « non notée » et exclue (jamais 0)."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    scored, unscored, errors, graves = [], [], [], []
    for row in rows:
        values = []
        for name, points in GRILLE:
            raw = str(row.get(f"{name}_{points}", "") or "").strip().replace(",", ".")
            if not raw:
                values = None
                break
            try:
                value = float(raw)
            except ValueError:
                errors.append(f"{row['id']} : « {raw} » n'est pas un nombre ({name})")
                values = None
                break
            if not 0 <= value <= points:
                errors.append(f"{row['id']} : {name} = {raw} hors de 0 à {points}")
                values = None
                break
            values.append(value)
        if str(row.get("hallucination_grave", "")).strip().lower() == "oui":
            graves.append(row["id"])
        if values is None:
            unscored.append(row["id"])
        else:
            scored.append((row["id"], row["categorie"], sum(values)))
    by_category: dict[str, list[float]] = {}
    for _id, category, total in scored:
        by_category.setdefault(category, []).append(total)
    mean = sum(t for *_x, t in scored) / len(scored) if scored else None
    return {
        "notees": len(scored), "non_notees": unscored, "erreurs": errors, "hallucinations_graves": graves,
        "moyenne": mean, "par_categorie": {c: sum(v) / len(v) for c, v in sorted(by_category.items())},
        "objectif_atteint": bool(mean is not None and mean >= OBJECTIF and not graves and not unscored and not errors),
    }


def score_report(result: dict, categories: dict) -> str:
    lines = [f"Questions notées : {result['notees']}"]
    if result["non_notees"]:
        lines.append(f"Non notées (exclues, pas comptées 0) : {', '.join(result['non_notees'])}")
    for error in result["erreurs"]:
        lines.append(f"Erreur de saisie : {error}")
    for category, mean in result["par_categorie"].items():
        lines.append(f"  {categories.get(category, category):35} {mean:5.1f} / 100")
    if result["moyenne"] is not None:
        lines.append(f"Moyenne : {result['moyenne']:.1f} / 100 (objectif {OBJECTIF})")
    lines.append(f"Hallucinations graves confirmées : {len(result['hallucinations_graves'])}"
                 + (f" ({', '.join(result['hallucinations_graves'])})" if result["hallucinations_graves"] else ""))
    lines.append("Objectif atteint (≥ 85, zéro hallucination grave, tout noté) : "
                 + ("oui" if result["objectif_atteint"] else "non"))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("hors-ligne", help="gratuit : base vérifiée et réponses prêtes, sans IA ni réseau")
    real = sub.add_parser("reel", help="PAYANT : vraies réponses de l'IA")
    where = real.add_mutually_exclusive_group(required=True)
    where.add_argument("--site", help="adresse du site, par exemple https://teranga-ai.fr")
    where.add_argument("--local", action="store_true", help="ce code, avec les clés de l'environnement")
    real.add_argument("--limite", type=int, default=0, help="nombre de questions (0 = toutes)")
    real.add_argument("--sortie", default="", help="préfixe des fichiers (défaut : banc-qualite-<date>)")
    note = sub.add_parser("noter", help="moyenne sur 100 à partir de la fiche remplie")
    note.add_argument("fiche")
    args = parser.parse_args(argv)
    data = load()

    if args.mode == "hors-ligne":
        sys.path.insert(0, str(ROOT))
        import app as app_module

        rows = run_offline(app_module, data)
        print(offline_report(rows))
        return 0 if all(not (r["contexte_manquant"] or r.get("attendus_manquants") or r.get("interdits_trouves"))
                        for r in rows) else 1
    if args.mode == "noter":
        result = score_sheet(Path(args.fiche))
        print(score_report(result, data["categories"]))
        return 0 if result["objectif_atteint"] else 1

    if args.local:
        sys.path.insert(0, str(ROOT))
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
            raise SystemExit("Mode --local : il faut les clés de l'IA dans l'environnement (jamais dans un fichier).")
    rows = run_real(data, site=args.site or "", limit=args.limite)
    prefix = args.sortie or f"banc-qualite-{dt.date.today().isoformat()}"
    source = args.site or "code local (route /chat)"
    Path(prefix + ".md").write_text(real_report(rows, source, data["categories"]), encoding="utf-8")
    write_sheet(rows, Path(prefix + ".csv"))
    print(f"\nRapport : {prefix}.md ; fiche de notation à remplir : {prefix}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
