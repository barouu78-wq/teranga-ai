// Thème du site, partagé par l'accueil et toutes les pages.
// Mode « auto » (par défaut) : jour = « Terre de Teranga », nuit (18 h–6 h,
// heure du visiteur) = « Nuit de Dakar ». Le visiteur peut forcer clair/sombre.
// Les grandes fêtes ajoutent une touche (data-fete) sans changer la base.
(function(){
  var KEY='teranga-theme';
  // Dates des fêtes religieuses : estimations (calendrier lunaire), à ajuster
  // selon l'annonce officielle. Format : [mois, jour] de début, durée en jours.
  var FETES={
    2026:{korite:[3,20,2],tabaski:[5,27,2],magal:[8,2,2]},
    2027:{korite:[3,10,2],tabaski:[5,17,2],magal:[7,23,2]}
  };
  // Les anciennes versions enregistraient « light » ou « dark » au moindre
  // clic, ce qui bloquait le mode automatique. On remet tout le monde en
  // « auto » une seule fois ; les choix faits ensuite sont respectés.
  var VERSION_KEY='teranga-theme-v',VERSION='2';
  try{
    if(localStorage.getItem(VERSION_KEY)!==VERSION){
      localStorage.removeItem(KEY);
      localStorage.setItem(VERSION_KEY,VERSION);
    }
  }catch(e){}
  function readMode(){
    try{var v=localStorage.getItem(KEY);if(v==='light'||v==='dark'||v==='auto')return v;}catch(e){}
    return 'auto';
  }
  function saveMode(mode){try{localStorage.setItem(KEY,mode);}catch(e){}}
  function isNight(date){var h=(date||new Date()).getHours();return h>=18||h<6;}
  function resolve(mode,date){return mode==='dark'||(mode==='auto'&&isNight(date))?'dark':'light';}
  function within(date,month,day,days){
    var start=new Date(date.getFullYear(),month-1,day);
    var end=new Date(start.getTime()+days*86400000);
    return date>=start&&date<end;
  }
  function fete(date){
    date=date||new Date();
    try{var forced=new URLSearchParams(location.search).get('fete');if(forced)return forced;}catch(e){}
    var m=date.getMonth()+1,d=date.getDate();
    if(m===4&&d>=3&&d<=5)return 'independance';
    if((m===12&&d===31)||(m===1&&d===1))return 'nouvel-an';
    var year=FETES[date.getFullYear()]||{};
    for(var name in year){var f=year[name];if(within(date,f[0],f[1],f[2]))return name;}
    return '';
  }
  function apply(target){
    var mode=readMode(),theme=resolve(mode);
    (target||document.documentElement).dataset.theme=theme;
    return {mode:mode,theme:theme};
  }
  window.terangaTheme={readMode:readMode,saveMode:saveMode,resolve:resolve,isNight:isNight,fete:fete,apply:apply};
  apply();
  // Passage automatique jour/nuit sans recharger la page.
  setInterval(function(){if(readMode()==='auto')apply();},5*60*1000);
})();
