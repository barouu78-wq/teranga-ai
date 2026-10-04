"""Crawl every sitemap page and check that internal links and assets resolve.

/og.png, /icon.svg, /pour-les-entreprises… were referenced but returned 404
without any test noticing.
"""

import os
import re
from urllib.parse import urlparse

os.environ.setdefault("OPENAI_API_KEY", "test-key")

LINK = re.compile(r'(?:href|src)="([^"#]+)"')
LOC = re.compile(r"<loc>([^<]+)</loc>")
META_IMAGE = re.compile(r'<meta (?:property|name)="(?:og|twitter):image" content="([^"]+)"')


def test_sitemap_pages_have_no_broken_internal_links():
    from app import SITE_URL, app

    client = app.test_client()
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    pages = [urlparse(url).path or "/" for url in LOC.findall(sitemap)]
    pages += ["/", "/explorer", "/trip-planner", "/opportunities", "/partners"]
    status = {}
    broken = []
    for page in dict.fromkeys(pages):
        response = client.get(page)
        if response.status_code != 200:
            broken.append((page, response.status_code))
            continue
        html = response.get_data(as_text=True)
        for href in LINK.findall(html) + META_IMAGE.findall(html):
            if href.startswith(SITE_URL):
                href = href[len(SITE_URL):] or "/"
            path = urlparse(href).path
            if href.startswith(("http://", "https://", "//")) or not path.startswith("/"):
                continue
            if path not in status:
                status[path] = client.get(path).status_code
            if status[path] >= 400:
                broken.append((page, path, status[path]))
    assert not broken, broken[:20]
    assert len(pages) > 100
