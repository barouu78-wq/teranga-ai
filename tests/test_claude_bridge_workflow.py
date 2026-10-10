"""Pont GitHub -> Claude Code : garde-fous du workflow, vérifiés sans réseau ni dépendance YAML.

Ces tests ne prouvent PAS que le pont fonctionne (cela demande une exécution réelle, voir
docs/claude-github-bridge.md) : ils empêchent seulement qu'un garde-fou soit retiré par inadvertance.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "claude-bridge.yml").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "claude-github-bridge.md").read_text(encoding="utf-8")
ALLOWED_SECRETS = {"CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"}


def _allowed_tools():
    quoted = re.search(r'--allowedTools "([^"]+)"', WORKFLOW).group(1)
    return [tool.strip() for tool in quoted.split(",")]


def test_only_an_issue_comment_can_start_the_bridge():
    assert re.search(r"^on:\n  issue_comment:\n    types: \[created\]\n", WORKFLOW, re.M)
    for forbidden in ("pull_request_target", "workflow_run", "pull_request:", "push:", "schedule:", "workflow_dispatch"):
        assert forbidden not in WORKFLOW.split("jobs:")[0], forbidden


def test_default_permissions_are_read_only_and_the_job_asks_only_for_what_it_needs():
    assert re.search(r"^permissions:\n  contents: read\n", WORKFLOW, re.M)
    job = WORKFLOW.split("jobs:")[1]
    block = re.search(r"    permissions:\n((?:      .+\n)+)", job).group(1)
    granted = dict(line.split("#")[0].strip().split(": ") for line in block.splitlines())
    assert granted == {"contents": "write", "pull-requests": "write", "issues": "write", "id-token": "write", "actions": "read"}


def test_trigger_requires_the_owner_a_leading_command_and_an_owner_pull_request():
    condition = re.search(r"    if: >-\n((?:      .+\n)+)", WORKFLOW).group(1)
    flat = " ".join(condition.split())
    assert "github.event.comment.user.login == github.repository_owner" in flat
    assert "startsWith(github.event.comment.body, '/claude')" in flat  # début de commentaire, pas « contains »
    assert "contains(github.event.comment.body" not in flat
    assert "github.event.issue.pull_request == null || github.event.issue.user.login == github.repository_owner" in flat


def test_runs_are_serialized_per_conversation_and_bot_comments_cannot_evict_a_command():
    assert "cancel-in-progress: false" in WORKFLOW
    group = re.search(r"  group: (.+)\n", WORKFLOW).group(1)
    assert "github.event.issue.number" in group
    assert "startsWith(github.event.comment.body, '/claude')" in group and "github.run_id" in group


def test_the_job_has_a_timeout_and_a_turn_limit():
    assert re.search(r"timeout-minutes: \d+\n", WORKFLOW) and int(re.search(r"timeout-minutes: (\d+)", WORKFLOW).group(1)) <= 30
    assert re.search(r"--max-turns \d+", WORKFLOW)


def test_third_party_actions_are_pinned_to_a_full_commit():
    refs = re.findall(r"^\s+uses: ([\w./-]+)@(\S+)", WORKFLOW, re.M)
    assert {name for name, _ in refs} == {"actions/checkout", "actions/setup-python", "anthropics/claude-code-action"}
    for name, ref in refs:
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{name}@{ref} n'est pas épinglé par commit (tag mobile)"


def test_allowed_tools_cannot_reach_main_install_code_or_the_web():
    tools = _allowed_tools()
    joined = " ".join(tools)
    for forbidden in ("pip install", "git checkout", "git switch", "git push", "git reset", "git merge", "git rebase",
                      "WebFetch", "WebSearch", "curl", "wget", "sudo", "gh ", "rm "):
        assert forbidden not in joined, forbidden
    assert "Bash(git branch:*)" not in tools and "Bash(*)" not in tools and "Bash(:*)" not in tools  # git branch -f main HEAD
    assert "Edit" in tools and "Write" in tools and "Bash(git commit:*)" in tools


def test_the_hardcoded_push_script_path_is_gone_the_action_adds_its_own():
    assert "git-push.sh" not in WORKFLOW


def test_secrets_are_only_used_by_name_in_with_or_env_and_never_printed():
    names = set(re.findall(r"secrets\.([A-Z_]+)", WORKFLOW))
    assert names == ALLOWED_SECRETS
    for number, line in enumerate(WORKFLOW.splitlines(), 1):
        if "secrets." in line:
            assert "echo" not in line and "run:" not in line, f"ligne {number}: secret hors de with/env"
    assert 'HAS_OAUTH: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN != \'\' }}' in WORKFLOW  # booléen, jamais la valeur
    # un seul secret transmis à l'action : OAuth s'il existe, sinon la clé API
    assert "anthropic_api_key: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN == '' && secrets.ANTHROPIC_API_KEY || '' }}" in WORKFLOW


def test_a_missing_credential_fails_loudly_before_the_action_runs():
    step = WORKFLOW.split("name: Vérifier la méthode d'accès à Claude")[1].split("- name:")[0]
    assert "exit 1" in step and "::error" in step


def test_failures_are_reported_in_the_conversation_without_retriggering_the_bridge():
    step = WORKFLOW.split("name: Signaler l'échec dans la conversation")[1]
    assert "if: failure()" in step and "gh issue comment" in step
    assert "/claude" not in step  # le commentaire d'échec ne doit jamais relancer le pont
    assert "github.event.issue.number" in step and "${{ github.event.comment" not in step  # pas d'entrée libre dans le shell
    assert "20 tours" in step and "branche claude/" in step  # cause observée (error_max_turns) et risque de doublon


def test_system_prompt_forbids_main_workflows_and_untested_claims():
    prompt = re.search(r'--append-system-prompt "([^"]+)"', WORKFLOW).group(1)
    for phrase in ("ne pousse jamais sur main", ".github/workflows", "N'écris jamais de secret", "Ne désactive aucun test",
                   "Ne fusionne pas et ne déploie pas", "exécuté et réussi", "ignoré", "non exécuté"):
        assert phrase in prompt, phrase


def test_documentation_matches_the_workflow():
    for needle in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "facturée", "protection", "main", "37998631452",
                   "Non vérifié", "doublon", "error_max_turns", "claude/pr-394-20261010-0736", "38035381220"):
        assert needle in DOC, needle
    assert "Examiner et fusionner la PR qui ajoute" not in DOC  # étape périmée : le workflow est déjà sur main
