(function () {
  'use strict';
  var form = document.getElementById('partner-form');
  if (!form) return;
  var status = document.getElementById('partner-form-status');
  function cookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    var button = form.querySelector('button[type=submit]');
    var data = {};
    new FormData(form).forEach(function (value, key) { data[key] = String(value).trim(); });
    button.disabled = true;
    status.textContent = 'Envoi…';
    try {
      var token = cookie('teranga_csrf');
      if (!token) {
        var r = await fetch('/csrf', { credentials: 'same-origin', cache: 'no-store' });
        token = ((await r.json()) || {}).token || cookie('teranga_csrf');
      }
      var res = await fetch('/api/partner-request', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
        body: JSON.stringify(data)
      });
      var body = await res.json().catch(function () { return {}; });
      if (!res.ok) throw new Error(body.error || 'Erreur');
      form.reset();
      status.textContent = 'Merci ! Votre demande est bien reçue, nous vous recontactons rapidement.';
    } catch (e) {
      status.textContent = (e && e.message && e.message !== 'csrf') ? e.message : "L'envoi n'a pas fonctionné. Réessayez dans un instant.";
      button.disabled = false;
    }
  });
})();
