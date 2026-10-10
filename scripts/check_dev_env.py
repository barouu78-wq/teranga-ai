"""Dit quels contrôles du projet peuvent réellement tourner dans cet environnement.

    python scripts/check_dev_env.py          # Python, pytest, couverture, Ruff, Bandit, Node
    python scripts/check_dev_env.py --e2e    # exige aussi Playwright et Chromium

Chaque ligne est « OK » (le contrôle peut tourner) ou « ABSENT » (il ne tournera pas : il n'a donc
PAS réussi, il n'a pas été exécuté). Le code de sortie est 1 s'il manque un outil exigé. Sans
--e2e, l'absence de Playwright est signalée « NON VÉRIFIÉ » : les tests e2e seraient ignorés
(skipped), jamais réussis.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 11)
INSTALL = "pip install -r requirements-dev.txt"
INSTALL_E2E = "pip install -r requirements-e2e.txt && python -m playwright install --with-deps chromium"


def _version(command: list[str]) -> str | None:
    """Numéro de version renvoyé par `<commande> --version`, ou None si l'outil est introuvable ou en erreur."""
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)  # nosec B603 - commandes fixes
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    found = re.search(r"\d+\.\d+(?:\.\d+)?", (done.stdout or "") + (done.stderr or ""))
    return found.group(0) if found else "version inconnue"


def chromium_launches() -> tuple[bool, str]:
    """Lance vraiment Chromium en mode headless : « Playwright installé » ne suffit pas pour que les e2e tournent."""
    try:
        from playwright import sync_api
    except ImportError:
        return False, "Playwright n'est pas installé"
    try:
        options = {}
        local = "/opt/pw-browsers/chromium"  # même règle que tests/e2e/conftest.py
        if os.path.exists(local) and not os.getenv("CI"):
            options["executable_path"] = local
        with sync_api.sync_playwright() as playwright:
            playwright.chromium.launch(**options).close()
    except Exception as exc:  # noqa: BLE001 - toute erreur de lancement signifie « navigateur indisponible »
        return False, f"Chromium ne démarre pas : {str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__}"
    return True, "Chromium démarre"


def collect(require_e2e: bool = False) -> list[tuple[str, str, str]]:
    """[(contrôle, état, détail)] avec état parmi OK, ABSENT, NON VÉRIFIÉ."""
    rows: list[tuple[str, str, str]] = []
    current = ".".join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info[:2] >= MIN_PYTHON
    rows.append(("python", "OK" if ok else "ABSENT", f"{current} (minimum {MIN_PYTHON[0]}.{MIN_PYTHON[1]}, CI en 3.12)"))
    for module, label in (("pytest", "pytest"), ("pytest_cov", "couverture (pytest-cov)")):
        found = importlib.util.find_spec(module) is not None
        rows.append((label, "OK" if found else "ABSENT", "installé" if found else INSTALL))
    for tool in ("ruff", "bandit"):  # les commandes documentées dans AGENTS.md sont `ruff` et `bandit`
        path = shutil.which(tool)
        version = _version([path, "--version"]) if path else None
        rows.append((tool, "OK" if version else "ABSENT", f"{tool} {version}" if version else f"commande `{tool}` introuvable : {INSTALL}"))
    node = shutil.which("node")
    node_version = _version([node, "--version"]) if node else None
    rows.append(("node (node --check)", "OK" if node_version else "ABSENT", f"node {node_version}" if node_version else "installer Node.js"))
    if require_e2e:
        launched, detail = chromium_launches()
        rows.append(("e2e (Playwright + Chromium)", "OK" if launched else "ABSENT", detail if launched else f"{detail} : {INSTALL_E2E}"))
    elif importlib.util.find_spec("playwright") is None:
        rows.append(("e2e (Playwright + Chromium)", "NON VÉRIFIÉ", f"tests/e2e seraient IGNORÉS (skipped), pas réussis : {INSTALL_E2E}"))
    else:
        rows.append(("e2e (Playwright + Chromium)", "NON VÉRIFIÉ", "Playwright installé ; lancer avec --e2e pour tester le démarrage de Chromium"))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--e2e", action="store_true", help="exige Playwright et Chromium")
    args = parser.parse_args(argv)
    rows = collect(require_e2e=args.e2e)
    width = max(len(label) for label, _, _ in rows)
    for label, state, detail in rows:
        print(f"{state:<12} {label:<{width}}  {detail}")
    missing = [label for label, state, _ in rows if state == "ABSENT"]
    if missing:
        print(f"\n{len(missing)} contrôle(s) ne peuvent pas tourner : {', '.join(missing)}. Ils n'ont PAS réussi : ils n'ont pas été exécutés.")
        return 1
    print("\nLes contrôles exigés peuvent tourner. « NON VÉRIFIÉ » veut dire non exécuté : ne pas l'annoncer comme réussi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
