# -*- coding: utf-8 -*-
"""Il calcolo dei punti e della classifica.

Regole, invariate dal primo giorno:
  3 punti  segno + risultato esatto
  1 punto  solo il segno giusto (NON si somma ai 3)
  0 punti  segno sbagliato, oppure pronostico non inviato

In classifica, a pari punti passa avanti chi ha piu' risultati esatti.
"Re della giornata" = chi ha fatto piu' punti in quella giornata.

Questo file non sa niente di HTML, di Excel e di date: prende i dati e
restituisce numeri. E' la parte piu' facile da testare e la piu' importante
da non rompere.
"""
from .dati import id_partita


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
    """Punti di un singolo pronostico su una singola partita."""
    if not risultato:
        return 0
    gol_casa, gol_ospite = risultato
    _, casa, ospite = (pronostico or [None, None, None])
    if casa is not None and ospite is not None and casa == gol_casa and ospite == gol_ospite:
        return 3
    return 1 if segno_pronosticato(pronostico) == segno(gol_casa, gol_ospite) else 0


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
            atteso = segno(*risultato)
            for p in giocatori:
                pronostico = (pronostici.get(mid) or {}).get(p)
                v = punti(pronostico, risultato)
                if v == 3:
                    stats[p]["esatti"] += 1
                    stats[p]["segni"] += 1
                elif v == 1:
                    stats[p]["segni"] += 1
                stats[p]["pt"] += v
                per_g[g][p] += v

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
