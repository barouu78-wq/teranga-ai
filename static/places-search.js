// Recherche instantanée sur /lieux : filtre les fiches par texte et par type.
(function () {
  "use strict";
  var q = document.getElementById("place-q");
  var t = document.getElementById("place-type");
  var n = document.getElementById("place-count");
  if (!q || !t) return;
  var cards = Array.prototype.slice.call(document.querySelectorAll("a.card[data-text]"));
  var blocks = Array.prototype.slice.call(document.querySelectorAll("[data-region-block]"));
  function norm(s) {
    return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }
  function run() {
    var words = norm(q.value).split(/\s+/).filter(Boolean);
    var type = t.value;
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!type || c.dataset.type === type) && words.every(function (w) { return c.dataset.text.indexOf(w) >= 0; });
      c.hidden = !ok;
      if (ok) shown++;
    });
    blocks.forEach(function (b) { b.hidden = !b.querySelector("a.card:not([hidden])"); });
    n.textContent = q.value || type ? shown + (shown > 1 ? " lieux" : " lieu") : "";
  }
  q.addEventListener("input", run);
  t.addEventListener("change", run);
})();
