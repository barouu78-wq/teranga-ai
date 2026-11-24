"""Capture les vrais écrans du site au format téléphone, pour les vidéos (scripts/video/rendu.py).

Lancer d'abord le site en local, sans vraie clé :
    OPENAI_API_KEY=test-key python -c "from app import app; app.run(port=5055)"
puis :
    python scripts/video/ecrans.py dossier_captures --theme light

Les captures portent le nom attendu par les modèles : accueil, voyage, lieux, fetes, urgences.
Aucune réponse de l'IA n'est capturée : en local, sans clé, elle n'existe pas, et on n'en invente pas.
"""

import argparse
import os
from pathlib import Path

PAGES = {"accueil": "/", "voyage": "/trip-planner", "lieux": "/lieux", "fetes": "/calendrier-fetes-senegal",
         "urgences": "/urgences"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sortie", type=Path)
    parser.add_argument("--base", default="http://127.0.0.1:5055")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()
    args.sortie.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    chromium = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium")
    with sync_playwright() as p:
        options = {"executable_path": chromium} if Path(chromium).exists() else {}
        navigateur = p.chromium.launch(**options)
        contexte = navigateur.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                                          is_mobile=True, has_touch=True)
        contexte.add_init_script(
            "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}"
            % args.theme)
        onglet = contexte.new_page()
        for nom, chemin in PAGES.items():
            onglet.goto(args.base + chemin, wait_until="load", timeout=15000)
            onglet.wait_for_timeout(900)
            onglet.screenshot(path=str(args.sortie / f"{nom}.jpg"), type="jpeg", quality=90)
            print(nom)
        navigateur.close()


if __name__ == "__main__":
    main()
