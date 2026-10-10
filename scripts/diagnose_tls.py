#!/usr/bin/env python3
"""Diagnostic TLS par adresse : quel serveur présente quel certificat pour teranga-ai.fr ?

Un nom de domaine peut pointer vers plusieurs serveurs (enregistrements DNS multiples). Si l'un d'eux présente
un certificat par défaut ou auto-signé, certaines connexions réussissent et d'autres échouent, y compris pour
des chemins différents du même site. Ce script résout chaque nom, puis lit, adresse par adresse, le certificat
présenté et le résultat de la vérification officielle d'OpenSSL.

Lecture seule : aucune requête HTTP, aucun contenu récupéré. La vérification TLS des contrôles réels
(`audits-seo-performance.yml`) n'est jamais assouplie : ce script ne fait qu'observer et rapporter.

    python scripts/diagnose_tls.py              # résumé lisible
    python scripts/diagnose_tls.py --json       # rapport JSON
    python scripts/diagnose_tls.py --json-file rapport.json   # résumé lisible + rapport JSON dans un fichier
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_HOSTS = ("teranga-ai.fr", "www.teranga-ai.fr")
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
PEM_RE = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)
VERIFY_RE = re.compile(r"Verify return code:\s*(\d+)\s*\(([^)]*)\)")
# Certificats que des proxys (Traefik, Kubernetes, Caddy) présentent faute de certificat valide pour le nom demandé.
DEFAULT_CERT_MARKERS = ("traefik default cert", "kubernetes ingress controller fake certificate", "default certificate")


def resolve(host, getaddrinfo=socket.getaddrinfo):
    """Adresses (IPv4 et IPv6) du nom, sans doublon, dans l'ordre renvoyé par le système."""
    found = []
    for family, _, _, _, sockaddr in getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        ip = sockaddr[0]
        if all(item["ip"] != ip for item in found):
            found.append({"ip": ip, "famille": "IPv6" if family == socket.AF_INET6 else "IPv4"})
    return found


def parse_s_client(text):
    """Extrait de la sortie d'`openssl s_client` : résultat de la vérification et premier certificat présenté."""
    pem = PEM_RE.search(text)
    verify = VERIFY_RE.search(text)
    if not pem:
        return {"joignable": False, "verification": None, "code": None, "message": _first_error(text), "pem": None}
    code = int(verify.group(1)) if verify else None
    return {
        "joignable": True,
        "verification": "ok" if code == 0 else "echec",
        "code": code,
        "message": verify.group(2) if verify else "résultat de vérification absent",
        "pem": pem.group(0),
    }


def _first_error(text):
    for line in text.splitlines():
        low = line.lower()
        if "errno" in low or "error" in low or "refused" in low or "timed out" in low or "unreachable" in low:
            return line.strip()[:200]
    return "aucun certificat reçu"


def describe_cert(pem, run=subprocess.run):
    """Sujet, émetteur, dates, empreinte et noms d'un certificat PEM (analysé par `openssl x509`)."""
    out = run(
        ["openssl", "x509", "-noout", "-subject", "-issuer", "-dates", "-fingerprint", "-sha256", "-ext", "subjectAltName"],
        input=pem, capture_output=True, text=True, timeout=15, check=False,
    ).stdout
    info = {"sujet": None, "emetteur": None, "debut": None, "fin": None, "sha256": None, "noms": []}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("subject="):
            info["sujet"] = line.split("=", 1)[1].strip()
        elif line.startswith("issuer="):
            info["emetteur"] = line.split("=", 1)[1].strip()
        elif line.startswith("notBefore="):
            info["debut"] = line.split("=", 1)[1].strip()
        elif line.startswith("notAfter="):
            info["fin"] = line.split("=", 1)[1].strip()
        elif "Fingerprint=" in line:
            info["sha256"] = line.split("=", 1)[1].strip()
        else:
            info["noms"].extend(re.findall(r"DNS:([^,\s]+)", line))
    info["auto_signe"] = bool(info["sujet"]) and _norm(info["sujet"]) == _norm(info["emetteur"])
    info["certificat_par_defaut"] = any(m in (info["sujet"] or "").lower() for m in DEFAULT_CERT_MARKERS)
    info["expire"] = _expired(info["fin"])
    return info


def _norm(dn):
    return re.sub(r"\s+", "", dn or "").lower()


def _expired(not_after, now=None):
    if not not_after:
        return None
    try:
        end = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return end < (now or datetime.now(timezone.utc))


