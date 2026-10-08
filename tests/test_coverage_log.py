"""Journal des lacunes : thèmes, couvert / non couvert, aucune donnée personnelle, page /stats-ia protégée."""

import datetime as dt
import hashlib
import os
import re
import threading
import time

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import app as app_module  # noqa: E402
from services import coverage_log as cl  # noqa: E402
from routes.coverage import render_coverage_page  # noqa: E402
from services.coverage_log import CoverageLog, THEME_LABELS, THEMES, chat_signals, classify, themes_of  # noqa: E402
from services.text import fold_text  # noqa: E402

B = "https://teranga-ai.fr"
TOKEN = "un-mot-de-passe-solide-123"
DAY = dt.date(2026, 10, 8)


# --- Faux Redis -----------------------------------------------------------------------------------------------------

class FakePipe:
    def __init__(self, redis):
        self.redis, self.ops = redis, []

    def hincrby(self, key, field, amount):
        self.ops.append(("hincrby", key, field, amount))

    def expire(self, key, seconds):
        self.ops.append(("expire", key, seconds))

    def hgetall(self, key):
        self.ops.append(("hgetall", key))

    def execute(self):
        self.redis.gate.wait(5)
        out = []
        for op in self.ops:
            if op[0] == "hincrby":
                bucket = self.redis.hashes.setdefault(op[1], {})
                bucket[op[2]] = bucket.get(op[2], 0) + op[3]
                out.append(bucket[op[2]])
            elif op[0] == "expire":
                self.redis.ttls[op[1]] = op[2]
                out.append(True)
            else:
                out.append({k: str(v) for k, v in self.redis.hashes.get(op[1], {}).items()})
        self.redis.done.set()
        return out


class FakeRedis:
    def __init__(self):
        self.hashes, self.ttls = {}, {}
        self.gate, self.done = threading.Event(), threading.Event()
        self.gate.set()

    def pipeline(self, transaction=False):
        return FakePipe(self)

    def dump(self) -> str:
        """Tout ce que Redis contient : clés, champs, valeurs."""
        return repr(self.hashes) + repr(self.ttls)


class BrokenRedis:
    def pipeline(self, transaction=False):
        raise ConnectionError("redis en panne")


def _payload(message, signals=(), **extra):
    """Charge utile minimale : le texte du contexte contient les titres que la base y met."""
    headers = {
        "lieux": "LIEUX PERTINENTS :", "regions": "CONTEXTE RÉGIONAL PERTINENT :", "plats": "PLATS ET BOISSONS PERTINENTS :",
        "fetes": "PROCHAINES FÊTES ET ÉVÉNEMENTS AU SÉNÉGAL (dates estimées) :",
    }
    instructions = "Prompt système.\n\n" + "\n".join(headers[s] + "\n- x" for s in signals if s in headers)
    return {"message": message, "instructions": instructions, "use_web": "web" in signals, **extra}


# --- Vocabulaire fermé ----------------------------------------------------------------------------------------------

def test_vocabulary_is_closed_and_well_formed():
    ids = [theme.id for theme in THEMES]
    assert len(ids) == len(set(ids)) and 30 <= len(ids) <= 40
    assert cl.OTHER not in ids and THEME_LABELS[cl.OTHER]
    for theme in THEMES:
        assert re.fullmatch(r"[a-z_]+", theme.id) and theme.label and theme.keywords
        for keyword in theme.keywords:
            if not keyword.startswith("re:"):
                plain = keyword.rstrip("*")
                assert plain == fold_text(plain), f"{theme.id}: « {keyword} » doit être sans accents ni majuscules"
        assert all(c.startswith("repere:") or c in {"cite", "lieux", "personnes", "histoire", "plats", "partenaires", "guide",
                                                    "marche", "fetes", "meteo", "wolof", "pulaar"} for c in theme.covers), theme.id


def test_practical_topics_used_for_coverage_exist():
    from services.practical_facts import TOPICS

    known = {name for name, _, _ in TOPICS}
    used = {c.removeprefix("repere:") for theme in THEMES for c in theme.covers if c.startswith("repere:")}
    assert used <= known, f"repères pratiques disparus ou renommés : {used - known}"


