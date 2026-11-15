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
  function champ(tag,cls,valeur,chemin){return modifiable(el(tag,cls,valeur||''),chemin);}
  function section(feuille,titre){const s=el('section','cv-section');s.appendChild(el('h4','cv-rubrique',titre));feuille.appendChild(s);return s;}

  function initiales(nom){
    return String(nom||'').split(/\s+/).filter(Boolean).slice(0,2).map(m=>m[0].toUpperCase()).join('');
  }
  // Trois zones : en-tête, corps (profil, expérience, formation) et côté (compétences, langues). Chaque modèle les
  // place à sa façon (CSS) : une colonne pour Sobre, deux colonnes sur la feuille A4 pour Moderne et Teranga.
  function rendre(){
    const f=$('cvFeuille');
    f.replaceChildren();
    f.className='cv-feuille '+modele;
    const tete=el('header','cv-tete'),corps=el('div','cv-corps'),cote=el('div','cv-cote');
    const mono=el('span','cv-mono',initiales(cv.nom));mono.setAttribute('aria-hidden','true');
    const ident=el('div','cv-ident');
    ident.append(champ('p','cv-nom',cv.nom||'Ton nom','nom'),champ('p','cv-titre',cv.titre,'titre'));
    const contact=[cv.ville,cv.telephone,cv.email].filter(Boolean);
    if(contact.length){const ul=el('ul','cv-contact');contact.forEach(c=>ul.appendChild(el('li','',c)));ident.appendChild(ul);}
    tete.append(mono,ident);
    if(cv.profil)section(corps,'Profil').appendChild(champ('p','cv-texte',cv.profil,'profil'));
    if(cv.experiences&&cv.experiences.length){
      const s=section(corps,'Expérience'),frise=el('div','cv-frise');
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
      const s=section(corps,'Formation'),frise=el('div','cv-frise');
      cv.formations.forEach((x,i)=>{
        const bloc=el('div','cv-bloc');
        if(x.dates)bloc.appendChild(el('p','cv-quand',x.dates));
        bloc.appendChild(champ('p','cv-poste',[x.diplome,x.etablissement].filter(Boolean).join(' · '),'formations.'+i+'.entete'));
        frise.appendChild(bloc);
      });
      s.appendChild(frise);
    }
    if(cv.competences&&cv.competences.length){
      const s=section(cote,'Compétences'),ul=el('ul','cv-tags');
      cv.competences.forEach((t,j)=>ul.appendChild(champ('li','',t,'competences.'+j)));
      s.appendChild(ul);
    }
    if(cv.langues&&cv.langues.length)section(cote,'Langues').appendChild(champ('p','cv-texte',cv.langues.join(', '),'langues.texte'));
    f.append(tete,corps);
    if(cote.childNodes.length)f.appendChild(cote);
    liste('cvVerifier',cv.a_verifier);
    liste('cvManque',cv.manque);
    const alerte=$('cvAlerte');alerte.textContent=cv.alerte||'';alerte.hidden=!cv.alerte;
    const lettre=$('cvLettre');lettre.replaceChildren();
    $('cvLettreBloc').hidden=!cv.lettre;
    if(cv.lettre)lettre.appendChild(champ('div','cv-lettre-texte',cv.lettre,'lettre'));
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
    $('cvForm').hidden=true;
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
      if(!piece){erreur('Choisis ton CV : PDF, Word ou photo.');$('cvFichier').focus();return;}
      corps.fichier=piece;
    }else{
      corps.parcours=$('cvParcours').value.trim();
      if(corps.parcours.length<20){erreur('Raconte ton parcours en quelques phrases.');$('cvParcours').focus();return;}
    }
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

  function imprimer(classe){
    document.body.classList.add(classe);
    const fin=()=>{document.body.classList.remove(classe);window.removeEventListener('afterprint',fin);};
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
    $('cvResultat').hidden=true;$('cvForm').hidden=false;$('cvForm').reset();
    $('cvBlocFichier').hidden=false;$('cvBlocParcours').hidden=true;$('cvFichierEtat').textContent='';
    $('cvCreer').focus();
  });

  // Un CV déjà créé sur ce téléphone revient tel quel.
  const garde=relire();
  if(garde){cv=garde.cv;modele=MODELES.includes(garde.modele)?garde.modele:'sobre';afficher();}
})();
