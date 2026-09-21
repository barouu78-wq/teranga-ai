import os
import re
import time
from collections import defaultdict, deque

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY est introuvable. Vérifie ton fichier .env."
    )

client = OpenAI(api_key=API_KEY)

MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_ITEMS = 8
MAX_HISTORY_CHARS = 10000
RATE_LIMIT = 12
RATE_WINDOW = 60

request_log = defaultdict(deque)


SYSTEM_PROMPT = """
Tu es Teranga AI, un assistant numérique moderne spécialisé dans le Sénégal.

MISSION
Aide les habitants du Sénégal, les voyageurs, la diaspora, les visiteurs et
les commerçants avec des informations utiles, claires et fiables sur le Sénégal.

LANGUES
- Réponds dans la langue utilisée par l'utilisateur.
- Français -> français naturel.
- English -> natural English.
- Wolof -> wolof lorsque tu peux le faire correctement.
- Comprends les mélanges français, anglais et wolof.
- Comprends les fautes de frappe, le langage SMS et les formulations courtes.

STYLE
- Sois chaleureux, professionnel et simple.
- Réponds directement.
- Sois concis par défaut.
- Donne les détails utiles quand ils sont nécessaires.
- Utilise des listes courtes quand cela améliore la lisibilité.
- N'invente jamais une information.

SÉNÉGAL
Tu peux aider notamment sur Dakar et les autres régions, tourisme, plages,
destinations, hôtels, restaurants, cuisine sénégalaise, marchés, commerce,
transport, culture, histoire, événements, démarches pratiques, entreprises,
services et vie quotidienne.

FIABILITÉ ET ACTUALITÉ
- Les prix, horaires, disponibilités, événements, transports, coordonnées et
  informations commerciales peuvent changer.
- Pour une information susceptible d'avoir changé récemment, utilise la
  recherche web lorsque c'est pertinent.
- Ne présente jamais une estimation comme un tarif officiel.
- Si une information n'est pas vérifiable ou reste incertaine, dis-le clairement.
- Privilégie les sources officielles ou récentes et fiables.
- Ne fabrique jamais le nom, l'adresse, le téléphone, le prix ou le site
  d'un hôtel, restaurant, entreprise ou service.

PRIX
- Pour un prix actuel, cherche une source récente lorsque nécessaire.
- Indique clairement lorsqu'un prix est indicatif, négociable ou variable.

POLITIQUE ET INFORMATIONS PUBLIQUES
- Pour les sujets politiques, électoraux ou institutionnels actuels, reste
  strictement factuel et neutre.
- Distingue les faits vérifiés, les déclarations et les analyses attribuées.
- Ne conseille pas à l'utilisateur pour qui voter et ne classe pas les candidats
  ou partis.

SÉCURITÉ
Pour les sujets sensibles ou dangereux, donne des conseils prudents et
recommande les sources officielles ou les professionnels appropriés.

OBJECTIF
L'utilisateur doit avoir l'impression de parler à un assistant sérieux,
moderne, utile et réellement adapté au Sénégal.
"""


def clean_answer(text):
    text = (text or "").strip()
    text = re.sub(r"\n{4,}", "\n\n", text)
    return text


def build_conversation(history, message):
    lines = []

    if isinstance(history, list):
        recent = history[-MAX_HISTORY_ITEMS:]

        for item in recent:
            if not isinstance(item, dict):
                continue

            role = str(item.get("role", "")).lower()
            content = str(item.get("content", "")).strip()

            if role not in {"user", "assistant"} or not content:
                continue

            label = "Utilisateur" if role == "user" else "Teranga AI"
            lines.append(f"{label}: {content[:2500]}")

    lines.append(f"Utilisateur: {message}")

    return "\n".join(lines)[-MAX_HISTORY_CHARS:]


def allowed_request(ip):
    now = time.time()
    log = request_log[ip]

    while log and now - log[0] > RATE_WINDOW:
        log.popleft()

    if len(log) >= RATE_LIMIT:
        return False

    log.append(now)
    return True


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "teranga-ai",
        "model": MODEL
    })


