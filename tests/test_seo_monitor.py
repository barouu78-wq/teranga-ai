"""Unit tests for the dependency-free technical SEO monitor."""
from scripts.seo_monitor import MetadataParser


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
