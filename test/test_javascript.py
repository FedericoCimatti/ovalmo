# -*- coding: utf-8 -*-
"""Che il JavaScript che finisce nella pagina sia almeno sintatticamente sano.

Un apostrofo non protetto dentro una stringa non rompe una funzione: rompe
tutto il blocco, e la pagina resta muta. E' successo con "L'hai mandata", e
nessun test se n'era accorto perche' i test guardavano il testo, non la sintassi.
"""
import os

import pytest

from controllo_js import JavaScriptRotto, controlla, estrai
from ovalmo import dati, diretta, orari, pagina, schedina

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINT = "https://script.google.com/macros/s/ABC/exec"
ADESSO = orari.quando("09/10/2026", "12:00")
DATI = {
    "players": ["Berta", "Lippi", "Lenzuolo"],
    "partite_per_giornata": 2,
    "calendario": {"9": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"]]},
    "risultati": {"G09-01": [2, 1]},
    "pronostici": {"G09-01": {"Berta": ["1", 2, 1]}},
    "consegne": {"9": {"Berta": "x"}},
}


def test_il_controllo_riconosce_un_apostrofo_non_protetto():
    """Il caso vero: L'hai chiude la stringa a meta'."""
    with pytest.raises(JavaScriptRotto):
        controlla("var x = 'L'hai mandata da un altro telefono';\n")
    controlla("var x = 'L\\'hai mandata';\n")          # protetto: va bene


def test_il_controllo_non_si_confonde_coi_commenti():
    controlla("// non e' un problema questo\nvar x = 1;\n")
    controlla("/* nemmeno l'apostrofo qui dentro */\nvar y = 2;\n")


def test_il_modulo_dei_pronostici_e_sintatticamente_sano():
    for js in estrai(schedina.blocco(DATI, adesso=ADESSO, endpoint=ENDPOINT)):
        assert controlla(js) > 0


def test_la_diretta_e_sintatticamente_sana():
    for js in estrai(diretta.blocco(DATI, adesso=ADESSO, endpoint=ENDPOINT)):
        assert controlla(js) > 0


def test_tutta_la_pagina_vera_e_sintatticamente_sana():
    """Compresi l'avviso e il controllo di freschezza, e coi dati veri."""
    stagione, pronostici = dati.carica()
    stagione = dict(stagione, endpoint_pronostici=ENDPOINT)
    with open(os.path.join(QUI, "template.html"), encoding="utf-8") as f:
        template = f.read()
    html = pagina.genera(dati.unisci(stagione, pronostici), template)
    pezzi = estrai(html)
    assert len(pezzi) >= 3
    for js in pezzi:
        controlla(js)


def test_il_modulo_non_cerca_elementi_che_non_esistono():
    """Un getElementById su un id sparito non da' errore di sintassi: da' errore
    quando qualcuno preme un pulsante, e la funzione muore a meta'.

    E' successo togliendo il pannello di conferma: il codice continuava a
    scrivere in un elemento che non c'era piu', e la sezione non si nascondeva
    piu' dopo l'invio.
    """
    import re

    html = schedina.blocco(DATI, adesso=ADESSO, endpoint=ENDPOINT)
    presenti = set(re.findall(r'id="([^"]+)"', html))
    cercati = set(re.findall(r"\$\('([^']+)'\)", html))
    cercati |= set(re.findall(r"getElementById\('([^']+)'\)", html))
    # 'modulo' e' l'id della sezione stessa, gli altri stanno dentro
    mancanti = sorted(cercati - presenti - {"modulo"})
    assert not mancanti, f"il codice cerca elementi che nella pagina non ci sono: {mancanti}"
