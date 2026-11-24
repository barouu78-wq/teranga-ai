"""Banc qualité de 50 questions (ticket QA P0 du 22 novembre 2026) : scripts/banc_qualite.py, tests/banc_qualite/.

Ce que pytest vérifie, sans IA ni réseau :
- le jeu de questions est complet et bien formé (50 questions, 10 catégories de 5, expressions valides) ;
- pour chaque question, la base vérifiée du site fournit les faits attendus (contexte de l'IA ou réponse prête) ;
- chaque réponse prête (sans IA) respecte ses attendus et ne contient aucun interdit : c'est la part du contrôle
  d'hallucination qui ne coûte rien ;
- les contrôles automatiques et le calcul de la note sur 100 sont justes.
Les réponses de l'IA elle-même se jugent en mode « reel » (payant) avec la fiche humaine.
"""

import csv
import io
import json
import re

import pytest

import app as app_module
from scripts import banc_qualite as banc

DATA = banc.load()
QUESTIONS = DATA["questions"]
IDS = [q["id"] for q in QUESTIONS]


def test_cinquante_questions_dix_categories_de_cinq():
    assert len(QUESTIONS) == 50 and len(set(IDS)) == 50
    assert set(DATA["categories"]) == {"vie", "transport", "emploi", "entreprise", "sante", "tourisme", "diaspora",
                                       "contexte", "langues", "suivi"}
    for category in DATA["categories"]:
        assert sum(q["categorie"] == category for q in QUESTIONS) == 5, category


@pytest.mark.parametrize("question", QUESTIONS, ids=IDS)
def test_chaque_question_est_bien_formee(question):
    assert question["langue"] in {"fr", "en", "wo"}
    assert isinstance(question["critique"], bool) and question["note"].strip()
    for pattern in question["attendus"] + question["interdits"]:
        re.compile(pattern)
    for turn in question.get("historique", []):
        assert turn["role"] in {"user", "assistant"} and turn["content"].strip()
    if question["categorie"] == "suivi":
        assert question.get("historique"), "une question de suivi a un historique"
    if question["critique"]:
        # Une question sensible se contrôle : un attendu, un interdit, ou une consigne de jugement humain.
        assert question["attendus"] or question["interdits"] or "humain" in question["note"]


def test_les_langues_et_les_questions_critiques_sont_representees():
    assert {q["langue"] for q in QUESTIONS} == {"fr", "en", "wo"}
    assert sum(q["critique"] for q in QUESTIONS) >= 15
    assert all(q["critique"] for q in QUESTIONS if q["categorie"] == "sante")


@pytest.fixture(scope="module")
def offline_rows():
    return {row["id"]: row for row in banc.run_offline(app_module, DATA)}


@pytest.mark.parametrize("qid", IDS)
def test_la_base_verifiee_fournit_les_faits_et_les_reponses_pretes_sont_justes(offline_rows, qid):
    row = offline_rows[qid]
    assert row["contexte_manquant"] == [], f"faits absents du contexte de l'IA : {row['contexte_manquant']}"
    assert not row.get("attendus_manquants"), f"réponse prête sans : {row.get('attendus_manquants')}"
    assert not row.get("interdits_trouves"), f"réponse prête avec un interdit : {row.get('interdits_trouves')}"


def test_les_urgences_sont_servies_sans_ia(offline_rows):
    for qid in ("sante-1", "sante-2", "diaspora-5"):
        assert offline_rows[qid]["pret"], qid  # réponse vérifiée, jamais laissée au modèle


@pytest.mark.parametrize("answer,manquants,interdits,grave", [
    ("Police secours : 17, sapeurs-pompiers : 18, SAMU : 1515.", 0, 0, False),
    ("Appelez le SAMU au 15 ou les pompiers au 18 ; police 17.", 1, 1, True),  # 15 : le SAMU de France
    ("Le numéro européen 112 fonctionne : police 17, pompiers 18, SAMU 1515.", 0, 1, True),
    ("Je ne sais pas.", 3, 0, False),
])
def test_controle_automatique_des_numeros_d_urgence(answer, manquants, interdits, grave):
    question = next(q for q in QUESTIONS if q["id"] == "sante-1")
    result = banc.check_answer(question, answer)
    assert len(result["attendus_manquants"]) == manquants
    assert len(result["interdits_trouves"]) == interdits
    assert result["hallucination_grave_auto"] is grave


def test_un_interdit_sur_une_question_non_critique_n_est_pas_une_hallucination_grave():
    question = next(q for q in QUESTIONS if q["id"] == "vie-4")  # jours fériés, non critique
    result = banc.check_answer(question, "Jours fériés : 4 avril (Indépendance), JOJ du 31 octobre.")
    assert result["interdits_trouves"] and not result["hallucination_grave_auto"]


