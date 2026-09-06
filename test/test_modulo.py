# -*- coding: utf-8 -*-
"""La lettura del foglio risposte del modulo Google."""
import pytest

from ovalmo import modulo, orari

STAGIONE = {
    "players": ["Berta", "Lippi", "Lenzuolo"],
    "partite_per_giornata": 3,
    "calendario": {
        "3": [["04/09/2026", "20:45", "Genoa", "Como"],
              ["05/09/2026", "15:00", "Fiorentina", "Torino"],
              ["05/09/2026", "18:00", "Inter", "Napoli"]],
        "4": [["11/09/2026", "20:45", "Milan", "Roma"],
              ["12/09/2026", "15:00", "Lazio", "Parma"],
              ["12/09/2026", "18:00", "Torino", "Genoa"]],
    },
}

INTESTAZIONE = "Timestamp,Chi sei?,Giornata,1. Genoa - Como,2. Fiorentina - Torino,3. Inter - Napoli"
PRIMA = orari.quando("03/09/2026", "12:00")     # giornata 3 ancora coperta
DOPO = orari.quando("06/09/2026", "12:00")      # giornata 3 gia' iniziata


def csv(*righe):
    return "\n".join([INTESTAZIONE] + list(righe))


# ---------------------------------------------------------------- formati liberi
@pytest.mark.parametrize("testo,atteso", [
    ("1 (2-1)", ("1", 2, 1)),
    ("1 2-1", ("1", 2, 1)),
    ("X", ("X", None, None)),
    ("2 0 a 3", ("2", 0, 3)),
    ("x (1-1)", ("X", 1, 1)),
    ("2-0", ("1", 2, 0)),          # solo i gol: il segno si deduce
    ("1 (2:1)", ("1", 2, 1)),
    ("  1   (2-1)  ", ("1", 2, 1)),
])
def test_formati_accettati(testo, atteso):
    assert modulo.parse_pronostico(testo) == atteso


@pytest.mark.parametrize("testo", ["", "   ", "boh", "non so"])
def test_celle_da_ignorare(testo):
    assert modulo.parse_pronostico(testo) is None


def test_segno_e_punteggio_che_si_contraddicono():
    esito = modulo.parse_pronostico("1 (0-2)")
    assert esito[0] == "INCOERENTE"


# ---------------------------------------------------------------- timestamp
def test_timestamp_italiano():
    letto = modulo.leggi_timestamp("04/09/2026 18:22:01")
    assert letto.replace(second=0) == orari.quando("04/09/2026", "18:22")


def test_timestamp_senza_secondi():
    assert modulo.leggi_timestamp("04/09/2026 18:22") == orari.quando("04/09/2026", "18:22")


def test_timestamp_illeggibile():
    assert modulo.leggi_timestamp("ieri sera") is None
    assert modulo.leggi_timestamp("") is None


def test_data_ambigua_letta_all_italiana():
    # 05/09 e' il 5 settembre, non il 9 maggio: il foglio e' italiano
    assert modulo.leggi_timestamp("05/09/2026 10:00:00").month == 9


def test_data_solo_americana_letta_lo_stesso():
    # 09/25 non esiste come giorno/mese: unica lettura possibile, 25 settembre
    assert modulo.leggi_timestamp("09/25/2026 10:00:00").day == 25


# ---------------------------------------------------------------- import
def test_importa_una_giornata_gia_iniziata():
    testo = csv("04/09/2026 18:00:00,Berta,,1 (2-1),X,2 (0-3)")
    consegne, pronostici, note, scarti = modulo.leggi(testo, STAGIONE, DOPO)
    assert consegne == {"3": {"Berta": "04/09/2026 18:00"}}
    assert pronostici["G03-01"]["Berta"] == ["1", 2, 1]
    assert pronostici["G03-02"]["Berta"] == ["X", None, None]
    assert pronostici["G03-03"]["Berta"] == ["2", 0, 3]
    assert not scarti


def test_giornata_ancora_coperta_niente_pronostici_solo_la_consegna():
    # la regola piu' importante del gioco: prima del fischio nel repository
    # pubblico non deve finire nessun pronostico, solo chi ha mandato
    testo = csv("03/09/2026 10:00:00,Berta,,1 (2-1),X,2 (0-3)")
    consegne, pronostici, note, _ = modulo.leggi(testo, STAGIONE, PRIMA)
    assert consegne == {"3": {"Berta": "03/09/2026 10:00"}}
    assert pronostici == {}
    assert any("coperti" in n for n in note)


