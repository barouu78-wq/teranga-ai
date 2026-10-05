// Bouton « Partager » des pages publiques (guides, pages traduites).
(function(){
  var btn=document.getElementById('share-page');
  if(!btn)return;
  var label=btn.textContent;
  var copied=btn.getAttribute('data-copied')||'Lien copié';
  var failed=btn.getAttribute('data-failed')||'Copiez l’adresse de la page';
  function flash(text){
    btn.textContent=text;
    clearTimeout(btn._t);
    btn._t=setTimeout(function(){btn.textContent=label;},2500);
  }
  function legacyCopy(text){
    var area=document.createElement('textarea');
    area.value=text;area.setAttribute('readonly','');
    area.style.position='fixed';area.style.opacity='0';
    document.body.appendChild(area);area.select();
    var ok=false;try{ok=document.execCommand('copy');}catch(_){}
    area.remove();return ok;
  }
  async function copy(){
    var url=location.href;
    try{
      if(navigator.clipboard&&navigator.clipboard.writeText){await navigator.clipboard.writeText(url);flash(copied);return;}
    }catch(_){}
    flash(legacyCopy(url)?copied:failed);
  }
  btn.addEventListener('click',async function(){
    if(btn.dataset.busy)return;
    btn.dataset.busy='1';
    try{
      if(navigator.share){
        try{await navigator.share({title:document.title,url:location.href});return;}
        catch(e){if(e&&e.name==='AbortError')return;}
      }
      await copy();
    }finally{delete btn.dataset.busy;}
  });
})();
