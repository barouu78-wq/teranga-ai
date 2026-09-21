import os
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY est manquante. "
        "Ajoute-la dans ton fichier .env ou dans les variables d'environnement."
    )

client = OpenAI(api_key=API_KEY)

MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY = 8
RATE_LIMIT = 12
RATE_WINDOW = 60

request_log = defaultdict(deque)


# =========================================================
# PROMPT TERANGA AI
# =========================================================

SYSTEM_PROMPT = """
Tu es Teranga AI, un assistant numérique moderne spécialisé dans le Sénégal.

Ta mission est d'aider les habitants du Sénégal, les voyageurs, la diaspora,
les commerçants et les visiteurs à obtenir des informations utiles, claires
et fiables sur le Sénégal.

LANGUES
- Réponds naturellement dans la langue utilisée par l'utilisateur.
- Français -> français.
- English -> English.
- Wolof -> Wolof lorsque tu peux répondre correctement.
- Si l'utilisateur mélange français, anglais et Wolof, comprends le mélange
  et réponds naturellement.
- Comprends autant que possible les fautes de frappe et le langage SMS.

STYLE
- Sois chaleureux, professionnel, simple et naturel.
- Réponds de façon concise par défaut.
- Utilise des listes lorsque cela facilite la lecture.
- Ne donne pas une réponse artificiellement longue.
- Ne répète pas inutilement la question de l'utilisateur.

SÉNÉGAL
Tu peux aider notamment sur :
- Dakar et les autres régions du Sénégal
- tourisme
- plages et destinations
- hôtels et hébergements
- restaurants et cuisine sénégalaise
- marchés et commerces
- transport
- culture et histoire
- événements
- démarches pratiques
- entreprises et services
- vie quotidienne
- conseils pratiques pour les visiteurs

FIABILITÉ
- N'invente jamais une information.
- Ne présente pas comme actuelle une information ancienne.
- Les prix, horaires, disponibilités, événements, transports,
  coordonnées et informations commerciales peuvent changer.
- Pour les informations susceptibles d'avoir changé, utilise la recherche
  Web lorsqu'elle est disponible.
- Si tu n'es pas certain, dis-le clairement.
- Ne transforme pas une estimation en prix officiel.
- Ne fabrique jamais de restaurant, hôtel, entreprise, adresse,
  numéro de téléphone ou événement.

PRIX
Ne donne pas de prix fixe présenté comme actuel sans vérification.
Si un prix actuel est nécessaire, cherche une source récente.
Indique lorsque le prix peut varier.

SÉCURITÉ
Pour les sujets sensibles ou dangereux, donne des conseils prudents
et recommande les sources officielles ou les professionnels compétents
lorsque nécessaire.

OBJECTIF
L'utilisateur doit avoir l'impression de parler à un assistant
sérieux, moderne et réellement utile pour le Sénégal.
"""


# =========================================================
# PAGE WEB
# =========================================================

HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0, viewport-fit=cover">

<meta name="theme-color" content="#087443">

<title>Teranga AI SN — Votre assistant intelligent au Sénégal</title>

<style>
:root {
    --green: #087443;
    --green-dark: #04552f;
    --green-light: #e9f7ef;
    --orange: #f59b23;
    --orange-light: #fff3df;
    --dark: #12231b;
    --text: #26352e;
    --muted: #718078;
    --white: #ffffff;
    --bg: #f5f8f6;
    --border: #e4ebe7;
    --shadow: 0 18px 50px rgba(18, 35, 27, .10);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
    color: var(--text);
    background: var(--bg);
}

button,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

.container {
    width: min(1180px, calc(100% - 32px));
    margin: auto;
}

/* ================= HEADER ================= */

header {
    position: sticky;
    top: 0;
    z-index: 20;
    background: rgba(255,255,255,.94);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid rgba(228,235,231,.8);
}

