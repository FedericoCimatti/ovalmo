# -*- coding: utf-8 -*-
"""Il calcolo dei punti e della classifica.

Regole:
  3 punti  segno + risultato esatto
  1 punto  solo il segno giusto (NON si somma ai 3)
  0 punti  segno sbagliato, oppure pronostico non inviato

I PUNTI CORAGGIO, dalla giornata 5 in poi
  Chi indovina da solo vale il doppio:
    6 punti  risultato esatto che nessun altro dei cinque aveva scritto
    2 punti  segno giusto che nessun altro dei cinque aveva scelto
  "Da solo" si guarda dentro la singola partita, e solo fra chi ha mandato:
  per i 2 punti conta il segno (1, X o 2), per i 6 punti il punteggio scritto.
  Chi non manda non ha scelto niente, quindi non fa compagnia a nessuno.

  Vale dalla giornata CORAGGIO_DA: le giornate precedenti restano com'erano,
  perche' la regola e' arrivata a giornata 4 gia' cominciata e i punti gia'
  assegnati non si toccano.

In classifica, a pari punti passa avanti chi ha piu' risultati esatti.
"Re della giornata" = chi ha fatto piu' punti in quella giornata.

Questo file non sa niente di HTML, di Excel e di date: prende i dati e
restituisce numeri. E' la parte piu' facile da testare e la piu' importante
da non rompere.
"""
from .dati import id_partita

# la prima giornata in cui il punto coraggio vale, e quanto vale
CORAGGIO_DA = 5
CORAGGIO_ESATTO = 6
CORAGGIO_SEGNO = 2


def segno(gol_casa, gol_ospite):
    """1, X o 2 a partire dal punteggio."""
    if gol_casa > gol_ospite:
        return "1"
    return "X" if gol_casa == gol_ospite else "2"


def segno_pronosticato(pronostico):
    """Il segno che vale per un pronostico ["1", 2, 1].

    Se e' stato dato solo il punteggio, il segno si deduce.
    Se non c'e' niente di utile, None.
    """
    s, casa, ospite = (pronostico or [None, None, None])
    if s:
        return s.upper()
    if casa is None or ospite is None:
        return None
    return segno(casa, ospite)


def punti(pronostico, risultato):
    """Punti di un singolo pronostico, senza guardare cosa hanno fatto gli altri.

    E' il punteggio base: 3, 1 o 0. Il raddoppio dei punti coraggio si decide in
    `punti_partita`, che e' l'unico posto che vede tutti e cinque insieme.
    """
    if not risultato:
        return 0
    gol_casa, gol_ospite = risultato
    _, casa, ospite = (pronostico or [None, None, None])
    if casa is not None and ospite is not None and casa == gol_casa and ospite == gol_ospite:
        return 3
    return 1 if segno_pronosticato(pronostico) == segno(gol_casa, gol_ospite) else 0


def punteggio_scritto(pronostico):
    """(gol casa, gol ospite) se il pronostico contiene un punteggio, altrimenti None."""
    _, casa, ospite = (pronostico or [None, None, None])
    return None if casa is None or ospite is None else (casa, ospite)


def punti_partita(picks, risultato, giornata, giocatori=None):
    """{giocatore: punti} per una partita, punti coraggio compresi.

    E' l'unico posto dove si decide chi era da solo: la pagina, la diretta e il
    file Excel devono dare lo stesso numero, e l'unico modo di esserne sicuri e'
    che ci sia una sola regola scritta una volta sola.

    picks      {giocatore: pronostico} di quella partita
    giornata   serve solo a sapere se il punto coraggio e' gia' in vigore
    """
    giocatori = list(giocatori if giocatori is not None else picks)
    if not risultato:
        return {p: 0 for p in giocatori}

    raddoppia = giornata >= CORAGGIO_DA
    quanti_segno, quanti_punteggio = {}, {}
    for p in giocatori:
        sg = segno_pronosticato(picks.get(p))
        if sg:
            quanti_segno[sg] = quanti_segno.get(sg, 0) + 1
        pg = punteggio_scritto(picks.get(p))
        if pg:
            quanti_punteggio[pg] = quanti_punteggio.get(pg, 0) + 1

    fuori = {}
    for p in giocatori:
        pronostico = picks.get(p)
        base = punti(pronostico, risultato)
        if base == 3 and raddoppia and quanti_punteggio[punteggio_scritto(pronostico)] == 1:
            base = CORAGGIO_ESATTO
        elif base == 1 and raddoppia and quanti_segno[segno_pronosticato(pronostico)] == 1:
            base = CORAGGIO_SEGNO
        fuori[p] = base
    return fuori


def calcola(dati):
    """Tutti i conti in una volta sola.

    Restituisce un dizionario con:
      stats      {giocatore: {pt, segni, esatti}}
      per_g      {giornata: {giocatore: punti di quella giornata}}
      giocate_g  {giornata: quante partite hanno un risultato}
      giocate    totale partite con risultato
      concluse   giornate con tutti i risultati
      ordine     giocatori dal primo all'ultimo
      pos        {giocatore: posizione in classifica, a pari merito stesso numero}
    """
    giocatori = dati["players"]
    per_giornata = dati["partite_per_giornata"]
    calendario = {int(k): v for k, v in dati["calendario"].items()}
    risultati = dati.get("risultati", {}) or {}
    pronostici = dati.get("pronostici", {}) or {}
    giornate = sorted(calendario)

    stats = {p: dict(pt=0, segni=0, esatti=0) for p in giocatori}
    per_g = {g: {p: 0 for p in giocatori} for g in giornate}
    giocate_g = {g: 0 for g in giornate}

    for g in giornate:
        for m in range(1, per_giornata + 1):
            mid = id_partita(g, m)
            risultato = risultati.get(mid)
            if not risultato:
                continue
            giocate_g[g] += 1
            picks = pronostici.get(mid) or {}
            valori = punti_partita(picks, risultato, g, giocatori)
            for p in giocatori:
                # segni ed esatti si contano sul punteggio base: il punto coraggio
                # raddoppia i punti, non trasforma un segno in un risultato esatto
                base = punti(picks.get(p), risultato)
                if base == 3:
                    stats[p]["esatti"] += 1
                    stats[p]["segni"] += 1
                elif base == 1:
                    stats[p]["segni"] += 1
                stats[p]["pt"] += valori[p]
                per_g[g][p] += valori[p]

    ordine = sorted(giocatori, key=lambda p: (-stats[p]["pt"], -stats[p]["esatti"], p))
    pos = {}
    for i, p in enumerate(ordine):
        prima = ordine[i - 1] if i else None
        pari = prima and (stats[p]["pt"], stats[p]["esatti"]) == (stats[prima]["pt"], stats[prima]["esatti"])
        pos[p] = pos[prima] if pari else i + 1

    concluse = [g for g in giornate if giocate_g[g] and giocate_g[g] == len(calendario[g])]
    return dict(stats=stats, per_g=per_g, giocate_g=giocate_g,
                giocate=sum(giocate_g.values()), concluse=concluse,
                ordine=ordine, pos=pos, giornate=giornate)


def re_della_giornata(conti, giocatori, giornata):
    """(elenco dei re, punti) per una giornata. (None, 0) se nessuno ha punti."""
    per_g = conti["per_g"][giornata]
    massimo = max(per_g.values()) if per_g else 0
    if massimo <= 0:
        return None, 0
    return [p for p in giocatori if per_g[p] == massimo], massimo
