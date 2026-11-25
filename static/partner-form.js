(function () {
  'use strict';
  // Formulaires simples du site : demande de partenariat (/offres-partenaires) et avis (/avis).
  var form = document.querySelector('form.partner-form');
  if (!form) return;
  var endpoint = form.getAttribute('data-endpoint') || '/api/partner-request';
  var success = form.getAttribute('data-success') || 'Merci ! Votre demande est bien reçue, nous vous recontactons rapidement.';
  var status = form.querySelector('[role=status]');
  function cookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  function inApp() {
    // Appli Android (TWA) ou appli installée : affichage sans barre du navigateur.
    try { return matchMedia('(display-mode: standalone)').matches || document.referrer.indexOf('android-app://') === 0; }
    catch (e) { return false; }
  }
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    var button = form.querySelector('button[type=submit]');
    var data = {};
    new FormData(form).forEach(function (value, key) { data[key] = String(value).trim(); });
    data.appli = inApp() ? '1' : '0';
    button.disabled = true;
    status.textContent = 'Envoi…';
    try {
      var token = cookie('teranga_csrf');
      if (!token) {
        var r = await fetch('/csrf', { credentials: 'same-origin', cache: 'no-store' });
        token = ((await r.json()) || {}).token || cookie('teranga_csrf');
      }
      var res = await fetch(endpoint, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
        body: JSON.stringify(data)
      });
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(body.error || 'Erreur');
      form.reset();
      status.textContent = success;
    } catch (e) {
      status.textContent = (e && e.message && e.message !== 'csrf') ? e.message : "L'envoi n'a pas fonctionné. Réessayez dans un instant.";
      button.disabled = false;
    }
  });
})();
