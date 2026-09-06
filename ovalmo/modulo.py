# -*- coding: utf-8 -*-
"""I pronostici, letti dal foglio risposte del modulo Google.

Il foglio e' pubblicato sul web in formato CSV (File > Condividi > Pubblica sul
web): si scarica senza credenziali, quindi un job automatico ce la fa.
L'indirizzo sta nei segreti del repository, non nel codice: chi ce l'ha legge
tutti i pronostici, anche quelli ancora coperti.

Le regole di lettura sono quelle collaudate dal vecchio leggi_modulo.py:

  - le colonne partita hanno per intestazione il nome vero della partita
    ("3. Inter - Napoli") e cambiano ogni settimana: contano la posizione e
    l'ordine, mai il nome
  - la giornata si deduce dal Timestamp: e' la prima giornata il cui primo
    calcio d'inizio e' successivo all'invio
  - verifica obbligatoria: le squadre nelle intestazioni devono coincidere col
    calendario di quella giornata. Se non coincidono non si importa niente
  - formati liberi: "1 (2-1)", "1 2-1", "X", "2 0 a 3". Solo segno o solo gol
    vanno bene entrambi; cella vuota o incomprensibile si ignora
  - invii multipli per la stessa giornata: vale il piu' recente
  - invii dopo il calcio d'inizio: la deduzione li sposta alla giornata dopo,
    dove le intestazioni non combaciano, quindi vengono scartati da soli

In piu' rispetto a prima, e per via del repository pubblico: i pronostici
vengono restituiti solo per le giornate GIA' INIZIATE. Per quelle ancora
coperte esce solo la consegna (chi ha mandato e quando), che e' quanto basta
per la spunta verde sulla pagina.
"""
import csv
import datetime
import io
import re
import urllib.error
import urllib.request

from . import orari
from .dati import id_partita

FORMATI_DATA = [
    "%d/%m/%Y %H:%M:%S",   # foglio in italiano, il caso normale
    "%d/%m/%Y %H.%M.%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",   # foglio in inglese: ultimo tentativo, vedi sotto
]


class ErroreFoglio(Exception):
    """Il foglio non e' raggiungibile o non ha la forma attesa."""


