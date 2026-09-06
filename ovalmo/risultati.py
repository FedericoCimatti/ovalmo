# -*- coding: utf-8 -*-
"""Calendario e risultati da football-data.org.

Una sola chiamata per giro: si scarica il calendario completo della stagione
(tutte le 380 partite) e si tiene la parte che serve. Il piano gratuito
concede 10 richieste al minuto: siamo abbondantemente dentro, e non c'e'
nessun motivo di essere piu' furbi.

LA COSA DA NON ROMPERE: l'identificativo di una partita (G03-01, G03-02...)
e' la sua POSIZIONE nella giornata, e pronostici e risultati gia' archiviati
sono agganciati a quel numero. Le date cambiano di continuo (anticipi,
posticipi, rinvii), quindi riordinare la giornata a ogni giro sposterebbe il
significato dei dati vecchi. Per questo la numerazione si assegna una volta
sola, alla prima importazione della giornata, e da li' in poi ogni partita
viene ritrovata dal suo id football-data (`id_partite` nel JSON) e aggiornata
al suo posto.
"""
import json
import urllib.error
import urllib.request

from . import orari, squadre
from .dati import id_partita

BASE = "https://api.football-data.org/v4"
# stati che significano "la partita e' finita e il punteggio e' quello definitivo"
FINITA = {"FINISHED"}
# stati che significano "non si e' giocata": niente risultato, resta in calendario
NON_GIOCATA = {"POSTPONED", "SUSPENDED", "CANCELLED", "AWARDED"}


class ErroreAPI(Exception):
    """Problema nel parlare con football-data.org."""


def scarica(token, competizione="SA", stagione=None, timeout=30):
    """Tutte le partite della competizione. Restituisce la lista grezza dell'API."""
    url = f"{BASE}/competitions/{competizione}/matches"
    if stagione:
        url += f"?season={stagione}"
    richiesta = urllib.request.Request(url, headers={"X-Auth-Token": token})
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            corpo = json.load(risposta)
    except urllib.error.HTTPError as e:
        dettaglio = ""
        try:
            dettaglio = " - " + json.load(e).get("message", "")
        except Exception:
            pass
        if e.code == 403:
            raise ErroreAPI(
                f"football-data ha risposto 403{dettaglio}. Di solito significa che il token "
                f"non e' valido, oppure che la competizione {competizione} non e' inclusa nel "
                f"piano gratuito.") from e
        if e.code == 429:
            raise ErroreAPI("football-data ha risposto 429: troppe richieste. Riprova fra un minuto.") from e
        raise ErroreAPI(f"football-data ha risposto {e.code}{dettaglio}") from e
    except urllib.error.URLError as e:
        raise ErroreAPI(f"non riesco a raggiungere football-data.org: {e.reason}") from e
    partite = corpo.get("matches")
    if partite is None:
        raise ErroreAPI("risposta senza il campo 'matches': l'API e' cambiata?")
    return partite


def controlla_squadre(partite):
    """Alza SquadraSconosciuta se qualche squadra non e' in tabella.

    Si fa PRIMA di toccare il calendario: meglio fermarsi che scrivere nomi
    inventati in un file che poi finisce sulla pagina.
    """
    nomi = set()
    for p in partite:
        nomi.add((p.get("homeTeam") or {}).get("name") or "")
        nomi.add((p.get("awayTeam") or {}).get("name") or "")
    mancanti = squadre.controlla(n for n in nomi if n)
    if mancanti:
        righe = "\n".join(f'    "{n}": "<nome corto italiano>",' for n in mancanti)
        raise squadre.SquadraSconosciuta(
            "Queste squadre non sono nella tabella di conversione:\n"
            + "\n".join("  - " + n for n in mancanti)
            + "\n\nAggiungile in ovalmo/squadre.py:\n" + righe)


def _normalizza(partita):
    """Una partita dell'API nella forma che usa il progetto."""
    inizio = orari.da_utc(partita["utcDate"])
    data, ora = orari.in_italiano(inizio)
    pieno = ((partita.get("score") or {}).get("fullTime") or {})
    stato = partita.get("status", "")
    risultato = None
    if stato in FINITA and pieno.get("home") is not None and pieno.get("away") is not None:
        risultato = [int(pieno["home"]), int(pieno["away"])]
    return dict(
        id=partita["id"],
        giornata=partita.get("matchday"),
        inizio=inizio,
        data=data,
        ora=ora,
        casa=squadre.italiano((partita.get("homeTeam") or {}).get("name")),
        ospite=squadre.italiano((partita.get("awayTeam") or {}).get("name")),
        stato=stato,
        risultato=risultato,
    )


