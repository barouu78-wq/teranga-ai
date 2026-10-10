"""Diagnostic TLS par adresse (scripts/diagnose_tls.py) : aucun accès réseau, certificats générés localement."""
import io
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

from scripts import diagnose_tls as d

SCRIPT = Path(d.__file__)

SELF_SIGNED_OUTPUT = """CONNECTED(00000003)
depth=0 CN = TRAEFIK DEFAULT CERT
verify error:num=18:self-signed certificate
---
Certificate chain
 0 s:CN = TRAEFIK DEFAULT CERT
-----BEGIN CERTIFICATE-----
MIIBfake
-----END CERTIFICATE-----
---
    Verification error: self-signed certificate
    Verify return code: 18 (self-signed certificate)
"""
VALID_OUTPUT = SELF_SIGNED_OUTPUT.replace("18 (self-signed certificate)", "0 (ok)").replace(
    "Verification error: self-signed certificate", "Verification: OK")
REFUSED_OUTPUT = "40C7:error:8000006F:system library:BIO_connect:Connection refused\nconnect:errno=111\n"


@pytest.fixture(scope="module")
def self_signed_pem(tmp_path_factory):
    assert shutil.which("openssl"), "openssl est requis pour analyser les certificats (outil standard)"
    folder = tmp_path_factory.mktemp("tls")
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1", "-nodes", "-days", "30",
         "-subj", "/CN=TRAEFIK DEFAULT CERT", "-keyout", str(folder / "k.pem"), "-out", str(folder / "c.pem")],
        check=True, capture_output=True,
    )
    return (folder / "c.pem").read_text()


def test_parse_s_client_reads_verification_result_and_certificate():
    bad = d.parse_s_client(SELF_SIGNED_OUTPUT)
    assert bad["joignable"] and bad["verification"] == "echec" and bad["code"] == 18
    assert bad["message"] == "self-signed certificate" and bad["pem"].startswith("-----BEGIN CERTIFICATE-----")
    good = d.parse_s_client(VALID_OUTPUT)
    assert good["verification"] == "ok" and good["code"] == 0


def test_parse_s_client_reports_unreachable_servers_without_inventing_a_verdict():
    refused = d.parse_s_client(REFUSED_OUTPUT)
    assert refused["joignable"] is False and refused["verification"] is None
    assert "refused" in refused["message"].lower()
    assert d.parse_s_client("")["message"] == "aucun certificat reçu"


def test_describe_cert_flags_a_self_signed_default_proxy_certificate(self_signed_pem):
    info = d.describe_cert(self_signed_pem)
    assert info["sujet"] == "CN = TRAEFIK DEFAULT CERT" and info["emetteur"] == info["sujet"]
    assert info["auto_signe"] is True and info["certificat_par_defaut"] is True
    assert info["expire"] is False and info["fin"] and len(info["sha256"]) == 95  # 32 octets en hexadécimal séparés par ':'


def test_expiry_is_computed_from_the_certificate_end_date():
    assert d._expired("Jan  1 00:00:00 2020 GMT") is True
    assert d._expired("Jan  1 00:00:00 2999 GMT") is False
    assert d._expired("pas une date") is None and d._expired(None) is None


def test_resolve_lists_each_address_once_with_its_family():
    fake = lambda host, port, type=0: [  # noqa: E731
        (socket.AF_INET, 1, 6, "", ("203.0.113.10", 443)),
        (socket.AF_INET, 1, 6, "", ("203.0.113.10", 443)),
        (socket.AF_INET6, 1, 6, "", ("2001:db8::1", 443, 0, 0)),
    ]
    assert d.resolve("teranga-ai.fr", fake) == [{"ip": "203.0.113.10", "famille": "IPv4"}, {"ip": "2001:db8::1", "famille": "IPv6"}]


def test_probe_refuses_anything_that_is_not_an_address_or_a_hostname():
    calls = []
    with pytest.raises(ValueError):
        d.probe("-evil", "203.0.113.10", lambda *a, **k: calls.append(a))
    with pytest.raises(ValueError):
        d.probe("teranga-ai.fr", "203.0.113.10 -x", lambda *a, **k: calls.append(a))
    assert calls == []  # rien n'est exécuté avant la validation


def test_probe_builds_a_fixed_command_for_ipv4_and_ipv6():
    seen = []

    def fake(cmd, **kwargs):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=REFUSED_OUTPUT, stderr="")

    d.probe("teranga-ai.fr", "203.0.113.10", fake)
    d.probe("www.teranga-ai.fr", "2001:db8::1", fake)
    assert seen[0][:4] == ["openssl", "s_client", "-connect", "203.0.113.10:443"]
    assert seen[1][3] == "[2001:db8::1]:443" and "www.teranga-ai.fr" in seen[1]
    assert all("-verify_hostname" in cmd for cmd in seen)  # le nom est vérifié, pas seulement la chaîne


