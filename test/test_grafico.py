# -*- coding: utf-8 -*-
"""L'andamento della classifica."""
import json
import re

from ovalmo import grafico, orari, pagina
from ovalmo.punteggio import calcola

GIOCATORI = ["Berta", "Lippi", "Lenzuolo"]
DATI = {
    "players": GIOCATORI,
    "partite_per_giornata": 2,
    "calendario": {"2": [["10/09/2026", "20:45", "Inter", "Milan"],
                         ["11/09/2026", "15:00", "Roma", "Lazio"]],
                   "3": [["17/09/2026", "20:45", "Napoli", "Como"],
                         ["18/09/2026", "15:00", "Genoa", "Parma"]]},
    "risultati": {"G02-01": [2, 1], "G02-02": [0, 0],
                  "G03-01": [1, 0], "G03-02": [3, 1]},
    "pronostici": {"G02-01": {"Berta": ["1", 2, 1], "Lippi": ["1", 3, 0], "Lenzuolo": ["2", 0, 1]},
                   "G02-02": {"Berta": ["X", 0, 0], "Lippi": ["X", 1, 1], "Lenzuolo": ["1", 2, 0]},
                   "G03-01": {"Berta": ["2", 0, 1], "Lippi": ["1", 1, 0], "Lenzuolo": ["1", 2, 1]},
                   "G03-02": {"Berta": ["1", 3, 1], "Lippi": ["1", 2, 0], "Lenzuolo": ["X", 1, 1]}},
}


def cfg(html):
    grezzo = re.search(r'data-cfg="(.*?)" viewBox', html, re.S).group(1)
    return json.loads(grezzo.replace("&quot;", '"'))


def test_una_linea_per_giocatore_col_suo_colore_fisso():
    html = grafico.disegna(calcola(DATI), GIOCATORI)
    assert html.count('class="linea"') == 3
    assert 'data-chi="Berta" points=' in html
    assert "var(--gr1)" in html and "var(--gr2)" in html and "var(--gr3)" in html


def test_i_punti_sono_cumulativi():
    conti = calcola(DATI)
    d = cfg(grafico.disegna(conti, GIOCATORI))
    for p in GIOCATORI:
        assert d["serie"][p][-1] == conti["stats"][p]["pt"]
        assert d["serie"][p][0] == conti["per_g"][2][p]


def test_con_una_giornata_sola_non_si_disegna_niente():
    """Un punto solo non e' un andamento."""
    dati = dict(DATI, risultati={"G02-01": [2, 1], "G02-02": [0, 0]})
    assert grafico.disegna(calcola(dati), GIOCATORI) == ""


def test_la_giornata_in_corso_entra_anche_senza_risultati():
    """E' il punto che la diretta fa salire a ogni gol: senza, quei punti
    finirebbero sulla giornata precedente, che e' gia' chiusa."""
    dati = dict(DATI, risultati={"G02-01": [2, 1], "G02-02": [0, 0]})
    html = grafico.disegna(calcola(dati), GIOCATORI, giornata_viva=3)
    assert html, "col la giornata in corso il grafico deve esserci"
    d = cfg(html)
    assert d["giornate"] == [2, 3]
    for p in GIOCATORI:
        assert d["serie"][p][1] == d["serie"][p][0]     # ancora nessun punto


def test_la_scala_lascia_spazio_alle_partite_ancora_aperte():
    """Se cambiasse mentre si gioca, il grafico andrebbe ridisegnato tutto e le
    due versioni (Python e browser) potrebbero divergere."""
    stretta = cfg(grafico.disegna(calcola(DATI), GIOCATORI, aperte_ora=0))["ymax"]
    larga = cfg(grafico.disegna(calcola(DATI), GIOCATORI, aperte_ora=10))["ymax"]
    assert larga >= stretta + 30


def test_nessun_pronostico_finisce_nel_grafico():
    """Il grafico dice punti, non segni: nemmeno indirettamente."""
    d = cfg(grafico.disegna(calcola(DATI), GIOCATORI))
    assert set(d) == {"xs", "giornate", "ymax", "y0", "dentroY", "serie", "giocatori"}


def test_il_grafico_sta_nella_pagina_dentro_una_cella_che_si_apre():
    import os
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(qui, "template.html"), encoding="utf-8") as f:
        template = f.read()
    html = pagina.genera(DATI, template, adesso=orari.quando("20/09/2026", "12:00"))
    assert '<details class="g andamento">' in html
    assert "<summary>" in html and "Andamento" in html
    # subito sotto la classifica, prima della schedina
    assert html.index("andamento") < html.index("La schedina")


def test_le_tacche_cadono_su_numeri_tondi():
    """Multipli di 6 o di 7 su un asse si leggono male."""
    for massimo in (7, 22, 25, 47, 120, 260, 340):
        scala = grafico._scala(massimo)
        assert scala >= massimo
        assert scala % grafico._passo(scala) == 0
        assert grafico._passo(scala) in (5, 10, 20, 50, 100, 200)
