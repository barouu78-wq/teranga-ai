"""Page /diaspora-senegalaise : des questions prêtes, chacune avec une réponse vérifiée.

Plan du 19 octobre 2026 (docs/PLAN-DIASPORA.md) : la diaspora d'abord. La page proposait des généralités ; elle
propose maintenant les questions concrètes de la diaspora. Un clic ouvre Teranga avec la question pré-remplie
(jamais envoyée sans l'utilisateur). Chaque question doit avoir une réponse vérifiée : réponse prête
(services/quick_answers.py) ou repères pratiques (services/practical_facts.py). Sinon, la page promettrait ce que
Teranga ne sait pas.
"""

import os
import re
from html import unescape
from urllib.parse import unquote

os.environ.setdefault("OPENAI_API_KEY", "test-key")

B = "https://teranga-ai.fr"

# Question → ce qui garantit la réponse : un début de réponse prête, ou un sujet de repères vérifiés.
ATTENDU = {
    "100 euros en FCFA ?": ("pret", "100 € = 65 595,70 FCFA"),
    "Comment envoyer de l'argent au Sénégal ?": ("repere", "argent"),
    "C'est quand la Tabaski ?": ("pret", "Tabaski (Aïd el-Kébir) : 17 mai 2027"),
    "Quels papiers pour renouveler ma carte d'identité ?": ("repere", "papiers"),
    "Que faut-il vérifier avant d'acheter un terrain au Sénégal ?": ("repere", "foncier"),
    "Que prévoir en arrivant à l'aéroport AIBD ?": ("repere", "transport"),
    "Quels numéros d'urgence au Sénégal ?": ("pret", "Numéros d'urgence au Sénégal"),
}


def _page():
    from app import app

    response = app.test_client().get("/diaspora-senegalaise", base_url=B)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_la_page_propose_les_questions_de_la_diaspora():
    html = _page()
    assert "Les questions de la diaspora" in html
    links = [unescape(unquote(q)) for q in re.findall(r'href="/\?q=([^"]+)"', html)]
    assert links == list(ATTENDU)


def test_chaque_question_proposee_a_une_reponse_verifiee(monkeypatch):
    import datetime as dt

    from services import quick_answers
    from services.practical_facts import matching_topics

    # Date fixe : la Tabaski 2027 est la prochaine au calendrier.
    monkeypatch.setattr(quick_answers, "_today", lambda: dt.date(2026, 10, 19))
    for question, (kind, expected) in ATTENDU.items():
        if kind == "pret":
            answer = quick_answer_for(quick_answers, question)
            assert answer is not None and expected in answer["reply"], question
        else:
            assert expected in matching_topics(question), question


def quick_answer_for(module, question):
    return module.quick_answer({"message": question, "language": "fr"}, {})


def test_les_questions_sont_de_vrais_liens_lisibles():
    html = _page()
    section = html.split("Les questions de la diaspora", 1)[1].split("</section>", 1)[0]
    cards = re.findall(r'<a class="card" href="/\?q=[^"]+"><strong>([^<]+)</strong><br><small>([^<]+)</small></a>', section)
    assert len(cards) == len(ATTENDU)
    assert all(label.strip() and text.strip() for label, text in cards)
