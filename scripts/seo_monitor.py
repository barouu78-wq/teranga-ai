#!/usr/bin/env python3
"""Lightweight technical SEO monitor for Teranga AI. Uses only Python stdlib."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

BASE_URL = "https://teranga-ai.fr"
USER_AGENT = "TerangaAI-SEO-Monitor/1.0 (+https://teranga-ai.fr)"
TIMEOUT = 15
MAX_PAGES = 40
MAX_SITEMAPS = 10


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title_parts = []
        self.in_title = False
        self.description = None
        self.canonical = None
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "").strip()
        elif tag.lower() == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif tag.lower() == "h1":
            self.h1_count += 1

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data.strip())

    @property
    def title(self):
        return " ".join(part for part in self.title_parts if part).strip()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(2_000_000).decode("utf-8", errors="replace")
            return {"url": url, "status": response.status, "final_url": response.geturl(),
                    "seconds": round(time.monotonic() - started, 2), "body": body, "error": None}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"url": url, "status": None, "final_url": None,
                "seconds": round(time.monotonic() - started, 2), "body": "",
                "error": str(exc)[:300]}


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(xml_body, base_url=BASE_URL):
    """Return (page_urls, child_sitemap_urls) from a sitemap XML document."""
    root = ET.fromstring(xml_body)
    root_name = _local_name(root.tag)
    pages = []
    child_sitemaps = []
    if root_name == "urlset":
        target = pages
        allowed_name = "url"
    elif root_name == "sitemapindex":
        target = child_sitemaps
        allowed_name = "sitemap"
    else:
        raise ET.ParseError(f"Root XML inattendue : {root_name}")

    base = urlparse(base_url)
    for entry in root:
        if _local_name(entry.tag) != allowed_name:
            continue
        loc = next((node.text.strip() for node in entry
                    if _local_name(node.tag) == "loc" and node.text and node.text.strip()), None)
        if not loc:
            continue
        parsed = urlparse(loc)
        if parsed.scheme != "https" or parsed.netloc.lower() != base.netloc.lower():
            continue
        if loc not in target:
            target.append(loc)
    return pages, child_sitemaps


def inspect_page(url):
    result = fetch(url)
    item = {key: result[key] for key in ("url", "status", "final_url", "seconds", "error")}
    if result["status"] is None or result["status"] >= 400:
        item["issues"] = ["page_unreachable"]
        return item
    parser = MetadataParser()
    try:
        parser.feed(result["body"])
    except Exception:
        pass
    issues = []
    if not parser.title:
        issues.append("missing_title")
    elif len(parser.title) > 70:
        issues.append("title_over_70_chars")
    if not parser.description:
        issues.append("missing_meta_description")
    elif len(parser.description) > 170:
        issues.append("meta_description_over_170_chars")
    if parser.h1_count == 0:
        issues.append("missing_h1")
    elif parser.h1_count > 1:
        issues.append("multiple_h1")
    if not parser.canonical:
        issues.append("missing_canonical")
    item.update({"title": parser.title, "meta_description": parser.description,
                 "canonical": parser.canonical, "h1_count": parser.h1_count, "issues": issues})
    return item


def main():
    report = {
        "site": BASE_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "pages": [],
        "summary": {"errors": 0, "warnings": 0},
    }
    for name, url in (("homepage", BASE_URL + "/"), ("robots", BASE_URL + "/robots.txt"),
                      ("sitemap", BASE_URL + "/sitemap.xml")):
        result = fetch(url)
        report["checks"][name] = {key: result[key] for key in ("url", "status", "final_url", "seconds", "error")}
        if result["status"] is None or result["status"] >= 400:
            report["summary"]["errors"] += 1

    sitemap_result = fetch(BASE_URL + "/sitemap.xml")
    urls = []
    if sitemap_result["status"] and sitemap_result["status"] < 400:
        try:
            page_urls, child_sitemaps = parse_sitemap(sitemap_result["body"])
            urls.extend(page_urls)
            for child_url in child_sitemaps[:MAX_SITEMAPS]:
                child_result = fetch(child_url)
                if child_result["status"] is None or child_result["status"] >= 400:
                    report["summary"]["errors"] += 1
                    report["checks"].setdefault("child_sitemaps", []).append({
                        "url": child_url, "status": child_result["status"], "error": child_result["error"]
                    })
                    continue
                child_pages, nested_sitemaps = parse_sitemap(child_result["body"])
                if nested_sitemaps:
                    report["summary"]["warnings"] += 1
                urls.extend(child_pages)
                urls = list(dict.fromkeys(urls))[:MAX_PAGES]
        except ET.ParseError as exc:
            report["checks"]["sitemap"]["parse_error"] = str(exc)
            report["summary"]["errors"] += 1

    # Always inspect the homepage, even if the sitemap is missing or malformed.
    urls = list(dict.fromkeys([BASE_URL + "/"] + urls))[:MAX_PAGES]
    for url in urls:
        page = inspect_page(url)
        report["pages"].append(page)
        if page.get("status") is None or (page.get("status") or 0) >= 400:
            report["summary"]["errors"] += 1
        report["summary"]["warnings"] += len(page.get("issues", []))

    report["summary"]["pages_checked"] = len(report["pages"])
    report["summary"]["pages_with_issues"] = sum(bool(p.get("issues")) for p in report["pages"])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Fail CI only on infrastructure-level errors; metadata findings remain actionable warnings.
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