@app.post("/chat")
def chat():
    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr or "unknown"
    )

    ip = ip.split(",")[0].strip()

    if not allowed_request(ip):
        return jsonify({
            "error": "Trop de demandes. Attends quelques secondes puis réessaie."
        }), 429

    data = request.get_json(silent=True) or {}

    message = str(data.get("message", "")).strip()
    history = data.get("history", [])
    language = str(data.get("language", "fr")).lower()

    if not message:
        return jsonify({
            "error": "Écris un message avant d'envoyer."
        }), 400

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": (
                f"Ton message est trop long. "
                f"Maximum {MAX_MESSAGE_LENGTH} caractères."
            )
        }), 400

    language_instruction = {
        "fr": (
            "L'utilisateur a choisi le français. "
            "Réponds en français naturel."
        ),
        "en": (
            "The user selected English. "
            "Reply in natural English."
        ),
        "wo": (
            "L'utilisateur a choisi le wolof. "
            "Réponds en wolof lorsque tu peux le faire correctement."
        ),
    }.get(
        language,
        "Réponds dans la langue de l'utilisateur."
    )

    final_instructions = (
        SYSTEM_PROMPT
        + "\n\n"
        + language_instruction
    )

    input_text = build_conversation(history, message)

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=final_instructions,
            input=input_text,
            tools=[
                {
                    "type": "web_search"
                }
            ],
            max_output_tokens=500
        )

        reply = clean_answer(response.output_text or "")

        if not reply:
            reply = (
                "Désolé, je n'ai pas réussi à obtenir une réponse. "
                "Réessaie dans quelques secondes."
            )

        return jsonify({
            "reply": reply
        })

    except Exception:
        app.logger.exception("Erreur dans /chat")

        return jsonify({
            "error": (
                "Désolé, le service est temporairement indisponible. "
                "Réessaie dans quelques secondes."
            )
        }), 500


