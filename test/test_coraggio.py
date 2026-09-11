# -*- coding: utf-8 -*-
"""Il punto coraggio: chi indovina da solo vale il doppio.

La regola e' arrivata a stagione cominciata, quindi ci sono due epoche: prima
della giornata CORAGGIO_DA si contano 3/1/0, da li' in poi anche 6/2. Le due
epoche devono convivere nello stesso file senza che i punti gia' assegnati
cambino: e' la ragione per cui meta' di questi test guardano una giornata
vecchia e meta' una nuova.
"""
from ovalmo.punteggio import CORAGGIO_DA, calcola, punti_partita

PRIMA = CORAGGIO_DA - 1
DOPO = CORAGGIO_DA


def _dati(giornata, pronostici, risultati):
    return {
        "players": ["Ada", "Bea", "Cid"],
        "partite_per_giornata": 1,
        "calendario": {str(giornata): [["01/01/2027", "15:00", "Inter", "Milan"]]},
        "risultati": risultati,
        "pronostici": pronostici,
    }


# --------------------------------------------------------------- il raddoppio

def test_prima_della_giornata_stabilita_non_raddoppia_niente():
    picks = {"Ada": ["1", 2, 1], "Bea": ["X", 1, 1], "Cid": ["2", 0, 1]}
    assert punti_partita(picks, [2, 1], PRIMA) == {"Ada": 3, "Bea": 0, "Cid": 0}


def test_risultato_esatto_scritto_da_uno_solo_vale_sei():
    picks = {"Ada": ["1", 2, 1], "Bea": ["X", 1, 1], "Cid": ["2", 0, 1]}
    assert punti_partita(picks, [2, 1], DOPO)["Ada"] == 6


def test_lo_stesso_risultato_scritto_in_due_vale_tre_a_testa():
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", 2, 1], "Cid": ["2", 0, 1]}
    conto = punti_partita(picks, [2, 1], DOPO)
    assert conto["Ada"] == conto["Bea"] == 3


def test_il_segno_scelto_da_uno_solo_vale_due():
    # Ada sola sull'1, le altre due sul 2: finisce 2-1
    picks = {"Ada": ["1", 3, 0], "Bea": ["2", 0, 1], "Cid": ["2", 1, 2]}
    assert punti_partita(picks, [2, 1], DOPO) == {"Ada": 2, "Bea": 0, "Cid": 0}


def test_il_segno_in_compagnia_vale_un_punto_come_sempre():
    picks = {"Ada": ["1", 3, 0], "Bea": ["1", 4, 0], "Cid": ["2", 0, 1]}
    conto = punti_partita(picks, [2, 1], DOPO)
    assert conto["Ada"] == conto["Bea"] == 1


def test_esatto_da_solo_anche_se_il_segno_lo_avevano_in_tanti():
    """Sono due premi diversi: il segno per il coraggio, il punteggio per la mira."""
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0], "Cid": ["1", 4, 1]}
    conto = punti_partita(picks, [2, 1], DOPO)
    assert conto == {"Ada": 6, "Bea": 1, "Cid": 1}


# ------------------------------------------------- chi non ha mandato, e i mezzi

def test_chi_non_manda_non_fa_compagnia_a_nessuno():
    picks = {"Ada": ["1", 2, 1]}          # Bea e Cid non hanno mandato
    conto = punti_partita(picks, [2, 1], DOPO, ["Ada", "Bea", "Cid"])
    assert conto == {"Ada": 6, "Bea": 0, "Cid": 0}


def test_chi_scrive_solo_il_segno_fa_compagnia_sul_segno_ma_non_sul_punteggio():
    # Bea ha scritto solo "1": toglie ad Ada il premio del segno, non quello
    # del punteggio, perche' un punteggio non lo ha scritto
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", None, None], "Cid": ["2", 0, 1]}
    assert punti_partita(picks, [2, 1], DOPO)["Ada"] == 6
    picks = {"Ada": ["1", 3, 0], "Bea": ["1", None, None], "Cid": ["2", 0, 1]}
    assert punti_partita(picks, [2, 1], DOPO)["Ada"] == 1


def test_senza_risultato_nessuno_prende_niente():
    picks = {"Ada": ["1", 2, 1]}
    assert punti_partita(picks, None, DOPO, ["Ada", "Bea"]) == {"Ada": 0, "Bea": 0}


# ------------------------------------------------------------- e la classifica

def test_in_classifica_il_sei_conta_come_un_risultato_esatto_non_come_due():
    """Il punto coraggio raddoppia i punti, non i risultati esatti: se li contasse
    doppi, lo spareggio a pari punti mentirebbe."""
    dati = _dati(DOPO, {f"G{DOPO:02d}-01": {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0],
                                            "Cid": ["1", 4, 0]}},
                 {f"G{DOPO:02d}-01": [2, 1]})
    stats = calcola(dati)["stats"]
    assert stats["Ada"] == {"pt": 6, "segni": 1, "esatti": 1}
    assert stats["Bea"] == {"pt": 1, "segni": 1, "esatti": 0}


def test_una_giornata_vecchia_e_una_nuova_convivono():
    """I punti gia' assegnati non si toccano: la stessa identica schedina vale
    3 nella giornata prima della regola e 6 in quella dopo."""
    schedina = {"Ada": ["1", 2, 1], "Bea": ["X", 1, 1], "Cid": ["2", 0, 1]}
    dati = {
        "players": ["Ada", "Bea", "Cid"],
        "partite_per_giornata": 1,
        "calendario": {str(PRIMA): [["01/01/2027", "15:00", "Inter", "Milan"]],
                       str(DOPO): [["08/01/2027", "15:00", "Inter", "Milan"]]},
        "pronostici": {f"G{PRIMA:02d}-01": schedina, f"G{DOPO:02d}-01": schedina},
        "risultati": {f"G{PRIMA:02d}-01": [2, 1], f"G{DOPO:02d}-01": [2, 1]},
    }
    conti = calcola(dati)
    assert conti["per_g"][PRIMA]["Ada"] == 3
    assert conti["per_g"][DOPO]["Ada"] == 6
    assert conti["stats"]["Ada"]["pt"] == 9