def test_vale_solo_l_invio_piu_recente():
    testo = csv("03/09/2026 10:00:00,Berta,,1 (2-1),X,2 (0-3)",
                "03/09/2026 22:00:00,Berta,,2 (0-1),X,2 (0-3)")
    consegne, pronostici, _, _ = modulo.leggi(testo, STAGIONE, DOPO)
    assert pronostici["G03-01"]["Berta"] == ["2", 0, 1]
    assert consegne["3"]["Berta"] == "03/09/2026 22:00"


def test_invio_arrivato_dopo_il_fischio_non_entra_nella_giornata():
    # scivola alla giornata 4, dove le intestazioni non corrispondono: scartato
    testo = csv("05/09/2026 10:00:00,Berta,,1 (2-1),X,2 (0-3)")
    consegne, pronostici, note, _ = modulo.leggi(testo, STAGIONE, DOPO)
    assert consegne == {} and pronostici == {}
    assert any("NON corrispondono" in n for n in note)


def test_intestazioni_di_un_altra_giornata_non_importano_niente():
    sbagliato = ("Timestamp,Chi sei?,Giornata,1. Milan - Roma,2. Lazio - Parma,3. Torino - Genoa\n"
                 "04/09/2026 18:00:00,Berta,,1 (2-1),X,2 (0-3)")
    consegne, pronostici, note, _ = modulo.leggi(sbagliato, STAGIONE, DOPO)
    assert consegne == {} and pronostici == {}
    assert any("NON corrispondono" in n for n in note)


def test_nome_sconosciuto_scartato():
    testo = csv("04/09/2026 18:00:00,Pinco,,1 (2-1),X,2 (0-3)")
    consegne, pronostici, _, scarti = modulo.leggi(testo, STAGIONE, DOPO)
    assert consegne == {} and pronostici == {}
    assert any("Pinco" in s for s in scarti)


def test_riga_con_data_illeggibile_scartata():
    testo = csv("ieri,Berta,,1 (2-1),X,2 (0-3)")
    _, pronostici, _, scarti = modulo.leggi(testo, STAGIONE, DOPO)
    assert pronostici == {} and scarti


def test_celle_vuote_ignorate_senza_rompere_il_resto():
    testo = csv("04/09/2026 18:00:00,Berta,,1 (2-1),,boh")
    _, pronostici, _, _ = modulo.leggi(testo, STAGIONE, DOPO)
    assert "G03-01" in pronostici
    assert "G03-02" not in pronostici and "G03-03" not in pronostici


def test_le_colonne_si_leggono_per_numero_non_per_nome():
    # le colonne arrivano in disordine: conta il numero davanti al nome
    disordinato = ("Timestamp,Chi sei?,Giornata,3. Inter - Napoli,1. Genoa - Como,2. Fiorentina - Torino\n"
                   "04/09/2026 18:00:00,Berta,,2 (0-3),1 (2-1),X")
    _, pronostici, _, _ = modulo.leggi(disordinato, STAGIONE, DOPO)
    assert pronostici["G03-01"]["Berta"] == ["1", 2, 1]
    assert pronostici["G03-03"]["Berta"] == ["2", 0, 3]


def test_foglio_senza_colonne_partita():
    with pytest.raises(modulo.ErroreFoglio):
        modulo.leggi("Timestamp,Chi sei?\n04/09/2026 18:00:00,Berta", STAGIONE, DOPO)


def test_foglio_vuoto():
    with pytest.raises(modulo.ErroreFoglio):
        modulo.leggi("", STAGIONE, DOPO)


def test_unisci_non_cancella_quello_che_c_era():
    archivio = {"consegne": {"3": {"Lippi": "01/09/2026 10:00"}},
                "pronostici": {"G03-01": {"Lippi": ["1", 1, 0]}}}
    cambiato = modulo.unisci(archivio, {"3": {"Berta": "04/09/2026 18:00"}},
                             {"G03-01": {"Berta": ["2", 0, 1]}})
    assert cambiato is True
    assert archivio["pronostici"]["G03-01"] == {"Lippi": ["1", 1, 0], "Berta": ["2", 0, 1]}
    assert set(archivio["consegne"]["3"]) == {"Lippi", "Berta"}


def test_unisci_due_volte_di_fila_non_cambia_niente():
    archivio = {"consegne": {}, "pronostici": {}}
    dati = ({"3": {"Berta": "04/09/2026 18:00"}}, {"G03-01": {"Berta": ["2", 0, 1]}})
    assert modulo.unisci(archivio, *dati) is True
    assert modulo.unisci(archivio, *dati) is False
