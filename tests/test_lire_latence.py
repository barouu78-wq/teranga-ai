"""scripts/lire_latence.py : médiane, p95 et nombre de requêtes par route, depuis des lignes de journal collées.

Les calculs sont comparés à des valeurs refaites à la main ; l'exemple de docs/MESURE-LATENCE.md est rejoué pour
que la documentation dise toujours ce que le script affiche ; enfin de vraies lignes écrites par l'application
passent par le script, ce qui casserait ce test si le format d'une ligne changeait sans lui.
"""

import contextlib
import io
import re
import runpy
from pathlib import Path

import pytest

import latence_harness as h

ROOT = Path(__file__).resolve().parents[1]
script = runpy.run_path(str(ROOT / "scripts" / "lire_latence.py"), run_name="lire_latence")
parse_line, median, percentile, summarize, read_records, main = (
    script[name] for name in ("parse_line", "median", "percentile", "summarize", "read_records", "main")
)


def chat(total, *, cache="non", statut="ok", extra=""):
    return f"latence route=chat total_ms={total} contexte_ms=5.0 recherche_ms=- premier_mot_ms={total} fournisseur_ms=1.0 cache={cache} web=non modele=m mode=flux statut={statut}{extra}"


def run(text, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err):
        code = main(list(args), stdin=io.StringIO(text), stdout=out)
    return code, out.getvalue(), err.getvalue()


# --- Lecture d'une ligne ------------------------------------------------------------------------------------


def test_a_latency_line_is_read_wherever_it_sits_in_the_log_line():
    base = chat("12.5")
    expected = {"route": "chat", "total_ms": "12.5", "contexte_ms": "5.0", "recherche_ms": "-", "premier_mot_ms": "12.5",
                "fournisseur_ms": "1.0", "cache": "non", "web": "non", "modele": "m", "mode": "flux", "statut": "ok"}
    assert parse_line(base) == expected
    assert parse_line("Oct 11 12:00:01 teranga-ai-1 " + base) == expected  # préfixe d'horodatage de Render
    assert parse_line('{"message":"' + base + '","level":"info"}') == expected  # export JSON
    assert parse_line("[2026-10-11 12:00:01] INFO " + base + "  ") == expected


@pytest.mark.parametrize("text", [
    "", "GET /chat 200", "la latence est basse", "latence route", "latence: route=chat", "http_request {\"status\": 200}",
])
def test_other_lines_are_ignored(text):
    assert parse_line(text) is None


# --- Calculs ---------------------------------------------------------------------------------------------------


def test_median_by_hand():
    assert median([5.0]) == 5.0
    assert median([3.0, 1.0, 2.0]) == 2.0
    assert median([4.0, 1.0, 3.0, 2.0]) == 2.5
    assert median([10.0, 10.0, 10.0, 1000.0]) == 10.0


def test_p95_is_the_value_at_rank_ceil_95_percent_of_n():
    assert percentile([7.0], 95) == 7.0
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 95) == 5.0  # ceil(4,75) = 5
    twenty = [float(i) for i in range(20, 0, -1)]
    assert percentile(twenty, 95) == 19.0  # 0,95 × 20 = 19 exactement : pas d'arrondi flottant vers 20
    hundred = [float(i) for i in range(1, 101)]
    assert percentile(hundred, 95) == 95.0
    assert percentile([float(i) for i in range(1, 101)] + [1000.0], 95) == 96.0  # n = 101 : ceil(95,95) = 96


# --- Résumé ----------------------------------------------------------------------------------------------------


def test_groups_statuses_and_dashes():
    lines = [chat("100.0"), chat("300.0"), chat("200.0"), chat("5000.0", statut="erreur"), chat("10.0", cache="oui"),
             "latence route=tts total_ms=50.0 fournisseur_ms=40.0 modele=x statut=ok",
             "latence route=stt total_ms=70.0 fournisseur_ms=- modele=- statut=invalide"]
    by_name = {item["groupe"]: item for item in summarize(read_records(lines))}
    assert set(by_name) == {"chat, cache=non", "chat, cache=oui", "tts", "stt"}
    miss = by_name["chat, cache=non"]
    assert (miss["lues"], miss["gardees"]) == (4, 3) and dict(miss["statuts"]) == {"ok": 3, "erreur": 1}
    assert miss["metriques"]["total_ms"] == {"n": 3, "mediane": 200.0, "p95": 300.0}  # l'erreur à 5000 est écartée
    assert "recherche_ms" not in miss["metriques"]  # que des « - » : pas de statistique inventée
    assert by_name["stt"]["gardees"] == 0 and by_name["stt"]["metriques"] == {}  # statut « invalide » écarté par défaut
    everything = {item["groupe"]: item for item in summarize(read_records(lines), keep_all=True)}
    assert everything["chat, cache=non"]["metriques"]["total_ms"]["n"] == 4
    assert everything["stt"]["metriques"]["total_ms"]["mediane"] == 70.0


def test_filters_keep_only_matching_lines():
    lines = [chat("100.0"), chat("900.0", extra=""), chat("50.0").replace("mode=flux", "mode=json")]
    flux = summarize(read_records(lines), filters={"mode": "flux"})[0]
    assert flux["lues"] == 2 and flux["metriques"]["total_ms"]["mediane"] == 500.0


