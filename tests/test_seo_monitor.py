"""Unit tests for the dependency-free technical SEO monitor."""
import xml.etree.ElementTree as ET

from scripts.seo_monitor import MetadataParser, parse_sitemap


def parse(html):
    parser = MetadataParser()
    parser.feed(html)
    return parser


def test_metadata_parser_extracts_title_description_canonical_and_h1():
    parser = parse(
        '<html><head><title>Teranga AI Sénégal</title>'
        '<meta name="description" content="Assistant IA au Sénégal">'
        '<link rel="canonical" href="https://teranga-ai.fr/">'
        '</head><body><h1>Bienvenue</h1></body></html>'
    )

    assert parser.title == "Teranga AI Sénégal"
    assert parser.description == "Assistant IA au Sénégal"
    assert parser.canonical == "https://teranga-ai.fr/"
    assert parser.h1_count == 1


def test_metadata_parser_handles_case_and_attribute_order():
    parser = parse(
        '<TITLE>Visiter Dakar</TITLE>'
        '<META content="Guide pratique de Dakar" NAME="description">'
        '<LINK href="https://teranga-ai.fr/dakar" rel="canonical">'
        '<h1>Dakar</h1><h1>Tourisme</h1>'
    )

    assert parser.title == "Visiter Dakar"
    assert parser.description == "Guide pratique de Dakar"
    assert parser.canonical == "https://teranga-ai.fr/dakar"
    assert parser.h1_count == 2


def test_metadata_parser_reports_missing_metadata_as_empty_values():
    parser = parse("<html><body><p>Contenu sans métadonnées</p></body></html>")

    assert parser.title == ""
    assert parser.description is None
    assert parser.canonical is None
    assert parser.h1_count == 0


def test_parse_urlset_extracts_only_same_host_https_page_urls():
    xml = """<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://teranga-ai.fr/dakar</loc></url>
      <url><loc>https://teranga-ai.fr/assistant-senegal</loc></url>
      <url><loc>https://example.com/external</loc></url>
      <url><loc>http://teranga-ai.fr/insecure</loc></url>
    </urlset>"""
    pages, children = parse_sitemap(xml)

    assert pages == ["https://teranga-ai.fr/dakar", "https://teranga-ai.fr/assistant-senegal"]
    assert children == []


def test_parse_sitemap_index_returns_child_sitemaps_not_page_urls():
    xml = """<?xml version="1.0"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://teranga-ai.fr/sitemap-pages.xml</loc></sitemap>
      <sitemap><loc>https://teranga-ai.fr/sitemap-blog.xml</loc></sitemap>
      <sitemap><loc>https://evil.example/sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    pages, children = parse_sitemap(xml)

    assert pages == []
    assert children == [
        "https://teranga-ai.fr/sitemap-pages.xml",
        "https://teranga-ai.fr/sitemap-blog.xml",
    ]


def test_parse_sitemap_rejects_unexpected_xml_root():
    try:
        parse_sitemap("<not-a-sitemap/>")
    except ET.ParseError as exc:
        assert "Root XML inattendue" in str(exc)
    else:
        raise AssertionError("An unexpected root must be rejected")


def test_parse_urlset_page_limit_is_enforced_by_monitor():
    from scripts import seo_monitor

    xml = "<urlset>" + "".join(
        f"<url><loc>https://teranga-ai.fr/page-{i}</loc></url>" for i in range(seo_monitor.MAX_PAGES + 5)
    ) + "</urlset>"
    pages, children = seo_monitor.parse_sitemap(xml)

    assert len(pages) == seo_monitor.MAX_PAGES + 5
    assert children == []
    assert len(pages[:seo_monitor.MAX_PAGES]) == seo_monitor.MAX_PAGES
