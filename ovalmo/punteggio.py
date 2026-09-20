# -*- coding: utf-8 -*-
"""Il calcolo dei punti e della classifica.

Regole:
  3 punti  segno + risultato esatto
  1 punto  solo il segno giusto (NON si somma ai 3)
  0 punti  segno sbagliato, oppure pronostico non inviato

Nient'altro: i punti non si moltiplicano mai. Una partita vale al massimo 3.

LE MEDAGLIE
  Il colore della casella non e' una seconda regola di punteggio, e' un modo
  di raccontare gli stessi punti:
    oro      risultato esatto, e nessun altro dei cinque l'aveva preso
    argento  risultato esatto, ma in compagnia
    bronzo   solo il segno giusto
    niente   niente
  Oro e argento valgono gli stessi 3 punti: cambia solo quanto era difficile.
  Per questo l'oro si decide guardando tutta la partita, mentre i punti si
  decidono guardando un pronostico solo.

In classifica, a pari punti passa avanti chi ha piu' risultati esatti.
"Re della giornata" = chi ha fatto piu' punti in quella giornata.

Questo file non sa niente di HTML, di Excel e di date: prende i dati e
restituisce numeri. E' la parte piu' facile da testare e la piu' importante
da non rompere.
"""
from .dati import id_partita

# quanto puo' valere al massimo una partita: serve al grafico, che deve
# lasciare in alto lo spazio per i punti che le partite in corso possono
# ancora dare
MASSIMO_PER_PARTITA = 3

# i nomi delle medaglie. Qui stanno i nomi, non i colori: il foglio di stile
# decide come sono fatte, questo file decide chi se le merita
ORO, ARGENTO, BRONZO = "oro", "argento", "bronzo"


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
    """Punti di un pronostico: 3, 1 o 0.

    Non guarda cosa hanno fatto gli altri, e non deve: i punti dipendono solo
    dal proprio pronostico e dal risultato. Chi ha scelto cosa conta per le
    medaglie, non per il punteggio.
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


def quanti_esatti(picks, risultato, giocatori=None):
    """Quanti, in questa partita, hanno preso il risultato esatto.

    E' l'unica cosa che serve sapere degli altri, e serve solo a distinguere
    l'oro dall'argento.
    """
    if not risultato:
        return 0
    giocatori = list(giocatori if giocatori is not None else picks)
    return sum(1 for p in giocatori if punti(picks.get(p), risultato) == 3)


def metallo(punti_suoi, esatti_nella_partita):
    """La medaglia di un pronostico, o None se non ha preso niente.

    Sta qui e non nella pagina perche' la stessa risposta la devono dare in
    tre: la pagina quando si genera, la diretta mentre le partite vanno, e
    chiunque venga dopo. Una regola sola, scritta una volta sola.
    """
    if punti_suoi == 3:
        return ORO if esatti_nella_partita == 1 else ARGENTO
    return BRONZO if punti_suoi == 1 else None


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
            for p in giocatori:
                suoi = punti(picks.get(p), risultato)
                if suoi == 3:
                    stats[p]["esatti"] += 1
                    stats[p]["segni"] += 1
                elif suoi == 1:
                    stats[p]["segni"] += 1
                stats[p]["pt"] += suoi
                per_g[g][p] += suoi

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