def test_aucun_numero_de_telephone_invente():
    question = next(q for q in QUESTIONS if q["id"] == "contexte-5")
    assert banc.check_answer(question, "Appelez le 77 123 45 67.")["hallucination_grave_auto"]
    assert not banc.check_answer(question, "Je n'ai pas ce numéro : demandez à la mairie.")["interdits_trouves"]


def test_lecture_du_flux_du_chat():
    lines = [b'{"st": "web"}\n', b'{"d": "Bonjour "}\n', b'{"d": "Dakar."}\n{"done": true}\n', b"pas du json\n"]
    text, info = banc._read_stream(lines)
    assert text == "Bonjour Dakar." and info == {"web": True, "degraded": False, "error": ""}
    text, info = banc._read_stream(['{"d": "Secours."}\n', '{"degraded": true, "done": true}\n'])
    assert text == "Secours." and info["degraded"]


def _fiche(tmp_path, rows):
    rows_out = []
    for qid, category, notes, grave in rows:
        row = {"id": qid, "categorie": category, "critique": "non", "question": "q", "reponse": "r",
               "attendus_manquants": "", "interdits_trouves": "", "hallucination_grave": grave, "commentaire": ""}
        for (name, points), note in zip(banc.GRILLE, notes):
            row[f"{name}_{points}"] = note
        rows_out.append(row)
    path = tmp_path / "fiche.csv"
    columns = list(rows_out[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter=";")
        writer.writeheader()
        writer.writerows(rows_out)
    return path


def test_note_sur_cent_et_objectif(tmp_path):
    path = _fiche(tmp_path, [
        ("a", "sante", ["25", "20", "20", "20", "15"], ""),        # 100
        ("b", "sante", ["20", "18", "16", "15", "11"], ""),        # 80
        ("c", "transport", ["22,5", "17", "18", "17", "13"], ""),  # 87,5 (virgule française)
    ])
    result = banc.score_sheet(path)
    assert result["notees"] == 3 and result["moyenne"] == pytest.approx((100 + 80 + 87.5) / 3)
    assert result["par_categorie"] == {"sante": 90.0, "transport": 87.5}
    assert result["objectif_atteint"] is True  # 89,2 ≥ 85, aucune hallucination grave


def test_une_hallucination_grave_fait_manquer_l_objectif(tmp_path):
    path = _fiche(tmp_path, [("a", "sante", ["25", "20", "20", "20", "15"], "oui")])
    result = banc.score_sheet(path)
    assert result["hallucinations_graves"] == ["a"] and result["objectif_atteint"] is False


def test_une_ligne_non_notee_n_est_ni_comptee_zero_ni_oubliee(tmp_path):
    path = _fiche(tmp_path, [("a", "sante", ["25", "20", "20", "20", "15"], ""),
                             ("b", "sante", ["", "", "", "", ""], "")])
    result = banc.score_sheet(path)
    assert result["moyenne"] == 100 and result["non_notees"] == ["b"]
    assert result["objectif_atteint"] is False  # tout doit être noté


def test_une_note_hors_bareme_est_signalee(tmp_path):
    path = _fiche(tmp_path, [("a", "sante", ["30", "20", "20", "20", "15"], "")])
    result = banc.score_sheet(path)
    assert result["erreurs"] and result["notees"] == 0 and not result["objectif_atteint"]


def test_fiche_de_notation_ecrite_pour_excel(tmp_path):
    question = next(q for q in QUESTIONS if q["id"] == "sante-2")
    row = {**question, "texte": "SAMU : 15", "premier_mot_s": 1.0, "total_s": 2.0, "web": False, "degraded": False,
           "error": "", **banc.check_answer(question, "SAMU : 15")}
    path = tmp_path / "fiche.csv"
    banc.write_sheet([row], path)
    content = path.read_text(encoding="utf-8-sig")
    lines = list(csv.reader(io.StringIO(content), delimiter=";"))
    assert lines[0][-2:] == ["hallucination_grave", "commentaire"]
    assert lines[1][0] == "sante-2" and lines[1][-2] == "oui (auto, à confirmer)"
    assert all(cell == "" for cell in lines[1][7:12])  # les cinq notes restent à un humain
    report = banc.real_report([row], "test", DATA["categories"])
    assert "Hallucinations graves probables" in report and "**Interdit trouvé**" in report


def test_le_fichier_de_questions_est_du_json_strict():
    raw = banc.QUESTIONS_FILE.read_text(encoding="utf-8")
    assert json.loads(raw)["version"] == 1
