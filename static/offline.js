// Page /offline : liste les pages gardées par le service worker, lisibles
// sans réseau (guides, fiches de lieux, régions déjà ouverts).
(async function(){
  var list=document.getElementById('offline-pages');
  if(!list||!('caches' in window))return;
  try{
    var names=(await caches.keys()).filter(function(k){return /-pages$/.test(k);});
    var seen={},items=[];
    for(var i=0;i<names.length;i++){
      var cache=await caches.open(names[i]);
      var keys=await cache.keys();
      for(var j=0;j<keys.length;j++){
        var url=new URL(keys[j].url);
        if(url.pathname==='/offline'||seen[url.pathname])continue;
        seen[url.pathname]=1;
        var title=url.pathname==='/'?'Accueil':url.pathname;
        try{
          var html=await (await cache.match(keys[j])).text();
          var m=html.match(/<title>([^<]*)<\/title>/i);
          if(m)title=m[1].replace(/\s*\|\s*Teranga AI\s*$/,'').trim()||title;
        }catch(_){}
        items.push({href:url.pathname+url.search,title:title});
      }
    }
    if(!items.length)return;
    list.replaceChildren.apply(list,items.map(function(item){
      var li=document.createElement('li'),a=document.createElement('a');
      a.href=item.href;a.textContent=item.title;li.appendChild(a);return li;
    }));
    list.hidden=false;
    var empty=document.getElementById('offline-empty');if(empty)empty.hidden=true;
  }catch(_){}
})();
