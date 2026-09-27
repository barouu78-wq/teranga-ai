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