@pytest.mark.parametrize("question,expected", [
    ("Quel est le numéro de la police ?", {"urgences"}),
    ("On m'a volé mon sac", {"urgences"}),
    ("Je cherche un docteur à Thiès", {"sante"}),
    ("Comment cultiver l'arachide ?", {"agriculture"}),
    ("Où pêcher à Joal ?", {"peche"}),
    ("Comment divorcer au Sénégal ?", {"justice"}),
    ("Comment trouver du travail à Dakar ?", {"emploi"}),
    ("Comment créer une entreprise ?", {"entreprise"}),
    ("Y a-t-il des éléphants au Sénégal ?", {"nature"}),
    ("Qui était Senghor ?", {"culture"}),
    ("Comment inscrire mon enfant à l'école ?", {"etudes", "famille"}),
    ("Peut-on payer avec Wave ?", {"argent"}),
    ("Where can I find a good restaurant in Dakar?", {"cuisine"}),
    ("Quelle est la religion majoritaire ?", {"religion"}),
    ("Un vol Paris-Dakar direct ?", {"transport"}),
    ("Quelle est la meilleure période pour partir ?", {"meteo"}),
    ("C'est quand la Tabaski ?", {"fetes"}),
    ("Comment obtenir mon acte de naissance ?", {"papiers"}),
    ("Parle-moi du wolof", {"langue"}),
    ("Combien coûte la vie à Dakar ?", {"economie"}),
])
def test_themes_are_recognised(question, expected):
    assert expected <= set(themes_of(question))


@pytest.mark.parametrize("question,forbidden", [
    ("Comment créer une entreprise ?", "electricite"),   # « prise » dans « entreprise »
    ("Comment ça marche ?", "artisanat"),                # « marche » de « ça marche »
    ("Je suis sur Dakar", "urgences"),                   # « sur »
    ("J'ai un vol demain matin", "urgences"),            # « vol » (avion) n'est pas un vol subi
    ("Où se trouve le plateau ?", "cuisine"),            # « plat » dans « plateau »
    ("Quelle est la meilleure aide possible ?", "fetes"),  # « aid » dans « aide »
])
def test_no_false_positive_on_look_alike_words(question, forbidden):
    assert forbidden not in themes_of(question)


def test_question_without_known_theme_goes_to_other():
    assert themes_of("Comment ça marche ?") == ["autre"]
    assert themes_of("zxqv blorp") == ["autre"]


def test_practical_topic_keeps_its_theme_even_without_keyword():
    # « prises » est reconnu par practical_facts : la question garde son thème.
    from services.practical_facts import matching_topics

    signals = frozenset("repere:" + t for t in matching_topics("Quelles prises au Sénégal ?"))
    assert "repere:electricite" in signals and "electricite" in themes_of("Quelles prises au Sénégal ?", signals)


def test_bare_place_or_dish_name_gets_its_theme_from_what_the_base_found():
    places = app_module.SENEGAL_KNOWLEDGE["places"]
    signals = chat_signals(_payload("Gorée", ["lieux"]), places)
    assert "cite" in signals and themes_of("Gorée", signals) == ["voyage"]
    assert themes_of("Saint-Louis", chat_signals(_payload("Saint-Louis"), places)) == ["voyage"]
    assert themes_of("ndambe", frozenset({"plats"})) == ["cuisine"]
    assert themes_of("le Cayor", frozenset({"histoire"})) == ["culture"]
    # Mots qui ressemblent à un lieu sans en citer : pas de thème inventé.
    assert themes_of("Comment ça marche ?", chat_signals(_payload("Comment ça marche ?", ["lieux", "regions"]), places)) == ["autre"]


# --- Couvert / non couvert ------------------------------------------------------------------------------------------

def test_covered_depends_on_what_the_context_held_for_that_theme():
    nothing, web = frozenset(), frozenset({"web"})
    assert classify("Comment divorcer ?", nothing) == {"justice": False}
    assert classify("Comment divorcer ?", web) == {"justice": True}          # une recherche web déclenchée couvre
    assert classify("Faut-il un visa ?", frozenset({"repere:visa"})) == {"visa": True}
    # Un repère sur un autre sujet ne couvre pas : visa fourni, mais la question parle aussi d'emploi.
    mixed = classify("Faut-il un visa pour travailler ?", frozenset({"repere:visa"}))
    assert mixed["visa"] is True and mixed["emploi"] is False
    # Les signaux larges (lieux choisis par recoupement de mots) ne couvrent ni l'emploi ni « autre ».
    loose = frozenset({"lieux", "regions", "personnes"})
    assert classify("Comment trouver du travail ?", loose) == {"emploi": False}
    assert classify("zxqv blorp", loose) == {"autre": False}
    assert classify("zxqv blorp", frozenset({"partenaires"})) == {"autre": True}


