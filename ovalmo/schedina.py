# -*- coding: utf-8 -*-
"""Il modulo per mandare i pronostici, dentro la pagina.

Sostituisce il modulo Google. Le dieci partite arrivano dal calendario che
scarichiamo dall'API, quindi non c'e' piu' niente da rinominare a mano prima di
ogni giornata: e' esattamente il lavoro manuale che restava.

Come funziona il giro completo:
  questa pagina  ->  script dentro Google (google/ricevi_pronostici.gs)
                 ->  foglio "Pronostici"
                 ->  il giro orario lo rilegge (modulo.leggi_sito)

Chi guarda la pagina non puo' leggere i pronostici degli altri: l'indirizzo
dello script accetta solo scritture, e la pagina mostra solo la propria
schedina, ripescata dalla memoria del telefono di chi la sta usando.
"""
import html
import json

from . import orari
from .dati import id_partita

E = html.escape


def giornata_aperta(calendario, adesso=None):
    """La giornata su cui si sta ancora pronosticando: la prima non iniziata."""
    adesso = adesso or orari.adesso()
    future = sorted(g for g in calendario if orari.calcio_dinizio(calendario[g]) > adesso)
    return future[0] if future else None


def blocco(dati, adesso=None, endpoint=None, modulo_google=None):
    """L'HTML del modulo. Stringa vuota se non c'e' niente da pronosticare."""
    adesso = adesso or orari.adesso()
    calendario = {int(k): v for k, v in dati["calendario"].items()}
    giocatori = dati["players"]
    g = giornata_aperta(calendario, adesso)
    if g is None:
        return ('<section><h2>Manda i tuoi pronostici</h2><p class="lede">Nessuna giornata '
                'aperta al momento: appena esce il calendario della prossima, la schedina '
                'compare qui.</p></section>')

    scadenza = orari.calcio_dinizio(calendario[g])
    quando = f"{scadenza:%d/%m} alle {scadenza:%H:%M}"

    # chi ha gia' consegnato per la giornata aperta. Solo i nomi: il contenuto
    # delle schedine non compare qui e non e' nemmeno nel repository, finche'
    # non si comincia a giocare.
    consegnato = [p for p in giocatori if p in (dati.get("consegne", {}).get(str(g)) or {})]
    mancano = [p for p in giocatori if p not in consegnato]

    if not endpoint:
        # rete di sicurezza: finche' lo script dentro Google non e' attivo, si
        # continua col modulo di prima invece di lasciare la pagina monca
        link = modulo_google or "#"
        return ('<section><h2>Manda i tuoi pronostici</h2>'
                f'<p class="lede">Giornata {g}, si chiude il {E(quando)}.</p>'
                f'<a class="cta" href="{E(link)}" target="_blank" rel="noopener">Vai al modulo</a>'
                '</section>')

    partite = []
    righe = []
    for n in range(1, len(calendario[g]) + 1):
        data, ora, casa, osp = calendario[g][n - 1]
        chiave = f"P{n:02d}"
        partite.append({"k": chiave, "n": f"{casa} - {osp}"})
        righe.append(
            f'<div class="riga" data-p="{chiave}">'
            f'<div><b>{E(casa)} &ndash; {E(osp)}</b><small>{E(str(data))} &middot; {E(str(ora))}</small></div>'
            f'<div class="tre">'
            f'<button type="button" data-s="1" aria-pressed="false">1</button>'
            f'<button type="button" data-s="X" aria-pressed="false">X</button>'
            f'<button type="button" data-s="2" aria-pressed="false">2</button>'
            f'</div>'
            f'<div class="gol2"><input class="gol" type="number" min="0" max="19" '
            f'inputmode="numeric" aria-label="gol {E(casa)}">'
            f'<span class="tra">&ndash;</span>'
            f'<input class="gol" type="number" min="0" max="19" '
            f'inputmode="numeric" aria-label="gol {E(osp)}"></div>'
            f'</div>')

    cfg = json.dumps({
        "endpoint": endpoint,
        "giornata": g,
        "giocatori": giocatori,
        "scadenza": scadenza.isoformat(),
    }, ensure_ascii=False)

    nomi = "".join(f'<button type="button" data-nome="{E(p)}" aria-pressed="false">{E(p)}</button>'
                   for p in giocatori)

    return f"""<section id="modulo">
    <h2>Manda i tuoi pronostici &mdash; giornata {g}</h2>
    <p class="lede">Si chiude al primo calcio d&rsquo;inizio, {E(quando)}. Basta il segno, il
    risultato esatto vale di piu&rsquo;. <strong>Una volta inviata la schedina non si pu&ograve;
    pi&ugrave; cambiare</strong>, quindi controllala prima di mandarla. Gli altri vedono che hai
    mandato, non che cosa hai scritto.</p>
    <p class="lede" id="chiHaMandato" data-giornata="{g}">{_chi(consegnato, mancano)}</p>
    <div class="mod">
      <div id="chisei">
        <p class="lede" style="margin-top:0">Chi sei?</p>
        <div class="chi">{nomi}</div>
        <div class="cod">
          <input type="tel" id="codice" inputmode="numeric" maxlength="4" placeholder="codice">
          <button type="button" class="go" id="entra">Entra</button>
        </div>
        <p class="esito" id="esito1"></p>
      </div>
      <form id="schedina" hidden>
        <p class="lede" style="margin-top:0">Ciao <b id="ciao"></b></p>
        {"".join(righe)}
        <p style="margin:14px 0 0">
          <button type="submit" class="go" id="invia">Invia i pronostici</button>
          <button type="button" class="no" id="annulla">Annulla</button>
        </p>
        <p class="esito" id="esito2"></p>
      </form>
      <div id="fatto" hidden>
        <p class="lede" style="margin-top:0"><b id="ciao2"></b>, la tua schedina della giornata
        {g} &egrave; arrivata. Non si pu&ograve; pi&ugrave; cambiare: si svela a tutti al primo
        calcio d&rsquo;inizio, {E(quando)}.</p>
        <button type="button" class="no" id="esci" style="margin-left:0">Esci</button>
        <p class="cta-note">Esce dal tuo nome su questo telefono: per rientrare serve di
        nuovo il codice. La schedina che hai mandato resta valida.</p>
      </div>
    </div>
    </section>
    <script>{_script(cfg, json.dumps(partite, ensure_ascii=False))}</script>"""


