import os
import re

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY est introuvable. Vérifie ton fichier .env."
    )

client = OpenAI(api_key=API_KEY)

app = Flask(__name__)


# ============================================================
# CERVEAU DE TERANGA AI
# ============================================================

SYSTEM_PROMPT = """
Tu es Teranga AI SN, un assistant intelligent spécialisé dans le Sénégal.

Tu aides les utilisateurs sur :

- tourisme
- Dakar
- Saint-Louis
- Thiès
- Touba
- Saly
- Mbour
- Somone
- Popenguine
- Toubab Dialaw
- Gorée
- Casamance
- Ziguinchor
- Cap Skirring
- Sine-Saloum
- Tambacounda
- Kédougou
- pays Bassari
- culture sénégalaise
- histoire
- gastronomie
- restaurants
- hôtels
- marchés
- artisanat
- vêtements traditionnels
- transports
- plages
- parcs et réserves
- conseils pratiques

PERSONNALITÉ
------------

Sois chaleureux, naturel, respectueux et utile.

Tu peux utiliser quelques expressions wolof naturellement :

Nanga def ?
Jërëjëf
Sama xarit
Ba beneen yoon
Inshallah
Ndimmbal ak Teranga

Mais ne mets pas du Wolof dans chaque phrase.

LANGUES
-------

Si l'utilisateur écrit en français :
réponds en français naturel.

Si l'utilisateur écrit en anglais :
réponds en anglais naturel.

Si l'utilisateur écrit avec des fautes, du langage SMS ou du français mélangé avec du Wolof,
comprends son intention sans le corriger de manière désagréable.

Exemples :

"combien coute goree"
"prix goree"
"c koi prix bateau"
"ou dormir dakar"
"resto pas cher"
"wax ma wolof"
"how much goree"

INFORMATIONS ACTUELLES
----------------------

Les prix, horaires, transports, hôtels, restaurants, événements,
disponibilités et conditions d'accès peuvent changer.

Lorsqu'une information peut avoir changé, utilise la recherche Web.

NE DONNE JAMAIS UN PRIX ACTUEL INVENTÉ.

Si une information n'est pas confirmée :
dis-le clairement.

Si plusieurs sources donnent des informations différentes :
explique brièvement la différence.

SOURCES
-------

Privilégie autant que possible :

- sites officiels
- organismes publics
- musées
- monuments
- UNESCO
- compagnies de transport
- hôtels officiels
- restaurants officiels
- sources récentes et reconnues

Quand tu utilises la recherche Web, indique les sources importantes
à la fin de la réponse.

Exemple :

Sources :
- UNESCO
- Maison des Esclaves
- source officielle du transport

NE RECOPIE PAS les longues URLs dans ta réponse.

RÉPONSES
--------

Réponds directement à la question.

Pour une question simple :
réponds généralement en 4 à 8 phrases maximum.

Pour une question complexe :
utilise des petits titres et des listes.

Exemple :

🏝️ Gorée

🚢 Traversée
...

🏛️ À voir
...

💰 Tarifs
...

⏱️ Durée
...

💡 Conseil
...

Ne fais pas de longues réponses inutiles.

Ne répète pas la question de l'utilisateur.

Ne commence pas toutes les réponses par "Nanga def".

TOURISME
--------

Pour une destination, indique si pertinent :

- quoi voir
- quoi faire
- combien de temps prévoir
- comment y aller
- budget indicatif si vérifié
- conseils pratiques
- meilleure période
- points importants

Si l'utilisateur demande un itinéraire,
propose un programme organisé par jour.

GASTRONOMIE
-----------

Tu peux expliquer les plats sénégalais :

- thiéboudienne
- yassa
- mafé
- ceebu yapp
- soupe kandia
- pastels
- fataya
- ngalakh
- bissap
- bouye
- attaya

Explique simplement les plats et les ingrédients principaux.

MARCHÉS ET ACHATS
-----------------

Explique :

- ce qu'on peut trouver
- comment comparer les prix
- comment négocier avec respect
- comment éviter les mauvaises surprises

Ne donne pas de prix actuels sans vérification.

TRANSPORT
---------

Tu peux expliquer :

- TER
- BRT
- taxis
- cars rapides
- Ndiaga Ndiaye
- bateaux
- transports interurbains
- location de voiture

Pour les horaires et tarifs actuels :
utilise la recherche Web.

HÉBERGEMENT
-----------

Pour un hôtel ou un logement, explique si pertinent :

- quartier
- emplacement
- confort
- transport
- proximité de la plage
- proximité des attractions
- type d'hébergement

Ne présente pas une disponibilité comme certaine sans vérification.

SÉCURITÉ
--------

Donne des conseils pratiques et prudents.

Ne donne un numéro d'urgence que si tu es suffisamment certain
qu'il est exact.

RÈGLE PRINCIPALE
----------------

Ne jamais inventer.

Il vaut mieux dire :
"Je ne peux pas confirmer ce tarif actuellement."

que donner une fausse information.

Ton objectif est d'être un assistant moderne, fiable,
chaleureux et très utile pour découvrir le Sénégal.
"""


