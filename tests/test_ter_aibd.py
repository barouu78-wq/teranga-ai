"""TER : la section Diamniadio–AIBD est en service depuis le 28 septembre 2026.

Source : APS, « Train express régional : la phase Diamniadio-AIBD inaugurée », 28 septembre 2026,
https://aps.sn/train-express-regional-la-phase-diamniadio-aibd-inauguree-un-investissement-de-plus-de-300-milliards-fcfa/
(« le trajet sera gratuit pendant une semaine sur la nouvelle section Diamniadio-AIBD, à compter de ce lundi
28 septembre »). Page lue par le propriétaire le 26 octobre 2026 ; aps.sn est bloqué depuis la session de l'agent.
Gares, horaires et tarifs ne sont pas sourcés : ils restent « à vérifier auprès de l'exploitant ».
"""

import json

from services.international_seo import TOPIC_DETAILS
from services.seo import SEO_PAGE_GUIDES

OUTDATED = ("prolongement vers l'aéroport est prévu", "vérifiez s'il est en service",
            "vérifiez si le prolongement", "check whether its airport extension", "jusqu'à Diamniadio",
            "as far as Diamniadio")


def _texts():
    yield "transport-senegal", json.dumps(SEO_PAGE_GUIDES["transport-senegal"], ensure_ascii=False)
    for topic in ("dakar-airport-to-city", "senegal-transport"):
        yield topic, json.dumps(TOPIC_DETAILS[topic], ensure_ascii=False)


def test_pages_no_longer_say_the_airport_extension_is_only_planned():
    for name, text in _texts():
        for phrase in OUTDATED:
            assert phrase not in text, f"{name} : {phrase!r}"


def test_pages_give_the_opening_date_and_send_details_to_the_operator():
    guide = json.dumps(SEO_PAGE_GUIDES["transport-senegal"], ensure_ascii=False)
    assert "en service depuis le 28 septembre 2026" in guide
    airport = TOPIC_DETAILS["dakar-airport-to-city"]
    assert "en service depuis le 28 septembre 2026" in json.dumps(airport["fr"], ensure_ascii=False)
    assert "running since 28 September 2026" in json.dumps(airport["en"], ensure_ascii=False)
    for name, text in _texts():
        assert "FCFA" not in text.split("TER")[1][:300], f"{name} : tarif du TER non sourcé"
