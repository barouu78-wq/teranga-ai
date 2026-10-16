"""Tests ciblés de validation des URL du sitemap par l'audit SEO."""

from scripts.audit_seo import audit


class _Response:
    def __init__(self, body="", status_code=200):
        self.status_code = status_code
        self._body = body

    def get_data(self, as_text=False):
        return self._body


class _Client:
    def __init__(self, sitemap):
        self.sitemap = sitemap
        self.requested_paths = []

    def get(self, path, base_url=None):
        if path == "/sitemap.xml":
            return _Response(self.sitemap)
        self.requested_paths.append(path)
        return _Response(status_code=404)


def test_audit_rejects_external_sitemap_url_without_requesting_it():
    client = _Client(
        '<urlset><url><loc>https://teranga-ai.fr/dakar</loc></url>'
        '<url><loc>https://example.com/untrusted</loc></url></urlset>'
    )

    count, problems = audit(client)

    assert count == 2
    assert client.requested_paths == ["/dakar"]
    assert any("URL non canonique ou externe" in problem for _, problem in problems)


def test_audit_rejects_non_https_and_query_sitemap_urls():
    client = _Client(
        '<urlset><url><loc>http://teranga-ai.fr/dakar</loc></url>'
        '<url><loc>https://teranga-ai.fr/dakar?utm_source=test</loc></url></urlset>'
    )

    count, problems = audit(client)

    assert count == 2
    assert client.requested_paths == []
    assert sum("URL non canonique ou externe" in problem for _, problem in problems) == 2
