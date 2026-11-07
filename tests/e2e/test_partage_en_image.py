"""V5, étape 3 « faire venir les gens » : partager une réponse en image (Go V5 du propriétaire, maquette « Partager en
image »).

Sous chaque réponse, « Partager en image » ouvre une fenêtre avec l'aperçu d'une image au format statut (1080 × 1920)
dessinée dans le téléphone : la question, la réponse (coupée proprement si elle est longue) et teranga-ai.fr. Trois
fonds au choix (Nuit dorée, Vert, Sable). « Partager » ouvre le menu de partage du téléphone avec le fichier PNG
(WhatsApp, TikTok, Instagram…) ; « Enregistrer l'image » le télécharge. Rien n'est envoyé au serveur.
"""

import json

PHONE = {"width": 390, "height": 844}

# Pixel du coin de l'image : la couleur du fond choisi.
PIXEL = """async () => {
  const img = document.querySelector('#shareImgPreview');
  if (!img.complete || !img.naturalWidth) await new Promise((ok) => img.addEventListener('load', ok, {once: true}));
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0);
  return {w: img.naturalWidth, h: img.naturalHeight, rgb: Array.from(ctx.getImageData(8, 8, 1, 1).data.slice(0, 3))};
}"""


def _repondre(page, base_url, texte):
    page.route(f"{base_url}/chat", lambda r: r.fulfill(body=json.dumps({"d": texte}) + "\n",
                                                       content_type="application/x-ndjson"))


def _reponse(page, base_url, texte="Le ceebu jën est le plat national du Sénégal.", chemin="/"):
    page.set_viewport_size(PHONE)
    page.add_init_script("localStorage.setItem('teranga-voice', '0')")
    _repondre(page, base_url, texte)
    page.goto(base_url + chemin)
    page.fill("#heroInput", "C'est quoi le ceebu jën ?")
    page.click("#heroSend")
    page.get_by_text(texte[:30]).wait_for(timeout=5000)


def _proche(rgb, attendu, marge=6):
    return all(abs(a - b) <= marge for a, b in zip(rgb, attendu))


def test_l_image_au_format_statut_change_de_fond(page, base_url):
    _reponse(page, base_url)
    bouton = page.get_by_role("button", name="Partager en image")
    assert bouton.bounding_box()["height"] >= 44
    bouton.click()
    fenetre = page.get_by_role("dialog", name="Partager en image")
    fenetre.wait_for(timeout=5000)
    image = page.evaluate(PIXEL)
    assert (image["w"], image["h"]) == (1080, 1920)
    assert _proche(image["rgb"], (11, 13, 16)), image  # Nuit dorée par défaut
    fenetre.get_by_role("button", name="Vert").click()
    page.wait_for_function("() => document.querySelector('#shareImgPreview').dataset.fond === 'vert'")
    assert _proche(page.evaluate(PIXEL)["rgb"], (15, 106, 67))
    fenetre.get_by_role("button", name="Sable").click()
    page.wait_for_function("() => document.querySelector('#shareImgPreview').dataset.fond === 'sable'")
    assert _proche(page.evaluate(PIXEL)["rgb"], (251, 248, 241))
    assert fenetre.get_by_role("button", name="Sable").get_attribute("aria-pressed") == "true"
    assert page.errors == []


def test_partager_donne_le_fichier_png_au_menu_du_telephone(page, base_url):
    page.add_init_script("""
      navigator.canShare = () => true;
      navigator.share = (d) => { window.__partage = {n: d.files.length, type: d.files[0].type, nom: d.files[0].name,
                                                     taille: d.files[0].size, texte: d.text || ''}; return Promise.resolve(); };
    """)
    _reponse(page, base_url)
    page.get_by_role("button", name="Partager en image").click()
    fenetre = page.get_by_role("dialog", name="Partager en image")
    fenetre.get_by_role("button", name="Partager", exact=True).click()
    page.wait_for_function("() => window.__partage")
    partage = page.evaluate("window.__partage")
    assert partage["n"] == 1 and partage["type"] == "image/png" and partage["nom"] == "teranga-ai.png"
    assert partage["taille"] > 20000
    assert "teranga-ai.fr" in partage["texte"]
    assert page.errors == []


def test_enregistrer_telecharge_l_image(page, base_url):
    _reponse(page, base_url)
    page.get_by_role("button", name="Partager en image").click()
    with page.expect_download() as telechargement:
        page.get_by_role("dialog", name="Partager en image").get_by_role("button", name="Enregistrer l'image").click()
    assert telechargement.value.suggested_filename == "teranga-ai.png"
    assert page.errors == []


def test_une_longue_reponse_est_coupee_sans_erreur_et_echap_ferme(page, base_url):
    longue = "Le thiéboudienne se prépare avec du riz, du poisson et des légumes. " * 60
    _reponse(page, base_url, longue)
    bouton = page.get_by_role("button", name="Partager en image")
    bouton.click()
    fenetre = page.get_by_role("dialog", name="Partager en image")
    fenetre.wait_for(timeout=5000)
    assert page.evaluate(PIXEL)["h"] == 1920
    page.keyboard.press("Escape")
    fenetre.wait_for(state="hidden", timeout=5000)
    assert page.evaluate("document.activeElement && document.activeElement.textContent") == "Partager en image"
    assert page.errors == []


def test_en_anglais(page, base_url):
    _reponse(page, base_url, chemin="/?lang=en")
    page.get_by_role("button", name="Share as image").click()
    page.get_by_role("dialog", name="Share as image").get_by_role("button", name="Save image").wait_for(timeout=5000)
    assert page.errors == []


def test_un_mot_trop_long_est_coupe_dans_la_largeur(page, base_url):
    """Relecture Gitar de #580 : un lien sans espace plus large que le panneau débordait de l'image (et le « … » aussi
    quand la réponse était coupée sur ce mot)."""
    _reponse(page, base_url)
    largeurs = page.evaluate("""async () => {
      await document.fonts.load('400 46px "Atkinson Hyperlegible"');
      const ctx = document.createElement('canvas').getContext('2d');
      ctx.font = '400 46px "Atkinson Hyperlegible",system-ui,sans-serif';
      const lien = 'https://www.service-public.sn/demarches/' + 'etat-civil-acte-de-naissance-'.repeat(4);
      const mesure = (r) => r.lines.map((l) => ctx.measureText(l).width);
      return {entier: mesure(shareImgLines(ctx, 'Voir ' + lien + ' pour la suite.', 840, 20)),
              coupe: mesure(shareImgLines(ctx, 'Voir ' + lien + ' ' + lien, 840, 2))};
    }""")
    assert len(largeurs["entier"]) >= 3
    assert max(largeurs["entier"]) <= 840, largeurs
    assert max(largeurs["coupe"]) <= 840, largeurs