def _probe(ip, state, subject="CN = demo", **extra):
    cert = {"sujet": subject, "emetteur": subject if extra.get("auto_signe") else "CN = R10", "fin": "Jan  1 00:00:00 2999 GMT",
            "noms": extra.get("noms", ["teranga-ai.fr"]), "auto_signe": extra.get("auto_signe", False),
            "certificat_par_defaut": "default" in subject.lower(), "expire": extra.get("expire", False)}
    return {"ip": ip, "joignable": True, "verification": state, "code": 0 if state == "ok" else 18, "message": "m",
            "certificat": cert}


def test_summary_all_valid():
    out = d.summarize("teranga-ai.fr", [_probe("1.1.1.1", "ok"), _probe("1.1.1.2", "ok")])
    assert out["verdict"] == "ok" and out["adresses_en_echec"] == [] and out["notes"] == []


def test_summary_mixed_explains_why_failures_depend_on_the_connection_not_the_path():
    out = d.summarize("teranga-ai.fr", [
        _probe("1.1.1.1", "ok"),
        _probe("2.2.2.2", "echec", subject="CN = TRAEFIK DEFAULT CERT", auto_signe=True, noms=[]),
    ])
    assert out["verdict"] == "mixte"
    assert out["adresses_valides"] == ["1.1.1.1"] and out["adresses_en_echec"] == ["2.2.2.2"]
    text = " ".join(out["notes"])
    assert "quel que soit le chemin" in text and "Hypothèse" in text
    assert "certificat par défaut de proxy" in text and "2.2.2.2" in text


def test_summary_all_failing_and_unreachable_and_no_address():
    failing = d.summarize("teranga-ai.fr", [_probe("2.2.2.2", "echec", auto_signe=True)])
    assert failing["verdict"] == "echec" and "auto-signé" in " ".join(failing["notes"])
    down = d.summarize("teranga-ai.fr", [{"ip": "::1", "joignable": False, "verification": None, "message": "x"}])
    assert down["verdict"] == "injoignable" and "IPv6" in down["notes"][0]
    assert d.summarize("teranga-ai.fr", [])["verdict"] == "aucune_adresse"


def test_summary_reports_expired_and_wrong_name_certificates():
    out = d.summarize("teranga-ai.fr", [_probe("3.3.3.3", "echec", expire=True, noms=["autre-site.example"])])
    text = " ".join(out["notes"])
    assert "expiré" in text and "ne couvre pas teranga-ai.fr" in text
    wildcard = d.summarize("www.teranga-ai.fr", [_probe("3.3.3.3", "echec", noms=["*.teranga-ai.fr"])])
    assert "ne couvre pas" not in " ".join(wildcard["notes"])


def test_main_json_report_and_exit_code():
    resolver = lambda host: [{"ip": "1.1.1.1", "famille": "IPv4"}, {"ip": "2.2.2.2", "famille": "IPv4"}]  # noqa: E731
    prober = lambda host, ip: _probe(ip, "ok" if ip == "1.1.1.1" else "echec", auto_signe=ip == "2.2.2.2")  # noqa: E731
    out = io.StringIO()
    code = d.main(["--json", "teranga-ai.fr"], resolver, prober, out)
    report = json.loads(out.getvalue())
    assert code == 1 and report["tout_ok"] is False
    assert report["hotes"][0]["resume"]["verdict"] == "mixte"
    assert [a["famille"] for a in report["hotes"][0]["adresses"]] == ["IPv4", "IPv4"]
    ok = io.StringIO()
    assert d.main(["teranga-ai.fr"], resolver, lambda host, ip: _probe(ip, "ok"), ok) == 0
    assert "== teranga-ai.fr : ok" in ok.getvalue()


def test_json_file_is_written_next_to_the_readable_summary(tmp_path):
    target = tmp_path / "rapport.json"
    out = io.StringIO()
    resolver = lambda host: [{"ip": "1.1.1.1", "famille": "IPv4"}]  # noqa: E731
    code = d.main(["--json-file", str(target), "teranga-ai.fr"], resolver, lambda host, ip: _probe(ip, "ok"), out)
    assert code == 0 and "== teranga-ai.fr : ok" in out.getvalue()
    assert json.loads(target.read_text(encoding="utf-8"))["hotes"][0]["resume"]["verdict"] == "ok"


def test_dns_failure_is_reported_not_raised():
    def broken(host):
        raise socket.gaierror("Name or service not known")

    report = d.run_diagnosis(["teranga-ai.fr"], broken, lambda h, ip: {})
    assert report["hotes"][0]["erreur_dns"] and report["hotes"][0]["resume"]["verdict"] == "aucune_adresse"


def test_default_hosts_cover_the_root_and_www_names():
    assert d.DEFAULT_HOSTS == ("teranga-ai.fr", "www.teranga-ai.fr")


def test_the_diagnostic_never_weakens_tls_in_code():
    """Règle du dépôt : on observe un certificat non valide, on ne désactive jamais la vérification."""
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("CERT_NONE", "check_hostname = False", "_create_unverified_context", "verify=False", " -k ", "--insecure",
                      "shell=True"):
        assert forbidden not in source, forbidden
    assert "import ssl" not in source  # pas de contexte TLS à configurer : seule la sortie d'openssl est lue
