// Mon CV (Teranga Emploi) : envoie le CV ou le parcours à /api/cv, affiche le CV rendu dans un des neuf modèles
// (MODELES suit les boutons de services/cv.py),
// le laisse corriger, et l'enregistre en PDF par l'impression du navigateur. Le CV créé reste dans ce navigateur
// (localStorage) : le serveur ne garde rien. Tout le texte venu de l'IA passe par textContent, jamais par innerHTML.
(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const CLE='teranga-cv',MAX=2*1024*1024;
  const DOCX='application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  const MODELES=['sobre','moderne','teranga','classique','minimal','creatif','ocean','baobab','elegant'];
  const ERREUR='Le CV n’a pas pu être créé. Réessaie dans un moment.';
  let piece=null,cv=null,modele='sobre';

  function garder(){try{localStorage.setItem(CLE,JSON.stringify({cv,modele}));}catch(_){}}
  function oublier(){try{localStorage.removeItem(CLE);}catch(_){}}
  function relire(){
    try{
      const d=JSON.parse(localStorage.getItem(CLE)||'null');
      if(d&&d.cv&&typeof d.cv==='object'&&!Array.isArray(d.cv))return d;
    }catch(_){}
    return null;
  }
  function erreur(texte){$('cvErreur').textContent=texte||'';}
  // Étapes du formulaire, comptées par le serveur chaque mois sans rien de ce que la personne écrit (routes/monetization.py,
  // cv_etape) : savoir où les visiteurs s'arrêtent. Une fois chacune par visite ; une erreur réseau est ignorée.
  const signales=new Set();
  function etape(nom){
    if(signales.has(nom))return;
    signales.add(nom);
    try{fetch('/cv/etape/'+nom,{cache:'no-store',keepalive:true,credentials:'omit'}).catch(()=>{});}catch(_){}
  }

  // --- Fichier : photo réduite en JPEG (1 568 px), PDF ou Word de 2 Mo au plus (le serveur revérifie tout) ---
  function base64(blob){
    return new Promise((ok,ko)=>{const r=new FileReader();r.onload=()=>ok(String(r.result).split(',')[1]||'');r.onerror=()=>ko(new Error('lecture'));r.readAsDataURL(blob);});
  }
  async function photoJpeg(file){
    const bmp=await createImageBitmap(file);
    const k=Math.min(1,1568/Math.max(bmp.width,bmp.height));
    const c=document.createElement('canvas');c.width=Math.max(1,Math.round(bmp.width*k));c.height=Math.max(1,Math.round(bmp.height*k));
    const g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,c.width,c.height);g.drawImage(bmp,0,0,c.width,c.height);
    if(bmp.close)bmp.close();
    const blob=await new Promise(ok=>c.toBlob(ok,'image/jpeg',0.85));
    if(!blob)throw new Error('lecture');
    return blob;
  }
  async function lirePiece(file){
    const nom=String(file.name||'cv').slice(-80);
    let type=file.type||'',blob=file;
    if(!type&&/\.docx$/i.test(nom))type=DOCX;
    if(!type&&/\.pdf$/i.test(nom))type='application/pdf';
    if(/^image\//.test(type)){
      try{blob=await photoJpeg(file);type='image/jpeg';}
      catch(_){if(!/^image\/(jpeg|png|webp)$/.test(type))throw new Error('Ce type de fichier n’est pas accepté : PDF, Word (.docx) ou photo.');}
    }else if(type!=='application/pdf'&&type!==DOCX)throw new Error('Ce type de fichier n’est pas accepté : PDF, Word (.docx) ou photo.');
    if(blob.size>MAX)throw new Error('Fichier trop lourd : 2 Mo au plus.');
    return {nom,type,donnees:await base64(blob)};
  }

  // --- Rendu du CV (textContent seulement) ---
  function el(tag,cls,texte){const e=document.createElement(tag);if(cls)e.className=cls;if(texte!=null)e.textContent=texte;return e;}
  function modifiable(e,chemin){
    e.dataset.champ=chemin;
    try{e.contentEditable='plaintext-only';}catch(_){e.contentEditable='true';}
    if(e.contentEditable!=='plaintext-only')e.contentEditable='true';
    return e;
  }
  function champModifiable(tag,cls,valeur,chemin){return modifiable(el(tag,cls,valeur||''),chemin);}
  // Icônes Lucide v1.75.0 (https://lucide.dev, licence ISC : static/LICENCE-lucide.txt), recopiées ici : aucun fichier
  // ni script d'un autre site. Décoratives (aria-hidden), elles prennent la couleur du texte de chaque modèle.
  const ICONES={
    ville:[["path",{"d":"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"}],["circle",{"cx":"12","cy":"10","r":"3"}]],
    telephone:[["path",{"d":"M13.832 16.568a1 1 0 0 0 1.213-.303l.355-.465A2 2 0 0 1 17 15h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2A18 18 0 0 1 2 4a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.8 1.6l-.468.351a1 1 0 0 0-.292 1.233 14 14 0 0 0 6.392 6.384"}]],
    email:[["path",{"d":"m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"}],["rect",{"x":"2","y":"4","width":"20","height":"16","rx":"2"}]],
    profil:[["circle",{"cx":"12","cy":"8","r":"5"}],["path",{"d":"M20 21a8 8 0 0 0-16 0"}]],
    experience:[["path",{"d":"M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"}],["rect",{"width":"20","height":"14","x":"2","y":"6","rx":"2"}]],
    formation:[["path",{"d":"M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"}],["path",{"d":"M22 10v6"}],["path",{"d":"M6 12.5V16a6 3 0 0 0 12 0v-3.5"}]],
    competences:[["path",{"d":"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"}],["path",{"d":"M20 2v4"}],["path",{"d":"M22 4h-4"}],["circle",{"cx":"4","cy":"20","r":"2"}]],
    langues:[["path",{"d":"m5 8 6 6"}],["path",{"d":"m4 14 6-6 2-3"}],["path",{"d":"M2 5h12"}],["path",{"d":"M7 2h1"}],["path",{"d":"m22 22-5-10-5 10"}],["path",{"d":"M14 18h6"}]],
  };
  const SVG='http://www.w3.org/2000/svg';
  function icone(nom){
    const s=document.createElementNS(SVG,'svg');
    [['class','cv-ico'],['viewBox','0 0 24 24'],['fill','none'],['stroke','currentColor'],['stroke-width','2'],['stroke-linecap','round'],
     ['stroke-linejoin','round'],['aria-hidden','true'],['focusable','false'],['data-icone',nom]].forEach(([k,v])=>s.setAttribute(k,v));
    ICONES[nom].forEach(([tag,attrs])=>{const e=document.createElementNS(SVG,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));s.appendChild(e);});
    return s;
  }
  function section(feuille,titre,nom){
    const s=el('section','cv-section'),h=el('h4','cv-rubrique');
    h.append(icone(nom),document.createTextNode(titre));
    s.appendChild(h);feuille.appendChild(s);return s;
  }

  // Exemple du haut de page : une personne fictive (dite comme telle sur la page), jamais le CV de quelqu'un.
  const EXEMPLE={
    nom:'Awa Ndiaye',titre:'Assistante comptable',ville:'Dakar',telephone:'77 000 00 00',email:'awa.ndiaye@exemple.sn',
    profil:'Titulaire d’un BTS comptabilité et gestion. Deux stages en cabinet : saisie, rapprochements bancaires et classement des pièces. Utilise Sage et Excel.',
    experiences:[
      {poste:'Stagiaire comptable',employeur:'Cabinet comptable',lieu:'Dakar',dates:'Mars – août 2025',
       taches:['Saisie des factures fournisseurs dans Sage','Préparation des rapprochements bancaires du mois','Classement et archivage des pièces comptables']},
      {poste:'Vendeuse (job d’été)',employeur:'Boutique de quartier',lieu:'Dakar',dates:'Été 2023',taches:['Tenue de la caisse','Accueil et conseil des clients']}],
    formations:[{diplome:'BTS Comptabilité et gestion',etablissement:'Institut de formation',dates:'2025'},
                {diplome:'Baccalauréat G',etablissement:'Lycée',dates:'2022'}],
    competences:['Sage','Excel : tableaux et formules','Saisie comptable','Rapprochement bancaire'],
    langues:['Français','Wolof','Anglais (notions)'],
  };
  function initiales(nom){
    return String(nom||'').split(/\s+/).filter(Boolean).slice(0,2).map(m=>m[0].toUpperCase()).join('');
  }
  // Trois zones : en-tête, corps (profil, expérience, formation) et côté (compétences, langues). Chaque modèle les
  // place à sa façon (CSS) : une colonne pour Sobre, deux colonnes sur la feuille A4 pour Moderne et Teranga.
  // dessiner() sert au vrai CV (modifiable) et à l'exemple du haut de page (lecture seule).
  function dessiner(f,cv,modele,modifier){
    const champ=(tag,cls,valeur,chemin)=>modifier?champModifiable(tag,cls,valeur,chemin):el(tag,cls,valeur||'');
    f.replaceChildren();
    f.className='cv-feuille '+modele;
    const tete=el('header','cv-tete'),corps=el('div','cv-corps'),cote=el('div','cv-cote');
    const mono=el('span','cv-mono',initiales(cv.nom));mono.setAttribute('aria-hidden','true');
    const ident=el('div','cv-ident');
    ident.append(champ('p','cv-nom',cv.nom||'Ton nom','nom'),champ('p','cv-titre',cv.titre,'titre'));
    const contact=[['ville',cv.ville],['telephone',cv.telephone],['email',cv.email]].filter(c=>c[1]);
    if(contact.length){
      const ul=el('ul','cv-contact');
      contact.forEach(([nom,valeur])=>{const li=el('li');li.append(icone(nom),document.createTextNode(valeur));ul.appendChild(li);});
      ident.appendChild(ul);
    }
    tete.append(mono,ident);
    if(cv.profil)section(corps,'Profil','profil').appendChild(champ('p','cv-texte',cv.profil,'profil'));
    if(cv.experiences&&cv.experiences.length){
      const s=section(corps,'Expérience','experience'),frise=el('div','cv-frise');
      cv.experiences.forEach((x,i)=>{
        const bloc=el('div','cv-bloc');
        const quand=[x.dates,x.lieu].filter(Boolean).join(' · ');
        if(quand)bloc.appendChild(el('p','cv-quand',quand));
        bloc.appendChild(champ('p','cv-poste',[x.poste,x.employeur].filter(Boolean).join(' · '),'experiences.'+i+'.entete'));
        if(x.taches&&x.taches.length){
          const ul=el('ul','cv-taches');
          x.taches.forEach((t,j)=>ul.appendChild(champ('li','',t,'experiences.'+i+'.taches.'+j)));
          bloc.appendChild(ul);
        }
        frise.appendChild(bloc);
      });
      s.appendChild(frise);
    }
    if(cv.formations&&cv.formations.length){
      const s=section(corps,'Formation','formation'),frise=el('div','cv-frise');
      cv.formations.forEach((x,i)=>{
        const bloc=el('div','cv-bloc');
        if(x.dates)bloc.appendChild(el('p','cv-quand',x.dates));
        bloc.appendChild(champ('p','cv-poste',[x.diplome,x.etablissement].filter(Boolean).join(' · '),'formations.'+i+'.entete'));
        frise.appendChild(bloc);
      });
      s.appendChild(frise);
    }
    if(cv.competences&&cv.competences.length){
      const s=section(cote,'Compétences','competences'),ul=el('ul','cv-tags');
      cv.competences.forEach((t,j)=>ul.appendChild(champ('li','',t,'competences.'+j)));
      s.appendChild(ul);
    }
    if(cv.langues&&cv.langues.length)section(cote,'Langues','langues').appendChild(champ('p','cv-texte',cv.langues.join(', '),'langues.texte'));
    f.append(tete,corps);
    if(cote.childNodes.length)f.appendChild(cote);
  }
  function rendre(){
    dessiner($('cvFeuille'),cv,modele,true);
    liste('cvVerifier',cv.a_verifier);
    liste('cvManque',cv.manque);
    const alerte=$('cvAlerte');alerte.textContent=cv.alerte||'';alerte.hidden=!cv.alerte;
    const lettre=$('cvLettre');lettre.replaceChildren();
    $('cvLettreBloc').hidden=!cv.lettre;
    if(cv.lettre)lettre.appendChild(champModifiable('div','cv-lettre-texte',cv.lettre,'lettre'));
    document.querySelectorAll('.cv-modele').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.modele===modele)));
  }
  function liste(id,valeurs){
    const bloc=$(id),ul=bloc.querySelector('ul');
    ul.replaceChildren(...(valeurs||[]).map(v=>el('li','',v)));
    bloc.hidden=!(valeurs&&valeurs.length);
  }
  // Une correction dans l'aperçu est reportée dans le CV gardé (texte seulement).
  function corriger(e){
    const cible=e.target.closest&&e.target.closest('[data-champ]');
    if(!cible||!cv)return;
    const morceaux=cible.dataset.champ.split('.'),texte=cible.textContent;
    if(morceaux[0]==='langues'){cv.langues=texte.split(',').map(t=>t.trim()).filter(Boolean);}
    else if(morceaux.length===1){cv[morceaux[0]]=texte;}
    else if(morceaux[2]==='entete'){
      const x=cv[morceaux[0]][+morceaux[1]];
      if(morceaux[0]==='experiences'){x.poste=texte;x.employeur='';}else{x.diplome=texte;x.etablissement='';}
    }
    else if(morceaux[0]==='competences'){cv.competences[+morceaux[1]]=texte;}
    else if(morceaux[2]==='taches'){cv.experiences[+morceaux[1]].taches[+morceaux[3]]=texte;}
    garder();
  }

  function afficher(){
    $('cvForm').hidden=true;$('cvExemple').hidden=true;
    $('cvResultat').hidden=false;
    rendre();
    const titre=$('cvResultatTitre');titre.tabIndex=-1;titre.focus();
  }

  // --- Envoi ---
  async function jeton(){
    try{const r=await fetch('/csrf',{credentials:'same-origin',cache:'no-store'});const d=await r.json();return d.token||'';}
    catch(_){return '';}
  }
  async function creer(e){
    e.preventDefault();
    erreur('');
    const depart=document.querySelector('input[name="depart"]:checked').value;
    const corps={poste:$('cvPoste').value.trim(),offre:$('cvOffre').value.trim()};
    if(depart==='fichier'){
      if(!piece){etape('refus-fichier');erreur('Choisis ton CV : PDF, Word ou photo.');$('cvFichier').focus();return;}
      corps.fichier=piece;
    }else{
      const recit=$('cvParcours').value.trim(),nom=$('cvNom').value.trim();
      if(recit.length<20){etape('refus-parcours');erreur('Raconte ton parcours en quelques phrases.');$('cvParcours').focus();return;}
      corps.parcours=(nom?'Nom : '+nom+'\n':'')+recit;
    }
    etape('envoi');
    const bouton=$('cvCreer');
    bouton.disabled=true;bouton.textContent='Création de ton CV…';bouton.setAttribute('aria-busy','true');
    try{
      const signal=window.AbortSignal&&AbortSignal.timeout?AbortSignal.timeout(90000):undefined;
      const r=await fetch('/api/cv',{method:'POST',credentials:'same-origin',signal,
        headers:{'Content-Type':'application/json','X-CSRF-Token':await jeton()},body:JSON.stringify(corps)});
      const d=await r.json().catch(()=>({}));
      if(!r.ok||!d.cv){erreur(d.error||ERREUR);return;}
      cv=d.cv;garder();afficher();
    }catch(_){erreur(ERREUR);}
    finally{bouton.disabled=false;bouton.textContent='Créer mon CV';bouton.removeAttribute('aria-busy');}
  }

  // Réduction qui fait tenir le CV sur une page A4 (largeur et hauteur utiles avec les marges de 14 mm de @page) :
  // mesurée sur une copie hors écran, à la largeur imprimée, sans descendre sous 0,8 (texte encore lisible). Plus long : deux pages.
  const A4_LARGEUR=688,A4_HAUTEUR=1000;
  function echelleUnePage(){
    const boite=document.createElement('div');
    boite.className='cv-resultat';
    boite.setAttribute('aria-hidden','true');
    boite.style.cssText='position:absolute;left:-10000px;top:0;width:'+A4_LARGEUR+'px;margin:0;visibility:hidden';
    const copie=$('cvFeuille').cloneNode(true);
    copie.removeAttribute('id');
    boite.appendChild(copie);
    document.body.appendChild(boite);
    let echelle=1;
    while(echelle>0.8&&boite.getBoundingClientRect().height>A4_HAUTEUR){
      echelle=Math.round((echelle-0.05)*100)/100;
      copie.style.zoom=echelle;
    }
    const tient=boite.getBoundingClientRect().height<=A4_HAUTEUR;
    boite.remove();
    return tient?echelle:1;
  }

  function imprimer(classe){
    const feuille=$('cvFeuille');
    if(classe==='imprime-cv')feuille.style.setProperty('--cv-echelle',String(echelleUnePage()));
    document.body.classList.add(classe);
    const fin=()=>{document.body.classList.remove(classe);feuille.style.removeProperty('--cv-echelle');window.removeEventListener('afterprint',fin);};
    window.addEventListener('afterprint',fin);
    window.print();
    setTimeout(fin,1000);  // navigateurs sans « afterprint »
  }

  // --- Branchements ---
  document.querySelectorAll('input[name="depart"]').forEach(r=>r.addEventListener('change',()=>{
    const fichier=document.querySelector('input[name="depart"]:checked').value==='fichier';
    $('cvBlocFichier').hidden=!fichier;$('cvBlocParcours').hidden=fichier;erreur('');
  }));
  $('cvFichier').addEventListener('change',async e=>{
    const file=e.target.files&&e.target.files[0];
    piece=null;$('cvFichierEtat').textContent='';erreur('');
    if(!file)return;
    try{piece=await lirePiece(file);$('cvFichierEtat').textContent='Fichier prêt : '+piece.nom;}
    catch(err){e.target.value='';erreur(err&&err.message?err.message:'Fichier illisible. Choisis-le de nouveau.');}
  });
  $('cvForm').addEventListener('submit',creer);
  // « debut » : un vrai champ touché par la personne (clic, choix, saisie), ni le bouton « Créer mon CV » ni le curseur
  // que la page place elle-même après un refus (relecture Codex, #644).
  ['click','change','input'].forEach(t=>$('cvForm').addEventListener(t,e=>{
    if(e.target&&e.target.matches&&e.target.matches('input,textarea,select'))etape('debut');
  }));
  const faireLeMien=document.querySelector('#cvExemple a[href="#cvForm"]');
  if(faireLeMien)faireLeMien.addEventListener('click',()=>etape('faire-le-mien'));
  document.querySelectorAll('.cv-modele').forEach(b=>b.addEventListener('click',()=>{
    if(!MODELES.includes(b.dataset.modele)||!cv)return;
    modele=b.dataset.modele;garder();rendre();
  }));
  $('cvFeuille').addEventListener('input',corriger);
  $('cvLettre').addEventListener('input',corriger);
  $('cvPdf').addEventListener('click',()=>imprimer('imprime-cv'));
  $('cvLettrePdf').addEventListener('click',()=>imprimer('imprime-lettre'));
  $('cvRecommencer').addEventListener('click',()=>{
    cv=null;piece=null;oublier();
    $('cvResultat').hidden=true;$('cvForm').hidden=false;$('cvExemple').hidden=false;$('cvForm').reset();
    $('cvBlocFichier').hidden=true;$('cvBlocParcours').hidden=false;$('cvFichierEtat').textContent='';
    $('cvCreer').focus();
  });

  dessiner($('cvExempleFeuille'),EXEMPLE,'teranga',false);
  // Un CV déjà créé sur ce téléphone revient tel quel.
  const garde=relire();
  if(garde){cv=garde.cv;modele=MODELES.includes(garde.modele)?garde.modele:'sobre';afficher();}
})();
