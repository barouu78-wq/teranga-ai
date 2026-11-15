"""Fichier joint au chat, dans un vrai navigateur (téléphone, 390 px) : « Go fichiers » du 15 novembre 2026.

Le fichier choisi s'affiche au-dessus du champ, part avec la question suivante (une photo est d'abord réduite en
JPEG), puis il est oublié : la question d'après part sans lui.
"""

import base64
import json
import struct
import zlib

PDF = b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n%%EOF\n"


def png(largeur=40, hauteur=30):
    """Une vraie image PNG (unie), sans bibliothèque."""
    def bloc(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    lignes = b"".join(b"\x00" + b"\xc8\x78\x28" * largeur for _ in range(hauteur))
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(lignes)) + bloc(b"IEND", b""))


def ouvrir(page, base_url, envois):
    def repondre(route):
        envois.append(json.loads(route.request.post_data or "{}"))
        route.fulfill(body=json.dumps({"d": f"Réponse {len(envois)}."}) + "\n", content_type="application/x-ndjson")

    page.set_viewport_size({"width": 390, "height": 844})
    page.route(f"{base_url}/chat", repondre)
    page.goto(base_url + "/")


def test_un_pdf_part_avec_la_question_puis_il_est_oublie(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.fill("#heroInput", "Bonjour")
    page.press("#heroInput", "Enter")
    page.get_by_text("Réponse 1.").wait_for()
    page.set_input_files("#pieceInput", files=[{"name": "mon-cv.pdf", "mimeType": "application/pdf", "buffer": PDF}])
    page.locator("#piece .piece").get_by_text("mon-cv.pdf").wait_for()
    assert page.locator("#piece .piece-note").get_by_text("jamais gardé par Teranga").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.fill("#input", "Améliore mon CV")
    page.get_by_role("button", name="Envoyer").click()
    page.get_by_text("Réponse 2.").wait_for()
    fichier = envois[-1]["fichier"]
    assert fichier["nom"] == "mon-cv.pdf" and fichier["type"] == "application/pdf"
    assert base64.b64decode(fichier["donnees"]) == PDF
    assert page.locator("#piece").is_hidden()  # plus rien en attente
    assert page.locator(".msg.user .msg-piece").get_by_text("mon-cv.pdf").is_visible()
    page.fill("#input", "Merci")
    page.get_by_role("button", name="Envoyer").click()
    page.get_by_text("Réponse 3.").wait_for()
    assert "fichier" not in envois[-1]


def test_une_photo_seule_part_depuis_l_accueil_en_jpeg(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.set_input_files("#pieceInput", files=[{"name": "facture.png", "mimeType": "image/png", "buffer": png()}])
    page.locator("#heroPiece .piece").get_by_text("facture.png").wait_for()
    page.get_by_role("button", name="Envoyer").first.click()
    page.get_by_text("Réponse 1.").wait_for()
    assert envois[-1]["message"] == "Explique-moi ce document."
    assert envois[-1]["fichier"]["type"] == "image/jpeg"
    assert base64.b64decode(envois[-1]["fichier"]["donnees"]).startswith(b"\xff\xd8\xff")


def test_un_fichier_refuse_ou_retire_ne_part_pas(page, base_url):
    envois = []
    ouvrir(page, base_url, envois)
    page.set_input_files("#pieceInput", files=[{"name": "note.txt", "mimeType": "text/plain", "buffer": b"bonjour"}])
    page.locator("#heroPiece").get_by_text("n’est pas accepté").wait_for()
    page.set_input_files("#pieceInput", files=[{"name": "mon-cv.pdf", "mimeType": "application/pdf", "buffer": PDF}])
    page.get_by_role("button", name="Retirer le fichier mon-cv.pdf").first.click()
    assert page.locator("#heroPiece").is_hidden()
    page.fill("#heroInput", "Bonjour")
    page.press("#heroInput", "Enter")
    page.get_by_text("Réponse 1.").wait_for()
    assert "fichier" not in envois[-1]
