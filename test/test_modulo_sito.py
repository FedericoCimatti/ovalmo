# -*- coding: utf-8 -*-
"""La lettura del foglio scritto dal modulo dentro il sito."""
import pytest

from ovalmo import modulo, orari

STAGIONE = {
    "players": ["Berta", "Lippi"],
    "partite_per_giornata": 3,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"],
                         ["11/10/2026", "18:00", "Como", "Parma"]]},
}
INTEST = "Timestamp,Giocatore,Giornata,P01,P02,P03"
PRIMA = orari.quando("09/10/2026", "12:00")     # giornata 7 coperta
DOPO = orari.quando("11/10/2026", "12:00")      # giornata 7 iniziata


def csv(*righe):
    return "\n".join([INTEST] + list(righe))


def test_timestamp_iso_senza_ambiguita():
    letto = modulo.leggi_timestamp_iso("2026-10-09T16:22:01.000Z")
    assert (letto.day, letto.month, letto.hour) == (9, 10, 18)     # 18:22 a Roma


def test_timestamp_illeggibile():
    assert modulo.leggi_timestamp_iso("ieri") is None
    assert modulo.leggi_timestamp_iso("") is None


def test_importa_una_giornata_iniziata():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,7,1 2-1,X,2 0-3")
    consegne, pronostici, note, scarti = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert consegne == {"7": {"Berta": "09/10/2026 18:00"}}
    assert pronostici["G07-01"]["Berta"] == ["1", 2, 1]
    assert pronostici["G07-02"]["Berta"] == ["X", None, None]
    assert pronostici["G07-03"]["Berta"] == ["2", 0, 3]
    assert not scarti


def test_prima_del_fischio_solo_la_consegna():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,7,1 2-1,X,2 0-3")
    consegne, pronostici, note, _ = modulo.leggi_sito(testo, STAGIONE, PRIMA)
    assert consegne == {"7": {"Berta": "09/10/2026 18:00"}}
    assert pronostici == {}


def test_vale_l_ultimo_invio():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,7,1 2-1,X,2 0-3",
                "2026-10-10T10:00:00.000Z,Berta,7,2 0-1,X,2 0-3")
    _, pronostici, _, _ = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert pronostici["G07-01"]["Berta"] == ["2", 0, 1]


def test_arrivato_dopo_il_calcio_dinizio_scartato():
    # 10/10 alle 21:00 italiane = 19:00Z, la giornata e' cominciata alle 20:45
    testo = csv("2026-10-10T19:00:00.000Z,Berta,7,1 2-1,X,2 0-3")
    consegne, pronostici, _, scarti = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert consegne == {} and pronostici == {}
    assert any("dopo il calcio d'inizio" in s for s in scarti)


def test_un_minuto_prima_del_fischio_vale():
    testo = csv("2026-10-10T18:44:00.000Z,Berta,7,1 2-1,X,2 0-3")
    consegne, _, _, scarti = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert consegne and not scarti


def test_nome_sconosciuto_scartato():
    testo = csv("2026-10-09T16:00:00.000Z,Pinco,7,1 2-1,X,2 0-3")
    consegne, _, _, scarti = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert consegne == {} and any("Pinco" in s for s in scarti)


def test_giornata_inesistente_scartata():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,31,1 2-1,X,2 0-3")
    consegne, _, _, scarti = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert consegne == {} and any("31" in s for s in scarti)


def test_celle_vuote_ignorate():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,7,1 2-1,,")
    _, pronostici, _, _ = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert list(pronostici) == ["G07-01"]


def test_due_giocatori_nella_stessa_giornata():
    testo = csv("2026-10-09T16:00:00.000Z,Berta,7,1 2-1,X,2 0-3",
                "2026-10-09T17:00:00.000Z,Lippi,7,X,1 1-0,")
    consegne, pronostici, _, _ = modulo.leggi_sito(testo, STAGIONE, DOPO)
    assert set(consegne["7"]) == {"Berta", "Lippi"}
    assert set(pronostici["G07-01"]) == {"Berta", "Lippi"}


def test_foglio_vuoto_non_e_un_errore():
    consegne, pronostici, note, _ = modulo.leggi_sito("", STAGIONE, DOPO)
    assert consegne == {} and pronostici == {} and note


def test_foglio_con_le_colonne_sbagliate():
    with pytest.raises(modulo.ErroreFoglio):
        modulo.leggi_sito("a,b,c\n1,2,3", STAGIONE, DOPO)