.nav {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.logo {
    display: flex;
    align-items: center;
    gap: 11px;
    text-decoration: none;
    color: var(--dark);
    font-weight: 900;
    font-size: 20px;
}

.logo-mark {
    width: 40px;
    height: 40px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    color: white;
    font-weight: 900;
    background:
        linear-gradient(145deg, var(--green), #0a8d51);
    box-shadow: 0 8px 20px rgba(8,116,67,.22);
}

.logo small {
    display: block;
    color: var(--green);
    font-size: 10px;
    letter-spacing: 1.2px;
    margin-top: 1px;
}

.nav-actions {
    display: flex;
    align-items: center;
    gap: 9px;
}

.lang-btn {
    border: 1px solid var(--border);
    background: white;
    color: var(--dark);
    border-radius: 999px;
    padding: 9px 14px;
    font-weight: 700;
}

/* ================= HERO ================= */

.hero {
    padding: 70px 0 45px;
    background:
        radial-gradient(circle at 85% 10%, rgba(245,155,35,.18), transparent 28%),
        radial-gradient(circle at 5% 20%, rgba(8,116,67,.12), transparent 30%),
        linear-gradient(180deg, #ffffff, #f5f8f6);
}

.hero-grid {
    display: grid;
    grid-template-columns: 1.05fr .95fr;
    gap: 45px;
    align-items: center;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--green-light);
    color: var(--green);
    border: 1px solid #cce8d8;
    border-radius: 999px;
    padding: 8px 13px;
    font-size: 13px;
    font-weight: 800;
}

.badge-dot {
    width: 8px;
    height: 8px;
    background: #19a862;
    border-radius: 50%;
}

h1 {
    margin: 20px 0 16px;
    font-size: clamp(40px, 6vw, 68px);
    line-height: 1.02;
    letter-spacing: -2.5px;
    color: var(--dark);
}

.hero h1 span {
    color: var(--green);
}

.hero-text {
    max-width: 650px;
    font-size: 18px;
    line-height: 1.65;
    color: var(--muted);
}

.hero-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 28px;
}

.primary {
    border: 0;
    background: var(--green);
    color: white;
    padding: 14px 21px;
    border-radius: 13px;
    font-weight: 800;
    box-shadow: 0 10px 25px rgba(8,116,67,.22);
}

.primary:hover {
    background: var(--green-dark);
}

.secondary {
    border: 1px solid var(--border);
    background: white;
    color: var(--dark);
    padding: 14px 21px;
    border-radius: 13px;
    font-weight: 800;
}

/* ================= HERO CARD ================= */

.hero-card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 25px;
    padding: 22px;
    box-shadow: var(--shadow);
}

.hero-card-top {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 17px;
    border-bottom: 1px solid var(--border);
}

.avatar {
    width: 46px;
    height: 46px;
    border-radius: 15px;
    display: grid;
    place-items: center;
    color: white;
    font-weight: 900;
    background: var(--green);
}

.status {
    color: #16804a;
    font-size: 12px;
    font-weight: 800;
}

.demo-message {
    padding: 18px 0 5px;
}

.bubble {
    width: fit-content;
    max-width: 90%;
    padding: 13px 15px;
    border-radius: 16px;
    line-height: 1.5;
    margin-bottom: 11px;
}

.bubble.user {
    margin-left: auto;
    color: white;
    background: var(--green);
    border-bottom-right-radius: 5px;
}

.bubble.ai {
    background: #f0f5f2;
    border-bottom-left-radius: 5px;
}

/* ================= SECTIONS ================= */

section {
    padding: 65px 0;
}

.section-title {
    text-align: center;
    margin-bottom: 32px;
}

.section-title h2 {
    margin: 0 0 9px;
    font-size: 34px;
    color: var(--dark);
}

.section-title p {
    margin: 0;
    color: var(--muted);
}

.cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}

.card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 19px;
    padding: 22px;
    transition: transform .2s, box-shadow .2s;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow);
}

.card-icon {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    background: var(--green-light);
    font-size: 22px;
    margin-bottom: 16px;
}

.card h3 {
    margin: 0 0 7px;
    color: var(--dark);
}

.card p {
    margin: 0;
    line-height: 1.55;
    color: var(--muted);
    font-size: 14px;
}

/* ================= CHAT ================= */

.chat-section {
    background: #eef5f1;
}

.chat-box {
    max-width: 900px;
    margin: auto;
    background: white;
    border: 1px solid var(--border);
    border-radius: 24px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

.chat-head {
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--border);
}

.chat-head strong {
    color: var(--dark);
}

.chat-head span {
    display: block;
    font-size: 12px;
    color: var(--muted);
    margin-top: 2px;
}

.messages {
    height: 430px;
    overflow-y: auto;
    padding: 20px;
    background: #fbfdfc;
}

.message {
    display: flex;
    margin-bottom: 14px;
}

.message.user {
    justify-content: flex-end;
}