def probe(host, ip, run=subprocess.run):
    """Lit le certificat que `ip` présente pour le nom `host` (SNI) et le résultat de la vérification OpenSSL."""
    ipaddress.ip_address(ip)  # refuse tout ce qui n'est pas une adresse (pas d'option injectée dans la commande)
    if not HOST_RE.match(host):
        raise ValueError("nom d'hôte invalide")
    target = f"[{ip}]:443" if ":" in ip else f"{ip}:443"
    try:
        done = run(
            ["openssl", "s_client", "-connect", target, "-servername", host, "-verify_hostname", host, "-showcerts"],
            input="", capture_output=True, text=True, timeout=25, check=False,
        )
        text = done.stdout + "\n" + done.stderr
    except subprocess.TimeoutExpired:
        return {"ip": ip, "joignable": False, "verification": None, "code": None, "message": "délai dépassé"}
    result = parse_s_client(text)
    pem = result.pop("pem")
    result["ip"] = ip
    if pem:
        result["certificat"] = describe_cert(pem, run)
    return result


def summarize(host, probes):
    """Verdict factuel pour un nom ; les causes proposées sont des hypothèses à confirmer côté DNS et hébergeur."""
    reached = [p for p in probes if p.get("joignable")]
    good = [p["ip"] for p in reached if p["verification"] == "ok"]
    bad = [p for p in reached if p["verification"] != "ok"]
    notes = []
    if not probes:
        verdict = "aucune_adresse"
    elif not reached:
        verdict = "injoignable"
        notes.append("Aucune adresse n'a répondu en TLS depuis ce poste (une adresse IPv6 est inaccessible sur les runners GitHub).")
    elif bad and good:
        verdict = "mixte"
        notes.append(
            "Plusieurs serveurs répondent pour ce nom et certains présentent un certificat non valide : une connexion "
            "sur deux peut échouer, quel que soit le chemin demandé. Hypothèse à confirmer : le DNS pointe vers plusieurs serveurs."
        )
    elif bad:
        verdict = "echec"
        notes.append("Aucune adresse ne présente de certificat valide pour ce nom.")
    else:
        verdict = "ok"
    for p in bad:
        cert = p.get("certificat") or {}
        if cert.get("certificat_par_defaut"):
            notes.append(f"{p['ip']} présente un certificat par défaut de proxy ({cert.get('sujet')}) : hypothèse, le proxy n'a "
                         "pas de certificat valide pour ce nom (émission Let's Encrypt non faite, nom non rattaché).")
        elif cert.get("auto_signe"):
            notes.append(f"{p['ip']} présente un certificat auto-signé ({cert.get('sujet')}).")
        if cert.get("expire"):
            notes.append(f"{p['ip']} présente un certificat expiré (fin : {cert.get('fin')}).")
        if cert.get("noms") and host not in cert["noms"] and not any(
                n.startswith("*.") and host.endswith(n[1:]) for n in cert["noms"]):
            notes.append(f"{p['ip']} : le certificat ne couvre pas {host} (noms : {', '.join(cert['noms'])}).")
    return {"hote": host, "verdict": verdict, "adresses_valides": good,
            "adresses_en_echec": [p["ip"] for p in bad], "notes": notes}


def run_diagnosis(hosts, resolver=resolve, prober=probe):
    report = {"verification_tls": "Aucune : le diagnostic lit les certificats, il ne contourne ni n'assouplit aucun contrôle.",
              "hotes": []}
    for host in hosts:
        entry = {"hote": host, "adresses": [], "erreur_dns": None}
        try:
            addresses = resolver(host)
        except OSError as exc:
            entry["erreur_dns"] = str(exc)[:200]
            addresses = []
        for address in addresses:
            probed = prober(host, address["ip"])
            probed["famille"] = address["famille"]
            entry["adresses"].append(probed)
        entry["resume"] = summarize(host, entry["adresses"])
        report["hotes"].append(entry)
    report["tout_ok"] = all(e["resume"]["verdict"] == "ok" for e in report["hotes"])
    return report


def render(report):
    lines = []
    for entry in report["hotes"]:
        lines.append(f"== {entry['hote']} : {entry['resume']['verdict']}")
        if entry["erreur_dns"]:
            lines.append(f"   DNS : {entry['erreur_dns']}")
        for p in entry["adresses"]:
            cert = p.get("certificat") or {}
            state = p["verification"] or "injoignable"
            lines.append(f"   {p['famille']} {p['ip']} : vérification={state} ({p['message']}) sujet={cert.get('sujet')} "
                         f"émetteur={cert.get('emetteur')} fin={cert.get('fin')} sha256={cert.get('sha256')}")
        lines.extend(f"   - {note}" for note in entry["resume"]["notes"])
    return "\n".join(lines)


def main(argv=None, resolver=resolve, prober=probe, out=sys.stdout):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("hosts", nargs="*", default=list(DEFAULT_HOSTS))
    parser.add_argument("--json", action="store_true", help="écrit le rapport JSON au lieu du résumé")
    parser.add_argument("--json-file", help="enregistre aussi le rapport JSON dans ce fichier")
    args = parser.parse_args(argv)
    report = run_diagnosis(args.hosts, resolver, prober)
    if args.json_file:
        with open(args.json_file, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    out.write((json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report)) + "\n")
    return 0 if report["tout_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