def test_signals_come_from_the_real_context_titles():
    """Garde-fou : si un titre du contexte change (base, fêtes, partenaires), les signaux s'éteindraient sans bruit."""
    from services.events import events_context
    from services.monetization import partners_context
    from services.senegal_knowledge import format_senegal_knowledge

    knowledge, people = app_module.SENEGAL_KNOWLEDGE, app_module.SENEGAL_PEOPLE

    def signals_for(text):
        return chat_signals({"message": "x", "instructions": text})

    assert {"lieux", "regions"} <= signals_for(format_senegal_knowledge(knowledge, query="Gorée", people=people))
    assert "plats" in signals_for(format_senegal_knowledge(knowledge, query="Le yassa", people=people))
    assert "personnes" in signals_for(format_senegal_knowledge(knowledge, query="Senghor", people=people))
    assert "histoire" in signals_for(format_senegal_knowledge(knowledge, query="Le royaume du Cayor", people=people))
    assert "wolof" in signals_for(format_senegal_knowledge(knowledge, query="Des phrases en wolof", people=people))
    assert "pulaar" in signals_for(format_senegal_knowledge(knowledge, query="Quelques mots de pulaar", people=people))
    assert "fetes" in signals_for(events_context(query="Tabaski"))
    assert "partenaires" in signals_for(partners_context([{"name": "Hôtel Test", "category": "hôtel", "description": "x"}]))
    assert signals_for("Prompt système sans titre.") == frozenset()


def _real_payload(message):
    with app_module.app.test_request_context("/chat", method="POST", json={"message": message, "language": "fr"}):
        payload, error = app_module.parse_chat_payload()
    assert error is None
    return payload


def test_real_chat_context_is_read_correctly():
    places = app_module.SENEGAL_KNOWLEDGE["places"]
    gor = chat_signals(_real_payload("Parle-moi de Gorée"), places)
    assert {"lieux", "cite"} <= gor
    visa = chat_signals(_real_payload("Faut-il un visa pour le Sénégal ?"), places)
    assert "repere:visa" in visa
    divorce = chat_signals(_real_payload("Comment divorcer au Sénégal ?"), places)
    assert classify("Comment divorcer au Sénégal ?", divorce) == {"justice": False}
    fete = chat_signals(_real_payload("C'est quand la Tabaski ?"), places)
    assert "fetes" in fete and classify("C'est quand la Tabaski ?", fete) == {"fetes": True}
    guide = chat_signals(_real_payload("Raconte-moi l'histoire de Gorée, fais-moi visiter"), places)
    assert "guide" in guide


# --- Écriture : Redis, mémoire, pannes ------------------------------------------------------------------------------

def test_record_adds_daily_counters_per_theme_in_memory():
    log = CoverageLog()
    log.record({"sante": False, "voyage": True}, day=DAY)
    log.record({"sante": False}, day=DAY)
    assert log._memory == {"2026-10-08": {"total": 2, "sante|n": 2, "voyage|c": 1}}
    log.record({"inventé": True, "evil|c": True}, day=DAY)  # hors vocabulaire : refusé, pas même compté
    assert log._memory["2026-10-08"]["total"] == 2 and set(log._memory["2026-10-08"]) == {"total", "sante|n", "voyage|c"}


def test_redis_receives_only_vocabulary_fields_with_a_90_day_lifetime():
    redis = FakeRedis()
    log = CoverageLog(redis, background=False)
    log.record({"justice": False, "autre": True}, day=DAY)
    assert redis.hashes == {"teranga:coverage:2026-10-08": {"total": 1, "justice|n": 1, "autre|c": 1}}
    assert redis.ttls == {"teranga:coverage:2026-10-08": 90 * 24 * 3600}
    assert log._memory == {}