.message-bubble {
    max-width: min(75%, 650px);
    padding: 13px 15px;
    border-radius: 17px;
    line-height: 1.55;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.message.ai .message-bubble {
    background: #edf4f0;
    border-bottom-left-radius: 5px;
}

.message.user .message-bubble {
    color: white;
    background: var(--green);
    border-bottom-right-radius: 5px;
}

.quick {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 12px 15px 4px;
}

.quick button {
    white-space: nowrap;
    border: 1px solid var(--border);
    background: white;
    border-radius: 999px;
    padding: 8px 12px;
    color: var(--green);
    font-weight: 700;
    font-size: 13px;
}

.composer {
    display: flex;
    gap: 10px;
    padding: 15px;
    border-top: 1px solid var(--border);
}

#message {
    flex: 1;
    resize: none;
    min-height: 48px;
    max-height: 130px;
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: 13px 14px;
    outline: none;
}

#message:focus {
    border-color: var(--green);
}

.send {
    width: 50px;
    min-width: 50px;
    border: 0;
    border-radius: 15px;
    color: white;
    background: var(--green);
    font-size: 19px;
}

.send:disabled {
    opacity: .5;
}

/* ================= DESTINATIONS ================= */

.destination {
    background: white;
}

.destination-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 17px;
}

.destination-card {
    min-height: 185px;
    padding: 23px;
    border-radius: 20px;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    overflow: hidden;
    background:
        linear-gradient(145deg, #087443, #07542f);
    position: relative;
}

.destination-card:nth-child(2) {
    background:
        linear-gradient(145deg, #bd7210, #f59b23);
}

.destination-card:nth-child(3) {
    background:
        linear-gradient(145deg, #116c7c, #18a1b5);
}

.destination-card h3 {
    margin: 0 0 5px;
    font-size: 22px;
}

.destination-card p {
    margin: 0;
    opacity: .9;
}

/* ================= FOOTER ================= */

footer {
    padding: 35px 0;
    color: #d8e8df;
    background: #10271d;
}

.footer-inner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

footer strong {
    color: white;
}

footer p {
    margin: 5px 0 0;
    font-size: 13px;
}

/* ================= MOBILE ================= */

@media (max-width: 850px) {
    .hero-grid {
        grid-template-columns: 1fr;
    }

    .hero-card {
        max-width: 600px;
        margin: auto;
    }

    .cards {
        grid-template-columns: repeat(2, 1fr);
    }

    .destination-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 560px) {
    .container {
        width: min(100% - 22px, 1180px);
    }

    .nav {
        height: 64px;
    }

    .logo {
        font-size: 17px;
    }

    .logo-mark {
        width: 36px;
        height: 36px;
    }

    h1 {
        font-size: 43px;
        letter-spacing: -1.7px;
    }

    .hero {
        padding-top: 43px;
    }

    .hero-text {
        font-size: 16px;
    }

    .cards {
        grid-template-columns: 1fr;
    }

    .messages {
        height: 390px;
    }

    .message-bubble {
        max-width: 86%;
    }

    .footer-inner {
        flex-direction: column;
        align-items: flex-start;
    }
}
</style>
</head>

<body>

<header>
    <div class="container nav">
        <a href="#" class="logo">
            <div class="logo-mark">T</div>
            <div>
                Teranga AI
                <small>SÉNÉGAL</small>
            </div>
        </a>

        <div class="nav-actions">
            <button class="lang-btn" id="langBtn">FR / EN</button>
        </div>
    </div>
</header>


<main>

<!-- HERO -->

<section class="hero">
    <div class="container hero-grid">

        <div>
            <div class="badge">
                <span class="badge-dot"></span>
                Assistant intelligent pour le Sénégal
            </div>

            <h1>
                Votre guide<br>
                <span>Teranga AI</span>
            </h1>

            <p class="hero-text">
                Découvrez le Sénégal, trouvez des informations utiles,
                préparez vos déplacements et posez vos questions à un
                assistant pensé pour le quotidien sénégalais.
            </p>

            <div class="hero-buttons">
                <button class="primary" id="startChat">
                    💬 Parler à Teranga AI
                </button>

                <button class="secondary" id="discoverBtn">
                    Découvrir le Sénégal
                </button>
            </div>
        </div>


        <div class="hero-card">

            <div class="hero-card-top">
                <div class="avatar">T</div>
                <div>
                    <strong>Teranga AI</strong>
                    <div class="status">● Disponible</div>
                </div>
            </div>

            <div class="demo-message">
                <div class="bubble user">
                    Que visiter à Dakar ?
                </div>

                <div class="bubble ai">
                    Dakar offre beaucoup de possibilités :
                    Gorée, les marchés, les musées, la corniche,
                    la cuisine sénégalaise et bien plus encore.
                    Je peux t'aider à préparer ton programme.
                </div>
            </div>

        </div>

    </div>
</section>


<!-- SERVICES -->

<section>
    <div class="container">

        <div class="section-title">
            <h2>Tout le Sénégal, dans votre assistant</h2>
            <p>Des réponses simples pour les besoins du quotidien.</p>
        </div>

        <div class="cards">

            <div class="card">
                <div class="card-icon">🌍</div>
                <h3>Découvrir</h3>
                <p>
                    Destinations, culture, histoire et activités
                    à travers le Sénégal.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">🍲</div>
                <h3>Goûter</h3>
                <p>
                    Cuisine sénégalaise, spécialités et idées
                    pour découvrir les saveurs locales.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">🚕</div>
                <h3>Se déplacer</h3>
                <p>
                    Informations pratiques sur les déplacements
                    et transports.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">🏨</div>
                <h3>Séjourner</h3>
                <p>
                    Conseils pour organiser un séjour et rechercher
                    des hébergements.
                </p>
            </div>

        </div>
    </div>
</section>


<!-- CHAT -->

<section class="chat-section" id="chatSection">

    <div class="container">

        <div class="section-title">
            <h2>Parlez avec Teranga AI</h2>
            <p>Posez votre question naturellement.</p>
        </div>

        <div class="chat-box">

            <div class="chat-head">
                <div class="avatar">T</div>
                <div>
                    <strong>Teranga AI</strong>
                    <span>Assistant Sénégal • FR / EN / Wolof</span>
                </div>
            </div>

            <div class="messages" id="messages">

                <div class="message ai">
                    <div class="message-bubble">
                        Bonjour 👋
                        Je suis Teranga AI.
                        Que souhaitez-vous découvrir ou savoir sur le Sénégal ?
                    </div>
                </div>

            </div>

            <div class="quick">
                <button data-question="Que visiter à Dakar ?">
                    📍 Dakar
                </button>

                <button data-question="Quels plats sénégalais dois-je goûter ?">
                    🍲 Cuisine
                </button>

                <button data-question="Comment se déplacer à Dakar ?">
                    🚕 Transport
                </button>

                <button data-question="Que visiter au Sénégal pour un premier voyage ?">
                    🌍 Voyage
                </button>
            </div>

            <div class="composer">

                <textarea
                    id="message"
                    maxlength="2000"
                    placeholder="Écrivez votre question..."
                    rows="1"
                ></textarea>

                <button class="send" id="sendBtn" title="Envoyer">
                    ➤
                </button>

            </div>

        </div>

    </div>
</section>


<!-- DESTINATIONS -->

<section class="destination" id="destinations">

    <div class="container">

        <div class="section-title">
            <h2>Quelques incontournables</h2>
            <p>Le Sénégal possède une grande diversité de paysages et de cultures.</p>
        </div>

        <div class="destination-grid">

            <div class="destination-card">
                <h3>Dakar</h3>
                <p>La capitale, la culture, la gastronomie et l'océan.</p>
            </div>

            <div class="destination-card">
                <h3>Saint-Louis</h3>
                <p>Une ville historique au patrimoine remarquable.</p>
            </div>

            <div class="destination-card">
                <h3>Casamance</h3>
                <p>Nature, paysages et richesse culturelle.</p>
            </div>

        </div>

    </div>
</section>

</main>


<footer>
    <div class="container footer-inner">
        <div>
            <strong>Teranga AI 🇸🇳</strong>
            <p>Votre assistant intelligent au Sénégal.</p>
        </div>

        <p>© 2026 Teranga AI</p>
    </div>
</footer>


<script>
const messages = document.getElementById("messages");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const startChat = document.getElementById("startChat");
const discoverBtn = document.getElementById("discoverBtn");
const langBtn = document.getElementById("langBtn");

let history = [];

function addMessage(text, role) {
    const wrapper = document.createElement("div");
    wrapper.className = "message " + role;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    // Important : textContent évite d'injecter du HTML.
    bubble.textContent = text;

    wrapper.appendChild(bubble);
    messages.appendChild(wrapper);

    messages.scrollTop = messages.scrollHeight;
}

function setLoading(loading) {
    sendBtn.disabled = loading;
    messageInput.disabled = loading;

    if (loading) {
        sendBtn.textContent = "…";
    } else {
        sendBtn.textContent = "➤";
        messageInput.disabled = false;
    }
}

async function sendMessage(text = null) {

    const question = (text || messageInput.value).trim();

    if (!question) {
        return;
    }

    if (question.length > 2000) {
        addMessage(
            "Votre message est trop long. Limitez-le à 2000 caractères.",
            "ai"
        );
        return;
    }

    addMessage(question, "user");

    messageInput.value = "";

    setLoading(true);

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: question,
                history: history
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error || "Une erreur est survenue."
            );
        }

        addMessage(data.reply, "ai");

        history.push({
            role: "user",
            content: question
        });

        history.push({
            role: "assistant",
            content: data.reply
        });

        // On garde uniquement les derniers échanges.
        if (history.length > 8) {
            history = history.slice(-8);
        }

    } catch (error) {

        addMessage(
            "Désolé, une erreur est survenue. Veuillez réessayer dans quelques instants.",
            "ai"
        );

        console.error(error);

    } finally {
        setLoading(false);
        messageInput.focus();
    }
}


