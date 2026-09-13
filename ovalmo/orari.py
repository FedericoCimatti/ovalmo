# -*- coding: utf-8 -*-
"""Date, orari e fuso orario.

Regola unica del progetto: **si ragiona sempre in ora di Roma**.
L'API football-data risponde in UTC, il modulo Google scrive in ora italiana,
il server di GitHub gira in UTC. Tutte le conversioni passano da qui, cosi'
c'e' un solo posto dove sbagliare (e un solo posto da testare).

Nel JSON date e ore restano nel formato leggibile italiano: "05/09/2026", "18:00".
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
UTC = ZoneInfo("UTC")

# ora usata quando l'orario non e' ancora stato deciso: mezzanotte, cioe' la
# deadline piu' prudente possibile per quella data
ORA_IGNOTA = "da definire"


def adesso():
    """Adesso, in ora di Roma."""
    return datetime.now(ROMA)


def da_utc(iso):
    """Converte un istante UTC dell'API ("2026-09-05T16:00:00Z") in ora di Roma."""
    testo = iso.strip()
    if testo.endswith("Z"):
        testo = testo[:-1] + "+00:00"
    return datetime.fromisoformat(testo).astimezone(ROMA)


def in_italiano(dt):
    """datetime -> ("05/09/2026", "18:00"), come si scrive nel JSON."""
    dt = dt.astimezone(ROMA)
    return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")


def quando(data, ora):
    """("05/09/2026", "18:00") -> datetime in ora di Roma.

    Se l'ora non e' nota (campo vuoto o "da definire") si usa mezzanotte:
    la deadline scatta prima, mai dopo.
    """
    g, m, a = (int(x) for x in str(data).split("/"))
    try:
        hh, mm = (int(x) for x in str(ora).split(":"))
    except (ValueError, AttributeError):
        hh, mm = 0, 0
    return datetime(a, m, g, hh, mm, tzinfo=ROMA)


def calcio_dinizio(partite):
    """Primo calcio d'inizio di una lista di partite [data, ora, casa, ospite]."""
    return min(quando(p[0], p[1]) for p in partite)


def ordine_cronologico(partite, quante=None):
    """I numeri delle partite, dalla prima che si gioca all'ultima.

    Il calendario tiene le partite nell'ordine in cui sono arrivate la prima
    volta e non le sposta mai piu': la posizione E' il nome della partita
    (G04-05 e' la quinta riga, e li' dentro stanno i pronostici di quella
    partita). Gli orari pero' si spostano di continuo, fra anticipi, posticipi
    e rinvii, e dopo un po' l'elenco salvato non e' piu' l'ordine del campo.

    Questa funzione riordina soltanto per mostrarle: restituisce i numeri, non
    le partite, cosi' chi la usa tiene ogni riga attaccata al suo posto.

    Una partita senza orario vale mezzanotte (come in quando()), quindi si
    mette all'inizio del suo giorno. A parita' di orario vince il numero piu'
    basso, cosi' l'ordine non balla da un giro all'altro.
    """
    numeri = range(1, (len(partite) if quante is None else min(quante, len(partite))) + 1)
    return sorted(numeri, key=lambda n: (quando(partite[n - 1][0], partite[n - 1][1]), n))


def inizi(calendario):
    """{giornata: primo calcio d'inizio} per tutto il calendario."""
    return {g: calcio_dinizio(partite) for g, partite in calendario.items()}


def giornata_del_timestamp(calendario, timestamp):
    """La giornata a cui appartiene un invio del modulo.

    E' la prima giornata il cui primo calcio d'inizio e' successivo all'invio.
    Restituisce None se non ce n'e' nessuna (invio arrivato a stagione finita,
    o dopo l'ultima giornata presente in calendario).
    """
    futuri = sorted(g for g, i in inizi(calendario).items() if i > timestamp)
    return futuri[0] if futuri else None


def coperta(calendario, giornata, ora=None):
    """True finche' la giornata non e' iniziata: i pronostici restano nascosti."""
    ora = ora or adesso()
    return ora < calcio_dinizio(calendario[giornata])