def _chi(consegnato, mancano):
    """La riga su chi ha gia' mandato. Nomi e basta: i pronostici restano coperti.

    Singolare e plurale contano: "Lippi ha gia' mandato" e non "hanno gia'
    mandato Lippi". La stessa frase la ricostruisce anche la diretta nel
    browser (diretta.py) quando arriva qualcuno di nuovo: le due versioni
    devono dire le stesse identiche parole.
    """
    def elenco(xs):
        xs = [E(x) for x in xs]
        return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " e " + xs[-1]

    if not consegnato:
        return "Non ha ancora mandato nessuno."
    if not mancano:
        return ("Hanno mandato tutti e cinque." if len(consegnato) == 5
                else "Hanno mandato tutti.")
    testa = (f"{E(consegnato[0])} ha gi&agrave; mandato."
             if len(consegnato) == 1
             else f"Hanno gi&agrave; mandato {elenco(consegnato)}.")
    coda = (f"Manca solo {E(mancano[0])}." if len(mancano) == 1
            else f"Mancano {elenco(mancano)}.")
    return f"{testa} {coda} Si sa solo chi ha consegnato: i pronostici restano coperti."


def _script(cfg, partite):
    """Il codice che gira nel browser di chi compila."""
    return """
(function(){
  var CFG = %s, PARTITE = %s;
  var IO = 'ovalmo-io', BOZZA = 'ovalmo-g' + CFG.giornata;
  var $ = function(id){ return document.getElementById(id) };
  var chisei = $('chisei'), schedina = $('schedina'), fatto = $('fatto');
  function chiaveInviato(nome){ return 'ovalmo-inviato-g' + CFG.giornata + '-' + nome }
  var scelto = null;

  function leggi(chiave){ try { return JSON.parse(localStorage.getItem(chiave)) } catch(e){ return null } }
  function scrivi(chiave, v){ try { localStorage.setItem(chiave, JSON.stringify(v)) } catch(e){} }

  // ---- chi sei ----
  chisei.querySelectorAll('.chi button').forEach(function(b){
    b.onclick = function(){
      chisei.querySelectorAll('.chi button').forEach(function(x){ x.setAttribute('aria-pressed','false') });
      b.setAttribute('aria-pressed','true'); scelto = b.dataset.nome;
    };
  });
  // Il codice si verifica QUI, non al momento dell'invio: altrimenti chiunque
  // potrebbe aprire la schedina di chiunque, e scoprirebbe di aver sbagliato
  // solo dopo aver compilato tutto.
  function sbagliato(testo){
    var campo = $('codice');
    campo.classList.remove('sbagliato');
    void campo.offsetWidth;                 // riavvia l'animazione
    campo.classList.add('sbagliato');
    campo.select();
    messaggio('esito1', testo, 'ko');
  }

  function verifica(nome, codice){
    return fetch(CFG.endpoint, {
      method: 'POST', redirect: 'follow',
      headers: {'Content-Type': 'text/plain;charset=utf-8'},
      body: JSON.stringify({azione: 'controlla', giocatore: nome, codice: codice})
    }).then(function(r){ return r.json() }).then(function(esito){ return !!(esito && esito.ok) });
  }

  $('entra').onclick = function(){
    var codice = $('codice').value.trim();
    if(!scelto){ return messaggio('esito1','Scegli il tuo nome.','ko') }
    if(!/^[0-9]{4}$/.test(codice)){ return sbagliato('Il codice è di quattro cifre.') }
    var bottone = $('entra');
    bottone.disabled = true;
    messaggio('esito1','Controllo...','');
    verifica(scelto, codice).then(function(giusto){
      bottone.disabled = false;
      if(giusto){
        messaggio('esito1','');
        $('codice').classList.remove('sbagliato');
        scrivi(IO, {nome: scelto, codice: codice});
        entra();
      } else {
        sbagliato('Codice sbagliato.');
      }
    }).catch(function(){
      bottone.disabled = false;
      sbagliato('Non riesco a verificare il codice: controlla la connessione e riprova.');
    });
  };
  // Annulla / Esci: si torna indietro e per rientrare serve di nuovo il codice.
  // Serve su un telefono che passa di mano, e perche' la schedina non resti
  // aperta per giorni.
  function esci(){
    try { localStorage.removeItem(IO) } catch(e){}
    schedina.hidden = true; fatto.hidden = true; chisei.hidden = false;
    $('codice').value = ''; scelto = null;
    chisei.querySelectorAll('.chi button').forEach(function(x){ x.setAttribute('aria-pressed','false') });
    messaggio('esito1',''); messaggio('esito2','');
  }
  $('annulla').onclick = esci;
  $('esci').onclick = esci;

  function entra(){
    var io = leggi(IO);
    if(!io || !io.nome) return;
    $('ciao').textContent = io.nome;
    $('ciao2').textContent = io.nome;
    chisei.hidden = true;
    if(leggi(chiaveInviato(io.nome))){      // ha gia' mandato: niente da cambiare
      schedina.hidden = true; fatto.hidden = false; return;
    }
    fatto.hidden = true; schedina.hidden = false;
    var bozza = leggi(BOZZA) || {};
    PARTITE.forEach(function(p){
      var testo = bozza[p.k]; if(!testo) return;
      var riga = schedina.querySelector('[data-p="' + p.k + '"]');
      var seg = (testo.match(/^([12X])/) || [])[1];
      if(seg){ riga.querySelectorAll('.tre button').forEach(function(b){
        b.setAttribute('aria-pressed', b.dataset.s === seg ? 'true' : 'false') }) }
      var gol = testo.match(/(\\d+)-(\\d+)/);
      if(gol){ var caselle = riga.querySelectorAll('.gol');
        caselle[0].value = gol[1]; caselle[1].value = gol[2] }
    });
  }

  // ---- segni ----
  schedina.querySelectorAll('.riga').forEach(function(riga){
    riga.querySelectorAll('.tre button').forEach(function(b){
      b.onclick = function(){
        var gia = b.getAttribute('aria-pressed') === 'true';
        riga.querySelectorAll('.tre button').forEach(function(x){ x.setAttribute('aria-pressed','false') });
        b.setAttribute('aria-pressed', gia ? 'false' : 'true');
      };
    });
  });

  function raccogli(){
    var fuori = {}, quanti = 0;
    PARTITE.forEach(function(p){
      var riga = schedina.querySelector('[data-p="' + p.k + '"]');
      var premuto = riga.querySelector('.tre button[aria-pressed="true"]');
      var caselle = riga.querySelectorAll('.gol');
      var casa = caselle[0].value.trim(), osp = caselle[1].value.trim();
      var testo = '';
      if(premuto) testo = premuto.dataset.s;
      if(casa !== '' && osp !== '') testo = (testo ? testo + ' ' : '') + casa + '-' + osp;
      if(testo){ fuori[p.k] = testo; quanti++ }
    });
    return {pronostici: fuori, quanti: quanti};
  }

  function messaggio(id, testo, classe){
    var e = $(id); e.textContent = testo; e.className = 'esito ' + (classe || '');
  }

  schedina.onsubmit = function(ev){
    ev.preventDefault();
    var io = leggi(IO); if(!io) return;
    if(new Date() >= new Date(CFG.scadenza)){
      return messaggio('esito2','I pronostici di questa giornata sono chiusi: si è già cominciato.','ko');
    }
    var raccolto = raccogli();
    if(!raccolto.quanti){ return messaggio('esito2','Non hai messo nessun pronostico.','ko') }
    scrivi(BOZZA, raccolto.pronostici);
    var invia = $('invia'); invia.disabled = true;
    messaggio('esito2','Sto mandando...','');
    fetch(CFG.endpoint, {
      method: 'POST', redirect: 'follow',
      headers: {'Content-Type': 'text/plain;charset=utf-8'},
      body: JSON.stringify({
        giocatore: io.nome, codice: io.codice,
        giornata: CFG.giornata, pronostici: raccolto.pronostici
      })
    }).then(function(r){ return r.json() }).then(function(esito){
      invia.disabled = false;
      if(esito && esito.ok){
        scrivi(chiaveInviato(io.nome), true);
        schedina.hidden = true; fatto.hidden = false;
      } else if(esito && esito.errore === 'codice sbagliato'){
        messaggio('esito2','Codice sbagliato.','ko');
      } else {
        messaggio('esito2','Non ha funzionato: ' + ((esito && esito.errore) || 'errore') +
          '. Riprova fra un minuto.','ko');
      }
    }).catch(function(){
      invia.disabled = false;
      messaggio('esito2','Non sono riuscito a mandarli: controlla la connessione e riprova. ' +
        'Quello che hai scritto resta qui.','ko');
    });
  };

  // All'apertura non ci si fida di quello che il telefono si ricorda: il codice
  // viene ricontrollato. Senza, chi fosse entrato una volta con un codice
  // sbagliato resterebbe dentro per sempre.
  var io = leggi(IO);
  if(io && io.nome){
    messaggio('esito1','Controllo...','');
    verifica(io.nome, io.codice).then(function(giusto){
      messaggio('esito1','');
      if(giusto) entra(); else esci();
    }).catch(function(){
      messaggio('esito1','Non riesco a verificare il codice: controlla la connessione.','ko');
    });
  }
})();
""" % (cfg, partite)
