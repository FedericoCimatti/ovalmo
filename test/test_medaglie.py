# -*- coding: utf-8 -*-
"""Le medaglie: il colore della casella.

Non sono una seconda regola di punteggio. I punti restano 3/1/0 e li decide il
pronostico da solo; la medaglia guarda anche gli altri, ma serve soltanto a
distinguere l'oro dall'argento, che valgono gli stessi 3 punti.
"""
from ovalmo.punteggio import (ARGENTO, BRONZO, ORO, calcola, metallo, punti,
                              quanti_sul_segno)

TUTTI = ["Ada", "Bea", "Cid"]


def test_l_oro_e_di_chi_sta_solo_contro_tutti():
    """Ada ha scritto 2-1, e nessun altro aveva nemmeno visto giusto l'1."""
    picks = {"Ada": ["1", 2, 1], "Bea": ["X", 1, 1], "Cid": ["2", 0, 1]}
    sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
    assert sul_segno == 1
    assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) == ORO


def test_basta_che_un_altro_sia_sul_segno_e_l_oro_diventa_argento():
    """La precisazione che conta: Bea sbaglia i gol ma azzecca l'1, quindi Ada
    non era sola sulla partita. Restano 3 punti, ma la medaglia e' argento."""
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0], "Cid": ["2", 0, 1]}
    sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
    assert sul_segno == 2
    assert punti(picks["Ada"], [2, 1]) == 3          # i punti non cambiano
    assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) == ARGENTO
    assert metallo(punti(picks["Bea"], [2, 1]), sul_segno) == BRONZO


def test_in_due_sullo_stesso_risultato_e_argento_per_entrambi():
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", 2, 1], "Cid": ["2", 0, 1]}
    sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
    assert sul_segno == 2
    assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) == ARGENTO
    assert metallo(punti(picks["Bea"], [2, 1]), sul_segno) == ARGENTO


def test_il_segno_da_solo_resta_bronzo():
    """Il segno non ha oro: preso da soli o in cinque, e' sempre bronzo.
    L'oro premia la mira, non il coraggio."""
    solo = {"Ada": ["1", 3, 0], "Bea": ["2", 0, 1], "Cid": ["X", 1, 1]}
    folla = {"Ada": ["1", 3, 0], "Bea": ["1", 4, 0], "Cid": ["1", 2, 0]}
    for picks in (solo, folla):
        sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
        assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) == BRONZO


def test_chi_sbaglia_non_prende_niente():
    picks = {"Ada": ["X", 1, 1], "Bea": ["1", 2, 1], "Cid": None}
    sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
    assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) is None
    assert metallo(punti(picks["Cid"], [2, 1]), sul_segno) is None


def test_chi_non_manda_non_toglie_l_oro_a_nessuno():
    """Chi non ha scritto niente non ha scelto nessun segno, quindi non fa
    compagnia a chi ha indovinato."""
    picks = {"Ada": ["1", 2, 1]}
    assert quanti_sul_segno(picks, [2, 1], TUTTI) == 1
    assert metallo(punti(picks["Ada"], [2, 1]), 1) == ORO


def test_conta_il_segno_anche_quando_e_solo_dedotto():
    """Chi scrive solo i gol, senza la lettera, ha scelto un segno lo stesso:
    3-0 e' un 1, e toglie l'oro a chi ha azzeccato il 2-1."""
    picks = {"Ada": ["1", 2, 1], "Bea": [None, 3, 0], "Cid": ["2", 0, 1]}
    sul_segno = quanti_sul_segno(picks, [2, 1], TUTTI)
    assert sul_segno == 2
    assert metallo(punti(picks["Ada"], [2, 1]), sul_segno) == ARGENTO


def test_senza_risultato_non_ci_sono_medaglie():
    picks = {"Ada": ["1", 2, 1], "Bea": ["1", 2, 1]}
    assert quanti_sul_segno(picks, None, TUTTI) == 0


# ------------------------------------------------- i punti non si moltiplicano
DATI = {
    "players": TUTTI,
    "partite_per_giornata": 2,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"]]},
    "risultati": {"G07-01": [2, 1], "G07-02": [0, 0]},
    # Ada azzecca da sola il risultato esatto, Bea solo il segno da sola
    "pronostici": {"G07-01": {"Ada": ["1", 2, 1], "Bea": ["1", 3, 0], "Cid": ["2", 0, 2]},
                   "G07-02": {"Ada": ["X", 0, 0], "Bea": ["X", 1, 1], "Cid": ["1", 1, 0]}},
}


def test_una_partita_vale_al_massimo_tre():
    """Il caso che prima faceva 6: risultato esatto che nessun altro aveva."""
    conti = calcola(DATI)
    assert conti["per_g"][7]["Ada"] == 6        # 3 + 3, due partite
    assert conti["stats"]["Ada"]["pt"] == 6
    assert conti["stats"]["Bea"]["pt"] == 2     # 1 + 1
    assert conti["stats"]["Cid"]["pt"] == 0
    for p in TUTTI:
        for g in conti["per_g"]:
            assert conti["per_g"][g][p] <= 3 * DATI["partite_per_giornata"]


def test_gli_esatti_si_contano_una_volta_sola():
    conti = calcola(DATI)
    assert conti["stats"]["Ada"]["esatti"] == 2
    assert conti["stats"]["Ada"]["segni"] == 2
    assert conti["stats"]["Bea"]["esatti"] == 0
    assert conti["stats"]["Bea"]["segni"] == 2


def test_niente_moltiplica_piu_i_punti():
    """La vecchia regola raddoppiava chi indovinava da solo. Non deve poter
    tornare da nessuna delle tre parti che assegnano punti: qui, la diretta nel
    browser, e le formule dell'Excel."""
    from ovalmo import diretta, excel, punteggio

    for nome in ("CORAGGIO_DA", "CORAGGIO_ESATTO", "CORAGGIO_SEGNO", "punti_partita"):
        assert not hasattr(punteggio, nome), f"punteggio.{nome} e' tornato"

    # qualunque pronostico, qualunque risultato: 3, 1 o 0 e mai altro
    for casa in range(4):
        for ospite in range(4):
            for pron in (None, ["1", None, None], ["X", 1, 1], ["2", 0, 1], [None, 2, 1]):
                assert punteggio.punti(pron, [casa, ospite]) in (0, 1, 3)

    js = diretta._script("{}")
    for parola in ("raddoppia", "coraggioDa", "valore = 6", "valore = 2"):
        assert parola not in js, f"la diretta fa ancora {parola}"

    sorgente = open(excel.__file__, encoding="utf-8").read()
    for cella in ("Config!$D$9", "Config!$D$10", "Config!$D$17"):
        assert cella not in sorgente, f"l'Excel legge ancora {cella}"
