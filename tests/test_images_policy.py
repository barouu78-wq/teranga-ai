from services.images import should_fetch_images


def test_should_fetch_images_detects_explicit_photo_requests():
    assert should_fetch_images("Montre-moi les photos de Gorée")
    assert should_fetch_images("show me the city")
    assert not should_fetch_images("Quelle est l'histoire de Gorée ?")
