"""Pont ChatGPT ↔ Claude Code : le formulaire de relais et le protocole écrit restent cohérents et sans danger."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "relais-agent.yml"
DOC = ROOT / "docs" / "pont-chatgpt-claude.md"
BRIDGE_DOC = ROOT / "docs" / "claude-github-bridge.md"


def _form():
    return yaml.safe_load(FORM.read_text(encoding="utf-8"))


def test_issue_form_is_a_valid_github_issue_form():
    form = _form()
    assert form["name"] and form["description"] and form["body"]
    fields = [item for item in form["body"] if item["type"] != "markdown"]
    ids = [item["id"] for item in fields]
    assert len(ids) == len(set(ids)), "identifiants en double"
    for item in fields:
        assert item["attributes"]["label"].strip()
        assert item["type"] in {"input", "textarea", "dropdown", "checkboxes"}
    # Les champs qui rendent une tâche exploitable par l'autre agent sont obligatoires.
    required = {item["id"] for item in fields if (item.get("validations") or {}).get("required")}
    assert {"de", "pour", "objectif", "contexte", "resultat"} <= required


def test_issue_form_forces_the_two_safety_rules_and_cannot_launch_a_run():
    fields = {item["id"]: item for item in _form()["body"] if "id" in item}
    options = fields["regles"]["attributes"]["options"]
    assert len(options) == 2 and all(option["required"] for option in options)
    text = " ".join(option["label"] for option in options).lower()
    assert "secret" in text and "fusion" in text and "déploiement" in text
    # Rien dans le formulaire ne commence par la commande du pont : créer un ticket ne lance aucun run payant.
    assert not re.search(r"^/claude", FORM.read_text(encoding="utf-8"), re.M)
    assert "labels" not in _form()  # une étiquette absente du dépôt serait ignorée : on n'en déclare pas


def test_protocol_has_roles_both_directions_formats_and_continuity():
    doc = DOC.read_text(encoding="utf-8")
    for needle in ("## Qui fait quoi", "## ChatGPT → Claude Code", "## Claude Code → ChatGPT", "## Format commun d'une tâche",
                   "## Format commun d'un rapport", "## Règles communes", "## Continuité", "## À coller dans les instructions de ChatGPT",
                   "## Ce qui n'est pas vérifié", "#387", "confirmé", "probable", "non vérifié",
                   "exécuté et réussi", "branche ou une PR"):
        assert needle in doc, needle
    # Honnêteté : le protocole dit lui-même ce qu'il n'est pas.
    assert "N'est pas" in doc and "temps réel" in doc


def test_protocol_never_contains_the_bridge_command_or_a_secret():
    doc = DOC.read_text(encoding="utf-8")
    # Une ligne qui commencerait par la commande du pont lancerait un run facturé si on la collait en commentaire.
    assert not re.search(r"^\s*/claude", doc, re.M)
    assert not re.search(r"sk-(ant-)?[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY", doc)
    assert "ne jamais commencer un rapport par la commande du pont" in doc.lower()


def test_protocol_links_point_to_files_that_exist():
    doc = DOC.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", doc)
    assert links, "le protocole doit renvoyer vers les documents existants"
    for link in links:
        if link.startswith("http"):
            continue
        assert (DOC.parent / link).resolve().exists(), link


def test_bridge_doc_states_that_the_api_key_is_already_configured():
    text = BRIDGE_DOC.read_text(encoding="utf-8")
    assert "déjà configuré" in text and "limite de dépense" in text