sendBtn.addEventListener("click", function () {
    sendMessage();
});


messageInput.addEventListener("keydown", function (event) {

    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }

});


document.querySelectorAll("[data-question]").forEach(function (button) {

    button.addEventListener("click", function () {

        const question = button.getAttribute("data-question");

        sendMessage(question);
    });

});


startChat.addEventListener("click", function () {

    document.getElementById("chatSection").scrollIntoView({
        behavior: "smooth"
    });

    setTimeout(function () {
        messageInput.focus();
    }, 500);

});


discoverBtn.addEventListener("click", function () {

    document.getElementById("destinations").scrollIntoView({
        behavior: "smooth"
    });

});


langBtn.addEventListener("click", function () {

    addMessage(
        "Le changement complet de langue sera ajouté dans une prochaine version. Pour le moment, écrivez simplement en français, anglais ou Wolof et je m'adapterai.",
        "ai"
    );

});


messageInput.addEventListener("input", function () {

    messageInput.style.height = "auto";
    messageInput.style.height =
        Math.min(messageInput.scrollHeight, 130) + "px";

});
</script>

</body>
</html>
"""


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "teranga-ai",
        "model": MODEL
    })


def allowed_request(ip):
    now = time.time()
    requests = request_log[ip]

    while requests and now - requests[0] > RATE_WINDOW:
        requests.popleft()

    if len(requests) >= RATE_LIMIT:
        return False

    requests.append(now)
    return True


@app.route("/chat", methods=["POST"])
def chat():

    ip = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr or "unknown"
    ).split(",")[0].strip()

    if not allowed_request(ip):
        return jsonify({
            "error": "Trop de demandes. Veuillez patienter une minute."
        }), 429

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Requête invalide."
        }), 400

    message = data.get("message", "")

    if not isinstance(message, str):
        return jsonify({
            "error": "Message invalide."
        }), 400

    message = message.strip()

    if not message:
        return jsonify({
            "error": "Veuillez écrire une question."
        }), 400

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": "Votre message est trop long."
        }), 400

    history = data.get("history", [])

    if not isinstance(history, list):
        history = []

    # Sécurité : limiter la taille de l'historique envoyé.
    history = history[-MAX_HISTORY:]

    conversation = []

    for item in history:

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role not in ["user", "assistant"]:
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        conversation.append({
            "role": role,
            "content": content[:4000]
        })

    conversation.append({
        "role": "user",
        "content": message
    })

    try:

        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=conversation,
            tools=[
                {
                    "type": "web_search"
                }
            ]
        )

        reply = (response.output_text or "").strip()

        if not reply:
            reply = (
                "Je n'ai pas réussi à générer une réponse. "
                "Veuillez réessayer."
            )

        return jsonify({
            "reply": reply
        })

    except Exception as error:

        print("Erreur OpenAI :", repr(error))

        return jsonify({
            "error": "Le service est temporairement indisponible."
        }), 500


# =========================================================
# DÉMARRAGE
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5002,
        debug=False
    )