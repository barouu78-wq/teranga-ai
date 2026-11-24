"""Parcours principaux sur téléphone et sur ordinateur (ticket E2E P1 du 22 novembre 2026).

1. Chaque bouton et lien visible de l'accueil réagit, sans erreur JavaScript : navigation, nouvelle fenêtre,
   sélecteur de fichier, changement de la page, requête, ou curseur placé. Un bouton qui ne fait rien échoue.
2. Les quatre profils (touriste, résident, diaspora, commerçant) : choisir son profil, toucher une suggestion, lire
   la réponse, poser une question de suite. La suite part avec l'historique et le profil.
Le chat est simulé : aucun appel à l'IA ni au réseau.
"""

import json

import pytest

VIEWPORTS = {"telephone": (390, 844), "ordinateur": (1280, 800)}

LIST = """() => [...document.querySelectorAll('button, a[href]')].filter(e => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  // Hors de la page (lien d'évitement, visible au clavier seulement) : non cliquable au doigt.
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.disabled && r.right > 0 && r.left < innerWidth && r.bottom + scrollY > 0;
}).map((e, i) => { e.dataset.parcours = 'b' + i;
  return {key: 'b' + i, tag: e.tagName, id: e.id, label: (e.getAttribute('aria-label') || e.textContent || '').trim()
    .replace(/\\s+/g, ' ').slice(0, 50), href: e.getAttribute('href') || '', current: e.getAttribute('aria-current') || '',
    on: e.classList.contains('on')}; })"""
WATCH = """() => { window.__changes = 0;
  new MutationObserver(m => { window.__changes += m.length; })
    .observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true}); }"""


def _chat(page, answers):
    """Sert les réponses du chat dans l'ordre et garde chaque requête envoyée."""
    sent, queue = [], iter(answers)

    def handler(route):
        sent.append(json.loads(route.request.post_data or "{}"))
        text = next(queue, "Réponse simulée.")
        route.fulfill(content_type="application/x-ndjson",
                      body=json.dumps({"d": text}, ensure_ascii=False) + "\n" + json.dumps({"done": True}) + "\n")

    page.route("**/chat", handler)
    return sent


def _home(page, base_url, viewport):
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.goto(base_url + "/")
    page.locator("#heroInput, #input").first.wait_for(state="attached", timeout=5000)
    page.wait_for_timeout(300)


@pytest.mark.parametrize("device", VIEWPORTS)
def test_chaque_bouton_de_l_accueil_reagit(browser, base_url, device):
    context = browser.new_context(locale="fr-FR", service_workers="block",
                                  viewport={"width": VIEWPORTS[device][0], "height": VIEWPORTS[device][1]})
    # Rien ne sort de la machine : un lien externe (WhatsApp) compte comme une nouvelle fenêtre ou une requête.
    context.route(lambda url: not url.startswith(base_url), lambda route: route.abort())
    probe = context.new_page()
    _chat(probe, [])
    _home(probe, base_url, VIEWPORTS[device])
    items = probe.evaluate(LIST)
    probe.close()
    assert len(items) >= 20, items

    dead, errors = [], []
    for item in items:
        page = context.new_page()
        _chat(page, [])
        page_errors, requests, popups, choosers = [], [], [], []
        page.on("pageerror", lambda exc, errs=page_errors: errs.append(str(exc)))
        page.on("request", lambda req, reqs=requests: reqs.append(req.url))
        page.on("popup", lambda popup, pops=popups: pops.append(popup))
        page.on("filechooser", lambda chooser, ch=choosers: ch.append(chooser))
        _home(page, base_url, VIEWPORTS[device])
        page.evaluate(LIST)
        page.evaluate(WATCH)
        start, before = page.url, len(requests)
        focus_before = page.evaluate("document.activeElement && document.activeElement.id")
        page.click(f"[data-parcours='{item['key']}']", timeout=3000)
        page.wait_for_timeout(400)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=2000)
        except Exception:  # noqa: BLE001 - pas de navigation : on regarde les autres effets
            pass
        moved = page.url != start
        changed = moved or page.evaluate("window.__changes || 0") > 0
        # Le focus pris par le bouton lui-même ne compte pas : seul compte un focus envoyé ailleurs (« Envoyer » sans
        # question remet le curseur dans la zone de saisie).
        focused = (not moved) and page.evaluate(
            "(key) => { const a = document.activeElement; return !!a && a.dataset.parcours !== key && a.id || ''; }",
            item["key"]) not in ("", focus_before)
        # Un onglet déjà ouvert (« Accueil » sur l'accueil) n'a rien à faire : il ne compte pas comme mort.
        already_here = item["current"] in ("page", "true") or (item["on"] and not item["href"])
        if not (changed or focused or popups or choosers or len(requests) > before or already_here):
            dead.append(item)
        if page_errors:
            errors.append((item, page_errors))
        page.close()
    context.close()
    assert dead == [], f"boutons sans effet : {dead}"
    assert errors == [], f"erreurs JavaScript : {errors}"


PERSONAS = ["tourist", "resident", "diaspora", "merchant"]


@pytest.mark.parametrize("device", VIEWPORTS)
@pytest.mark.parametrize("audience", PERSONAS)
def test_parcours_d_un_profil_suggestion_reponse_puis_suite(page, base_url, device, audience):
    sent = _chat(page, ["Première réponse simulée.", "Deuxième réponse simulée."])
    _home(page, base_url, VIEWPORTS[device])
    page.click(f".audience-btn[data-audience='{audience}']")
    assert "on" in page.get_attribute(f".audience-btn[data-audience='{audience}']", "class")
    chip = page.locator("#heroChips button:visible").first
    suggestion = chip.inner_text().strip()
    assert suggestion
    chip.click()
    page.get_by_text("Première réponse simulée.").wait_for(timeout=5000)
    assert sent[0]["audience"] == audience and sent[0]["message"]

    page.fill("#input", "Et pour demain ?")
    page.click("#send")
    page.get_by_text("Deuxième réponse simulée.").wait_for(timeout=5000)
    second = sent[1]
    assert second["message"] == "Et pour demain ?" and second["audience"] == audience
    contents = [turn.get("content", "") for turn in second.get("history", [])]
    assert any("Première réponse simulée." in c for c in contents), second.get("history")
    assert page.evaluate("document.documentElement.scrollWidth") <= VIEWPORTS[device][0]  # pas de défilement de côté
    assert page.errors == []
