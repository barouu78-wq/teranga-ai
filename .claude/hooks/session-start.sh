#!/bin/bash
# Démarrage d'une session Claude Code dans le cloud : installe ce qu'il faut pour les contrôles d'AGENTS.md
# (pytest, couverture, Ruff, Bandit ; Playwright pour les tests e2e). Synchrone : la session attend la fin,
# pour que Claude ne lance jamais un test avant que les outils soient là.
set -euo pipefail

# Sur l'ordinateur du propriétaire, rien à faire : l'environnement est déjà le sien.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# Idempotent : pip ne réinstalle pas ce qui est déjà à la bonne version (l'état du conteneur est gardé en cache).
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements-dev.txt

# Playwright et Chromium sont préinstallés dans les sessions cloud, en versions accordées : ne jamais lancer
# « playwright install » ici (une autre version ne trouverait pas ce navigateur). Le paquet Python n'est
# installé que s'il manque.
if ! python3 -c "import playwright" >/dev/null 2>&1; then
  python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements-e2e.txt
fi

# Les tests n'appellent jamais OpenAI, mais deux fichiers importent l'application, qui exige une clé : la même
# fausse clé que le CI (AGENTS.md). Jamais à la place d'une vraie clé déjà fournie par l'environnement.
if [ -z "${OPENAI_API_KEY:-}" ] && [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export OPENAI_API_KEY=test-key' >> "$CLAUDE_ENV_FILE"
fi

# Ce qui peut réellement tourner ici (OK, ABSENT, NON VÉRIFIÉ), pour information : n'arrête jamais la session.
python3 scripts/check_dev_env.py --e2e || true
