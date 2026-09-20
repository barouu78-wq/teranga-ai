from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT = """You are Teranga AI, the intelligent assistant for Senegal. You help TWO types of users:

1) SENEGALESE MERCHANTS: find customers, suppliers, sell online, know Wave/Orange Money.
2) TOURISTS: discover markets, prices, negotiate, avoid scams, places to visit.

LANGUAGE: Detect automatically the language of the user message.
- French message -> answer in French.
- English message -> answer in English.
- Wolof message -> answer in French with some Wolof expressions.
- You can mix French and English if the user does.

CONTEXT DETECTION:
- Sales, business, customers, suppliers -> merchant mode.
- Travel, market, visit, tourist prices -> tourist mode.
- Otherwise, ask politely.

=== MERCHANT INFO ===
Payment: Wave, Orange Money, Free Money. Pro markets: Sandaga, HLM, Colobane.
Tips: WhatsApp Business, TikTok, Instagram, online shop.
Suppliers: Diack Tissu (HLM5), Suhayb Tissus (Mbacke), Cosmeticatop, Bonfoni.

=== TOURIST INFO ===
PLACES IN DAKAR:
- Goree Island: boat 5000 FCFA, Slave House 500-1500 FCFA, UNESCO
- African Renaissance Monument: 2000-5000 FCFA, 52m, panoramic view
- Pink Lake (Lac Rose): 35km, pink water, pirogue 5000-15000 FCFA
- Bandia Reserve: safari, adults 12000 FCFA, children 7000 FCFA
- Mamelles Lighthouse: 153m, 3000 FCFA, 360 view
- Kermel Market: flowers, souvenirs, 7am-7pm except Sun afternoon
- Sandaga: textile, negotiation required
- HLM: high-end fabrics, tailors
- Soumbedioune: crafts, fishing port, pirogues return 5pm
- Almadies Point: westernmost point of Africa
- Ngor Beach: island accessible by pirogue 2000 FCFA

OUTSIDE DAKAR:
- Saint-Louis: UNESCO, 3h drive
- Sine Saloum: delta, mangroves, pirogue
- Lompoul: desert dunes, 1 night under tent
- Casamance: green region, 8h
- Touba: holy city, 2h
- Saly: seaside resort, 1h30
- Joal-Fadiouth: shell island

PRICES 2026:
- Simple boubou 3000-15000 / embroidered 15000-50000 / high-end 50000-150000 FCFA
- Bazin 2500-3500 FCFA/m (Getzner 10000)
- Wax 2000-5000 FCFA/m
- Ebony mask 10000-50000 FCFA
- Wood sculpture 15000-100000 FCFA
- Leather sandals 10000-25000 FCFA
- Ndiakhass ring 15000-20000 / Bracelet 55000 / Gold set 380000-430000 FCFA
- Woven basket 35000-90000 FCFA
- Attaya teapot 5000-10000 FCFA
- Djembe 45000-80000 FCFA

RESTAURANTS DAKAR:
- Chez Loutcha: thieboudienne, yassa. 5000-15000 FCFA
- Le Djoloff: elegant. 8000-20000 FCFA
- Terrou-Bi: sea view. 15000-40000 FCFA
- Ngor Pieds Dans L'Eau: fish. 10000-30000 FCFA

TRANSPORT:
- Taxi Plateau-Point E: 1000-1500 / Plateau-Ngor: 2000-3000 FCFA
- Airport-Downtown: taxi 50000-55000, Yango/Heetch 15000-25000, Dem Dikk 5000
- Boat Dakar-Goree: 5000-5500 FCFA, 20 min
- Car rapide: 100-300 FCFA

SPECIALTIES:
- Thieboudienne 3000-8000 FCFA
- Yassa 3000-7000 FCFA
- Mafe 3000-7000 FCFA
- Bissap, Bouye, Cafe Touba, Attaya: 200-1000 FCFA

NEGOTIATION: Ask 50% of price. Smile. Stay polite. If too expensive, walk away. Buy in group.

SCAMS TO AVOID:
- Fake money changers at airport
- Unofficial guides
- Tourist prices x2 or x3
- Flashy jewelry in public
- Isolated areas at night

Respond in 3-5 sentences. Be warm like a Senegalese friend."""

HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Teranga AI - Senegal</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Poppins',sans-serif;-webkit-tap-highlight-color:transparent}
body{background:linear-gradient(-45deg,#001a0e,#006b32,#00853F,#FF8C00,#00853F,#001a0e);background-size:400% 400%;animation:bg 20s ease infinite;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:12px;position:relative;overflow:hidden}
@keyframes bg{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.orb{position:absolute;border-radius:50%;filter:blur(60px);opacity:.4;pointer-events:none}
.orb.o1{width:400px;height:400px;background:#FDEF42;top:-100px;left:-100px;animation:fl1 18s ease-in-out infinite}
.orb.o2{width:350px;height:350px;background:#FF8C00;bottom:-80px;right:-80px;animation:fl2 22s ease-in-out infinite}
.orb.o3{width:300px;height:300px;background:#00a84f;top:50%;left:50%;transform:translate(-50%,-50%);animation:fl3 25s ease-in-out infinite}
@keyframes fl1{0%,100%{transform:translate(0,0)}50%{transform:translate(60px,40px)}}
@keyframes fl2{0%,100%{transform:translate(0,0)}50%{transform:translate(-50px,-40px)}}
@keyframes fl3{0%,100%{transform:translate(-50%,-50%) scale(1)}50%{transform:translate(-50%,-50%) scale(1.3)}}
.chat{background:rgba(255,255,255,.98);backdrop-filter:blur(20px);width:100%;max-width:520px;height:94vh;border-radius:28px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.5),0 0 0 1px rgba(255,255,255,.15),inset 0 1px 0 rgba(255,255,255,.8);position:relative;z-index:10;animation:chatIn .8s cubic-bezier(.2,.8,.2,1)}
@keyframes chatIn{from{opacity:0;transform:translateY(40px) scale(.95)}to{opacity:1;transform:translateY(0) scale(1)}}
.flag{display:flex;height:6px;position:relative;overflow:hidden}
.band{flex:1;position:relative;animation:wave 2.5s ease-in-out infinite;transform-origin:bottom}
.band::after{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.5),transparent);animation:shine 3s linear infinite}
.band.g{background:linear-gradient(90deg,#00853F,#00b359)}
.band.y{background:linear-gradient(90deg,#FDEF42,#FFD700);animation-delay:.35s}
.band.r{background:linear-gradient(90deg,#E31B23,#FF3B3B);animation-delay:.7s}
@keyframes wave{0%,100%{transform:scaleY(1)}50%{transform:scaleY(2)}}
@keyframes shine{0%{transform:translateX(-100%)}100%{transform:translateX(200%)}}
.h{padding:24px 20px 20px;text-align:center;color:#fff;position:relative;overflow:hidden;background:linear-gradient(135deg,#00853F,#00a84f,#FF8C00,#D35400);background-size:300% 300%;animation:grad 8s ease infinite}
@keyframes grad{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.h::before{content:'';position:absolute;top:-60%;right:-15%;width:220px;height:220px;background:radial-gradient(circle,rgba(253,239,66,.35),transparent 70%);border-radius:50%;animation:orb 8s ease-in-out infinite}
.h::after{content:'';position:absolute;bottom:-60%;left:-15%;width:180px;height:180px;background:radial-gradient(circle,rgba(255,255,255,.2),transparent 70%);border-radius:50%;animation:orb 10s ease-in-out infinite reverse}
@keyframes orb{0%,100%{transform:translate(0,0)}50%{transform:translate(-20px,20px)}}
.h .logo{font-size:28px;font-weight:800;letter-spacing:.5px;position:relative;z-index:1;text-shadow:0 2px 12px rgba(0,0,0,.2)}
.h .logo span{color:#FDEF42}
.h .sub{font-size:13px;margin-top:8px;opacity:.95;position:relative;z-index:1;font-weight:500}
.h .badge{display:inline-block;margin-top:10px;padding:6px 16px;background:rgba(255,255,255,.25);border-radius:20px;font-size:11px;font-weight:600;backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.35);position:relative;z-index:1}
.lang-switch{position:absolute;top:14px;right:14px;display:flex;gap:4px;background:rgba(255,255,255,.25);border-radius:16px;padding:3px;z-index:5;backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.35)}
.lang-switch button{padding:5px 12px;border:none;background:transparent;color:#fff;font-weight:700;font-size:11px;border-radius:12px;cursor:pointer;transition:all .3s}
.lang-switch button.on{background:rgba(255,255,255,.9);color:#00853F}
.msgs{flex:1;overflow-y:auto;padding:20px;background:linear-gradient(180deg,#f8f9fa,#fff);scroll-behavior:smooth}
.msgs::-webkit-scrollbar{width:5px}
.msgs::-webkit-scrollbar-thumb{background:#ccc;border-radius:3px}
.m{margin-bottom:16px;padding:14px 18px;border-radius:20px;max-width:88%;line-height:1.55;font-size:14px;word-wrap:break-word;animation:msgIn .5s cubic-bezier(.2,.8,.2,1);position:relative}
@keyframes msgIn{from{opacity:0;transform:translateY(20px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}
.m.u{color:#fff;margin-left:auto;border-bottom-right-radius:6px;font-weight:500;background:linear-gradient(135deg,#00853F,#00a84f,#FF8C00);background-size:200% 200%;animation:msgIn .5s cubic-bezier(.2,.8,.2,1),grad 6s ease infinite;box-shadow:0 8px 20px rgba(0,133,63,.3)}
.m.a{background:#fff;color:#1a1a1a;border:1px solid #e9ecef;border-bottom-left-radius:6px;padding-left:54px;box-shadow:0 4px 15px rgba(0,0,0,.04)}
.m.a::before{content:'🤖';position:absolute;top:14px;left:14px;width:30px;height:30px;background:linear-gradient(135deg,#e8f5ee,#d4ede0);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 4px 12px rgba(0,133,63,.2);animation:glow 3s ease-in-out infinite}
@keyframes glow{0%,100%{box-shadow:0 4px 12px rgba(0,133,63,.2)}50%{box-shadow:0 4px 20px rgba(0,133,63,.4)}}
.sug{display:flex;gap:8px;padding:12px 16px;overflow-x:auto;background:#fff;border-top:1px solid #f0f0f0}
.sug::-webkit-scrollbar{display:none}
.sug button{padding:9px 16px;border-radius:20px;font-size:12px;cursor:pointer;white-space:nowrap;font-weight:600;transition:all .3s cubic-bezier(.4,0,.2,1);background:linear-gradient(135deg,#e8f5ee,#fff4e6);color:#006b32;border:1.5px solid #c8e6d4}
.sug button:hover{background:linear-gradient(135deg,#00853F,#FF8C00);color:#fff;transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,133,63,.35);border-color:transparent}
.inp{display:flex;padding:14px;background:#fff;gap:10px;border-top:1px solid #eee}
.inp input{flex:1;padding:14px 20px;border:2px solid #e9ecef;border-radius:26px;outline:none;font-size:14px;font-family:'Poppins',sans-serif;transition:all .3s;background:#f8f9fa}
.inp input:focus{border-color:#00853F;background:#fff;box-shadow:0 0 0 4px rgba(0,133,63,.1)}
.inp button{color:#fff;border:none;width:52px;height:52px;border-radius:50%;cursor:pointer;font-size:20px;font-weight:700;transition:all .2s;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#00853F,#00a84f,#FF8C00);background-size:200% 200%;animation:pulse 2.5s infinite,grad 6s ease infinite;box-shadow:0 8px 20px rgba(0,133,63,.4)}
.inp button:hover{transform:scale(1.1)}
.inp button:disabled{background:#ccc;animation:none;box-shadow:none}
@keyframes pulse{0%,100%{box-shadow:0 8px 20px rgba(0,133,63,.4),0 0 0 0 rgba(0,133,63,.6)}50%{box-shadow:0 8px 20px rgba(0,133,63,.4),0 0 0 15px rgba(0,133,63,0)}}
.ld{padding:14px 18px;padding-left:54px;background:#fff;border:1px solid #e9ecef;border-radius:20px;border-bottom-left-radius:6px;display:inline-block;margin-bottom:16px;position:relative;box-shadow:0 4px 15px rgba(0,0,0,.04);animation:msgIn .4s ease-out}
.ld::before{content:'🤖';position:absolute;top:14px;left:14px;width:30px;height:30px;background:linear-gradient(135deg,#e8f5ee,#d4ede0);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px}
.ld span{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 3px;background:#00853F;animation:b 1.4s infinite}
.ld span:nth-child(2){animation-delay:.15s;background:#FF8C00}
.ld span:nth-child(3){animation-delay:.3s}
@keyframes b{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-10px);opacity:1}}
@media(max-width:600px){.chat{height:100vh;border-radius:0;max-width:100%}body{padding:0}.h .logo{font-size:22px}}
</style>
</head>
<body>
<div class="orb o1"></div>
<div class="orb o2"></div>
<div class="orb o3"></div>
<div class="chat">
<div class="flag"><div class="band g"></div><div class="band y"></div><div class="band r"></div></div>
<div class="h">
<div class="lang-switch">
<button id="frBtn" class="on" onclick="setLang('fr')">FR</button>
<button id="enBtn" onclick="setLang('en')">EN</button>
</div>
<div class="logo">Teranga<span>AI</span> 🇸🇳</div>
<div class="sub" id="sub">Votre assistant intelligent au Senegal</div>
<div class="badge" id="badge">✨ Commercants & Touristes</div>
</div>
<div class="msgs" id="msgs">
<div class="m a" id="welcome">Nanga def ! 👋<br><br>Je suis <b>Teranga AI</b>, ton assistant au Senegal.<br><br>Je t'aide que tu sois <b>commercant</b> (clients, fournisseurs, ventes) ou <b>touriste</b> (marches, prix, lieux a visiter).<br><br>Pose-moi une question ou clique sur une suggestion 👇</div>
</div>
<div class="sug" id="sug">
<button onclick="ask(this)">Trouver des clients</button>
<button onclick="ask(this)">Fournisseurs bazin</button>
<button onclick="ask(this)">Lieux a visiter</button>
<button onclick="ask(this)">Prix dun boubou</button>
<button onclick="ask(this)">Ou manger</button>
</div>
<div class="inp">
<input type="text" id="q" placeholder="Pose ta question..." onkeypress="if(event.key==='Enter')send()">
<button id="btn" onclick="send()">➤</button>
</div>
</div>
<script>
let lang='fr';
function setLang(l){
  lang=l;
  document.getElementById('frBtn').className=(l==='fr'?'on':'');
  document.getElementById('enBtn').className=(l==='en'?'on':'');
  if(l==='fr'){
    document.getElementById('sub').textContent='Votre assistant intelligent au Senegal';
    document.getElementById('badge').textContent='✨ Commercants & Touristes';
    document.getElementById('welcome').innerHTML='Nanga def ! 👋<br><br>Je suis <b>Teranga AI</b>, ton assistant au Senegal.<br><br>Je t\\'aide que tu sois <b>commercant</b> (clients, fournisseurs, ventes) ou <b>touriste</b> (marches, prix, lieux a visiter).<br><br>Pose-moi une question ou clique sur une suggestion 👇';
    document.getElementById('q').placeholder='Pose ta question...';
    document.getElementById('sug').innerHTML='<button onclick="ask(this)">Trouver des clients</button><button onclick="ask(this)">Fournisseurs bazin</button><button onclick="ask(this)">Lieux a visiter</button><button onclick="ask(this)">Prix dun boubou</button><button onclick="ask(this)">Ou manger</button>';
  }else{
    document.getElementById('sub').textContent='Your smart assistant in Senegal';
    document.getElementById('badge').textContent='✨ Merchants & Tourists';
    document.getElementById('welcome').innerHTML='Nanga def ! 👋<br><br>I am <b>Teranga AI</b>, your assistant in Senegal.<br><br>I help you whether you are a <b>merchant</b> (customers, suppliers, sales) or a <b>tourist</b> (markets, prices, places to visit).<br><br>Ask me a question or click a suggestion 👇';
    document.getElementById('q').placeholder='Ask your question...';
    document.getElementById('sug').innerHTML='<button onclick="ask(this)">Find customers</button><button onclick="ask(this)">Bazin suppliers</button><button onclick="ask(this)">Places to visit</button><button onclick="ask(this)">Boubou price</button><button onclick="ask(this)">Where to eat</button>';
  }
}
function ask(el){document.getElementById('q').value=el.textContent;send();}
async function send(){
  const i=document.getElementById('q');
  const t=i.value.trim();
  if(!t)return;
  const ms=document.getElementById('msgs');
  ms.innerHTML+='<div class="m u">'+t+'</div>';
  i.value='';
  ms.innerHTML+='<div class="ld" id="ld"><span></span><span></span><span></span></div>';
  ms.scrollTop=ms.scrollHeight;
  document.getElementById('btn').disabled=true;
  try{
    const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t,lang:lang})});
    const d=await r.json();
    document.getElementById('ld').remove();
    ms.innerHTML+='<div class="m a">'+d.reply.replace(/\\n/g,'<br>')+'</div>';
    ms.scrollTop=ms.scrollHeight;
  }catch(e){
    document.getElementById('ld').remove();
    ms.innerHTML+='<div class="m a">'+(lang==='fr'?'Erreur. Reessaie.':'Error. Try again.')+'</div>';
  }
  document.getElementById('btn').disabled=false;
  document.getElementById('q').focus();
}
</script>
</body>
</html>"""

@app.route('/')
def home():
    return HTML

@app.route('/chat', methods=['POST'])
def chat():
    try:
        d = request.json
        m = d.get('message', '')
        lang = d.get('lang', 'fr')
        p = PROMPT + "\\n\\nIMPORTANT: User chose language: " + ("Francais" if lang == "fr" else "English") + ". Respond in that language."
        r = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":p},{"role":"user","content":m}])
        return jsonify({"reply": r.choices[0].message.content})
    except Exception as e:
        return jsonify({"reply": "Erreur: " + str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
