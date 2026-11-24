/* PostHog privacy gate: load the remote SDK only after explicit opt-in. */
(() => {
  "use strict";
  const script = document.currentScript;
  if (!script) return;
  const projectKey = script.dataset.projectKey || "";
  const apiHost = script.dataset.apiHost || "";
  const assetHost = script.dataset.assetHost || "";
  if (!projectKey.startsWith("phc_") || !apiHost.startsWith("https://") || !assetHost.startsWith("https://")) return;

  const CONSENT_KEY = "teranga_analytics_consent_v1";
  const isEnglish = /^en\b/i.test(document.documentElement.lang || "");
  const labels = isEnglish
    ? {title:"Help improve Teranga AI",body:"Optional anonymous audience measurement helps us improve the service. No analytics runs unless you agree.",accept:"Accept analytics",reject:"Reject",settings:"Privacy settings"}
    : {title:"Aider à améliorer Teranga AI",body:"Une mesure d’audience facultative nous aide à améliorer le service. Aucune analyse n’est activée sans votre accord.",accept:"Accepter les statistiques",reject:"Refuser",settings:"Paramètres de confidentialité"};

  const readConsent = () => {
    try { return window.localStorage.getItem(CONSENT_KEY); } catch (_) { return null; }
  };
  const writeConsent = value => {
    try { window.localStorage.setItem(CONSENT_KEY, value); } catch (_) {}
  };
  let sdkStarted = false;
  let panel;

  function loadSdk() {
    if (sdkStarted || readConsent() !== "accepted") return;
    sdkStarted = true;
    const sdk = document.createElement("script");
    sdk.src = assetHost + "/static/array.js";
    sdk.async = true;
    sdk.onload = () => {
      if (!window.posthog || typeof window.posthog.init !== "function" || readConsent() !== "accepted") return;
      window.posthog.init(projectKey, {
        api_host: apiHost,
        autocapture: false,
        capture_pageview: false,
        capture_pageleave: false,
        disable_session_recording: true,
        person_profiles: "never",
        persistence: "memory",
        ip: false,
        loaded: ph => {
          if (readConsent() !== "accepted") return;
          ph.capture("$pageview", { $current_url: window.location.origin + window.location.pathname });
        }
      });
    };
    sdk.onerror = () => { sdkStarted = false; };
    document.head.appendChild(sdk);
  }

  function removePanel() {
    if (panel) panel.remove();
    panel = null;
  }
  function showPanel() {
    removePanel();
    panel = document.createElement("section");
    panel.className = "teranga-consent-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-labelledby", "teranga-consent-title");
    panel.setAttribute("aria-describedby", "teranga-consent-description");
    panel.innerHTML = '<div class="teranga-consent-copy"><strong id="teranga-consent-title"></strong><p id="teranga-consent-description"></p></div><div class="teranga-consent-actions"><button type="button" data-choice="reject"></button><button type="button" data-choice="accept"></button></div>';
    panel.querySelector("#teranga-consent-title").textContent = labels.title;
    panel.querySelector("#teranga-consent-description").textContent = labels.body;
    panel.querySelector('[data-choice="reject"]').textContent = labels.reject;
    panel.querySelector('[data-choice="accept"]').textContent = labels.accept;
    panel.querySelector('[data-choice="reject"]').addEventListener("click", () => {
      writeConsent("rejected");
      if (window.posthog && typeof window.posthog.opt_out_capturing === "function") window.posthog.opt_out_capturing();
      removePanel();
    });
    panel.querySelector('[data-choice="accept"]').addEventListener("click", () => {
      writeConsent("accepted");
      removePanel();
      loadSdk();
    });
    document.body.appendChild(panel);
  }

  const style = document.createElement("style");
  style.textContent = ".teranga-consent-panel{position:fixed;z-index:2147483000;inset:auto 16px 16px 16px;max-width:760px;margin-inline:auto;padding:18px;display:flex;gap:18px;align-items:center;justify-content:space-between;background:#fffdf6;color:#1c2a20;border:1px solid #d9a441;border-radius:16px;box-shadow:0 12px 36px #0003;font:16px/1.45 system-ui,sans-serif}.teranga-consent-copy{min-width:0}.teranga-consent-copy strong{display:block;font-size:1rem}.teranga-consent-copy p{margin:6px 0 0}.teranga-consent-actions{display:flex;gap:8px;flex-wrap:wrap}.teranga-consent-actions button{min-height:44px;padding:9px 12px;border:1px solid #0f6a43;border-radius:10px;background:#fffdf6;color:#0f6a43;font:inherit;cursor:pointer}.teranga-consent-actions button[data-choice=accept]{background:#0f6a43;color:white}@media(max-width:600px){.teranga-consent-panel{inset:auto 8px 8px;display:block;padding:14px}.teranga-consent-actions{margin-top:12px}.teranga-consent-actions button{flex:1}}";
  document.head.appendChild(style);

  const settings = document.createElement("button");
  settings.type = "button";
  settings.textContent = labels.settings;
  settings.className = "teranga-consent-settings";
  settings.style.cssText = "position:fixed;z-index:2147482999;left:10px;bottom:10px;min-height:44px;padding:8px 12px;border:1px solid #0f6a43;border-radius:10px;background:#fffdf6;color:#0f6a43;font:14px system-ui,sans-serif;cursor:pointer";
  settings.addEventListener("click", showPanel);
  document.addEventListener("DOMContentLoaded", () => {
    document.body.appendChild(settings);
    const consent = readConsent();
    if (consent === "accepted") loadSdk();
    else if (consent !== "rejected") showPanel();
  });
})();
