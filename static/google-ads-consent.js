/* Balise Google Ads : gtag.js n'est chargé qu'après un « Accepter » explicite (services/google_ads_tag.py). */
(() => {
  "use strict";
  const script = document.currentScript;
  if (!script) return;
  const tagId = script.dataset.tagId || "";
  if (!/^AW-\d{6,15}$/.test(tagId)) return;

  const CONSENT_KEY = "teranga_ads_consent_v1";
  const isEnglish = /^en\b/i.test(document.documentElement.lang || "");
  const labels = isEnglish
    ? {title:"Advertising cookies",body:"With your consent, Google Ads cookies measure what visitors coming from our ads do on the site. Nothing is loaded if you refuse.",accept:"Accept",reject:"Refuse"}
    : {title:"Cookies publicitaires",body:"Avec votre accord, des cookies Google Ads mesurent ce que font sur le site les visiteurs venus de nos annonces. Rien n’est chargé si vous refusez.",accept:"Accepter",reject:"Refuser"};

  // Choix gardé aussi en mémoire : si le navigateur bloque le stockage local, « Accepter » charge quand même la
  // balise pour cette page (relecture Codex de #614).
  let memoryConsent = null;
  const readConsent = () => {
    if (memoryConsent) return memoryConsent;
    try { return window.localStorage.getItem(CONSENT_KEY); } catch (_) { return null; }
  };
  const writeConsent = value => {
    memoryConsent = value;
    try { window.localStorage.setItem(CONSENT_KEY, value); } catch (_) {}
  };
  const GRANTED = {ad_storage:"granted",ad_user_data:"granted",ad_personalization:"granted",analytics_storage:"denied"};
  const DENIED = {ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied",analytics_storage:"denied"};
  let started = false;
  let panel;

  function gtag() { window.dataLayer.push(arguments); }

  function loadTag() {
    if (started || readConsent() !== "accepted") return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    // Mode consentement v2 : refus par défaut, puis l'accord donné par le visiteur.
    gtag("consent", "default", DENIED);
    gtag("consent", "update", GRANTED);
    gtag("js", new Date());
    gtag("config", tagId);
    const tag = document.createElement("script");
    tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(tagId);
    tag.async = true;
    tag.onerror = () => { started = false; };
    document.head.appendChild(tag);
  }

  // Conversions (GOOGLE_ADS_CONVERSIONS) : seulement après « Accepter », une fois par session et par action.
  const conversions = {question: script.dataset.conversionQuestion, appli: script.dataset.conversionAppli,
                       cv: script.dataset.conversionCv};
  const sent = {};
  function sendConversion(name) {
    const label = conversions[name] || "";
    if (!started || readConsent() !== "accepted" || !/^AW-\d{6,15}\/[A-Za-z0-9_-]{4,40}$/.test(label)) return;
    const key = "teranga_ads_conv_" + name;
    let done = sent[name];
    try { done = done || window.sessionStorage.getItem(key) === "1"; } catch (_) {}
    if (done) return;
    sent[name] = true;
    try { window.sessionStorage.setItem(key, "1"); } catch (_) {}
    gtag("event", "conversion", {send_to: label});
  }
  window.terangaAdsConversion = sendConversion;
  // Lien vers l'application Android (APK ou Google Play), sur n'importe quelle page.
  document.addEventListener("click", event => {
    const link = event.target && event.target.closest ? event.target.closest("a[href]") : null;
    if (!link) return;
    const href = link.getAttribute("href") || "";
    if (/play\.google\.com\/store\/apps/.test(href) || /\.apk(?:$|[?#])/.test(href)) sendConversion("appli");
  }, true);

  function removePanel() {
    if (panel) panel.remove();
    panel = null;
  }
  function showPanel() {
    removePanel();
    panel = document.createElement("section");
    panel.className = "teranga-ads-consent-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-labelledby", "teranga-ads-consent-title");
    panel.setAttribute("aria-describedby", "teranga-ads-consent-description");
    panel.innerHTML = '<div class="teranga-ads-consent-copy"><strong id="teranga-ads-consent-title"></strong><p id="teranga-ads-consent-description"></p></div><div class="teranga-ads-consent-actions"><button type="button" data-choice="reject"></button><button type="button" data-choice="accept"></button></div>';
    panel.querySelector("#teranga-ads-consent-title").textContent = labels.title;
    panel.querySelector("#teranga-ads-consent-description").textContent = labels.body;
    panel.querySelector('[data-choice="reject"]').textContent = labels.reject;
    panel.querySelector('[data-choice="accept"]').textContent = labels.accept;
    panel.querySelector('[data-choice="reject"]').addEventListener("click", () => {
      writeConsent("rejected");
      if (started && Array.isArray(window.dataLayer)) gtag("consent", "update", DENIED);
      removePanel();
    });
    panel.querySelector('[data-choice="accept"]').addEventListener("click", () => {
      writeConsent("accepted");
      removePanel();
      loadTag();
    });
    document.body.appendChild(panel);
  }

  // Deux boutons de même poids : « Refuser » aussi visible que « Accepter » (CNIL).
  const style = document.createElement("style");
  style.textContent = ".teranga-ads-consent-panel{position:fixed;z-index:2147483001;inset:auto 16px 16px 16px;max-width:760px;margin-inline:auto;padding:18px;display:flex;gap:18px;align-items:center;justify-content:space-between;background:#fffdf6;color:#1c2a20;border:1px solid #d9a441;border-radius:16px;box-shadow:0 12px 36px #0003;font:16px/1.45 system-ui,sans-serif}.teranga-ads-consent-copy{min-width:0}.teranga-ads-consent-copy strong{display:block;font-size:1rem}.teranga-ads-consent-copy p{margin:6px 0 0}.teranga-ads-consent-actions{display:flex;gap:8px;flex-wrap:wrap}.teranga-ads-consent-actions button{min-height:44px;min-width:110px;padding:9px 12px;border:1px solid #0f6a43;border-radius:10px;background:#0f6a43;color:#fff;font:inherit;cursor:pointer}@media(max-width:600px){.teranga-ads-consent-panel{inset:auto 8px 8px;display:block;padding:14px}.teranga-ads-consent-actions{margin-top:12px}.teranga-ads-consent-actions button{flex:1}}";
  document.head.appendChild(style);

  // Pas de bouton flottant (il couvrirait la saisie du chat) : la page de confidentialité porte un bouton
  // [data-ads-consent] qui rouvre le choix.
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-ads-consent]").forEach(button => {
      button.hidden = false;
      button.addEventListener("click", showPanel);
    });
    const consent = readConsent();
    if (consent === "accepted") loadTag();
    else if (consent !== "rejected") showPanel();
  });
})();