def test_redis_write_runs_in_the_background_and_never_blocks_the_answer():
    redis = FakeRedis()
    redis.gate.clear()  # Redis « bloqué » : execute() attend
    log = CoverageLog(redis)  # mode normal : écriture dans un fil
    started = time.perf_counter()
    log.record_chat(_payload("Comment divorcer au Sénégal ?"), "Mozilla/5.0 (Android 14) Chrome/120")
    assert time.perf_counter() - started < 1  # la réponse du chat n'attend pas
    assert redis.hashes == {}
    redis.gate.set()
    assert redis.done.wait(5)
    assert next(iter(redis.hashes.values()))["justice|n"] == 1


def test_too_many_pending_redis_writes_fall_back_to_memory_without_waiting():
    redis = FakeRedis()
    log = CoverageLog(redis)
    log._writers = threading.BoundedSemaphore(0)  # aucun fil d'écriture disponible
    log.record({"sante": True}, day=DAY)
    assert redis.hashes == {} and log._memory["2026-10-08"]["sante|c"] == 1


def test_live_weather_and_modes_count_as_context():
    signals = chat_signals({"message": "x", "instructions": "", "live_weather": True, "modes": ["market_practice", "guide", "autre"]})
    assert signals == {"meteo", "marche", "guide"}
    assert classify("Quel temps fait-il demain ?", signals) == {"meteo": True}


def test_redis_without_pipeline_is_supported():
    class PlainRedis:
        def __init__(self):
            self.hashes, self.ttls = {}, {}

        def hincrby(self, key, field, amount):
            self.hashes.setdefault(key, {})[field] = self.hashes.get(key, {}).get(field, 0) + amount

        def expire(self, key, seconds):
            self.ttls[key] = seconds

        def hgetall(self, key):
            return {field.encode(): str(value).encode() for field, value in self.hashes.get(key, {}).items()}

    redis = PlainRedis()
    log = CoverageLog(redis, background=False)
    log.record({"justice": False}, day=DAY)
    assert redis.hashes == {"teranga:coverage:2026-10-08": {"total": 1, "justice|n": 1}}
    assert log.summary(today=DAY)["themes"][0]["id"] == "justice"  # champs en octets acceptés


def test_thread_start_failure_is_absorbed(monkeypatch):
    log = CoverageLog(FakeRedis())

    def refuse(*args, **kwargs):
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(cl.threading, "Thread", refuse)
    log.record({"sante": True}, day=DAY)
    assert log._memory["2026-10-08"]["sante|c"] == 1
    assert log._writers.acquire(blocking=False)  # le jeton a été rendu


def test_redis_outage_falls_back_to_memory_and_is_logged_without_content(caplog):
    log = CoverageLog(BrokenRedis(), logger=app_module.app.logger, background=False)
    with caplog.at_level("WARNING"):
        log.record_chat(_payload("Mon numéro 771234567, comment divorcer ?"), "Mozilla/5.0 Chrome/120")
        summary = log.summary()  # la lecture panne aussi : elle ne plante pas
    assert any(t["id"] == "justice" and t["uncovered"] == 1 for t in summary["themes"])
    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "coverage-log" in logs and "771234567" not in logs and "divorcer" not in logs


def test_memory_keeps_at_most_90_days():
    log = CoverageLog()
    today = dt.date.today()
    log.record({"sante": True}, day=today - dt.timedelta(days=120))
    log.record({"sante": True}, day=today)
    assert list(log._memory) == [today.isoformat()]


# --- Ce qui n'est pas compté ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("agent", ["", "Googlebot/2.1 (+http://www.google.com/bot.html)", "curl/8.4.0", "python-requests/2.32",
                                   "Mozilla/5.0 (X11; Linux) HeadlessChrome/120", "GPTBot/1.0"])
def test_robots_are_not_counted(agent):
    log = CoverageLog()
    log.record_chat(_payload("Comment divorcer au Sénégal ?"), agent)
    assert log._memory == {}


@pytest.mark.parametrize("agent", [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Werkzeug/3.0.1",
])
def test_real_browsers_are_counted(agent):
    log = CoverageLog()
    log.record_chat(_payload("Comment divorcer au Sénégal ?"), agent)
    assert log._memory[dt.date.today().isoformat()]["justice|n"] == 1


