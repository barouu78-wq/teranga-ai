"""Rend une animation HTML (scripts/video/modeles/) en vidéo MP4, image par image.

Usage :
    python scripts/video/rendu.py scripts/video/modeles/clip-pub.html sortie.mp4 --duree 19 --ecrans dossier_captures

Le modèle peut contenir trois repères, remplacés au rendu :
    {{LION}}    le lion de Teranga (services/site_layout.LION_SVG) ;
    {{FONTS}}   le dossier des polices du site (static/fonts/) ;
    {{ECRANS}}  le dossier des captures faites par scripts/video/ecrans.py.

Les animations CSS sont mises en pause puis avancées image par image : le rendu est identique d'une fois sur l'autre,
quelle que soit la vitesse de la machine. Le format 9:16 (1080×1920) sert aux Reels et à TikTok ; 16:9 (1920×1080)
à YouTube et au site. Il faut Chromium (Playwright) et ffmpeg.
"""

import argparse
import os
import shutil
import subprocess  # nosec B404 - appel à ffmpeg avec une liste d'arguments, sans shell
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMATS = {"9x16": (540, 960), "16x9": (960, 540)}  # taille CSS ; rendu en ×2


def lion_svg() -> str:
    sys.path.insert(0, str(ROOT))
    from services.site_layout import LION_SVG

    return f'<svg viewBox="0 5 100 100" aria-hidden="true">{LION_SVG}</svg>'


def prepare(modele: Path, ecrans: Path | None, dossier: Path) -> Path:
    texte = modele.read_text(encoding="utf-8")
    texte = texte.replace("{{LION}}", lion_svg()).replace("{{FONTS}}", str(ROOT / "static" / "fonts") + "/")
    if "{{ECRANS}}" in texte:
        if not ecrans or not ecrans.is_dir():
            raise SystemExit("Ce modèle montre des écrans du site : lancez d'abord scripts/video/ecrans.py (--ecrans).")
        texte = texte.replace("{{ECRANS}}", str(ecrans.resolve()) + "/")
    page = dossier / "page.html"
    page.write_text(texte, encoding="utf-8")
    return page


def rendre(page: Path, images: Path, duree: float, fps: int, taille: tuple[int, int]) -> int:
    from playwright.sync_api import sync_playwright

    chromium = os.environ.get("CHROMIUM", "/opt/pw-browsers/chromium")
    with sync_playwright() as p:
        options = {"executable_path": chromium} if Path(chromium).exists() else {}
        navigateur = p.chromium.launch(**options)
        onglet = navigateur.new_page(viewport={"width": taille[0], "height": taille[1]}, device_scale_factor=2)
        onglet.goto(page.as_uri())
        onglet.evaluate("document.fonts.ready")
        onglet.wait_for_timeout(300)
        onglet.evaluate("document.getAnimations().forEach(a => a.pause())")
        total = int(duree * fps)
        for i in range(total):
            onglet.evaluate(f"document.getAnimations().forEach(a => {{ a.currentTime = {i * 1000 / fps}; }})")
            onglet.screenshot(path=str(images / f"{i:04d}.jpg"), type="jpeg", quality=92)
        navigateur.close()
    return total


def encoder(images: Path, sortie: Path, fps: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg est introuvable.")
    # H.264 « high », yuv420p et faststart : lisible sur iPhone, Android, Instagram et TikTok.
    subprocess.run(  # nosec B603 - arguments fixes, aucun texte venant d'un visiteur
        [ffmpeg, "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(images / "%04d.jpg"),
         "-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-crf", "20",
         "-movflags", "+faststart", str(sortie)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("modele", type=Path)
    parser.add_argument("sortie", type=Path)
    parser.add_argument("--duree", type=float, required=True, help="durée en secondes")
    parser.add_argument("--format", choices=sorted(FORMATS), default="9x16")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--ecrans", type=Path, help="dossier des captures (scripts/video/ecrans.py)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        images = dossier / "images"
        images.mkdir()
        page = prepare(args.modele, args.ecrans, dossier)
        n = rendre(page, images, args.duree, args.fps, FORMATS[args.format])
        encoder(images, args.sortie, args.fps)
    print(f"{args.sortie} : {n} images, {args.duree} s")


if __name__ == "__main__":
    main()
