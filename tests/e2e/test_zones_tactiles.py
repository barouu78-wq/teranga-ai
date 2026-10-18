"""Zones tactiles d'au moins 44 px sur téléphone (AGENTS.md), sans changer le dessin du site.

Contrôle du 17 octobre 2026 à 390 px : des boutons et des liens de 36 à 42 px de haut (en-tête des pages
secondaires, pastilles de liens, bouton de thème, « Tous les lieux », WhatsApp…). La zone se mesure comme un doigt la
touche : la boîte du contrôle, agrandie par son ::before ou son ::after quand il en a un (comme les boutons de
langue), doit faire au moins 44 × 44 px.
"""

import pytest

PAGES = ["/", "/lieux", "/lieux/goree", "/explorer", "/visiter-goree", "/offres-partenaires",
         "/pour-les-entreprises", "/regions/dakar"]

# Boutons de langue FR/EN/WO : collés dans une même pastille, avec une zone déjà agrandie (42 × 56 px) ; un carré
# de 44 px de large déborderait sur le bouton voisin.
EXEMPT = "#langs button"

MESURE = r"""(exempt) => {
  const trop_petits = [];
  for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea')) {
    if (el.matches(exempt)) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || !el.getClientRects().length) continue;
    // Lien dans une phrase : exception « en ligne » (WCAG 2.5.8).
    if (el.tagName === 'A' && s.display === 'inline' && el.closest('p, li, td, small, span')) continue;
    el.scrollIntoView({block: 'center', inline: 'center'});
    const r = el.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (!hit || !(hit === el || el.contains(hit))) continue;  // caché ou recouvert : pas une cible à l'écran
    // Zone réelle : la boîte, agrandie par un ::before/::after placé en absolu (inset négatif).
    let [left, top, right, bottom] = [r.left, r.top, r.right, r.bottom];
    if (s.position !== 'static') {
      for (const pseudo of ['::before', '::after']) {
        const p = getComputedStyle(el, pseudo);
        if (p.content === 'none' || p.position !== 'absolute' || p.display === 'none') continue;
        const [t, rt, b, l] = [p.top, p.right, p.bottom, p.left].map(parseFloat);
        if ([t, rt, b, l].some(Number.isNaN)) continue;
        left = Math.min(left, r.left + l); top = Math.min(top, r.top + t);
        right = Math.max(right, r.right - rt); bottom = Math.max(bottom, r.bottom - b);
      }
    }
    if (right - left < 43.5 || bottom - top < 43.5) {
      const nom = (el.getAttribute('aria-label') || el.textContent || el.id || el.tagName).trim().replace(/\s+/g, ' ');
      trop_petits.push(`${el.tagName.toLowerCase()} « ${nom.slice(0, 40)} » ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
  }
  return [...new Set(trop_petits)];
}"""


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("path", PAGES)
def test_chaque_bouton_offre_une_zone_de_44_px(page, base_url, path, theme):
    page.set_viewport_size({"width": 390, "height": 844})
    page.add_init_script(
        "try{localStorage.setItem('teranga-theme-v','2');localStorage.setItem('teranga-theme','%s')}catch(e){}" % theme)
    page.goto(base_url + path)
    assert page.evaluate(MESURE, EXEMPT) == []
    assert page.errors == []


def test_le_bouton_whatsapp_reste_lisible(page, base_url):
    """Texte blanc sur le vert WhatsApp : 4,14:1 avant la correction, 4,5:1 au minimum."""
    page.goto(base_url + "/")
    ratio = page.evaluate("""() => {
      const el = document.getElementById('waShare'); const s = getComputedStyle(el);
      const rgb = c => c.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
      const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
        const [r, g, b] = rgb(c); return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
      const a = lum(s.color), b = lum(s.backgroundColor);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    }""")
    assert ratio >= 4.5