# ============================================================
# NETTOYAGE DES RÉPONSES
# ============================================================

def clean_answer(text):
    if not text:
        return "Désolé, je n'ai pas réussi à obtenir une réponse."

    # Nettoie les liens Markdown
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r"\1",
        text
    )

    # Supprime les longues URLs
    text = re.sub(
        r"https?://\S+",
        "",
        text
    )

    # Nettoie les titres Markdown
    text = re.sub(
        r"^#{1,6}\s*",
        "",
        text,
        flags=re.MULTILINE
    )

    # Nettoie le gras Markdown
    text = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        text
    )

    # Nettoie les espaces
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Maximum deux lignes vides
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# INTERFACE TERANGA AI
# ============================================================

HTML_PAGE = """
<!DOCTYPE html>

<html lang="fr">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Teranga AI SN</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    font-family: Arial, Helvetica, sans-serif;
    color: #17231d;

    background:
        radial-gradient(
            circle at 10% 10%,
            rgba(0, 133, 63, 0.25),
            transparent 30%
        ),
        radial-gradient(
            circle at 90% 20%,
            rgba(227, 27, 35, 0.20),
            transparent 30%
        ),
        linear-gradient(
            135deg,
            #edf8f1,
            #ffffff 50%,
            #fff2f2
        );
}


/* HEADER */

.header {
    position: relative;
    padding: 55px 20px 75px;
    text-align: center;
    color: white;

    background:
        linear-gradient(
            135deg,
            #064d2d,
            #087f45,
            #063522
        );
}

.header::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 8px;

    background:
        linear-gradient(
            90deg,
            #00853f 0%,
            #00853f 33%,
            #f5c400 33%,
            #f5c400 66%,
            #e31b23 66%,
            #e31b23 100%
        );
}

.logo {
    font-size: clamp(38px, 7vw, 60px);
    font-weight: 900;
    letter-spacing: -2px;
}

.logo-ai {
    color: #f5c400;
}

.logo-sn {
    opacity: 0.8;
    font-weight: 600;
}

.subtitle {
    margin-top: 10px;
    font-size: 18px;
}

.wolof-badge {
    display: inline-block;
    margin-top: 20px;
    padding: 11px 20px;
    border-radius: 999px;
    background: rgba(255,255,255,0.15);
    font-weight: bold;
}


/* LANGUES */

.language {
    position: absolute;
    top: 20px;
    right: 25px;

    display: flex;
    padding: 4px;
    border-radius: 999px;

    background: rgba(0,0,0,0.25);
}

.language button {
    border: 0;
    padding: 9px 14px;
    border-radius: 999px;
    background: transparent;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

.language button.active {
    background: white;
    color: #087f45;
}


/* CONTENEUR */

.container {
    width: min(1050px, 94%);
    margin: -45px auto 40px;
    position: relative;
}


/* CARTES */

.info-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 15px;
}

.info-card {
    padding: 17px;
    border-radius: 20px;
    background: rgba(255,255,255,0.94);
    box-shadow: 0 10px 30px rgba(0,0,0,0.07);
}

.info-icon {
    font-size: 25px;
}

.info-title {
    margin-top: 7px;
    font-weight: bold;
    color: #087f45;
}

.info-text {
    margin-top: 5px;
    font-size: 13px;
    color: #65736b;
}


/* CHAT */

.chat-box {
    overflow: hidden;
    border-radius: 30px;
    background: rgba(255,255,255,0.97);
    box-shadow: 0 25px 70px rgba(0,0,0,0.13);
}

.chat-top {
    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 22px 25px;

    border-bottom: 1px solid #edf0ee;
}

.chat-title {
    font-size: 19px;
    font-weight: 900;
}

.status {
    display: flex;
    align-items: center;
    gap: 7px;
    color: #087f45;
    font-size: 13px;
}

.status-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #20a45c;
}


/* MESSAGES */

.messages {
    min-height: 500px;
    max-height: 62vh;
    overflow-y: auto;
    padding: 25px;
}

.message {
    max-width: 82%;
    margin-bottom: 18px;
    padding: 16px 19px;

    border-radius: 20px;

    line-height: 1.65;
    white-space: pre-wrap;
    word-break: break-word;
}

.bot {
    background: #f0f5f2;
    margin-right: auto;
    border-bottom-left-radius: 6px;
}

.user {
    background: linear-gradient(
        135deg,
        #087f45,
        #056234
    );

    color: white;
    margin-left: auto;
    border-bottom-right-radius: 6px;
}


/* QUESTIONS RAPIDES */

.suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;

    padding: 0 25px 20px;
}

.suggestions button {
    border: 1px solid #dce8e0;
    background: #f7fbf8;
    color: #087f45;

    padding: 10px 14px;

    border-radius: 999px;

    font-weight: bold;
    cursor: pointer;
}

.suggestions button:hover {
    background: #e7f4eb;
}


/* CHAMP */

.input-area {
    display: flex;
    gap: 12px;

    padding: 20px 25px 25px;

    border-top: 1px solid #edf0ee;
}

.input-area input {
    flex: 1;
    min-width: 0;

    border: 2px solid #e0e9e3;

    border-radius: 18px;

    padding: 16px 18px;

    font-size: 16px;

    outline: none;
}

.input-area input:focus {
    border-color: #087f45;
}

.send {
    width: 58px;
    height: 58px;

    border: 0;
    border-radius: 18px;

    background: linear-gradient(
        135deg,
        #087f45,
        #056234
    );

    color: white;

    font-size: 24px;

    cursor: pointer;
}

.send:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}


/* FOOTER */

.footer {
    text-align: center;
    padding: 10px 20px 35px;
    color: #607069;
    font-size: 13px;
}


/* MOBILE */

@media (max-width: 760px) {

    .header {
        padding: 50px 15px 65px;
    }

    .info-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    .container {
        width: 96%;
    }

    .messages {
        min-height: 450px;
        padding: 18px;
    }

    .message {
        max-width: 92%;
    }

    .chat-top {
        padding: 18px;
    }

    .suggestions {
        padding: 0 18px 18px;
    }

    .input-area {
        padding: 15px 18px 18px;
    }
}

</style>

</head>


<body>


<header class="header">

    <div class="language">

        <button id="frBtn" class="active">
            FR
        </button>

        <button id="enBtn">
            EN
        </button>

    </div>


    <div class="logo">
        Teranga<span class="logo-ai">AI</span>
        <span class="logo-sn">SN</span>
    </div>


    <div class="subtitle" id="subtitle">
        Votre assistant intelligent au Sénégal
    </div>


    <div class="wolof-badge">
        Ndimmbal ak Teranga 🇸🇳
    </div>

</header>


<main class="container">


    <div class="info-grid">

        <div class="info-card">
            <div class="info-icon">🗺️</div>
            <div class="info-title">Découvrir</div>
            <div class="info-text">
                Villes, plages, îles et patrimoine
            </div>
        </div>


        <div class="info-card">
            <div class="info-icon">🍲</div>
            <div class="info-title">Goûter</div>
            <div class="info-text">
                Cuisine et spécialités sénégalaises
            </div>
        </div>


        <div class="info-card">
            <div class="info-icon">🚕</div>
            <div class="info-title">Se déplacer</div>
            <div class="info-text">
                TER, BRT, taxis et transports
            </div>
        </div>


        <div class="info-card">
            <div class="info-icon">🛏️</div>
            <div class="info-title">Séjourner</div>
            <div class="info-text">
                Quartiers, hôtels et conseils
            </div>
        </div>

    </div>


    <section class="chat-box">


        <div class="chat-top">

            <div class="chat-title">
                💬 Discussion avec Teranga AI
            </div>

            <div class="status">
                <span class="status-dot"></span>
                Assistant disponible
            </div>

        </div>


        <div id="messages" class="messages">

            <div class="message bot">
Nanga def ! 👋

Je suis Teranga AI SN 🇸🇳

Je peux t'aider à découvrir le Sénégal :
voyages, villes, culture, gastronomie,
transports, marchés, hôtels et bien plus.

Sama xarit, pose-moi ta question.
            </div>

        </div>


        <div class="suggestions">

            <button onclick="quickQuestion('Que visiter au Sénégal pour un premier voyage ?')">
                🗺️ Premier voyage
            </button>

            <button onclick="quickQuestion('Que faire à Dakar pendant 2 jours ?')">
                🌆 Dakar
            </button>

            <button onclick="quickQuestion('Quels sont les tarifs actuels pour visiter Gorée ?')">
                🏝️ Gorée
            </button>

            <button onclick="quickQuestion('Quels plats sénégalais dois-je absolument goûter ?')">
                🍲 Cuisine
            </button>

            <button onclick="quickQuestion('Comment se déplacer facilement à Dakar ?')">
                🚕 Transport
            </button>

            <button onclick="quickQuestion('Quels quartiers choisir pour dormir à Dakar ?')">
                🛏️ Hébergement
            </button>

        </div>


        <div class="input-area">

            <input
                id="question"
                type="text"
                maxlength="2000"
                placeholder="Pose ta question sur le Sénégal..."
                autocomplete="off"
            >

            <button
                id="sendButton"
                class="send"
                type="button"
            >
                ➤
            </button>

        </div>

    </section>

</main>


<footer class="footer">

    Teranga AI SN 🇸🇳
    <br>
    Votre assistant pour découvrir le Sénégal

</footer>


<script>

let currentLanguage = "fr";

let conversationHistory = [];


const messages =
    document.getElementById("messages");

const input =
    document.getElementById("question");

const sendButton =
    document.getElementById("sendButton");

const frBtn =
    document.getElementById("frBtn");

const enBtn =
    document.getElementById("enBtn");

const subtitle =
    document.getElementById("subtitle");


function addMessage(text, type) {

    const div =
        document.createElement("div");

    div.className =
        "message " + type;

    div.textContent =
        text;

    messages.appendChild(div);

    messages.scrollTop =
        messages.scrollHeight;
}


function quickQuestion(question) {

    input.value = question;
    input.focus();
}


function setLanguage(language) {

    currentLanguage = language;

    if (language === "fr") {

        frBtn.classList.add("active");
        enBtn.classList.remove("active");

        subtitle.textContent =
            "Votre assistant intelligent au Sénégal";

        input.placeholder =
            "Pose ta question sur le Sénégal...";

    } else {

        enBtn.classList.add("active");
        frBtn.classList.remove("active");

        subtitle.textContent =
            "Your intelligent assistant for Senegal";

        input.placeholder =
            "Ask your question about Senegal...";
    }
}


async function sendMessage() {

    const question =
        input.value.trim();

    if (!question) {
        return;
    }

    addMessage(
        question,
        "user"
    );

    conversationHistory.push({
        role: "user",
        content: question
    });

    input.value = "";

    sendButton.disabled = true;

    addMessage(
        currentLanguage === "fr"
            ? "Je recherche les informations utiles... 🔎"
            : "I'm checking the useful information... 🔎",
        "bot"
    );

    try {

        const response =
            await fetch(
                "/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: question,
                        language: currentLanguage,
                        history:
                            conversationHistory.slice(-8)
                    })
                }
            );


        const data =
            await response.json();


        const bots =
            document.querySelectorAll(
                ".message.bot"
            );

        if (bots.length > 1) {

            bots[bots.length - 1].remove();
        }


        if (!response.ok) {

            addMessage(
                data.reply ||
                "Une erreur est survenue.",
                "bot"
            );

            return;
        }


        const answer =
            data.reply ||
            "Je n'ai pas reçu de réponse.";


        addMessage(
            answer,
            "bot"
        );


        conversationHistory.push({
            role: "assistant",
            content: answer
        });


    } catch (error) {

        const bots =
            document.querySelectorAll(
                ".message.bot"
            );

        if (bots.length > 1) {
            bots[bots.length - 1].remove();
        }

        addMessage(
            currentLanguage === "fr"
                ? "Impossible de contacter Teranga AI. Vérifie que le serveur est lancé."
                : "Unable to contact Teranga AI. Check that the server is running.",
            "bot"
        );

    } finally {

        sendButton.disabled = false;
        input.focus();
    }
}


sendButton.addEventListener(
    "click",
    sendMessage
);


input.addEventListener(
    "keydown",
    function(event) {

        if (event.key === "Enter") {
            sendMessage();
        }

    }
);


frBtn.addEventListener(
    "click",
    function() {
        setLanguage("fr");
    }
);


enBtn.addEventListener(
    "click",
    function() {
        setLanguage("en");
    }
);

</script>

</body>

</html>
"""


