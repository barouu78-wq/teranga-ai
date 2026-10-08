"""Shareable answers: a signed, self-contained link to one Teranga AI reply.

Nothing is stored server-side. The question, the answer and its sources are
compressed into a token signed with the app secret, so a shared link can only
show text that Teranga AI really produced. The token travels in the URL
fragment (/partage#<token>), which browsers never send to the server.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import zlib
from html import escape
from urllib.parse import urlparse

from services.site_layout import HEAD_ASSETS, site_footer, site_header

MAX_QUESTION = 500
MAX_ANSWER = 6000
MAX_SOURCES = 5
MAX_TOKEN = 12000
_MAX_INFLATED = 32000


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _mac(secret: str, data: str) -> str:
    digest = hmac.new(str(secret).encode("utf-8"), b"share:v1:" + data.encode("ascii"), hashlib.sha256).digest()
    return _b64(digest[:18])


def _clean_sources(sources) -> list[dict]:
    clean = []
    for item in sources or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if urlparse(url).scheme not in ("http", "https"):
            continue
        clean.append({"title": str(item.get("title") or url)[:160], "url": url[:500]})
        if len(clean) >= MAX_SOURCES:
            break
    return clean


def sign_answer(secret: str, question: str, answer: str, sources=None, language: str = "fr") -> str:
    answer = str(answer or "").strip()
    if not answer or not secret:
        return ""
    body = {
        "v": 1,
        "q": str(question or "").strip()[:MAX_QUESTION],
        "a": answer[:MAX_ANSWER],
        "s": _clean_sources(sources),
        "l": "en" if language == "en" else "fr",
        "t": int(time.time()),
    }
    data = _b64(zlib.compress(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9))
    return f"{data}.{_mac(secret, data)}"


def open_token(secret: str, token: object) -> dict | None:
    token = str(token or "").strip()
    if not secret or not token or len(token) > MAX_TOKEN or token.count(".") != 1 or not token.isascii():
        return None
    data, mac = token.split(".")
    if not hmac.compare_digest(mac, _mac(secret, data)):
        return None
    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(_unb64(data), _MAX_INFLATED)
        if inflater.unconsumed_tail:
            return None
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, zlib.error):
        return None
    if not isinstance(body, dict) or body.get("v") != 1 or not body.get("a"):
        return None
    return {
        "question": str(body.get("q") or ""),
        "answer": str(body.get("a") or ""),
        "sources": _clean_sources(body.get("s")),
        "language": "en" if body.get("l") == "en" else "fr",
        "created_at": int(body.get("t") or 0),
    }


_TEXT = {
    "fr": {
        "title": "Réponse partagée | Teranga AI",
        "kicker": "Réponse partagée",
        "question": "Question",
        "answer": "Réponse de Teranga AI",
        "sources": "Sources",
        "ask": "Poser ma propre question",
        "loading": "Chargement de la réponse…",
        "invalid": "Ce lien de partage est invalide ou incomplet. Vérifie qu’il a été copié en entier.",
        "note": "Réponse générée par une IA à la date indiquée : vérifie les informations importantes (prix, horaires, démarches).",
        "date": "Générée le",
    },
    "en": {
        "title": "Shared answer | Teranga AI",
        "kicker": "Shared answer",
        "question": "Question",
        "answer": "Teranga AI answer",
        "sources": "Sources",
        "ask": "Ask my own question",
        "loading": "Loading the answer…",
        "invalid": "This share link is invalid or incomplete. Check that it was copied in full.",
        "note": "AI-generated answer as of the date shown: double-check important details (prices, hours, procedures).",
        "date": "Generated on",
    },
}


def render_share_page(site_url: str, nonce: str, lang: str = "fr") -> str:
    ui = "en" if lang == "en" else "fr"
    t = _TEXT[ui]
    texts = json.dumps(_TEXT, ensure_ascii=True).replace("<", "\\u003c")
    nonce_attr = f' nonce="{escape(nonce)}"' if nonce else ""
    # Le texte est inséré avec textContent : aucune donnée du lien n'est
    # interprétée comme du HTML.
    script = (
        f"<script{nonce_attr}>addEventListener('hashchange',()=>location.reload());(async()=>{{const TX={texts};"
        "const box=document.getElementById('shared');const tok=location.hash.slice(1);"
        "const fail=()=>{box.replaceChildren();const p=document.createElement('p');p.className='muted';"
        "p.textContent=TX[document.documentElement.lang==='en'?'en':'fr'].invalid;box.appendChild(p)};"
        "if(!tok){fail();return}"
        "try{const r=await fetch('/api/share/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:tok})});"
        "if(!r.ok){fail();return}const d=await r.json();const t=TX[d.language]||TX.fr;document.documentElement.lang=d.language;"
        "document.title=t.title;box.replaceChildren();"
        "const el=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!=null)n.textContent=txt;return n};"
        "box.appendChild(el('div','kicker',t.kicker));"
        "if(d.question){box.appendChild(el('h2','',t.question));box.appendChild(el('blockquote','shared-q',d.question))}"
        "box.appendChild(el('h2','',t.answer));const a=el('div','shared-a');"
        "d.answer.split(/\\n{2,}/).forEach(par=>{const p=el('p');par.split('\\n').forEach((line,i)=>{if(i)p.appendChild(document.createElement('br'));"
        "p.appendChild(document.createTextNode(line.replace(/\\*\\*/g,'')))});a.appendChild(p)});box.appendChild(a);"
        "if(d.sources&&d.sources.length){box.appendChild(el('h2','',t.sources));const ul=el('ul');"
        "d.sources.forEach(s=>{const li=el('li');const l=el('a','',s.title);l.href=s.url;l.target='_blank';l.rel='noopener noreferrer nofollow';li.appendChild(l);ul.appendChild(li)});box.appendChild(ul)}"
        "if(d.created_at){box.appendChild(el('p','muted',t.date+' '+new Date(d.created_at*1000).toLocaleDateString(d.language==='en'?'en-GB':'fr-FR',{day:'numeric',month:'long',year:'numeric'})))}"
        "box.appendChild(el('p','muted',t.note));"
        "const act=el('div','actions');const c=el('a','cta',t.ask);c.href='/?q='+encodeURIComponent(d.question||'');act.appendChild(c);box.appendChild(act)"
        "}catch(_){fail()}})();</script>"
    )
    return (
        '<!doctype html><html lang="' + ui + '"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,follow"><meta name="referrer" content="no-referrer">'
        f'<meta property="og:site_name" content="Teranga AI"><meta property="og:title" content="{escape(t["title"])}">'
        f'<meta property="og:image" content="{escape(site_url.rstrip("/"))}/og.png"><meta name="twitter:card" content="summary_large_image">'
        f"<title>{escape(t['title'])}</title>{HEAD_ASSETS}"
        "<style>.shared-q{margin:0;padding:12px 16px;border-left:3px solid var(--accent);background:var(--surface-2);border-radius:8px}"
        ".shared-a p{line-height:1.65}</style></head>"
        "<body>" + site_header("", ui)
        + f'<main><article id="shared" aria-live="polite"><p class="muted">{escape(t["loading"])}</p></article></main>'
        + site_footer(ui)
        + script
        + "</body></html>"
    )
