/*! Teranga AI — widget partenaire.
 * Usage :
 *   <script src="https://teranga-ai.fr/widget.js" data-partner="mon-hotel" data-lang="fr" defer></script>
 * Options : data-partner (identifiant libre, sert à la mesure d'audience),
 *           data-lang (fr | en | wo), data-position (right | left),
 *           data-question (question pré-remplie, facultative).
 * Le bouton ouvre Teranga AI sur teranga-ai.fr (fenêtre ou nouvel onglet) :
 * aucune donnée du site partenaire n'est lue ni transmise.
 */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script || window.__terangaWidget) return;
  window.__terangaWidget = true;

  var base = new URL(script.src, location.href).origin;
  var data = script.dataset || {};
  var partner = String(data.partner || "").toLowerCase().replace(/[^a-z0-9_-]/g, "").slice(0, 40) || "partenaire";
  var lang = ["fr", "en", "wo"].indexOf(data.lang) >= 0 ? data.lang : "fr";
  var side = data.position === "left" ? "left" : "right";
  var question = String(data.question || "").slice(0, 300);
  var TEXT = {
    fr: { label: "Une question sur le Sénégal ?", aria: "Ouvrir Teranga AI, l’assistant du Sénégal (nouvelle fenêtre)" },
    en: { label: "Questions about Senegal?", aria: "Open Teranga AI, the Senegal assistant (new window)" },
    wo: { label: "Laaj ci Senegaal ?", aria: "Ubbi Teranga AI (palanteer bu bees)" }
  }[lang];

  var params = new URLSearchParams({ lang: lang, utm_source: partner, utm_medium: "widget", utm_campaign: "partenaires" });
  if (question) params.set("q", question);
  var url = base + "/?" + params.toString();

  function mount() {
    var host = document.createElement("div");
    host.setAttribute("data-teranga-widget", "");
    // Shadow DOM : le style du site partenaire ne touche pas le bouton, et inversement.
    var root = host.attachShadow ? host.attachShadow({ mode: "closed" }) : host;
    var style = document.createElement("style");
    style.textContent =
      ":host{all:initial}" +
      "a{position:fixed;bottom:20px;" + side + ":20px;z-index:2147483000;display:flex;align-items:center;gap:10px;" +
      "padding:12px 18px 12px 12px;border-radius:999px;background:#0f6b45;color:#fff;text-decoration:none;" +
      "font:600 15px/1.2 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.22);" +
      "transition:transform .15s ease,box-shadow .15s ease}" +
      "a:hover{transform:translateY(-2px);box-shadow:0 12px 28px rgba(0,0,0,.26)}" +
      "a:focus-visible{outline:3px solid #e2b34a;outline-offset:3px}" +
      ".mark{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#f6e7c2;flex:none}" +
      ".mark svg{width:20px;height:20px}" +
      "@media (max-width:480px){a{bottom:14px;" + side + ":14px;padding:10px}.text{display:none}}" +
      "@media (prefers-reduced-motion:reduce){a{transition:none}a:hover{transform:none}}";
    var link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.setAttribute("aria-label", TEXT.aria);
    link.title = "Teranga AI";
    link.innerHTML =
      '<span class="mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M12 21V9M5 13c3-.8 4.2-4 7-4s4 3.2 7 4" ' +
      'stroke="#0f6b45" stroke-width="1.8" stroke-linecap="round"/><circle cx="17" cy="5" r="1.8" fill="#c8902e"/></svg></span>' +
      '<span class="text"></span>';
    link.querySelector(".text").textContent = TEXT.label;
    link.addEventListener("click", function (event) {
      // Grand écran : petite fenêtre à côté du site partenaire. Sinon (ou si
      // elle est bloquée), le lien s'ouvre normalement dans un nouvel onglet.
      if (window.innerWidth < 900) return;
      // Pas de « noopener » dans window.open : il renverrait toujours null.
      var popup = window.open(url, "teranga-ai", "popup=yes,width=440,height=760");
      if (popup) {
        popup.opener = null;
        event.preventDefault();
      }
    });
    root.appendChild(style);
    root.appendChild(link);
    document.body.appendChild(host);
  }

  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