# ============================================================
# PAGE PRINCIPALE
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return HTML_PAGE


# ============================================================
# CHAT
# ============================================================

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(silent=True) or {}

        message = str(
            data.get("message", "")
        ).strip()

        language = str(
            data.get("language", "fr")
        ).lower().strip()

        history = data.get(
            "history",
            []
        )

        if not message:

            return jsonify({
                "reply":
                    "Écris-moi une question sur le Sénégal."
            }), 400


        if len(message) > 2000:

            return jsonify({
                "reply":
                    "Ta question est trop longue. Essaie de la raccourcir."
            }), 400


        if language not in ["fr", "en"]:
            language = "fr"


        if not isinstance(history, list):
            history = []


        if language == "en":

            language_instruction = """
The user selected English.
Answer in natural English.
Use only a little Wolof when appropriate.
"""

        else:

            language_instruction = """
L'utilisateur a choisi le français.
Réponds en français naturel.
Utilise seulement quelques expressions wolof lorsque c'est naturel.
"""


        final_instructions = (
            SYSTEM_PROMPT
            + "\n\n"
            + language_instruction
        )


        # Prépare l'historique de la conversation.
        # On le transforme en texte pour garder la requête simple
        # et compatible avec l'API Responses.

        history_text = ""

        for item in history[-8:]:

            if not isinstance(item, dict):
                continue

            role = item.get("role", "")
            content = item.get("content", "")

            if role not in ["user", "assistant"]:
                continue

            if not content:
                continue

            if role == "user":
                history_text += (
                    "\nUtilisateur : "
                    + str(content)
                )

            else:
                history_text += (
                    "\nTeranga AI : "
                    + str(content)
                )


        input_text = (
            "Voici la conversation récente :\n"
            + history_text
            + "\n\nNouvelle question de l'utilisateur :\n"
            + message
        )


        response = client.responses.create(

            model=MODEL,

            instructions=final_instructions,

            input=input_text,

            tools=[
                {
                    "type": "web_search"
                }
            ]
        )


        reply = response.output_text or ""

        reply = clean_answer(reply)


        if not reply:

            reply = (
                "Désolé, je n'ai pas réussi à obtenir "
                "une réponse. Réessaie dans quelques secondes."
            )


        return jsonify({
            "reply": reply
        })


    except Exception:

        app.logger.exception(
            "Erreur dans /chat"
        )

        return jsonify({
            "reply": (
                "Désolé, une erreur technique est survenue. "
                "Vérifie que ta clé API fonctionne puis réessaie."
            )
        }), 500


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5002
    )