@pytest.mark.parametrize("message", ["", "   ", "???", "Bonjour", "Merci beaucoup !", "ok", "Oui, merci", "Salam aleikoum", "d'accord"])
def test_greetings_and_empty_messages_are_not_questions(message):
    log = CoverageLog()
    log.record_chat(_payload(message), "Mozilla/5.0 Chrome/120")
    assert log._memory == {}


def test_photo_requests_and_malformed_payloads_are_not_counted():
    log = CoverageLog()
    log.record_chat(_payload("Montre-moi des photos de Gorée", photo_only=True), "Mozilla/5.0 Chrome/120")
    log.record_chat(None, "Mozilla/5.0 Chrome/120")
    log.record_chat({}, "Mozilla/5.0 Chrome/120")
    assert log._memory == {}


def test_an_accident_inside_the_journal_is_swallowed(monkeypatch):
    log = CoverageLog()
    monkeypatch.setattr(cl, "classify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boum")))
    log.record_chat(_payload("Comment divorcer ?"), "Mozilla/5.0 Chrome/120")  # ne lève rien
    assert log._memory == {}


# --- Lecture : priorité, fenêtre de 30 jours, champs étrangers ignorés ----------------------------------------------

def test_summary_sorts_by_missing_context_and_ignores_foreign_fields():
    redis = FakeRedis()
    log = CoverageLog(redis, background=False)
    for _ in range(3):
        log.record({"sante": False}, day=DAY)
    for _ in range(10):
        log.record({"voyage": True}, day=DAY)
    log.record({"voyage": False}, day=DAY - dt.timedelta(days=29))
    log.record({"emploi": False}, day=DAY)
    log.record({"emploi": False}, day=DAY - dt.timedelta(days=30))  # hors des 30 jours
    redis.hashes["teranga:coverage:2026-10-08"].update({"texte libre|n": 99, "evil|c": 99, "sante|x": 99})
    summary = log.summary(today=DAY)
    assert summary["days"] == 30 and summary["storage"] == "redis" and summary["total"] == 15
    rows = [(t["id"], t["questions"], t["uncovered"]) for t in summary["themes"]]
    assert rows == [("sante", 3, 3), ("emploi", 1, 1), ("voyage", 11, 1)]  # emploi : 100 % ; voyage : 1 sur 11
    assert summary["themes"][2]["share"] == pytest.approx(1 / 11)
    assert not any("texte" in repr(t) or "evil" in repr(t) for t in summary["themes"])


def test_summary_adds_memory_counted_during_an_outage():
    redis = FakeRedis()
    log = CoverageLog(redis, background=False)
    log.record({"sante": False}, day=DAY)
    log._store_memory("2026-10-07", ["total", "sante|n"])
    summary = log.summary(today=DAY)
    assert summary["total"] == 2 and summary["themes"][0]["uncovered"] == 2


# --- Aucune donnée personnelle, sur la vraie route du chat ----------------------------------------------------------

def _chat(ip, message, agent=None, mode_json=True):
    client = app_module.app.test_client()
    token_response = client.get("/csrf", base_url=B)
    token = token_response.get_json()["token"]
    client.set_cookie("teranga_csrf", token, domain="teranga-ai.fr")
    headers = {"X-CSRF-Token": token, "Origin": B}
    if mode_json:
        headers["X-Teranga-Mode"] = "json"
    if agent:
        headers["User-Agent"] = agent
    response = client.post("/chat", json={"message": message, "language": "fr"}, headers=headers, base_url=B,
                           environ_base={"REMOTE_ADDR": ip})
    cookies = token_response.headers.getlist("Set-Cookie") + response.headers.getlist("Set-Cookie")
    return response, [token] + [c.split(";")[0].split("=", 1)[1] for c in cookies if "=" in c]


@pytest.fixture
def journal(monkeypatch):
    """Journal de l'application, vide, avec un faux Redis lisible, et une IA simulée."""
    log = app_module.COVERAGE_LOG
    redis = FakeRedis()
    monkeypatch.setattr(log, "redis", redis)
    monkeypatch.setattr(log, "_background", False)
    monkeypatch.setattr(log, "_memory", {})
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", lambda payload: ("Voici la réponse.", [], None, None))
    return log, redis


