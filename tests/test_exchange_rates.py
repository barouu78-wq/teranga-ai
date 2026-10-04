from services.exchange_rates import parse_bceao_rates


def test_parse_bceao_rates_extracts_known_currency_values():
    raw = """
    <p>Cours des devises du 27 septembre 2026</p>
    <table>
      <tr><td>Euro</td><td>655,957</td></tr>
      <tr><td>Dollar US</td><td>577,070</td></tr>
      <tr><td>Livre sterling</td><td>762,860</td></tr>
    </table>
    """
    date, rates = parse_bceao_rates(raw, {"EUR": 1.0, "USD": 2.0, "GBP": 3.0})
    assert date == "27 septembre 2026"
    assert rates == {"EUR": 655.957, "USD": 577.070, "GBP": 762.860}


def test_parse_bceao_rates_keeps_fallback_for_invalid_values():
    date, rates = parse_bceao_rates("<td>Euro</td><td>n/a</td>", {"EUR": 655.957})
    assert date == ""
    assert rates["EUR"] == 655.957


def test_fetch_bceao_rates_closes_response():
    from services.exchange_rates import fetch_bceao_rates

    class Response:
        def __init__(self):
            self.closed = False
        def read(self):
            return b"<td>Euro</td><td>655,957</td>"
        def close(self):
            self.closed = True

    response = Response()
    result = fetch_bceao_rates(
        {"at": 0.0, "date": "", "rates": {"EUR": 1.0}},
        now=1000.0,
        fetch=lambda req, timeout: response,
    )

    assert result["rates"]["EUR"] == 655.957
    assert response.closed is True


def test_fetch_bceao_rates_backs_off_after_failure():
    from services.exchange_rates import DEFAULT_RATES, FX_CACHE_TTL, fetch_bceao_rates

    calls = []

    def failing_fetch(req, timeout=None):
        calls.append(req)
        raise OSError("BCEAO down")

    cache = {"at": 0.0, "date": "", "rates": dict(DEFAULT_RATES)}
    cache = fetch_bceao_rates(cache, now=10_000.0, fetch=failing_fetch)
    cache = fetch_bceao_rates(cache, now=10_001.0, fetch=failing_fetch)
    assert len(calls) == 1
    assert cache["rates"] == DEFAULT_RATES
    fetch_bceao_rates(cache, now=10_000.0 + FX_CACHE_TTL + 1, fetch=failing_fetch)
    assert len(calls) == 2
