"""Generated static assets used by the web application.

Keep image generation details out of the Flask route module so the application
can focus on HTTP behavior and configuration.
"""

from __future__ import annotations

import io
import math

from .site_layout import LOGO_SVG

# Version 3.0 « Nuit dorée » : le logo (baobab doré) sur le noir de la nuit.
ICON_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect rx="14" width="64" height="64" fill="#0b0d10"/>
<g transform="translate(6 6) scale(0.52)">{LOGO_SVG}</g>
</svg>"""

OG_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#fbf8f1"/>
<circle cx="1080" cy="80" r="220" fill="#f3dca6"/>
<g transform="translate(80 150) scale(1.16)">{LOGO_SVG}</g>
<text x="80" y="340" font-size="72" font-family="Georgia,serif" fill="#14110d">Teranga AI</text>
<text x="80" y="410" font-size="32" font-family="Georgia,serif" fill="#5e574b">L’assistant du Sénégal · FR · EN · WO</text>
</svg>"""

_GOLD = "#e8b04b"
_NIGHT = "#0b0d10"


def _quadratic(p0, p1, p2, steps=16):
    return [
        ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
         (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
        for t in (i / steps for i in range(steps + 1))
    ]


def _draw_logo(draw, x: float, y: float, size: float) -> None:
    """Le logo LOGO_SVG (repère 100 × 100) dessiné avec Pillow, pour les PNG."""
    s = size / 100

    def pt(px, py):
        return (x + px * s, y + py * s)

    draw.ellipse((x + 6 * s, y + 6 * s, x + 94 * s, y + 94 * s), fill=_GOLD)
    # Sol : la courbe de l'horizon, puis le bas du disque (comme le chemin SVG « Q … A »).
    ground = _quadratic((19.8, 82), (50, 75), (80.2, 82))
    start, end = math.atan2(32, 30.2), math.atan2(32, -30.2)
    # Rayon 44,5 (et non 44) : couvre le bord lissé du disque, sans liseré doré sous le sol.
    ground += [(50 + 44.5 * math.cos(a), 50 + 44.5 * math.sin(a))
               for a in (start + (end - start) * i / 24 for i in range(25))]
    draw.polygon([pt(px, py) for px, py in ground], fill=_NIGHT)
    trunk = _quadratic((37, 85), (44, 72), (43, 57)) + _quadratic((57, 57), (56, 72), (63, 85))
    draw.polygon([pt(px, py) for px, py in trunk], fill=_NIGHT)
    width = max(1, round(5.5 * s))
    for branch in (((46, 58), (36, 46), (28, 42)), ((36, 46), (34, 37)), ((50, 57), (50, 37)),
                   ((50, 45), (43, 35)), ((50, 43), (57, 33)), ((54, 58), (64, 46), (72, 42)), ((64, 46), (66, 37))):
        draw.line([pt(px, py) for px, py in branch], fill=_NIGHT, width=width, joint="curve")
        for px, py in (branch[0], branch[-1]):
            cx, cy = pt(px, py)
            r = width / 2
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=_NIGHT)


def build_og_png() -> bytes:
    """Render the Open Graph preview as PNG bytes."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 630), "#fbf8f1")
    draw = ImageDraw.Draw(img)
    draw.ellipse((860, -140, 1300, 300), fill="#f3dca6")
    _draw_logo(draw, 80, 150, 116)
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72
        )
        sub_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32
        )
    except Exception:
        # Image Docker « slim » sans DejaVu : police intégrée de Pillow, à la
        # bonne taille quand la version le permet (Pillow >= 10.1).
        try:
            title_font = ImageFont.load_default(size=72)
            sub_font = ImageFont.load_default(size=32)
        except TypeError:
            title_font = ImageFont.load_default()
            sub_font = title_font
    draw.text((80, 300), "Teranga AI", fill="#14110d", font=title_font)
    draw.text(
        (80, 400),
        "L’assistant du Sénégal  ·  FR  EN  WO",
        fill="#5e574b",
        font=sub_font,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_icon_png(size: int) -> bytes:
    """Render a square PWA icon as PNG bytes."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), _NIGHT)
    draw = ImageDraw.Draw(img)
    # Marge de 10 % : le logo reste entier dans les icônes « maskable » d'Android.
    _draw_logo(draw, size * 0.1, size * 0.1, size * 0.8)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