def test_chat_counts_the_topic_and_stores_nothing_about_the_person(journal):
    log, redis = journal
    message = "Bonjour, je suis Fatou Diop (fatou.diop@example.com), mon numéro 77 123 45 67 : comment divorcer au Sénégal ?"
    ip = "203.0.113.150"
    response, secrets_ = _chat(ip, message)
    assert response.status_code == 200 and response.get_json()["reply"] == "Voici la réponse."
    # Ce qui est conservé : le thème, rien d'autre.
    assert list(redis.hashes) == [f"teranga:coverage:{dt.date.today().isoformat()}"]
    (counters,) = redis.hashes.values()
    assert counters["total"] == 1 and counters["justice|n"] == 1
    assert redis.ttls[next(iter(redis.hashes))] == 90 * 24 * 3600
    for field in counters:
        assert re.fullmatch(r"total|[a-z_]+\|[cn]", field) and (field == "total" or field.split("|")[0] in THEME_LABELS)
    # Ni le texte, ni l'IP, ni l'identifiant (cookie, jeton), ni une empreinte de l'un d'eux, nulle part.
    dump = (redis.dump() + repr(log._memory)).lower()
    forbidden = ["fatou", "diop", "example.com", "123 45", "771234567", ip, "203.0.113", "divorcer", message.lower()]
    forbidden += [s.lower() for s in secrets_ if len(s) >= 8]
    for secret in [ip, message, *secrets_]:
        data = secret.encode("utf-8")
        forbidden += [getattr(hashlib, name)(data).hexdigest() for name in ("md5", "sha1", "sha256")]
    assert not [item for item in forbidden if item in dump]
    assert log._memory == {}


def test_blocked_invalid_and_robot_requests_are_not_counted(journal):
    log, redis = journal
    ip = "203.0.113.151"
    assert _chat(ip, "   ")[0].status_code == 400                                   # message vide : invalide
    assert _chat(ip, "Comment divorcer ?", agent="Googlebot/2.1")[0].status_code == 200  # robot : répondu, pas compté
    client = app_module.app.test_client()
    denied = client.post("/chat", json={"message": "Comment divorcer ?"}, base_url=B, headers={"Origin": B},
                         environ_base={"REMOTE_ADDR": ip})                          # sans jeton CSRF
    assert denied.status_code == 403
    assert redis.hashes == {} and log._memory == {}
    # Limite de débit : seules les requêtes servies sont comptées.
    served = 0
    blocked = 0
    for _ in range(25):
        status = _chat("203.0.113.152", "Comment divorcer au Sénégal ?")[0].status_code
        served += status == 200
        blocked += status == 429
    assert blocked > 0 and served > 0
    (counters,) = redis.hashes.values()
    assert counters["total"] == served


def test_journal_failure_never_changes_the_answer(journal, monkeypatch):
    log, _ = journal
    monkeypatch.setattr(log, "record_chat", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("journal cassé")))
    response, _ = _chat("203.0.113.153", "Comment divorcer au Sénégal ?")
    assert response.status_code == 200 and response.get_json()["reply"] == "Voici la réponse."


def test_classifier_and_redis_failures_never_change_the_answer(journal, monkeypatch):
    log, _ = journal
    monkeypatch.setattr(log, "redis", BrokenRedis())
    monkeypatch.setattr(cl, "classify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boum")))
    response, _ = _chat("203.0.113.154", "Comment divorcer au Sénégal ?")
    assert response.status_code == 200 and response.get_json()["reply"] == "Voici la réponse."
    assert log._memory == {}
    monkeypatch.undo()  # classement rétabli, Redis toujours en panne : comptage en mémoire, réponse intacte
    monkeypatch.setattr(log, "redis", BrokenRedis())
    monkeypatch.setattr(log, "_background", False)
    monkeypatch.setattr(log, "_memory", {})
    monkeypatch.setitem(app_module._CHAT_SERVICE, "complete_reply", lambda payload: ("Réponse sans journal.", [], None, None))
    response, _ = _chat("203.0.113.156", "Comment divorcer au Sénégal ?")
    assert response.get_json()["reply"] == "Réponse sans journal."
    assert log._memory[dt.date.today().isoformat()]["justice|n"] == 1