def test_first_sound_of_the_voice_is_summarised_and_can_be_kept_alone_with_mode_flux():
    """Après le passage de la voix en flux : premier_son_ms est le temps que le visiteur attend avant d'entendre."""
    lines = [
        "latence route=tts total_ms=9000.0 fournisseur_ms=900.0 modele=x statut=ok premier_son_ms=900.0 mode=flux",
        "latence route=tts total_ms=7000.0 fournisseur_ms=700.0 modele=x statut=ok premier_son_ms=700.0 mode=flux",
        "latence route=tts total_ms=15300.0 fournisseur_ms=15200.0 modele=x statut=ok premier_son_ms=- mode=fichier",
        "latence route=tts total_ms=15000.0 fournisseur_ms=14900.0 modele=x statut=ok",  # ligne d'avant le changement
    ]
    everything = summarize(read_records(lines))[0]
    assert everything["metriques"]["premier_son_ms"] == {"n": 2, "mediane": 800.0, "p95": 900.0}
    flux = summarize(read_records(lines), filters={"mode": "flux"})[0]
    assert flux["lues"] == 2 and flux["metriques"]["total_ms"]["mediane"] == 8000.0
    _, out, _ = run("\n".join(lines), "--garder", "mode=flux")
    assert re.search(r"premier_son_ms\s+n=2\s+médiane=800\.0\s+p95=900\.0", out)


def test_command_line_prints_median_p95_and_counts_per_route():
    code, out, _ = run("\n".join([chat(f"{i}.0") for i in range(1, 21)] + ["bruit sans rapport"]))
    assert code == 0
    assert "Lignes « latence » lues : 20" in out
    assert "chat, cache=non : 20 requête(s) gardée(s) sur 20 (ok=20)" in out
    assert re.search(r"total_ms\s+n=20\s+médiane=10\.5\s+p95=19\.0", out)
    assert "Attention" not in out  # 20 requêtes : le p95 est assez fiable pour ne pas avertir


def test_command_line_warns_when_there_are_too_few_requests():
    _, out, _ = run(chat("10.0") + "\n")
    assert "moins de 20 requêtes" in out


def test_command_line_options_and_empty_input():
    text = chat("100.0") + "\n" + chat("200.0", statut="secours") + "\n"
    assert "secours=1" in run(text)[1] and "n=1 " in run(text)[1]
    assert "n=2 " in run(text, "--tout")[1] and "Statuts gardés : tous" in run(text, "--tout")[1]
    assert "Filtres : mode=json" in run(text, "--garder", "mode=json")[1]
    code, out, err = run("rien d'utile ici\n")
    assert code == 1 and out == "" and "Aucune ligne" in err
    with pytest.raises(SystemExit):
        run(text, "--garder", "sans_egal")


def test_a_pasted_log_with_invalid_bytes_still_reads_through_the_real_stdin(tmp_path):
    import subprocess
    import sys

    export = tmp_path / "export.txt"
    export.write_bytes(b"\xff\xfe bruit\n" + chat("10.0").encode() + b"\n")
    with export.open("rb") as handle:
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "lire_latence.py")], stdin=handle, capture_output=True, timeout=60, check=False)  # nosec B603
    assert done.returncode == 0 and "médiane=10.0".encode() in done.stdout


# --- La documentation dit ce que le script affiche ---------------------------------------------------------


def fenced(name):
    doc = (ROOT / "docs" / "MESURE-LATENCE.md").read_text(encoding="utf-8")
    found = re.search(rf"```{name}\n(.*?)```", doc, re.S)
    assert found, f"bloc {name} introuvable dans docs/MESURE-LATENCE.md"
    return found.group(1)


def test_the_example_of_the_documentation_is_exactly_what_the_script_prints():
    code, out, _ = run(fenced("latence-entree"))
    assert code == 0 and out == fenced("latence-sortie")


def test_the_documentation_sets_no_numeric_target():
    doc = (ROOT / "docs" / "MESURE-LATENCE.md").read_text(encoding="utf-8")
    assert "Aucun objectif chiffré n'est fixé ici" in doc and "après la première mesure réelle" in doc
    assert not re.search(r"objectif[^.\n]{0,40}\d+\s*(ms|s\b|secondes?)", doc, re.I)


# --- Vraies lignes de l'application -----------------------------------------------------------------------


def test_real_lines_written_by_the_application_go_through_the_script(monkeypatch):
    handler = h.capture_lines()
    try:
        h.install_provider(monkeypatch, events=[h.delta("Bonjour " * 12), h.completed("Bonjour " * 12)])
        for question in ("Parle-moi de la culture sérère.", "Que faire à Dakar ?", "Que faire à Thiès ?"):
            h.finish(h.post_chat(question))
        h.finish(h.post_chat("Parle-moi de la culture sérère."))  # même question : cache
        h.post_tts("Bonjour", monkeypatch=monkeypatch).close()
        lines = list(handler.lines)
    finally:
        h.release_lines(handler)
    code, out, _ = run("\n".join(lines))
    assert code == 0 and len(lines) == 5
    assert "chat, cache=non : 3 requête(s) gardée(s) sur 3 (ok=3)" in out
    assert "chat, cache=oui : 1 requête(s) gardée(s) sur 1 (ok=1)" in out
    assert "tts : 1 requête(s) gardée(s) sur 1 (ok=1)" in out
    assert re.search(r"premier_mot_ms\s+n=3", out) and re.search(r"fournisseur_ms\s+n=3", out)