def giornate_da_tenere(partite, prima_giornata, quante_avanti=1):
    """Quali giornate mettere nel JSON.

    Dalla prima giornata del gioco fino alla giornata in corso piu' una: il
    file resta corto (la pagina e l'Excel disegnano tutto quello che trovano)
    e la schedina della prossima giornata compare in tempo per i pronostici.
    """
    per_giornata = {}
    for p in partite:
        g = p.get("matchday")
        if g is None or g < prima_giornata:
            continue
        per_giornata.setdefault(g, []).append(p)
    if not per_giornata:
        return []
    aperte = [g for g, lista in sorted(per_giornata.items())
              if any(x.get("status") not in FINITA for x in lista)]
    corrente = aperte[0] if aperte else max(per_giornata)
    ultima = min(corrente + quante_avanti, max(per_giornata))
    return [g for g in sorted(per_giornata) if prima_giornata <= g <= ultima]


def aggiorna(stagione, partite):
    """Scrive calendario e risultati nella stagione. Restituisce le note di cosa e' cambiato.

    La stagione viene modificata sul posto. Le note servono al riepilogo e al
    messaggio di commit.
    """
    controlla_squadre(partite)
    note = []
    prima = stagione.get("prima_giornata", 1)
    calendario = stagione.setdefault("calendario", {})
    risultati = stagione.setdefault("risultati", {})
    id_partite = stagione.setdefault("id_partite", {})

    normalizzate = {}
    for p in partite:
        if p.get("matchday") is None:
            continue
        normalizzate.setdefault(p["matchday"], []).append(_normalizza(p))

    for g in giornate_da_tenere(partite, prima):
        del_giorno = sorted(normalizzate[g], key=lambda x: (x["inizio"], x["casa"]))
        chiave = str(g)
        if chiave not in calendario:
            # prima volta che vediamo questa giornata: si fissa adesso l'ordine,
            # e non si tocchera' mai piu'
            calendario[chiave] = []
            for n, partita in enumerate(del_giorno, start=1):
                calendario[chiave].append([partita["data"], partita["ora"], partita["casa"], partita["ospite"]])
                id_partite[id_partita(g, n)] = partita["id"]
            note.append(f"giornata {g}: calendario importato ({len(del_giorno)} partite)")

        # da qui in poi la posizione e' gia' decisa: si aggiorna al suo posto
        righe = calendario[chiave]
        per_id = {p["id"]: p for p in del_giorno}
        for n in range(1, len(righe) + 1):
            mid = id_partita(g, n)
            data, ora, casa, ospite = righe[n - 1]
            nuova = per_id.get(id_partite.get(mid))
            if nuova is None:
                # partita importata prima che esistessero gli id (o id cambiato):
                # la si ritrova dalle squadre, che nella giornata sono uniche
                nuova = next((p for p in del_giorno if p["casa"] == casa and p["ospite"] == ospite), None)
                if nuova is not None:
                    id_partite[mid] = nuova["id"]
            if nuova is None:
                note.append(f"{mid}: {casa}-{ospite} non e' piu' nel calendario dell'API, lasciata com'e'")
                continue
            if (nuova["casa"], nuova["ospite"]) != (casa, ospite):
                note.append(f"{mid}: l'API dice {nuova['casa']}-{nuova['ospite']} ma qui c'e' "
                            f"{casa}-{ospite}: non tocco niente, controlla a mano")
                continue
            if [nuova["data"], nuova["ora"]] != [data, ora]:
                note.append(f"{mid} {casa}-{ospite}: spostata dal {data} {ora} al {nuova['data']} {nuova['ora']}")
                righe[n - 1] = [nuova["data"], nuova["ora"], casa, ospite]
            if nuova["risultato"] and risultati.get(mid) != nuova["risultato"]:
                if mid in risultati:
                    note.append(f"{mid} {casa}-{ospite}: risultato corretto in "
                                f"{nuova['risultato'][0]}-{nuova['risultato'][1]}")
                else:
                    note.append(f"{mid} {casa}-{ospite}: {nuova['risultato'][0]}-{nuova['risultato'][1]}")
                risultati[mid] = nuova["risultato"]
            if nuova["stato"] in NON_GIOCATA and mid not in risultati:
                note.append(f"{mid} {casa}-{ospite}: {nuova['stato'].lower()}, in attesa di recupero")
    return note