def test_streamed_chat_is_counted_too(journal, monkeypatch):
    from types import SimpleNamespace

    log, redis = journal

    def stream(payload, stream=True):
        yield SimpleNamespace(type="response.output_text.delta", delta="Gorée est une île.")

    monkeypatch.setitem(app_module._CHAT_SERVICE, "create_response", stream)
    response, _ = _chat("203.0.113.155", "Parle-moi de Gorée", mode_json=False)
    assert response.status_code == 200 and "Gorée est une île." in response.get_data(as_text=True)
    (counters,) = redis.hashes.values()
    assert counters["voyage|c"] == 1 and counters["total"] == 1


# --- Page protégée /stats-ia ----------------------------------------------------------------------------------------

def _stats(monkeypatch, token=TOKEN):
    if token is None:
        monkeypatch.delenv("STATS_TOKEN", raising=False)
    else:
        monkeypatch.setenv("STATS_TOKEN", token)
    return app_module.app.test_client()


def test_stats_page_is_absent_without_a_strong_token(monkeypatch):
    assert _stats(monkeypatch, None).get("/stats-ia", base_url=B).status_code == 404
    assert _stats(monkeypatch, "trop-court").post("/stats-ia", data={"cle": "trop-court"}, base_url=B).status_code == 404


def test_stats_page_needs_the_password_and_is_private(monkeypatch):
    monkeypatch.setattr(app_module.COVERAGE_LOG, "_memory", {})
    monkeypatch.setattr(app_module.COVERAGE_LOG, "redis", None)
    app_module.COVERAGE_LOG.record({"justice": False})
    client = _stats(monkeypatch)
    form = client.get("/stats-ia", base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.160"})
    html = form.get_data(as_text=True)
    assert form.status_code == 200 and 'type="password"' in html and "Justice" not in html
    assert form.headers["Cache-Control"] == "no-store" and "noindex" in form.headers["X-Robots-Tag"]
    assert '<meta name="robots" content="noindex,nofollow">' in html
    wrong = client.post("/stats-ia", data={"cle": "faux"}, base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.160"})
    assert wrong.status_code == 403 and "Justice" not in wrong.get_data(as_text=True)
    ok = client.post("/stats-ia", data={"cle": TOKEN}, base_url=B, environ_base={"REMOTE_ADDR": "203.0.113.160"})
    page = ok.get_data(as_text=True)
    assert ok.status_code == 200 and "Justice et droit" in page and "100 %" in page
    assert ok.headers["Cache-Control"] == "no-store" and "noindex" in ok.headers["X-Robots-Tag"]
    assert "noindex" in page and "Comment lire ce tableau" in page and "Redis" in page and "pas configuré" in page


def test_stats_password_attempts_are_limited(monkeypatch):
    client = _stats(monkeypatch)
    statuses = [client.post("/stats-ia", data={"cle": f"essai-{i}"}, base_url=B,
                            environ_base={"REMOTE_ADDR": "203.0.113.161"}).status_code for i in range(8)]
    assert statuses[:5] == [403] * 5 and 429 in statuses[5:]


def test_stats_page_lists_themes_by_priority_and_warns_when_data_is_thin(monkeypatch):
    log = CoverageLog(FakeRedis(), background=False)
    log.record({"sante": False})
    log.record({"voyage": True})
    page = render_coverage_page(log.summary())
    assert page.index("Santé") < page.index("Voyage et tourisme")
    assert "Peu de questions comptées" in page and "pas configuré" not in page
    empty = render_coverage_page(CoverageLog(FakeRedis()).summary())
    assert "Aucune question comptée" in empty


def test_stats_page_is_not_advertised(monkeypatch):
    client = app_module.app.test_client()
    assert "stats-ia" not in client.get("/sitemap.xml", base_url=B).get_data(as_text=True)
    assert "stats-ia" not in client.get("/robots.txt", base_url=B).get_data(as_text=True)
    assert "stats-ia" not in client.get("/llms.txt", base_url=B).get_data(as_text=True)


# --- Politique de confidentialité -----------------------------------------------------------------------------------

def test_privacy_policy_describes_the_anonymous_counters():
    client = app_module.app.test_client()
    fr = client.get("/confidentialite", base_url=B).get_data(as_text=True)
    en = client.get("/privacy", base_url=B).get_data(as_text=True)
    assert "Statistiques anonymes des sujets" in fr and "ni le texte de votre question, ni votre adresse IP" in fr and "90 jours" in fr
    assert "Anonymous topic statistics" in en and "nor your IP address" in en and "90 days" in en
