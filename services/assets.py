"""Generated static assets used by the web application.

Keep image generation details out of the Flask route module so the application
can focus on HTTP behavior and configuration.
"""

from __future__ import annotations

import io


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect rx="14" width="64" height="64" fill="#1a3d2a"/>
<circle cx="44" cy="18" r="8" fill="#e2b34a"/>
<path d="M32 54V28M18 36c8-2 10-10 14-10s6 8 14 10" stroke="#f3e6c8" stroke-width="3" fill="none" stroke-linecap="round"/>
</svg>"""

OG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#f6efe3"/>
<circle cx="1080" cy="80" r="220" fill="#e2b34a" opacity=".45"/>
<rect x="80" y="160" rx="28" width="96" height="96" fill="#1a3d2a"/>
<text x="80" y="340" font-size="72" font-family="Georgia,serif" fill="#1a120c">Teranga AI</text>
<text x="80" y="410" font-size="32" font-family="Georgia,serif" fill="#7a6d5f">L’assistant du Sénégal · FR · EN · WO</text>
</svg>"""


def build_og_png() -> bytes:
    """Render the Open Graph preview as PNG bytes."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1200, 630), "#f6efe3")
    draw = ImageDraw.Draw(img)
    draw.ellipse((920, -140, 1340, 280), fill="#e2b34a")
    draw.rounded_rectangle((80, 150, 196, 266), 28, fill="#1a3d2a")
    draw.ellipse((148, 172, 180, 204), fill="#e2b34a")
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
    draw.text((80, 300), "Teranga AI", fill="#1a120c", font=title_font)
    draw.text(
        (80, 400),
        "L'assistant du Senegal  ·  FR  EN  WO",
        fill="#7a6d5f",
        font=sub_font,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def build_icon_png(size: int) -> bytes:
    """Render a square PWA icon as PNG bytes."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (size, size), "#1a3d2a")
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=size // 5,
        fill="#1a3d2a",
    )
    sun = size // 5
    draw.ellipse(
        (size - pad - sun, pad, size - pad, pad + sun),
        fill="#e2b34a",
    )
    trunk_w = max(4, size // 14)
    draw.rectangle(
        (
            size // 2 - trunk_w // 2,
            size // 2,
            size // 2 + trunk_w // 2,
            size - pad,
        ),
        fill="#f3e6c8",
    )
    draw.arc(
        (pad, size // 3, size - pad, size - pad // 2),
        start=200,
        end=340,
        fill="#f3e6c8",
        width=max(3, size // 18),
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
