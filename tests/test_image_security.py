from services.images import allowed_image_url


def test_allowed_image_url_accepts_only_expected_https_hosts():
    assert allowed_image_url("https://upload.wikimedia.org/example.jpg")
    assert allowed_image_url("https://thumb.wikimedia.org/example.jpg")
    assert not allowed_image_url("http://upload.wikimedia.org/example.jpg")
    assert not allowed_image_url("https://example.com/example.jpg")
    assert not allowed_image_url("https://upload.wikimedia.org:444/example.jpg")
    assert not allowed_image_url("https://user:pass@upload.wikimedia.org/example.jpg")
