# -*- coding: utf-8 -*-
"""I gol in diretta, mentre si gioca.

Il sito e' una pagina ferma, rigenerata una volta all'ora: da sola non potrebbe
mai mostrare un gol appena fatto. Qui si aggiunge uno strato sottile che gira
nel browser di chi guarda: ogni minuto chiede allo script dentro Google come
vanno le partite, e aggiorna i punteggi, i punti e la classifica sotto gli
occhi di chi sta guardando.

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
from .punteggio import calcola

# ogni quanto la pagina richiede i risultati, in secondi
OGNI = 45
# quanto prima del calcio d'inizio comincia a guardare, e quanto dopo smette
PRIMA_ORE = 1
DOPO_ORE = 3


def blocco(dati, conti=None, adesso=None, endpoint=None):
    """Lo <script> della diretta. Stringa vuota se non c'e' niente da seguire."""
    if not endpoint:
        return ""
    adesso = adesso or orari.adesso()
    calendario = {int(k): v for k, v in dati["calendario"].items()}
    risultati = dati.get("risultati", {}) or {}
    pronostici = dati.get("pronostici", {}) or {}
    giocatori = dati["players"]
    conti = conti or calcola(dati)

    # le partite che oggi possono ancora muovere qualcosa: senza risultato, e
    # in una finestra ragionevole attorno al loro orario
    aperte = {}
    for g, partite in calendario.items():
        for n in range(1, len(partite) + 1):
            mid = id_partita(g, n)
            if risultati.get(mid):
                continue
            data, ora, casa, ospite = partite[n - 1]
            inizio = orari.quando(data, ora)
            ore = (adesso - inizio).total_seconds() / 3600
            if -PRIMA_ORE <= ore <= DOPO_ORE:
                aperte[mid] = {"g": g, "casa": casa, "ospite": ospite}
    if not aperte:
        return ""

    # i pronostici che servono per i conti in diretta: solo quelli delle
    # partite aperte, e solo se la loro giornata e' gia' cominciata
    picks = {}
    for mid, p in aperte.items():
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
        "ogni": OGNI,
        "giocatori": giocatori,
        "base": base,
        "aperte": aperte,
        "picks": picks,
        "squadre": mappa,
    }, ensure_ascii=False)
    return "<script>" + _script(cfg) + "</script>"


def _script(cfg):
    return """
(function(){
  var D = %s;
  var ultimo = null;

  // stesse regole di punteggio.py: 3 segno e risultato, 1 solo il segno, 0 il resto
  function segno(a, b){ return a > b ? '1' : (a === b ? 'X' : '2') }
  function punti(pronostico, gol){
    if(!pronostico) return 0;
    var s = pronostico[0], casa = pronostico[1], osp = pronostico[2];
    if(casa !== null && osp !== null && casa === gol[0] && osp === gol[1]) return 3;
    if(!s && casa !== null && osp !== null) s = segno(casa, osp);
    return s === segno(gol[0], gol[1]) ? 1 : 0;
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
    D.giocatori.forEach(function(g){ extra[g] = 0; esatti[g] = 0 });

    Object.keys(D.aperte).forEach(function(mid){
      var a = D.aperte[mid];
      var viva = vive[a.g + '|' + a.casa + '|' + a.ospite];
      if(!viva) return;
      quante++;
      disegnaPartita(mid, viva);
      var picks = D.picks[mid];
      if(!picks) return;
      D.giocatori.forEach(function(g){
        var v = punti(picks[g], viva.gol);
        extra[g] += v;
        if(v === 3) esatti[g]++;
        disegnaPunto(mid, g, v);
      });
    });

    if(quante) disegnaClassifica(extra, esatti, stato.adesso);
    disegnaConsegne(stato.consegne || {});
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
    cella.classList.remove('pk3', 'pk2');
    if(valore === 3) cella.classList.add('pk3');
    if(valore === 1) cella.classList.add('pk2');
    var pts = cella.querySelector('.pts');
    if(!pts){ pts = document.createElement('span'); pts.className = 'pts'; cella.appendChild(pts) }
    pts.textContent = valore;
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

  function disegnaConsegne(consegne){
    var riga = document.getElementById('chiHaMandato');
    if(!riga) return;
    var g = riga.dataset.giornata;
    var chi = consegne[g] || [];
    var mancano = D.giocatori.filter(function(p){ return chi.indexOf(p) < 0 });
    function elenco(xs){ return xs.length === 1 ? xs[0] : xs.slice(0,-1).join(', ') + ' e ' + xs[xs.length-1] }
    if(!chi.length){ riga.textContent = 'Non ha ancora mandato nessuno.'; return }
    if(!mancano.length){
      riga.textContent = 'Hanno mandato tutti e cinque.'; return;
    }
    riga.textContent = 'Hanno gia\\u2019 mandato ' + elenco(chi) + '. Mancano ' + elenco(mancano) +
      '. Di loro si sa solo che hanno consegnato: i pronostici restano coperti.';
  }

  function chiedi(){
    if(document.hidden) return;            // scheda in secondo piano: si sta fermi
    fetch(D.endpoint + '?azione=stato', {redirect: 'follow'})
      .then(function(r){ return r.json() })
      .then(function(stato){ if(stato && stato.ok){ ultimo = stato; aggiorna(stato) } })
      .catch(function(){ /* rete assente o script giu': si tiene quello che c'e' */ });
  }

  chiedi();
  setInterval(chiedi, D.ogni * 1000);
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) chiedi() });
})();
""" % cfg
