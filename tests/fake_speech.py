"""Faux fournisseur de voix : imite ``client.audio.speech.with_streaming_response.create`` (aucun réseau).

``install(monkeypatch, client, calls)`` remplace l'appel ; chaque appel note ses arguments dans ``calls``.
``chunks`` : morceaux d'audio envoyés l'un après l'autre (le flux) ; ``error`` : échec avant le premier octet ;
``late_error`` : échec après le premier morceau (coupure en plein flux).
"""

FAKE_MP3 = (b"ID3fake", b"-mp3-", b"-fin")


class _Speech:
    def __init__(self, chunks, late_error, state):
        self._chunks = chunks
        self._late_error = late_error
        self._state = state

    def iter_bytes(self, chunk_size=None):
        self._state["chunk_size"] = chunk_size
        for index, chunk in enumerate(self._chunks):
            yield chunk
            if self._late_error and index == 0:
                raise RuntimeError(self._late_error)


class _Upstream:
    def __init__(self, speech, state):
        self._speech = speech
        self._state = state

    def __enter__(self):
        return self._speech

    def __exit__(self, *exc):
        self._state["closed"] = True
        return False


class _Streaming:
    def __init__(self, calls, chunks, error, late_error):
        self.calls = calls
        self.chunks = chunks
        self.error = error
        self.late_error = late_error
        self.state = {"closed": False}
        self.options = []  # réglages demandés à client.with_options (la voix : aucune nouvelle tentative)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise RuntimeError(self.error)
        return _Upstream(_Speech(self.chunks, self.late_error, self.state), self.state)


def install(monkeypatch, client, calls, *, chunks=FAKE_MP3, error=None, late_error=None):
    fake = _Streaming(calls, chunks, error, late_error)
    monkeypatch.setattr(client.audio.speech, "with_streaming_response", fake)

    def with_options(**options):
        fake.options.append(options)
        return client  # la copie sans relance est ce même client simulé

    monkeypatch.setattr(client, "with_options", with_options)
    return fake