HTML = r"""
<!doctype html>

<html lang="fr">

<head>

<meta charset="utf-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<meta name="theme-color"
      content="#0b7a4b">

<title>Teranga AI SN</title>

<style>

:root {
    --green: #0b7a4b;
    --green-dark: #075c39;
    --orange: #f28c28;
    --cream: #fffaf2;
    --ink: #17251f;
    --muted: #68756f;
    --card: #ffffff;
    --border: #e6ece8;
    --shadow: 0 16px 45px rgba(16, 48, 35, .10);
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Inter, Arial, sans-serif;
    color: var(--ink);
    background:
        linear-gradient(
            180deg,
            #f4fbf7 0%,
            var(--cream) 100%
        );
}

header {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(255,255,255,.94);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
}

.nav {
    max-width: 1120px;
    margin: auto;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 800;
}

.logo {
    width: 42px;
    height: 42px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    color: white;
    background:
        linear-gradient(
            135deg,
            var(--green),
            var(--orange)
        );
    font-size: 21px;
}

.lang {
    display: flex;
    gap: 6px;
}

.lang button {
    border: 1px solid var(--border);
    background: white;
    border-radius: 999px;
    padding: 7px 11px;
    cursor: pointer;
    font-weight: 700;
}

.lang button.active {
    background: var(--green);
    color: white;
    border-color: var(--green);
}

main {
    max-width: 1120px;
    margin: auto;
    padding: 34px 18px 60px;
}

.hero {
    background:
        linear-gradient(
            135deg,
            #08784a,
            #0e9560 55%,
            #f28c28
        );
    color: white;
    border-radius: 28px;
    padding: 42px 30px;
    box-shadow: var(--shadow);
}

.hero h1 {
    margin: 0 0 10px;
    font-size: clamp(34px, 6vw, 58px);
    line-height: 1;
}

.hero p {
    max-width: 720px;
    margin: 0;
    font-size: 18px;
    line-height: 1.55;
    opacity: .96;
}

.section {
    margin-top: 28px;
}

.section h2 {
    font-size: 24px;
    margin: 0 0 14px;
}

.quick {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.quick button,
.destination {
    border: 1px solid var(--border);
    background: var(--card);
    border-radius: 18px;
    padding: 16px;
    text-align: left;
    box-shadow:
        0 7px 22px rgba(20,50,35,.05);
}

.quick button {
    cursor: pointer;
    font: inherit;
}

.quick button:hover {
    transform: translateY(-1px);
}

.chat {
    margin-top: 28px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 24px;
    box-shadow: var(--shadow);
    overflow: hidden;
}

.chat-head {
    padding: 18px 20px;
    border-bottom: 1px solid var(--border);
    font-weight: 800;
}

#messages {
    min-height: 260px;
    max-height: 560px;
    overflow: auto;
    padding: 18px;
}

.msg {
    display: flex;
    margin: 10px 0;
    gap: 8px;
}

.msg.user {
    justify-content: flex-end;
}

.bubble {
    max-width: 85%;
    padding: 12px 15px;
    border-radius: 18px;
    line-height: 1.5;
    white-space: pre-wrap;
}

.assistant .bubble {
    background: #eef8f2;
}

.user .bubble {
    background: var(--green);
    color: white;
}

.voice-button {
    border: 0;
    border-radius: 14px;
    padding: 0 16px;
    min-width: 58px;
    background: var(--orange);
    color: white;
    font-size: 22px;
    font-weight: 800;
    cursor: pointer;
}

.voice-button.listening {
    background: #c93636;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    50% {
        transform: scale(1.05);
    }
}

.speak-button {
    display: block;
    margin-top: 7px;
    border: 0;
    background: transparent;
    color: var(--green);
    cursor: pointer;
    font-size: 14px;
    font-weight: 700;
    padding: 2px 0;
}

.composer {
    display: flex;
    gap: 10px;
    padding: 14px;
    border-top: 1px solid var(--border);
}

textarea {
    flex: 1;
    resize: none;
    min-height: 50px;
    max-height: 150px;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 13px;
    font: inherit;
    outline: none;
}

textarea:focus {
    border-color: var(--green);
}

#send {
    border: 0;
    border-radius: 16px;
    padding: 0 20px;
    background: var(--green);
    color: white;
    font-weight: 800;
    cursor: pointer;
}

#send:disabled {
    opacity: .55;
    cursor: not-allowed;
}

.destinations {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
}

.destination {
    text-align: left;
}

.destination strong {
    display: block;
    margin-bottom: 5px;
}

.destination span {
    color: var(--muted);
    line-height: 1.45;
}

footer {
    text-align: center;
    padding: 30px 18px 45px;
    color: var(--muted);
}

@media (max-width: 800px) {

    .quick {
        grid-template-columns: repeat(2, 1fr);
    }

    .destinations {
        grid-template-columns: 1fr;
    }

    .hero {
        padding: 32px 22px;
    }
}

@media (max-width: 520px) {

    .quick {
        grid-template-columns: 1fr;
    }

    .composer {
        flex-direction: column;
    }

    .voice-button,
    #send {
        min-height: 48px;
        width: 100%;
    }

    .bubble {
        max-width: 94%;
    }
}

</style>

</head>

<body>

<header>

<div class="nav">

<div class="brand">

<div class="logo">
🌴
</div>

<div>
Teranga AI SN
</div>

</div>

<div class="lang">

<button data-lang="fr" class="active">FR</button>
<button data-lang="en">EN</button>
<button data-lang="wo">WO</button>

</div>

</div>

</header>


<main>

<section class="hero">

<h1>
Teranga AI 🇸🇳
</h1>

<p id="heroText">
Ton assistant intelligent pour le Sénégal :
tourisme, transport, prix, culture,
démarches et vie quotidienne.
</p>

</section>


<section class="section">

<h2 id="quickTitle">
Questions rapides
</h2>

<div class="quick">

<button data-question="Quel temps fait-il à Dakar aujourd'hui ?">
🌤️ Météo à Dakar
</button>

<button data-question="Combien coûte un taxi de l'aéroport AIBD à Dakar ?">
🚕 AIBD → Dakar
</button>

<button data-question="Quels sont les endroits à visiter au Sénégal ?">
📍 Destinations
</button>

<button data-question="Quels plats sénégalais dois-je goûter ?">
🍲 Cuisine
</button>

</div>

</section>


<section class="chat">

<div class="chat-head"
     id="chatTitle">
Pose ta question à Teranga AI
</div>

<div id="messages">
</div>

<div class="composer">

<textarea
id="input"
maxlength="2000"
placeholder="Ex. Quel est le prix d'un taxi AIBD → Dakar ?">
</textarea>

<button
id="mic"
class="voice-button"
type="button"
title="Parler">
🎤
</button>

<button id="send">
Envoyer
</button>

</div>

</section>


<section class="section">

<h2>
Quelques idées 🇸🇳
</h2>

<div class="destinations">

<div class="destination">
<strong>Dakar</strong>
<span>
Culture, marchés, restaurants
et vie urbaine.
</span>
</div>

<div class="destination">
<strong>Île de Gorée</strong>
<span>
Histoire, patrimoine
et découverte culturelle.
</span>
</div>

<div class="destination">
<strong>Saly & Petite Côte</strong>
<span>
Plages, détente et activités
touristiques.
</span>
</div>

</div>

</section>

</main>


<footer>
Teranga AI SN — Un assistant numérique dédié au Sénégal 🇸🇳
</footer>


<script>

const input =
    document.getElementById('input');

const send =
    document.getElementById('send');

const mic =
    document.getElementById('mic');

const messages =
    document.getElementById('messages');

let history = [];

let currentLanguage = 'fr';

let recognition = null;

let isListening = false;


const translations = {

    fr: {
        hero:
            'Ton assistant intelligent pour le Sénégal : tourisme, transport, prix, culture, démarches et vie quotidienne.',
        quick:
            'Questions rapides',
        chat:
            'Pose ta question à Teranga AI',
        placeholder:
            "Ex. Quel est le prix d'un taxi AIBD → Dakar ?",
        send:
            'Envoyer',
        welcome:
            'Bonjour 👋 Je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',
        listen:
            '🎤',
        listening:
            '🔴'
    },

    en: {
        hero:
            'Your intelligent assistant for Senegal: tourism, transport, prices, culture, practical procedures and daily life.',
        quick:
            'Quick questions',
        chat:
            'Ask Teranga AI',
        placeholder:
            'Example: How much is a taxi from AIBD to Dakar?',
        send:
            'Send',
        welcome:
            'Hello 👋 I am Teranga AI. What would you like to know about Senegal?',
        listen:
            '🎤',
        listening:
            '🔴'
    },

    wo: {
        hero:
            'Sa xam-xam bu bees ci Senegaal: tukki, transport, njëg, aada ak dund gu bees.',
        quick:
            'Laaj yu gaaw',
        chat:
            'Laajal Teranga AI',
        placeholder:
            'Misaal: Ñaata la taxi AIBD ba Dakar?',
        send:
            'Yónnee',
        welcome:
            'Salaam 👋 Maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',
        listen:
            '🎤',
        listening:
            '🔴'
    }

};


const voiceLanguages = {
    fr: 'fr-FR',
    en: 'en-US',
    wo: 'wo-SN'
};


function addMessage(role, text) {

    const row =
        document.createElement('div');

    row.className =
        'msg ' + role;

    const bubble =
        document.createElement('div');

    bubble.className =
        'bubble';

    bubble.textContent =
        text;

    row.appendChild(bubble);

    if (role === 'assistant') {

        const speakButton =
            document.createElement('button');

        speakButton.type = 'button';

        speakButton.className =
            'speak-button';

        speakButton.textContent =
            '🔊 Écouter';

        speakButton.addEventListener(
            'click',
            function () {
                speakText(text);
            }
        );

        row.appendChild(speakButton);
    }

    messages.appendChild(row);

    messages.scrollTop =
        messages.scrollHeight;
}


function speakText(text) {

    if (!('speechSynthesis' in window)) {
        return;
    }

    window.speechSynthesis.cancel();

    const utterance =
        new SpeechSynthesisUtterance(text);

    utterance.lang =
        voiceLanguages[currentLanguage] || 'fr-FR';

    utterance.rate = 0.95;
    utterance.pitch = 1;

    window.speechSynthesis.speak(
        utterance
    );
}


function setupVoice() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        mic.disabled = true;
        mic.title =
            'La reconnaissance vocale n’est pas disponible sur ce navigateur.';

        return;
    }

    recognition =
        new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.lang =
        voiceLanguages[currentLanguage];

    recognition.onstart =
        function () {

            isListening = true;

            mic.classList.add('listening');

            mic.textContent =
                translations[currentLanguage].listening;
        };


    recognition.onresult =
        function (event) {

            const transcript =
                event.results[0][0].transcript;

            input.value =
                transcript;

            input.dispatchEvent(
                new Event(
                    'input',
                    { bubbles: true }
                )
            );

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;

            isListening = false;

            sendMessage();
        };


    recognition.onerror =
        function () {

            isListening = false;

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;
        };


    recognition.onend =
        function () {

            isListening = false;

            mic.classList.remove(
                'listening'
            );

            mic.textContent =
                translations[currentLanguage].listen;
        };
}


function startVoice() {

    if (!recognition) {
        return;
    }

    if (isListening) {
        recognition.stop();
        return;
    }

    recognition.lang =
        voiceLanguages[currentLanguage] || 'fr-FR';

    try {
        recognition.start();
    } catch (error) {
        isListening = false;
    }
}


function setLanguage(lang) {

    currentLanguage = lang;

    document
        .querySelectorAll('.lang button')
        .forEach(btn => {

            btn.classList.toggle(
                'active',
                btn.dataset.lang === lang
            );

        });

    const t =
        translations[lang];

    document
        .getElementById('heroText')
        .textContent = t.hero;

    document
        .getElementById('quickTitle')
        .textContent = t.quick;

    document
        .getElementById('chatTitle')
        .textContent = t.chat;

    document
        .getElementById('input')
        .placeholder = t.placeholder;

    document
        .getElementById('send')
        .textContent = t.send;

    if (mic && !isListening) {
        mic.textContent = t.listen;
    }

    if (recognition) {
        recognition.lang =
            voiceLanguages[lang] || 'fr-FR';
    }
}


async function sendMessage(textFromButton = null) {

    const text =
        (textFromButton || input.value).trim();

    if (!text || send.disabled) {
        return;
    }

    addMessage(
        'user',
        text
    );

    history.push({
        role: 'user',
        content: text
    });

    input.value = '';

    send.disabled = true;

    send.textContent =
        currentLanguage === 'en'
            ? 'Thinking…'
            : 'Réflexion…';

    try {

        const response =
            await fetch('/chat', {

                method: 'POST',

                headers: {
                    'Content-Type':
                        'application/json'
                },

                body: JSON.stringify({

                    message: text,

                    history:
                        history.slice(-8),

                    language:
                        currentLanguage

                })

            });


        const data =
            await response.json();


        if (!response.ok) {
            throw new Error(
                data.error || 'Erreur'
            );
        }


        const reply =
            data.reply ||
            'Aucune réponse.';


        addMessage(
            'assistant',
            reply
        );


        history.push({
            role: 'assistant',
            content: reply
        });


        history =
            history.slice(-8);


    } catch (error) {

        addMessage(
            'assistant',
            error.message ||
            'Service temporairement indisponible.'
        );

    } finally {

        send.disabled = false;

        send.textContent =
            translations[
                currentLanguage
            ].send;

        input.focus();
    }
}


document
    .querySelectorAll('.lang button')
    .forEach(btn => {

        btn.addEventListener(
            'click',
            () => setLanguage(
                btn.dataset.lang
            )
        );

    });


document
    .querySelectorAll('.quick button')
    .forEach(btn => {

        btn.addEventListener(
            'click',
            () => sendMessage(
                btn.dataset.question
            )
        );

    });


send.addEventListener(
    'click',
    () => sendMessage()
);


mic.addEventListener(
    'click',
    () => startVoice()
);


input.addEventListener(
    'keydown',
    event => {

        if (
            event.key === 'Enter' &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }

    }
);


setLanguage('fr');

setupVoice();

addMessage(
    'assistant',
    translations.fr.welcome
);

</script>

</body>

</html>
"""


@app.get("/")
def home():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=False
    )