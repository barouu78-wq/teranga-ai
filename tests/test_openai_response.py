from services.openai_response import create_response


class Client:
    class Responses:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                raise RuntimeError("model not found")
            return {"ok": True}

    def __init__(self):
        self.responses = self.Responses()


def test_create_response_retries_with_fallback_model():
    client = Client()
    result = create_response(
        client,
        {"use_web": False},
        build_kwargs=lambda payload, stream: {"model": "primary", "stream": stream},
        model="primary",
        logger=type("Logger", (), {"warning": lambda *args: None})(),
        stream=True,
        fallback_models=("fallback",),
    )
    assert result == {"ok": True}
    assert client.responses.calls == [
        {"model": "primary", "stream": True},
        {"model": "fallback", "stream": True},
    ]
