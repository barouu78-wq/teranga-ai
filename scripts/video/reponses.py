"""Capture de vraies réponses du site local (réponses prêtes, sans IA) au format téléphone, pour les vidéos.

Lancer d'abord le site en local, sans vraie clé, en autorisant son adresse (sinon /chat répond 403) :
    OPENAI_API_KEY=test-key ALLOWED_ORIGINS="http://127.0.0.1:5055" python -c "from app import app; app.run(port=5055)"
puis :
    python scripts/video/reponses.py dossier_captures --theme dark \\
        --question reponse "C'est quoi le plat national ?" "Plat national"

Chaque --question donne un nom de capture, la question posée et un texte que la réponse doit contenir. Deux images par
question : <nom>.jpg (le fil remonté jusqu'à la question, pour voir le début de la réponse) et <nom>-bas.jpg (la fin).
Seules les réponses prêtes (services/quick_answers.py) arrivent en local : sans clé, le modèle ne répond pas, et on
n'invente jamais une réponse. Une question sans réponse prête s'arrête avec un message clair.
"""

import argparse
import os
import sys
from pathlib import Path

# Remonte le fil jusqu'à la bulle de la question, sous l'en-tête fixe.
_REMONTER = """(q) => {
    const bulles = [...document.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim() === q);
    const bulle = bulles[bulles.length - 1];
    if (!bulle) return false;
    bulle.scrollIntoView({block: 'start'});
    let el = bulle.parentElement;
    while (el && el !== document.body) {
        if (el.scrollHeight > el.clientHeight + 5 && getComputedStyle(el).overflowY !== 'visible') { el.scrollTop -= 110; break; }
        el = el.parentElement;
    }
    window.scrollBy(0, -110);
    return true;
}"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sortie", type=Path)
    parser.add_argument("--base", default="http://127.0.0.1:5055")
    parser.add_argument("--theme", choices=("light", "dark"), default="dark")
    parser.add_argument("--question", nargs=3, action="append", required=True, metavar=("NOM", "QUESTION", "ATTENDU"),
                        help="nom de la capture, question posée, texte que la réponse doit contenir")
    args = parser.parse_args()
    args.sortie.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import TimeoutError as Delai
    from playwright.sync_api import sync_playwright

    chromium = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium")
    with sync_playwright() as p:
        options = {"executable_path": chromium} if Path(chromium).exists() else {}
        navigateur = p.chromium.launch(**options)
        for nom, question, attendu in args.question:
            contexte = navigateur.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                                              is_mobile=True, has_touch=True)
            contexte.add_init_script(
                "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}"
                % args.theme)
            onglet = contexte.new_page()
            onglet.goto(args.base + "/", wait_until="load", timeout=15000)
            onglet.wait_for_timeout(600)
            onglet.fill("#heroInput", question)
            onglet.press("#heroInput", "Enter")
            try:
                # La réponse est arrivée quand le texte attendu suit la question dans le fil.
                onglet.wait_for_function(
                    "([q, t]) => { const txt = document.body.innerText; return txt.includes(q) && txt.split(q).pop().includes(t); }",
                    arg=[question, attendu], timeout=20000)
            except Delai:
                navigateur.close()
                sys.exit(f"« {question} » : pas de réponse prête contenant « {attendu} ». En local, sans clé, seules les "
                         "réponses prêtes répondent (services/quick_answers.py) : choisir une autre question.")
            onglet.wait_for_timeout(1500)
            onglet.screenshot(path=str(args.sortie / f"{nom}-bas.jpg"), type="jpeg", quality=92)
            onglet.evaluate(_REMONTER, question)
            onglet.wait_for_timeout(700)
            onglet.screenshot(path=str(args.sortie / f"{nom}.jpg"), type="jpeg", quality=92)
            print(f"{nom} : {args.sortie / (nom + '.jpg')}")
            contexte.close()
        navigateur.close()


if __name__ == "__main__":
    main()
