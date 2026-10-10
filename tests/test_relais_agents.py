"""Relais automatique des agents : un échec de l'audit public ne doit ni se répéter par PR ni créer un ticket par exécution."""
import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / ".github" / "workflows" / "agent-handoff.yml"
AUDITS = ROOT / ".github" / "workflows" / "audits-seo-performance.yml"


def _load(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["triggers"] = data.get("on", data.get(True))  # PyYAML lit la clé « on » comme le booléen True
    return data


def test_public_site_probe_does_not_run_on_pull_requests_but_the_local_audit_does():
    workflow = _load(AUDITS)
    assert {"schedule", "workflow_dispatch", "pull_request"} <= set(workflow["triggers"])
    probe = workflow["jobs"]["performance-smoke"]
    assert probe["if"].strip() == "github.event_name != 'pull_request'"
    # L'audit SEO du code, lui, reste actif sur les PR : il dépend du code de la PR.
    assert "if" not in workflow["jobs"]["seo-audit"]


def test_handoff_ignores_failures_that_come_from_pull_requests():
    job = _load(HANDOFF)["jobs"]["triage-audit-failure"]
    condition = " ".join(str(job["if"]).split())
    assert "github.event.workflow_run.event != 'pull_request'" in condition
    assert "github.event.workflow_run.conclusion == 'failure'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition  # le déclenchement manuel reste possible


def test_handoff_uses_one_fixed_title_and_groups_new_failures_under_the_open_ticket():
    text = HANDOFF.read_text(encoding="utf-8")
    title = re.search(r'const title = (.+);', text).group(1)
    assert "runId" not in title and "${" not in title, "le titre ne doit plus contenir l'identifiant de l'exécution"
    assert "title.startsWith(title)" in text  # reconnaît aussi les anciens tickets « … — run <id> »
    assert "issues.createComment" in text and "issues.create(" in text


def test_handoff_script_is_valid_javascript(tmp_path):
    node = shutil.which("node")
    assert node, "node est requis pour vérifier la syntaxe du script du relais"
    step = next(s for s in _load(HANDOFF)["jobs"]["triage-audit-failure"]["steps"] if s.get("uses", "").startswith("actions/github-script"))
    wrapped = "async function relais(github, context, core) {\n" + step["with"]["script"] + "\n}\n"
    script = tmp_path / "relais.js"
    script.write_text(wrapped, encoding="utf-8")
    result = subprocess.run([node, "--check", str(script)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
