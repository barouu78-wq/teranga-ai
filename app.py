diff --git a/app.py b/app.py
index 7abc57a5afba6414797e9be589cca7c397e5cb98..b167f665bf7c292d72cbd5c088498bd6ce4787c9 100644
--- a/app.py
+++ b/app.py
@@ -739,50 +739,51 @@ header{
 .mark svg{width:24px;height:24px}
 .brand strong{display:block;font-size:15px;letter-spacing:-.04em;white-space:nowrap}
 .brand em{font-style:normal;color:var(--gold)}
 .brand span{display:flex;align-items:center;gap:6px;color:var(--mute);font-size:11px}
 .dot{width:7px;height:7px;border-radius:50%;background:#3dbe7e;box-shadow:0 0 0 4px rgba(61,190,126,.15)}
 .tools{display:flex;gap:6px;align-items:center}
 .seg{display:flex;padding:3px;border:1px solid var(--line);border-radius:999px;background:var(--card)}
 .seg button,.icon{
   border:0;background:transparent;color:var(--mute);border-radius:999px;
   padding:6px 8px;font-weight:750;cursor:pointer
 }
 .seg button.on{background:var(--brand-2);color:#fff}
 .icon{width:36px;height:36px;border:1px solid var(--line);background:var(--card);display:grid;place-items:center}
 .icon svg{width:16px;height:16px}
 #stage{flex:1;min-height:0;overflow:auto;padding:8px 16px 12px;contain:layout paint;overflow-anchor:none;-webkit-overflow-scrolling:touch;display:flex;flex-direction:column}
 #messages{margin-top:auto;padding-top:8px}
 .hero{
   margin:18px 0 8px;padding:22px 20px 18px;border-radius:28px;
   background:var(--card);
   border:1px solid var(--line);box-shadow:var(--shadow);
   contain:content;
 }
 .hero.is-hidden{display:none}
 .hero h1{margin:0 0 8px;font-size:28px;letter-spacing:-.05em;line-height:1.1}
 .hero p{margin:0 0 16px;color:var(--mute);max-width:42ch}
+.quick-label{margin:0 0 8px!important;color:var(--brand)!important;font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
 .cards{display:grid;grid-template-columns:1fr 1fr;gap:8px}
 .card{
   text-align:left;border:1px solid var(--line);background:color-mix(in srgb,var(--sand) 70%,transparent);
   border-radius:18px;padding:13px 14px;cursor:pointer;color:inherit
 }
 .card b{display:block;font-size:13px;margin-bottom:4px}
 .card span{display:block;color:var(--mute);font-size:12px;line-height:1.35}
 .card:hover{border-color:var(--gold)}
 .msg{margin:0 0 14px;display:flex;gap:8px;align-items:flex-end;contain:content;content-visibility:auto;contain-intrinsic-size:auto 72px}
 .msg.is-new{animation:in .18s ease}
 .msg.user{justify-content:flex-end}
 .avatar{
   flex:none;width:28px;height:28px;border-radius:10px;display:grid;place-items:center;
   background:linear-gradient(160deg,#1a5c3b,#072318);color:#f6e7c2;font-size:13px
 }
 .user .avatar{display:none}
 .col{max-width:min(86%,580px)}
 .bubble{
   padding:12px 14px;border-radius:20px;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere
 }
 .bubble.live{contain:content}
 .assistant .bubble{background:var(--soft);border-bottom-left-radius:7px}
 .user .bubble{background:linear-gradient(180deg,#214833,#14281e);color:#f7fff9;border-bottom-right-radius:7px}
 .acts{display:flex;gap:4px;margin-top:6px;opacity:.0;transition:.15s}
 .assistant:hover .acts,.assistant:focus-within .acts{opacity:1}
@@ -807,50 +808,51 @@ header{
 .typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
 .cursor{display:inline-block;width:7px;height:1em;background:var(--gold);margin-left:2px;vertical-align:-2px;animation:b .8s infinite}
 @keyframes b{50%{opacity:.25;transform:translateY(-2px)}}
 @keyframes in{from{opacity:0;transform:translateY(8px)}}
 .dock{
   padding:10px 14px calc(14px + env(safe-area-inset-bottom));
   background:color-mix(in srgb,var(--sand) 92%,transparent);
   contain:layout style;
 }
 .composer{
   border:1px solid var(--line);background:var(--card);border-radius:24px;
   padding:8px 8px 8px 14px;box-shadow:var(--shadow)
 }
 body.has-chat .chips,body.has-chat #hero{display:none}
 .chips{display:flex;gap:8px;overflow:auto;padding:0 2px 10px;scrollbar-width:none}
 .chips::-webkit-scrollbar{display:none}
 .chips button{
   flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink);
   border-radius:999px;padding:7px 12px;font-size:12px;cursor:pointer
 }
 .row{display:grid;grid-template-columns:1fr auto auto;gap:7px;align-items:end}
 textarea{
   width:100%;min-height:46px;max-height:130px;resize:none;border:0;
   padding:10px 4px 8px 0;background:transparent;color:var(--ink);outline:0;font:inherit
 }
+.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
 #mic,#send{height:44px;border:0;border-radius:16px;cursor:pointer;font-weight:800}
 #mic{width:44px;background:color-mix(in srgb,var(--gold) 28%,var(--card));color:#7a4a00}
 #mic.listen{background:#c93636;color:#fff}
 #send{padding:0 16px;background:var(--brand-2);color:#fff}
 #send:disabled{opacity:.5}
 .meta{display:flex;justify-content:space-between;gap:8px;margin-top:8px;color:var(--mute);font-size:11px;padding:0 6px}
 .meta button{border:0;background:0;color:var(--brand);font-weight:750;cursor:pointer}
 .spread{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
 .spread a,.spread button{
   border:1px solid var(--line);background:var(--sand);color:var(--ink);
   border-radius:999px;padding:8px 12px;font-size:13px;font-weight:750;cursor:pointer;text-decoration:none
 }
 .spread .wa{background:#128C7E;border-color:#128C7E;color:#fff}
 .spread .install{background:var(--brand-2);border-color:var(--brand-2);color:#fff}
 .spread .install[hidden]{display:none}
 .seo{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
 .foot{
   display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;
   padding:6px 6px 0;color:var(--mute);font-size:11px
 }
 .foot button,.foot a{border:0;background:0;color:var(--brand);font-weight:750;cursor:pointer;text-decoration:none}
 #count{font-variant-numeric:tabular-nums}
 @media(max-width:680px){
   header{padding:10px 12px calc(8px + env(safe-area-inset-top));gap:6px}
   .brand span#sub,.brand .dot{display:none}
@@ -886,170 +888,184 @@ textarea{
       <span><i class="dot"></i> <span id="sub">Assistant Sénégal</span></span>
     </div>
   </div>
   <div class="tools">
     <div class="seg" id="langs">
       <button type="button" data-lang="fr" class="on">FR</button>
       <button type="button" data-lang="en">EN</button>
       <button type="button" data-lang="wo">WO</button>
       <button type="button" data-lang="ff">PU</button>
     </div>
     <button class="icon" id="themeBtn" type="button" title="Thème" aria-label="Thème">
       <svg viewBox="0 0 24 24" fill="none"><path d="M12 3v2M12 19v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M3 12h2M19 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4M8 12a4 4 0 1 0 8 0 4 4 0 0 0-8 0Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
     </button>
     <button class="icon" id="shareAppBtn" type="button" title="Partager" aria-label="Partager">
       <svg viewBox="0 0 24 24" fill="none"><path d="M15 8a3 3 0 1 0-2.8-4H12a3 3 0 0 0 .2 4L8.5 12M15 16l-4.7-4M8.5 12A3 3 0 1 0 6 17.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
     </button>
     <button class="icon" id="resetBtn" type="button" title="Nouveau" aria-label="Nouveau chat">
       <svg viewBox="0 0 24 24" fill="none"><path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
     </button>
   </div>
 </header>
 <div id="stage">
   <div id="hero" class="hero">
     <h1 id="heroTitle">L’hospitalité, en quelques questions.</h1>
     <p id="heroText">Météo, trajets, plats, plages, marchés — Teranga t’oriente sans inventer les détails qui bougent.</p>
+    <p class="quick-label" id="quickLabel">Questions populaires</p>
     <div class="cards" id="cards"></div>
     <div class="spread">
       <a class="wa" id="waShare" target="_blank" rel="noopener noreferrer" href="#">WhatsApp</a>
       <button type="button" class="install" id="installBtn" hidden>Installer l’app</button>
       <button type="button" id="copyLink">Copier le lien</button>
     </div>
   </div>
   <section class="seo">
     <h2>Assistant Sénégal</h2>
     <p>Teranga AI aide habitants, diaspora et voyageurs : géographie des 14 régions, où manger à Dakar par quartier, météo, taxi AIBD, ferry Gorée, visa. L’interface parle français, anglais, wolof et pulaar.</p>
   </section>
-  <div id="messages"></div>
+  <div id="messages" role="log" aria-live="polite" aria-relevant="additions"></div>
 </div>
 <div class="dock">
   <div class="chips" id="chips"></div>
   <div class="composer">
     <div class="row">
-      <textarea id="input" maxlength="2000" placeholder="Pose ta question…" rows="1"></textarea>
+      <label class="sr-only" for="input" id="inputLabel">Votre question</label>
+      <textarea id="input" maxlength="2000" placeholder="Pose ta question…" rows="1" aria-describedby="hint count"></textarea>
       <button id="mic" type="button" title="Parler" aria-label="Parler">🎤</button>
       <button id="send" type="button">Envoyer</button>
     </div>
   </div>
   <div class="meta">
     <span id="hint">Réponse en direct</span>
     <span id="count">0 / 2000</span>
     <button id="voiceToggle" type="button">Voix auto off</button>
   </div>
 </div>
 </div>
 <script nonce="__CSP_NONCE__">
 const $ = id => document.getElementById(id);
 const messages=$('messages'), input=$('input'), send=$('send'), mic=$('mic'), stage=$('stage'), hero=$('hero');
 const reduceMotion=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
 const T={
 fr:{
   sub:'Assistant Sénégal',ph:'Pose ta question…',send:'Envoyer',
+  quickLabel:'Questions populaires',inputLabel:'Votre question sur le Sénégal',
   welcome:'Salut, je suis Teranga AI. Que veux-tu savoir sur le Sénégal ?',
   timeout:'Délai dépassé. Réessaie.',err:'Service indisponible.',
   vOn:'Voix auto on',vOff:'Voix auto off',listen:'Écouter',copy:'Copier',copied:'Copié',
   share:'Partager',stop:'Arrêter',retry:'Réessayer',resetAsk:'Effacer la conversation ?',
   sources:'Sources',copyLink:'Copier le lien',linkCopied:'Lien copié',
   shareText:'Teranga AI — l’assistant du Sénégal (français, anglais, wolof). Météo, taxi, visa, cuisine :',
   install:'Installer l’app',
   heroTitle:'L’hospitalité, en quelques questions.',
   heroText:'Météo, trajets, plats, plages, marchés — Teranga t’oriente sans inventer les détails qui bougent.',
   hint:'Réponse en direct · Entrée pour envoyer',
   hintTouch:'Réponse en direct',
   cards:[
     {q:"Quel temps fait-il à Dakar aujourd'hui ?",t:'Météo Dakar',d:'Ciel, chaleur et vent du jour'},
     {q:"Combien coûte un taxi de l'aéroport AIBD à Dakar ?",t:'Taxi AIBD',d:'Ordre de prix et options'},
     {q:"Raconte brièvement l'histoire de Dakar et montre la ville.",t:'Histoire Dakar',d:'Ville, origine, photo'},
     {q:"Quelles sont les spécialités culinaires de chaque région du Sénégal ?",t:'Spécialités',d:'Plats du Nord, Centre, Casamance'},
     {q:"Où manger à Dakar selon le quartier : Plateau, Médina, Almadies, Ngor, Ouakam ?",t:'Où manger',d:'Quartier, plage ou marché'},
-    {q:"Présente la géographie du Sénégal : régions, grandes villes et Casamance.",t:'Régions',d:'14 régions et grandes villes'}
+    {q:"Présente la géographie du Sénégal : régions, grandes villes et Casamance.",t:'Régions',d:'14 régions et grandes villes'},
+    {q:"Comment acheter une SIM au Sénégal et utiliser Orange Money ?",t:'SIM & paiement',d:'Réseau, données et paiement mobile'},
+    {q:"Comment organiser une visite de l’île de Gorée depuis Dakar ?",t:'Gorée',d:'Ferry, départ et conseils'}
   ]
 },
 en:{
   sub:'Senegal assistant',ph:'Ask a question…',send:'Send',
+  quickLabel:'Popular questions',inputLabel:'Your question about Senegal',
   welcome:'Hi, I am Teranga AI. What do you want to know about Senegal?',
   timeout:'Timed out. Try again.',err:'Service unavailable.',
   vOn:'Auto voice on',vOff:'Auto voice off',listen:'Listen',copy:'Copy',copied:'Copied',
   share:'Share',stop:'Stop',retry:'Retry',resetAsk:'Clear the conversation?',
   sources:'Sources',copyLink:'Copy link',linkCopied:'Link copied',
   shareText:'Teranga AI — Senegal assistant (French, English, Wolof). Weather, taxi, visa, food:',
   install:'Install app',
   heroTitle:'Hospitality, in a few questions.',
   heroText:'Weather, rides, food, beaches, markets — Teranga guides you without inventing shifting details.',
   hint:'Live answers · Enter to send',
   hintTouch:'Live answers',
   cards:[
     {q:'What is the weather like in Dakar today?',t:'Dakar weather',d:'Sky, heat and wind today'},
     {q:'How much is a taxi from AIBD airport to Dakar?',t:'AIBD taxi',d:'Price range and options'},
     {q:'Briefly tell the history of Dakar and show the city.',t:'Dakar history',d:'City, origin, photo'},
     {q:'What are the regional food specialties across Senegal?',t:'Specialties',d:'Dishes from North, Center, Casamance'},
     {q:'Where should I eat in Dakar by area: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Where to eat',d:'Neighborhood, beach or market'},
-    {q:'Explain the geography of Senegal: regions, main cities and Casamance.',t:'Regions',d:'14 regions and main cities'}
+    {q:'Explain the geography of Senegal: regions, main cities and Casamance.',t:'Regions',d:'14 regions and main cities'},
+    {q:'How do I buy a SIM card in Senegal and use Orange Money?',t:'SIM & payments',d:'Network, data and mobile payments'},
+    {q:'How should I plan a visit to Gorée Island from Dakar?',t:'Gorée',d:'Ferry, departure and tips'}
   ]
 },
 wo:{
   sub:'Assistant Senegaal',ph:'Laajal…',send:'Yónnee',
+  quickLabel:'Laaj yu ñu faral di laaj',inputLabel:'Sa laaj ci Senegaal',
   welcome:'Salaam, maa ngi doon Teranga AI. Lan nga bëgg xam ci Senegaal?',
   timeout:'Dafa yàgg. Jéemaatal.',err:'Service bañ na.',
   vOn:'Baat auto on',vOff:'Baat auto off',listen:'Dégg',copy:'Koppi',copied:'Koppi na',
   share:'Séddoo',stop:'Taxal',retry:'Jéemaatal',resetAsk:'Dindi waxtaan wi?',
   sources:'Téere',copyLink:'Koppi lien',linkCopied:'Lien koppi na',
   shareText:'Teranga AI — assistant Senegaal (français, anglais, wolof). Tàkk-tàkk, taksi, visa, ñam :',
   install:'Yebal app bi',
   heroTitle:'Teranga, ci laaj yu néew.',
   heroText:'Taw, taksi, ñam, teex ak marché — Teranga dina la wonal te du sos lu mëna soppi.',
   hint:'Tontu ci kaw · Enter ngir yónnee',
   hintTouch:'Tontu ci kaw',
   cards:[
     {q:"Lan mooy tàkk-tàkk Dakaar tey?",t:'Tàkk-tàkk',d:'Asamaan, tàngaay ak ngelaw'},
     {q:"Ñaata la taksi AIBD ba Dakaar?",t:'Taksi AIBD',d:'Njëg ak tànneef'},
     {q:"Nettali sama ndakaru Dakaar, wone dëkk bi.",t:'Tàriix Dakaar',d:'Dëkk, tàriix, nataal'},
     {q:'Ban ñam aju ci réegion yu Senegaal?',t:'Ñam réegion',d:'Nord, centre, Kasamans'},
     {q:'Fan laa wara lekk ci Dakaar: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Lekk',d:'Quartier, teex walla marché'},
-    {q:'Wan nga ma géographie Senegaal: régions, dëkk yu mag ak Kasamans.',t:'Réegion',d:'14 régions ak dëkk yu mag'}
+    {q:'Wan nga ma géographie Senegaal: régions, dëkk yu mag ak Kasamans.',t:'Réegion',d:'14 régions ak dëkk yu mag'},
+    {q:'Naka laa jënde SIM ci Senegaal te jëfandikoo Orange Money?',t:'SIM & fay',d:'Réseau, data ak fay ci telefon'},
+    {q:'Naka laa waajal seet île de Gorée jógé Dakaar?',t:'Gorée',d:'Baatu gaal, départ ak ndigal'}
   ]
 },
 ff:{
   sub:'Ballal Senegaal',ph:'Naamndu…',send:'Neldu',
+  quickLabel:'Naamne ɗe ɓurɗe waɗde',inputLabel:'Naamndu maa e Senegaal',
   welcome:'Jam tan, miin woni Teranga AI. Hol ko njiɗɗaa anndude e Senegaal?',
   timeout:'Sahaa booyii. Fuɗɗit.',err:'Sarwiis jaɓaani.',
   vOn:'Sawtu auto on',vOff:'Sawtu auto off',listen:'Heɗo',copy:'Natal',copied:'Natalaa',
   share:'Lollin',stop:'Dartin',retry:'Fuɗɗit',resetAsk:'Momtu yeewtere nde?',
   sources:'Iwdiiji',copyLink:'Natal jokkol',linkCopied:'Jokkol nataa',
   shareText:'Teranga AI — ballal Senegaal (farayse, english, wolof, pulaar).',
   install:'Aaf app',
   heroTitle:'Teranga, e naamne seeɗa.',
   heroText:'Kaanawol, taksi, ñaamdu, geec, luumooji — Teranga holata, wonaa fefindoo.',
   hint:'Jaabawol e sahaa. Sawtu nde ɓadiima pulaar.',
   hintTouch:'Jaabawol e sahaa. Sawtu ɓadiima.',
   cards:[
     {q:'Hol kaanawol Dakaar hannde?',t:'Kaanawol',d:'Dakaar hannde'},
     {q:'Fotde taksi AIBD haa Dakaar?',t:'Taksi AIBD',d:'Njoɓdi e tati'},
     {q:'Hol ñaamdu Dakaar e diiwe: Plateau, Medina, Almadies, Ngor, Ouakam?',t:'Ñaamdu',d:'Diiwal, geec walla luumo'},
     {q:'Hol geografi Senegaal: diiwe, gure mawɗe e Kasamans?',t:'Diiwe',d:'Diiwe 14 e gure'},
-    {q:'Haal Aada Dakaar e hollu wuro ngo.',t:'Aada Dakaar',d:'Wuro, aada, natal'}
-    {q:'Hol ñaamdu diiwe Senegaal kala?',t:'Ñaamdu diiwe',d:'Fuuta, hakkunde, Kasamans'}
+    {q:'Haal Aada Dakaar e hollu wuro ngo.',t:'Aada Dakaar',d:'Wuro, aada, natal'},
+    {q:'Hol ñaamdu diiwe Senegaal kala?',t:'Ñaamdu diiwe',d:'Fuuta, hakkunde, Kasamans'},
+    {q:'Hol no mi waɗirta SIM e Senegaal e Orange Money?',t:'SIM & ceede',d:'Réseau, data e ceede telefon'},
+    {q:'Hol no mi waɗirta yillugol Gorée iwde Dakaar?',t:'Gorée',d:'Baatu, yaltude e dokkal'}
   ]
 }
 };
 const voiceMap={fr:'fr-FR',en:'en-US',wo:'wo-SN',ff:'fr-FR'};
 let lang=localStorage.getItem('teranga-lang')||'fr';
 if(!T[lang])lang='fr';
 let history=[], rec=null, listening=false, audio=null, autoVoice=localStorage.getItem('teranga-voice')==='1', inflight=null;
 let persistTimer=0, scrollRaf=0, stickToBottom=true, lastLang='';
 function cleanReply(text){
   return String(text||'')
     .replace(/```[\s\S]*?```/g,m=>m.replace(/```/g,''))
     .replace(/`([^`]+)`/g,'$1')
     .replace(/\*\*([^*]+)\*\*/g,'$1')
     .replace(/__([^_]+)__/g,'$1')
     .replace(/(^|\s)\*([^*\n]+)\*(?=\s|$|[.,;!?])/g,'$1$2')
     .replace(/\*\*/g,'')
     .replace(/__/g,'')
     .replace(/^#{1,6}\s+/gm,'')
     .replace(/^\s*[-*•]\s+/gm,'')
     .replace(/\n{3,}/g,'\n\n')
     .trim();
 }
 function cookie(name){
   const m=document.cookie.match(new RegExp('(?:^|; )'+name+'=([^;]*)'));
   return m?decodeURIComponent(m[1]):'';
@@ -1166,51 +1182,52 @@ async function speak(text,btn){
   }catch(e){if(btn){btn.disabled=false;btn.textContent=T[lang].listen;}}
 }
 function renderCards(){
   if(lastLang===lang)return;
   lastLang=lang;
   const t=T[lang];
   const cardFrag=document.createDocumentFragment();
   const chipFrag=document.createDocumentFragment();
   t.cards.forEach(c=>{
     const card=document.createElement('button');
     card.className='card';card.type='button';card.dataset.q=c.q;
     const b=document.createElement('b');b.textContent=c.t;
     const s=document.createElement('span');s.textContent=c.d;
     card.append(b,s);cardFrag.appendChild(card);
     const chip=document.createElement('button');
     chip.type='button';chip.dataset.q=c.q;chip.textContent=c.t;
     chipFrag.appendChild(chip);
   });
   $('cards').replaceChildren(cardFrag);
   $('chips').replaceChildren(chipFrag);
 }
 function setLang(next){
   lang=next;localStorage.setItem('teranga-lang',next);
   document.querySelectorAll('#langs button').forEach(b=>b.classList.toggle('on',b.dataset.lang===next));
   const t=T[lang];
-  $('sub').textContent=t.sub;input.placeholder=t.ph;send.textContent=t.send;
+  $('sub').textContent=t.sub;input.placeholder=t.ph;input.setAttribute('aria-label',t.inputLabel);
+  $('inputLabel').textContent=t.inputLabel;$('quickLabel').textContent=t.quickLabel;send.textContent=t.send;
   $('voiceToggle').textContent=autoVoice?t.vOn:t.vOff;
   $('heroTitle').textContent=t.heroTitle;$('heroText').textContent=t.heroText;
   $('hint').textContent=isTouch()?t.hintTouch:t.hint;
   document.documentElement.lang=next==='wo'?'wo':next;
   renderCards();
   bindShare();
   if(rec)rec.lang=voiceMap[lang];
 }
 function themeInit(){
   const saved=localStorage.getItem('teranga-theme');
   if(saved)document.body.dataset.theme=saved;
   applyThemeColor();
 }
 function reset(){
   if(history.length&&!confirm(T[lang].resetAsk))return;
   if(inflight)inflight.abort();
   history=[];messages.replaceChildren();showHero();
   sessionStorage.removeItem('teranga-history');
 }
 function setupMic(){
   const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
   if(!SR){mic.disabled=true;mic.title='Micro non disponible';return;}
   rec=new SR();rec.continuous=false;rec.interimResults=false;rec.lang=voiceMap[lang];
   rec.onstart=()=>{listening=true;mic.classList.add('listen');};
   rec.onresult=e=>{input.value=e.results[0][0].transcript;ask();};