def scarica(url, timeout=30):
    """Scarica il CSV pubblicato. Restituisce il testo."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as risposta:
            grezzo = risposta.read()
    except urllib.error.HTTPError as e:
        raise ErroreFoglio(
            f"il foglio ha risposto {e.code}. Controlla che sia ancora pubblicato sul web "
            f"(File > Condividi > Pubblica sul web) e che l'indirizzo nel segreto FOGLIO_CSV "
            f"sia quello giusto.") from e
    except urllib.error.URLError as e:
        raise ErroreFoglio(f"non riesco a raggiungere il foglio Google: {e.reason}") from e
    testo = grezzo.decode("utf-8-sig", errors="replace")
    if "<html" in testo[:400].lower():
        raise ErroreFoglio(
            "il foglio ha risposto con una pagina HTML invece che con un CSV: quasi sempre "
            "vuol dire che la pubblicazione sul web e' stata disattivata.")
    return testo


def leggi_timestamp(testo):
    """L'orario di invio, in ora di Roma. None se illeggibile.

    ATTENZIONE alle date ambigue: "05/09/2026" e' il 5 settembre per un foglio
    italiano e il 9 maggio per uno inglese. Si prova prima il formato italiano,
    che e' quello del foglio di Cima; il formato americano resta come ultima
    spiaggia per non buttare via una riga leggibile.
    """
    grezzo = (testo or "").strip()
    if not grezzo:
        return None
    for formato in FORMATI_DATA:
        try:
            naive = datetime.datetime.strptime(grezzo, formato)
        except ValueError:
            continue
        return naive.replace(tzinfo=orari.ROMA)
    return None


def parse_pronostico(testo):
    """"1 (2-1)" -> ("1", 2, 1). Accetta anche "1 2-1", "X", "2 0 a 3".

    Restituisce None se la cella e' vuota o incomprensibile, e la tupla
    ("INCOERENTE", testo, segno, dedotto) se segno e punteggio si contraddicono.
    """
    t = (testo or "").strip()
    if not t:
        return None
    gol = re.search(r"(\d+)\s*(?:-|–|a|:)\s*(\d+)", t)
    # il segno si cerca FUORI dal punteggio: in "2-0" quel 2 sono i gol di casa,
    # non un segno "2". Cercandolo dentro, una cella con i soli gol verrebbe
    # scartata come incoerente e il pronostico sparirebbe senza dire niente.
    resto = (t[:gol.start()] + " " + t[gol.end():]) if gol else t
    trovato = re.search(r"(?<![0-9])([12xX])(?![0-9])", resto)
    seg = trovato.group(1).upper() if trovato else None
    if gol:
        casa, ospite = int(gol.group(1)), int(gol.group(2))
        dedotto = "1" if casa > ospite else ("X" if casa == ospite else "2")
        if seg and seg != dedotto:
            return ("INCOERENTE", t, seg, dedotto)
        return (seg or dedotto, casa, ospite)
    return (seg, None, None) if seg else None


def _colonne_partita(intestazioni):
    """[(numero, indice colonna, casa, ospite)] ordinate per numero."""
    colonne = []
    for i, h in enumerate(intestazioni):
        m = re.match(r"^(\d+)\s*\.\s*(.+?)\s*-\s*(.+)$", (h or "").replace("\\", "").strip())
        if m:
            colonne.append((int(m.group(1)), i, m.group(2).strip(), m.group(3).strip()))
    colonne.sort()
    return colonne


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def leggi(testo_csv, stagione, adesso=None):
    """Legge il foglio e restituisce (consegne, pronostici, note, scarti).

    consegne   {"3": {"Berta": "04/09/2026 18:22"}} - chi ha mandato, sempre
    pronostici {"G03-01": {"Berta": ["1", 2, 1]}}   - solo giornate gia' iniziate
    note       cosa e' stato importato e cosa e' stato ignorato
    scarti     righe buttate, col motivo
    """
    adesso = adesso or orari.adesso()
    calendario = {int(k): v for k, v in stagione["calendario"].items()}
    giocatori = set(stagione["players"])

    righe = list(csv.reader(io.StringIO(testo_csv)))
    righe = [r for r in righe if any((c or "").strip() for c in r)]
    if not righe:
        raise ErroreFoglio("il foglio e' vuoto: nessuna riga da leggere.")
    intestazioni, dati = righe[0], righe[1:]

    colonne = _colonne_partita(intestazioni)
    if not colonne:
        raise ErroreFoglio(
            "nessuna colonna partita riconosciuta nel foglio. Le intestazioni devono avere la "
            "forma \"3. Inter - Napoli\": probabilmente le domande del modulo non sono state "
            "rinominate con le partite della giornata.")
    try:
        i_ts = next(i for i, h in enumerate(intestazioni) if _norm(h).startswith("timestamp")
                    or _norm(h).startswith("informazioni cronologiche"))
        i_nome = next(i for i, h in enumerate(intestazioni) if _norm(h).startswith("chi sei"))
    except StopIteration:
        raise ErroreFoglio(
            "nel foglio mancano le colonne Timestamp e/o \"Chi sei?\": e' il foglio giusto?")

    note, scarti, migliori = [], [], {}
    for r in dati:
        if len(r) <= max(i_ts, i_nome):
            continue
        ts = leggi_timestamp(r[i_ts])
        if ts is None:
            scarti.append(f"riga con data illeggibile: {r[i_ts]!r}")
            continue
        nome = (r[i_nome] or "").strip()
        if nome not in giocatori:
            scarti.append(f"nome non riconosciuto: {nome!r}")
            continue
        g = orari.giornata_del_timestamp(calendario, ts)
        if g is None:
            scarti.append(f"{nome} {ts:%d/%m %H:%M}: nessuna giornata ancora da giocare "
                          f"(invio arrivato dopo l'ultima giornata in calendario)")
            continue
        chiave = (nome, g)
        if chiave not in migliori or ts > migliori[chiave][0]:
            migliori[chiave] = (ts, r)

    # verifica intestazioni: le partite del modulo devono essere quelle della giornata
    valide = []
    for g in sorted({g for _, g in migliori}):
        atteso = [(p[2], p[3]) for p in calendario[g]]
        trovato = [(c[2], c[3]) for c in colonne]
        uguali = len(atteso) == len(trovato) and all(
            _norm(a[0]) == _norm(b[0]) and _norm(a[1]) == _norm(b[1])
            for a, b in zip(atteso, trovato))
        if uguali:
            valide.append(g)
        else:
            note.append(f"GIORNATA {g}: le intestazioni del modulo NON corrispondono al "
                        f"calendario. Il modulo e' fermo a un'altra giornata: non importo nulla.")
            note.append("  modulo:     " + ", ".join(f"{c[2]}-{c[3]}" for c in colonne))
            note.append("  calendario: " + ", ".join(f"{a}-{b}" for a, b in atteso))

    consegne, pronostici = {}, {}
    for (nome, g), (ts, r) in sorted(migliori.items()):
        if g not in valide:
            continue
        consegne.setdefault(str(g), {})[nome] = f"{ts:%d/%m/%Y %H:%M}"
        iniziata = not orari.coperta(calendario, g, adesso)
        if not iniziata:
            note.append(f"consegnato: {nome}, giornata {g} ({ts:%d/%m %H:%M}) - "
                        f"pronostici coperti fino al calcio d'inizio")
            continue
        quanti = 0
        for n, idx, _, _ in colonne:
            mid = id_partita(g, n)
            p = parse_pronostico(r[idx] if idx < len(r) else "")
            if p is None:
                continue
            if p[0] == "INCOERENTE":
                note.append(f"{nome} {mid}: {p[1]!r} ha segno {p[2]} ma punteggio da {p[3]} - ignorato")
                continue
            pronostici.setdefault(mid, {})[nome] = [p[0], p[1], p[2]]
            quanti += 1
        note.append(f"importato: {nome}, giornata {g} ({ts:%d/%m %H:%M}) - {quanti} partite")
    return consegne, pronostici, note, scarti


def unisci(archivio, consegne, pronostici):
    """Mette consegne e pronostici nuovi nell'archivio. True se e' cambiato qualcosa.

    Non cancella mai niente: un pronostico gia' salvato resta al suo posto anche
    se il foglio sparisce, e le giornate vecchie non vengono ricalcolate.
    """
    cambiato = False
    for g, chi in consegne.items():
        for nome, quando in chi.items():
            if archivio["consegne"].setdefault(g, {}).get(nome) != quando:
                archivio["consegne"][g][nome] = quando
                cambiato = True
    for mid, picks in pronostici.items():
        for nome, p in picks.items():
            if archivio["pronostici"].setdefault(mid, {}).get(nome) != p:
                archivio["pronostici"][mid][nome] = p
                cambiato = True
    return cambiato


# ---------------------------------------------------------------------------
# Il modulo dentro il sito (foglio "Pronostici", scritto da Apps Script)
#
# E' molto piu' semplice da leggere del modulo Google: la pagina manda anche il
# numero della giornata e l'orario in formato internazionale, quindi qui non si
# deve piu' dedurre niente ne' verificare che le intestazioni siano quelle
# giuste. Le due parti piu' delicate del vecchio sistema spariscono.
# ---------------------------------------------------------------------------

def leggi_timestamp_iso(testo):
    """"2026-09-08T18:22:01.123Z" -> orario di Roma. None se illeggibile."""
    grezzo = (testo or "").strip()
    if not grezzo:
        return None
    if grezzo.endswith("Z"):
        grezzo = grezzo[:-1] + "+00:00"
    try:
        istante = datetime.datetime.fromisoformat(grezzo)
    except ValueError:
        return None
    if istante.tzinfo is None:                    # senza fuso: si assume Roma
        return istante.replace(tzinfo=orari.ROMA)
    return istante.astimezone(orari.ROMA)


def leggi_sito(testo_csv, stagione, adesso=None):
    """Come leggi(), ma per il foglio scritto dal modulo dentro il sito.

    Restituisce (consegne, pronostici, note, scarti) con lo stesso significato.
    """
    adesso = adesso or orari.adesso()
    calendario = {int(k): v for k, v in stagione["calendario"].items()}
    giocatori = set(stagione["players"])

    righe = [r for r in csv.reader(io.StringIO(testo_csv)) if any((c or "").strip() for c in r)]
    if not righe:
        return {}, {}, ["il foglio dei pronostici e' vuoto: nessuno ha ancora mandato"], []
    intestazioni, dati = righe[0], righe[1:]
    try:
        i_ts = next(i for i, h in enumerate(intestazioni) if _norm(h).startswith("timestamp"))
        i_nome = next(i for i, h in enumerate(intestazioni) if _norm(h).startswith("giocatore"))
        i_giornata = next(i for i, h in enumerate(intestazioni) if _norm(h).startswith("giornata"))
    except StopIteration:
        raise ErroreFoglio(
            "il foglio \"Pronostici\" non ha le colonne Timestamp, Giocatore e Giornata: "
            "e' il foglio giusto?")
    colonne = sorted((int(h[1:]), i) for i, h in enumerate(intestazioni)
                     if re.fullmatch(r"P\d{2}", (h or "").strip()))
    if not colonne:
        raise ErroreFoglio("il foglio \"Pronostici\" non ha le colonne P01...P10.")

    note, scarti, migliori = [], [], {}
    for r in dati:
        if len(r) <= max(i_ts, i_nome, i_giornata):
            continue
        ts = leggi_timestamp_iso(r[i_ts])
        if ts is None:
            scarti.append(f"riga con data illeggibile: {r[i_ts]!r}")
            continue
        nome = (r[i_nome] or "").strip()
        if nome not in giocatori:
            scarti.append(f"nome non riconosciuto: {nome!r}")
            continue
        try:
            g = int(r[i_giornata])
        except (ValueError, TypeError):
            scarti.append(f"{nome}: giornata illeggibile {r[i_giornata]!r}")
            continue
        if g not in calendario:
            scarti.append(f"{nome}: giornata {g} non presente in calendario")
            continue
        if ts >= orari.calcio_dinizio(calendario[g]):
            scarti.append(f"{nome} giornata {g}: arrivato dopo il calcio d'inizio, non vale")
            continue
        chiave = (nome, g)
        if chiave not in migliori or ts > migliori[chiave][0]:
            migliori[chiave] = (ts, r)

    consegne, pronostici = {}, {}
    for (nome, g), (ts, r) in sorted(migliori.items()):
        consegne.setdefault(str(g), {})[nome] = f"{ts:%d/%m/%Y %H:%M}"
        if orari.coperta(calendario, g, adesso):
            note.append(f"consegnato: {nome}, giornata {g} ({ts:%d/%m %H:%M}) - "
                        f"pronostici coperti fino al calcio d'inizio")
            continue
        quanti = 0
        for n, idx in colonne:
            if n > len(calendario[g]):
                continue
            p = parse_pronostico(r[idx] if idx < len(r) else "")
            if p is None:
                continue
            if p[0] == "INCOERENTE":
                note.append(f"{nome} G{g:02d}-{n:02d}: {p[1]!r} ha segno {p[2]} ma punteggio "
                            f"da {p[3]} - ignorato")
                continue
            pronostici.setdefault(id_partita(g, n), {})[nome] = [p[0], p[1], p[2]]
            quanti += 1
        note.append(f"importato: {nome}, giornata {g} ({ts:%d/%m %H:%M}) - {quanti} partite")
    return consegne, pronostici, note, scarti


def leggi_qualunque(testo_csv, stagione, adesso=None):
    """Legge il foglio senza sapere in anticipo quale dei due sia.

    Durante il passaggio dal modulo Google al modulo dentro il sito possono
    esistere tutti e due. Si guarda l'intestazione e si sceglie il lettore
    giusto, cosi' il giro automatico non va cambiato il giorno del cambio.
    """
    prima = (testo_csv or "").splitlines()[:1]
    intestazione = _norm(prima[0] if prima else "")
    if "giocatore" in intestazione and "giornata" in intestazione:
        return leggi_sito(testo_csv, stagione, adesso)
    return leggi(testo_csv, stagione, adesso)
