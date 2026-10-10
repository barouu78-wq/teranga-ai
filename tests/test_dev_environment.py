"""Environnement de développement : les outils que AGENTS.md demande de lancer sont déclarés, et le contrôle
d'environnement distingue « peut tourner » de « absent » (un contrôle absent n'a pas réussi)."""

import os
import re
import runpy
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_dev_env.py"


def _requirement_names(filename):
    names = set()
    for line in (ROOT / filename).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            names.add(re.split(r"[<>=!~ ;\[]", line, maxsplit=1)[0].lower().replace("_", "-"))
    return names


def test_every_python_tool_of_the_pr_checklist_is_declared_in_requirements_dev():
    block = re.search(r"## Avant chaque PR.*?```bash\n(.*?)```", (ROOT / "AGENTS.md").read_text(encoding="utf-8"), re.S).group(1)
    commands = {line.split()[0] for line in block.splitlines() if line.strip() and not line.startswith(("#", "pip", "python"))}
    declared = _requirement_names("requirements-dev.txt")
    for tool, package in (("ruff", "ruff"), ("bandit", "bandit"), ("pytest", "pytest")):
        assert tool in commands, f"{tool} n'est plus dans la liste de contrôles d'AGENTS.md"
        assert package in declared, f"{package} manque dans requirements-dev.txt : `{tool}` serait introuvable"
    assert "pytest-cov" in declared  # --cov dans la commande de couverture


def test_e2e_requirements_add_playwright_on_top_of_the_dev_requirements():
    text = (ROOT / "requirements-e2e.txt").read_text(encoding="utf-8")
    assert "-r requirements-dev.txt" in text
    assert "playwright" in _requirement_names("requirements-e2e.txt")


def test_ci_uses_the_requirement_files_for_every_tool():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "pip install -r requirements-dev.txt" in workflow and "pip install -r requirements-e2e.txt" in workflow
    assert 'pip install "ruff' not in workflow and "pip install bandit" not in workflow  # plus de version en double
    assert 'E2E_REQUIRED: "1"' in workflow  # au CI, un navigateur manquant fait échouer


def test_check_script_reports_a_missing_tool_as_absent_and_fails():
    module = runpy.run_path(str(SCRIPT), run_name="check_dev_env")
    collect = module["collect"]
    original_which = module["shutil"].which
    try:
        module["shutil"].which = lambda name: None if name == "ruff" else original_which(name)
        rows = {label: (state, detail) for label, state, detail in collect()}
    finally:
        module["shutil"].which = original_which
    state, detail = rows["ruff"]
    assert state == "ABSENT" and "requirements-dev.txt" in detail


def test_check_script_exit_code_and_wording(monkeypatch, capsys):
    module = runpy.run_path(str(SCRIPT), run_name="check_dev_env")
    main = module["main"]
    monkeypatch.setitem(main.__globals__, "collect", lambda require_e2e=False: [
        ("ruff", "ABSENT", "commande `ruff` introuvable"), ("pytest", "OK", "installé"),
        ("e2e (Playwright + Chromium)", "NON VÉRIFIÉ", "tests/e2e seraient IGNORÉS"),
    ])
    assert main([]) == 1
    out = capsys.readouterr().out
    assert "ABSENT" in out and "n'ont PAS réussi" in out and "NON VÉRIFIÉ" in out
    monkeypatch.setitem(main.__globals__, "collect", lambda require_e2e=False: [("pytest", "OK", "installé")])
    assert main([]) == 0


def test_unrequested_e2e_is_never_reported_as_ok(monkeypatch):
    module = runpy.run_path(str(SCRIPT), run_name="check_dev_env")
    rows = {label: state for label, state, _ in module["collect"](require_e2e=False)}
    assert rows["e2e (Playwright + Chromium)"] == "NON VÉRIFIÉ"  # on ne l'a pas lancé : ni OK ni réussi


def test_e2e_fixture_still_fails_instead_of_skipping_when_required():
    source = (ROOT / "tests" / "e2e" / "conftest.py").read_text(encoding="utf-8")
    assert 'required = os.getenv("E2E_REQUIRED") == "1"' in source
    assert 'pytest.fail("Playwright non installé")' in source and 'pytest.skip("Playwright non installé")' in source
