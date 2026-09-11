# -*- coding: utf-8 -*-
"""La diretta: quello che si muove senza aspettare il giro automatico.

Il sito e' una pagina ferma, rigenerata ogni mezz'ora quando GitHub si degna:
da sola non potrebbe mai mostrare un gol appena fatto. Qui si aggiunge uno
strato sottile che gira nel browser di chi guarda e chiede allo script dentro
Google come vanno le cose - ogni 30 secondi mentre si gioca, ogni 90 quando non
c'e' nessuna partita ma qualcuno potrebbe mandare la schedina.

Aggiorna i punteggi, i punti, la classifica e la riga di chi ha gia' consegnato,
sotto gli occhi di chi sta guardando e senza ricaricare niente.

Due cose per capire perche' e' fatto cosi':

  I CONTI VERI RESTANO IN PYTHON. Qui non si ricalcola niente da zero: si parte
  dai totali gia' calcolati da punteggio.py e si somma soltanto quello che le
  partite ancora aperte aggiungono adesso. Cosi' la classifica in diretta non
  puo' divergere da quella vera: al giro successivo i due numeri coincidono.

  I PRONOSTICI COPERTI RESTANO COPERTI. Nella pagina finiscono solo i pronostici
  delle giornate gia' cominciate, che sono gia' pubblici. Di una giornata non
  ancora iniziata la diretta aggiorna al massimo l'elenco dei nomi di chi ha
  consegnato.

Se lo script in Google non risponde, non succede niente: la pagina resta quella
che era, con i dati dell'ultimo giro.
"""
import json

from . import orari, squadre
from .dati import id_partita
from .punteggio import CORAGGIO_DA, calcola

# ogni quanto la pagina richiede notizie, in secondi: fitto mentre si gioca,
# piu' rado quando c'e' solo da vedere chi ha consegnato
OGNI_IN_GIOCO = 30
OGNI_A_RIPOSO = 90
# quanto prima del calcio d'inizio comincia a guardare, e quanto dopo smette
PRIMA_ORE = 1
DOPO_ORE = 3


def blocco(dati, conti=None, adesso=None, endpoint=None, medaglie=None):
    """Lo <script> della diretta.

    Gira sempre, non solo durante le partite: anche a campionato fermo tiene
    aggiornata la riga di chi ha gia' consegnato, che altrimenti resterebbe
    ferma fino al giro successivo. Quando non si gioca chiede notizie piu'
    di rado.
    """
    if not endpoint:
        return ""
    adesso = adesso or orari.adesso()
    calendario = {int(k): v for k, v in dati["calendario"].items()}
    risultati = dati.get("risultati", {}) or {}
    pronostici = dati.get("pronostici", {}) or {}
    giocatori = dati["players"]
    conti = conti or calcola(dati)

    # TUTTE le partite non ancora giocate, con il loro orario. Quali seguire lo
    # decide il browser mentre gira, non questo file: la pagina viene rigenerata
    # quando GitHub si degna, e se la lista fosse decisa qui una pagina fatta
    # tre ore prima non saprebbe di dover seguire la partita delle nove.
    da_seguire = {}
    for g, partite in calendario.items():
        for n in range(1, len(partite) + 1):
            mid = id_partita(g, n)
            if risultati.get(mid):
                continue
            data, ora, casa, ospite = partite[n - 1]
            da_seguire[mid] = {"g": g, "casa": casa, "ospite": ospite,
                               "inizio": orari.quando(data, ora).isoformat()}

    # i pronostici che servono per i conti in diretta: solo quelli delle
    # giornate gia' cominciate, che sono gia' pubblici
    picks = {}
    for mid, p in da_seguire.items():
        if orari.coperta(calendario, p["g"], adesso):
            continue
        if pronostici.get(mid):
            picks[mid] = pronostici[mid]

    base = {p: {"pt": conti["stats"][p]["pt"], "esatti": conti["stats"][p]["esatti"]}
            for p in giocatori}
    # nomi dell'API -> nomi del gioco, per le sole squadre di questa stagione
    in_gioco = {sq for partite in calendario.values() for p in partite for sq in (p[2], p[3])}
    mappa = {api: it for api, it in squadre.MAPPA.items() if it in in_gioco}

    cfg = json.dumps({
        "endpoint": endpoint,
        "ogniInGioco": OGNI_IN_GIOCO,
        "ogniARiposo": OGNI_A_RIPOSO,
        "prima": PRIMA_ORE,
        "dopo": DOPO_ORE,
        "giocatori": giocatori,
        "base": base,
        "partite": da_seguire,
        "picks": picks,
        "squadre": mappa,
        "coraggioDa": CORAGGIO_DA,
        "medaglie": medaglie or {},
    }, ensure_ascii=False)
    return "<script>" + _script(cfg) + "</script>"


