"""Banc d'essai de l'IA : 50 questions réelles de visiteurs.

Pour chacune, on vérifie que le contexte envoyé au modèle contient bien les
faits nécessaires à une bonne réponse (lieu, histoire, accès, méthode de
négociation…). La question elle-même est retirée avant la vérification.
"""

import pytest

from app import app, parse_chat_payload

BENCH = [
 ("fr", "Comment aller à l'île de Gorée ?", ["Gorée", "chaloupe", "gare maritime"]),
 ("fr", "Raconte-moi l'histoire de la Maison des Esclaves", ["Maison des Esclaves", "Boubacar Joseph Ndiaye"]),
 ("fr", "Que voir à Saint-Louis ?", ["Saint-Louis", "Faidherbe"]),
 ("fr", "C'est quoi le Lac Rose ?", ["Lac Rose", "Retba"]),
 ("fr", "Combien payer un boubou au marché Sandaga ?", ["Sandaga", "NÉGOCIATION", "Où acheter", "Marché HLM"]),
 ("fr", "Comment négocier au marché ?", ["NÉGOCIATION"]),
 ("fr", "Entraîne-moi à marchander", ["vendeur"]),
 ("fr", "Quel temps fait-il à Dakar ?", []),
 ("fr", "Qu'est-ce que le thiéboudienne ?", ["Thiéboudienne"]),
 ("fr", "Comment dire merci en wolof ?", ["Jërëjëf"]),
 ("fr", "Parle-moi du Monument de la Renaissance africaine", ["Renaissance"]),
 ("fr", "Que faire en Casamance ?", ["Casamance"]),
 ("fr", "Visiter le parc du Niokolo-Koba", ["Niokolo"]),
 ("fr", "Le delta du Saloum, ça vaut le coup ?", ["Saloum"]),
 ("fr", "Qui était Léopold Sédar Senghor ?", ["Senghor"]),
 ("fr", "Histoire du royaume du Cayor", ["Cayor"]),
 ("fr", "Qui est Lat Dior ?", ["Lat Dior"]),
 ("fr", "Que voir à Touba ?", ["Touba"]),
 ("fr", "C'est quoi le Grand Magal ?", ["Magal"]),
 ("fr", "Joal-Fadiouth l'île aux coquillages", ["Fadiouth"]),
 ("fr", "Que faire à Kédougou ?", ["Kédougou", "Dindéfello", "Accès :"]),
 ("fr", "Les cercles mégalithiques de Sénégambie", ["mégalith"]),
 ("fr", "Visiter le parc du Djoudj", ["Djoudj"]),
 ("fr", "La réserve de Bandia", ["Bandia"]),
 ("fr", "Que voir à Saly et à Mbour ?", ["Saly"]),
 ("fr", "Visiter Ziguinchor", ["Ziguinchor"]),
 ("fr", "Île de Carabane histoire", ["Carabane"]),
 ("fr", "Que faire au Cap Skirring ?", ["Skirring"]),
 ("fr", "Visiter Podor et le Fouta", ["Podor"]),
 ("fr", "La mosquée de la Divinité à Ouakam", ["- Mosquée de la Divinité", "falaises"]),
 ("fr", "Le marché Kermel", ["Kermel"]),
 ("fr", "Le village artisanal de Soumbédioune", ["Soumbédioune"]),
 ("fr", "Prix d'un taxi de Dakar à l'aéroport AIBD", ["AIBD"]),
 ("fr", "Quelle est la monnaie du Sénégal ?", ["franc CFA"]),
 ("fr", "Faut-il un visa pour le Sénégal ?", []),
 ("fr", "Quelle est la meilleure saison pour visiter ?", []),
 ("fr", "Les Almadies et la pointe des Almadies", ["Almadies"]),
 ("fr", "Visiter Rufisque", ["Rufisque"]),
 ("fr", "Les îles de la Madeleine", ["Madeleine"]),
 ("fr", "Le Musée des civilisations noires", ["civilisations noires"]),
 ("en", "How do I get to Goree Island?", ["Gorée"]),
 ("en", "What is the history of Saint-Louis?", ["Saint-Louis"]),
 ("en", "How much should I pay for a taxi in Dakar?", []),
 ("en", "How do I bargain at the market?", ["MODE"]),
 ("en", "What is thieboudienne?", ["Thiéboudienne"]),
 ("en", "Tell me about Pink Lake", ["Lac Rose", "Dunaliella"]),
 ("en", "What to do in Casamance?", ["Casamance"]),
 ("wo", "Naka laa demee Gorée ?", ["Gorée"]),
 ("wo", "Lan mooy thiéboudienne ?", ["Thiéboudienne"]),
 ("fr", "Teranga ça veut dire quoi ?", ["Teranga"]),
]


@pytest.mark.parametrize("lang,question,expected", BENCH, ids=[q for _, q, _ in BENCH])
def test_ai_bench_context_has_the_facts(lang, question, expected):
    with app.test_request_context("/chat", method="POST", json={"message": question, "language": lang}):
        payload, error = parse_chat_payload()
    assert error is None
    context = payload["instructions"].replace(question, " ").casefold()
    missing = [fact for fact in expected if fact.casefold() not in context]
    assert not missing, f"Faits absents du contexte : {missing}"


def test_ai_bench_has_fifty_questions_in_three_languages():
    assert len(BENCH) == 50
    assert {lang for lang, _, _ in BENCH} == {"fr", "en", "wo"}
