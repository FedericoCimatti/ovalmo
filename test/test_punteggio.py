# -*- coding: utf-8 -*-
"""I punti: la parte che non si puo' sbagliare."""
from ovalmo.punteggio import calcola, punti, re_della_giornata, segno, segno_pronosticato


def test_segno():
    assert segno(2, 1) == "1"
    assert segno(1, 1) == "X"
    assert segno(0, 3) == "2"


def test_tre_punti_solo_col_risultato_esatto():
    assert punti(["1", 2, 1], [2, 1]) == 3


def test_un_punto_col_segno_giusto_e_risultato_sbagliato():
    assert punti(["1", 3, 0], [2, 1]) == 1


def test_i_punti_non_si_sommano():
    # chi prende il risultato esatto fa 3, non 3+1
    assert punti(["1", 2, 1], [2, 1]) == 3


def test_zero_col_segno_sbagliato():
    assert punti(["X", 1, 1], [2, 1]) == 0


def test_zero_se_non_ha_mandato():
    assert punti(None, [2, 1]) == 0
    assert punti([None, None, None], [2, 1]) == 0


def test_solo_il_segno_vale_un_punto():
    assert punti(["1", None, None], [2, 1]) == 1
    assert punti(["2", None, None], [2, 1]) == 0


def test_solo_il_punteggio_deduce_il_segno():
    assert segno_pronosticato([None, 0, 3]) == "2"
    assert punti([None, 2, 1], [2, 1]) == 3
    assert punti([None, 1, 0], [2, 1]) == 1


def test_niente_risultato_niente_punti():
    assert punti(["1", 2, 1], None) == 0


def _dati(pronostici, risultati):
    return {
        "players": ["Ada", "Bea", "Cid"],
        "partite_per_giornata": 2,
        "calendario": {"1": [["01/01/2027", "15:00", "Inter", "Milan"],
                             ["01/01/2027", "18:00", "Roma", "Lazio"]]},
        "risultati": risultati,
        "pronostici": pronostici,
    }


def test_classifica_e_spareggio_sui_risultati_esatti():
    # Ada e Bea finiscono a 4 punti, ma Ada ha un esatto in piu'
    dati = _dati(
        {"G01-01": {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0], "Cid": ["2", 0, 1]},
         "G01-02": {"Ada": ["1", 5, 0], "Bea": ["1", 1, 0], "Cid": ["X", 1, 1]}},
        {"G01-01": [2, 1], "G01-02": [1, 0]})
    conti = calcola(dati)
    assert conti["stats"]["Ada"]["pt"] == 4 and conti["stats"]["Ada"]["esatti"] == 1
    assert conti["stats"]["Bea"]["pt"] == 4 and conti["stats"]["Bea"]["esatti"] == 1
    assert conti["ordine"][2] == "Cid"
    # 4 punti e 1 esatto a testa: veramente pari, stessa posizione
    assert conti["pos"]["Ada"] == conti["pos"]["Bea"] == 1


def test_pari_merito_stessa_posizione():
    dati = _dati({"G01-01": {"Ada": ["1", 2, 1], "Bea": ["1", 2, 1], "Cid": ["2", 0, 1]}},
                 {"G01-01": [2, 1]})
    conti = calcola(dati)
    assert conti["pos"] == {"Ada": 1, "Bea": 1, "Cid": 3}


def test_re_della_giornata():
    dati = _dati({"G01-01": {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0], "Cid": ["2", 0, 1]}},
                 {"G01-01": [2, 1]})
    conti = calcola(dati)
    re, punteggio = re_della_giornata(conti, dati["players"], 1)
    assert re == ["Ada"] and punteggio == 3


def test_re_della_giornata_a_pari_merito():
    dati = _dati({"G01-01": {"Ada": ["1", 2, 1], "Bea": ["1", 2, 1], "Cid": ["2", 0, 1]}},
                 {"G01-01": [2, 1]})
    conti = calcola(dati)
    re, punteggio = re_della_giornata(conti, dati["players"], 1)
    assert re == ["Ada", "Bea"] and punteggio == 3


def test_giornata_senza_punti_non_ha_re():
    dati = _dati({"G01-01": {"Ada": ["2", 0, 1], "Bea": ["2", 0, 2], "Cid": ["X", 1, 1]}},
                 {"G01-01": [2, 1]})
    conti = calcola(dati)
    assert re_della_giornata(conti, dati["players"], 1) == (None, 0)


def test_conta_solo_le_partite_con_risultato():
    dati = _dati({"G01-01": {"Ada": ["1", 2, 1]}, "G01-02": {"Ada": ["1", 1, 0]}},
                 {"G01-01": [2, 1]})
    conti = calcola(dati)
    assert conti["giocate"] == 1
    assert conti["concluse"] == []   # la giornata non e' finita: 1 partita su 2