def _script(cfg):
    return """
(function(){
  var D = %s;
  var ultimaChiamata = 0;

  // quali partite stanno per cominciare, o sono in corso, ADESSO
  function aperteAdesso(){
    var fuori = {};
    Object.keys(D.partite).forEach(function(mid){
      var p = D.partite[mid];
      var ore = (Date.now() - new Date(p.inizio).getTime()) / 3600000;
      if(ore >= -D.prima && ore <= D.dopo) fuori[mid] = p;
    });
    return fuori;
  }

  // stesse regole di punteggio.py: 3 segno e risultato, 1 solo il segno, 0 il resto
  function segno(a, b){ return a > b ? '1' : (a === b ? 'X' : '2') }
  function segnoDi(pronostico){
    if(!pronostico) return null;
    var s = pronostico[0], casa = pronostico[1], osp = pronostico[2];
    if(s) return String(s).toUpperCase();
    if(casa === null || osp === null || casa === undefined || osp === undefined) return null;
    return segno(casa, osp);
  }
  function punteggioDi(pronostico){
    if(!pronostico) return null;
    var casa = pronostico[1], osp = pronostico[2];
    if(casa === null || osp === null || casa === undefined || osp === undefined) return null;
    return casa + '-' + osp;
  }
  function punti(pronostico, gol){
    if(!pronostico) return 0;
    if(punteggioDi(pronostico) === gol[0] + '-' + gol[1]) return 3;
    return segnoDi(pronostico) === segno(gol[0], gol[1]) ? 1 : 0;
  }

  // il punto coraggio: chi ha indovinato da solo vale doppio, dalla giornata
  // D.coraggioDa in poi. Stessa regola di punti_partita in punteggio.py.
  function puntiPartita(picks, gol, giornata){
    var quantiSegno = {}, quantiPunteggio = {}, fuori = {};
    D.giocatori.forEach(function(g){
      var sg = segnoDi(picks[g]);
      if(sg) quantiSegno[sg] = (quantiSegno[sg] || 0) + 1;
      var pg = punteggioDi(picks[g]);
      if(pg) quantiPunteggio[pg] = (quantiPunteggio[pg] || 0) + 1;
    });
    var raddoppia = giornata >= D.coraggioDa;
    D.giocatori.forEach(function(g){
      var base = punti(picks[g], gol), valore = base;
      if(base === 3 && raddoppia && quantiPunteggio[punteggioDi(picks[g])] === 1) valore = 6;
      else if(base === 1 && raddoppia && quantiSegno[segnoDi(picks[g])] === 1) valore = 2;
      fuori[g] = {pt: valore, esatto: base === 3};
    });
    return fuori;
  }

  function aggiorna(stato){
    // dai nomi dell'API ai nomi del gioco
    var vive = {};
    (stato.partite || []).forEach(function(p){
      var casa = D.squadre[p.casa], osp = D.squadre[p.ospite];
      if(!casa || !osp || !p.gol) return;
      vive[p.giornata + '|' + casa + '|' + osp] = {gol: p.gol, stato: p.stato};
    });

    var extra = {}, esatti = {}, quante = 0;
    var aperte = aperteAdesso();
    D.giocatori.forEach(function(g){ extra[g] = 0; esatti[g] = 0 });

    Object.keys(aperte).forEach(function(mid){
      var a = aperte[mid];
      var viva = vive[a.g + '|' + a.casa + '|' + a.ospite];
      if(!viva) return;
      quante++;
      disegnaPartita(mid, viva);
      var picks = D.picks[mid];
      if(!picks) return;
      var conto = puntiPartita(picks, viva.gol, a.g);
      D.giocatori.forEach(function(g){
        extra[g] += conto[g].pt;
        if(conto[g].esatto) esatti[g]++;
        disegnaPunto(mid, g, conto[g].pt);
      });
    });

    if(quante){ disegnaClassifica(extra, esatti, stato.adesso); disegnaAndamento(extra) }
    disegnaConsegne(stato.consegne || {});
    disegnaControllo(stato.adesso);
  }

  function disegnaPartita(mid, viva){
    var carta = document.querySelector('[data-mid="' + mid + '"]');
    if(!carta) return;
    var meta = carta.querySelector('.meta');
    if(!meta) return;
    var vecchio = meta.querySelector('.ris, .ora');
    if(!vecchio) return;
    var sg = viva.gol[0] > viva.gol[1] ? '1' : (viva.gol[0] === viva.gol[1] ? 'X' : '2');
    var nuovo = document.createElement('span');
    nuovo.className = 'ris';
    nuovo.innerHTML = viva.gol[0] + '&ndash;' + viva.gol[1] +
      ' <span class="sg sg-' + sg.toLowerCase() + '">' + sg + '</span>' +
      (viva.stato === 'FINISHED' ? '' : ' <span class="live">in gioco</span>');
    vecchio.replaceWith(nuovo);
  }

  function disegnaPunto(mid, chi, valore){
    var cella = document.querySelector('[data-mid="' + mid + '"] [data-chi="' + chi + '"]');
    if(!cella) return;
    Object.keys(D.medaglie).forEach(function(p){ cella.classList.remove(D.medaglie[p]) });
    var metallo = D.medaglie[valore];                 // 1 rame, 2 bronzo, 3 argento, 6 oro
    if(metallo) cella.classList.add(metallo);
    var pts = cella.querySelector('.pts');
    if(!pts){ pts = document.createElement('span'); pts.className = 'pts'; cella.appendChild(pts) }
    pts.textContent = valore;
  }

  // il grafico dell'andamento: si muove l'ultimo punto di ogni linea, a ogni gol.
  // La geometria si legge dal grafico stesso, che e' l'unica copia: cosi' i due
  // disegni non possono divergere.
  function disegnaAndamento(extra){
    var svg = document.getElementById('andamento');
    if(!svg) return;
    var G;
    try { G = JSON.parse(svg.dataset.cfg) } catch(e){ return }
    var ultimo = G.xs.length - 1;
    D.giocatori.forEach(function(p){
      var serie = G.serie[p];
      if(!serie) return;
      var valore = serie[ultimo] + (extra[p] || 0);
      var y = G.y0 - (valore / G.ymax) * G.dentroY;
      var linea = svg.querySelector('.linea[data-chi="' + p + '"]');
      if(linea){
        var punti = linea.getAttribute('points').trim().split(/\s+/);
        punti[ultimo] = G.xs[ultimo] + ',' + y.toFixed(1);
        linea.setAttribute('points', punti.join(' '));
      }
      var punta = svg.querySelector('.punta[data-chi="' + p + '"]');
      if(punta) punta.setAttribute('cy', y.toFixed(1));
      var totale = document.querySelector('[data-tot="' + p + '"]');
      if(totale) totale.textContent = valore;
      G.serie[p] = serie.slice(0, ultimo).concat([valore]);
    });
    svg.dataset.cfg = JSON.stringify(G);   // anche il mirino dice i numeri veri
  }

  function disegnaClassifica(extra, esatti, quando){
    var tabella = document.getElementById('classifica');
    if(!tabella) return;
    var righe = D.giocatori.map(function(g){
      return {chi: g, pt: D.base[g].pt + extra[g], esatti: D.base[g].esatti + esatti[g]};
    }).sort(function(a, b){
      return b.pt - a.pt || b.esatti - a.esatti || a.chi.localeCompare(b.chi);
    });
    righe.forEach(function(r, i){
      var prima = righe[i-1];
      r.pos = (prima && prima.pt === r.pt && prima.esatti === r.esatti) ? prima.pos : i + 1;
    });
    var corpo = tabella.querySelector('tbody');
    righe.forEach(function(r){
      var riga = corpo.querySelector('[data-chi="' + r.chi + '"]');
      if(!riga) return;
      riga.querySelector('.pos').textContent = r.pos;
      riga.querySelector('.num-pt').textContent = r.pt;
      riga.className = r.pos === 1 ? 'leader' : '';
      corpo.appendChild(riga);            // riordina
    });
    var nota = document.getElementById('inGioco');
    if(nota){
      var ora = new Date(quando);
      nota.textContent = 'In diretta \\u00b7 aggiornato alle ' +
        ('0' + ora.getHours()).slice(-2) + ':' + ('0' + ora.getMinutes()).slice(-2);
      nota.hidden = false;
    }
  }

  // la prova di vita in fondo alla pagina: l'ora in cui si e' parlato con
  // Google, presa da Google e non dall'orologio di chi guarda
  function disegnaControllo(quando){
    var dove = document.getElementById('controllato');
    if(!dove) return;
    var ora = new Date(quando);
    dove.textContent = ' \u00b7 controllato alle ' +
      ('0' + ora.getHours()).slice(-2) + ':' + ('0' + ora.getMinutes()).slice(-2);
  }

  // le spunte accanto ai nomi, nella schedina ancora coperta: chi ha consegnato
  // deve comparire subito come la riga qui sotto, non al giro successivo
  function spunte(giornata, chi){
    document.querySelectorAll('[data-coperta="' + giornata + '"]').forEach(function(carta){
      D.giocatori.forEach(function(g){
        var cella = carta.querySelector('[data-chi="' + g + '"]');
        if(!cella) return;
        if(cella.dataset.mio) return;   // e' il pronostico di chi sta guardando
        var mandato = chi.indexOf(g) >= 0;
        var segno = cella.querySelector('.sg');
        if(!segno) return;
        segno.className = 'sg ' + (mandato ? 'sg-lock' : 'sg-tbd');
        segno.innerHTML = mandato ? '&#10003;' : 'TBD';
        cella.classList.toggle('attesa-p', !mandato);
      });
    });
  }

  // Le stesse identiche parole di _chi() in schedina.py: singolare quando ha
  // mandato una persona sola, plurale quando sono di piu'. Se le due versioni
  // divergono, la riga cambia da sola sotto gli occhi appena arriva la diretta.
  function disegnaConsegne(consegne){
    var riga = document.getElementById('chiHaMandato');
    if(!riga) return;
    var g = riga.dataset.giornata;
    var chi = D.giocatori.filter(function(p){ return (consegne[g] || []).indexOf(p) >= 0 });
    var mancano = D.giocatori.filter(function(p){ return chi.indexOf(p) < 0 });
    function elenco(xs){
      return xs.length === 1 ? xs[0] : xs.slice(0,-1).join(', ') + ' e ' + xs[xs.length-1];
    }
    spunte(g, chi);
    if(!chi.length){ riga.textContent = 'Non ha ancora mandato nessuno.'; return }
    if(!mancano.length){
      riga.textContent = chi.length === 5 ? 'Hanno mandato tutti e cinque.' : 'Hanno mandato tutti.';
      return;
    }
    var testa = chi.length === 1
      ? chi[0] + ' ha gi\u00e0 mandato.'
      : 'Hanno gi\u00e0 mandato ' + elenco(chi) + '.';
    var coda = mancano.length === 1
      ? 'Manca solo ' + mancano[0] + '.'
      : 'Mancano ' + elenco(mancano) + '.';
    riga.textContent = testa + ' ' + coda +
      ' Si sa solo chi ha consegnato: i pronostici restano coperti.';
  }

  function chiedi(){
    if(document.hidden) return;            // scheda in secondo piano: si sta fermi
    // fitto mentre si gioca, rado quando c'e' solo da vedere chi ha consegnato
    var pausa = Object.keys(aperteAdesso()).length ? D.ogniInGioco : D.ogniARiposo;
    if(Date.now() - ultimaChiamata < pausa * 1000) return;
    ultimaChiamata = Date.now();
    fetch(D.endpoint + '?azione=stato', {redirect: 'follow'})
      .then(function(r){ return r.json() })
      .then(function(stato){ if(stato && stato.ok) aggiorna(stato) })
      .catch(function(){ /* rete assente o script giu': si tiene quello che c'e' */ });
  }

  chiedi();
  setInterval(chiedi, 10 * 1000);          // il freno vero e' dentro chiedi()
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) chiedi() });
})();
""" % cfg
