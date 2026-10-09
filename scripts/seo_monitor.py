#!/usr/bin/env python3
"""Lightweight technical SEO monitor for Teranga AI. Uses only Python stdlib."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

BASE_URL = "https://teranga-ai.fr"
USER_AGENT = "TerangaAI-SEO-Monitor/1.0 (+https://teranga-ai.fr)"
TIMEOUT = 15
MAX_PAGES = 40


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
            root = ET.fromstring(sitemap_result["body"])
            for node in root.iter():
                if node.tag.rsplit("}", 1)[-1] == "loc" and node.text:
                    candidate = node.text.strip()
                    if candidate.startswith(BASE_URL + "/") or candidate == BASE_URL:
                        if candidate not in urls:
                            urls.append(candidate)
                    if len(urls) >= MAX_PAGES:
                        break
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
