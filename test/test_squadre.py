# -*- coding: utf-8 -*-
"""La tabella dei nomi squadra. Se qui manca una riga, il job si deve fermare
con un messaggio chiaro invece di scrivere un nome inventato nel calendario."""
import json
import os

import pytest

from ovalmo import dati, squadre


def test_nomi_lunghi_dell_api_diventano_nomi_corti():
    assert squadre.italiano("FC Internazionale Milano") == "Inter"
    assert squadre.italiano("AC Milan") == "Milan"
    assert squadre.italiano("Juventus FC") == "Juventus"
    assert squadre.italiano("Hellas Verona FC") == "Verona"


def test_spazi_di_troppo_non_disturbano():
    assert squadre.italiano("  AS Roma  ") == "Roma"


def test_squadra_sconosciuta_si_ferma_e_dice_cosa_fare():
    with pytest.raises(squadre.SquadraSconosciuta) as e:
        squadre.italiano("Real Madrid CF")
    assert "squadre.py" in str(e.value)          # dice dove mettere le mani
    assert "Real Madrid CF" in str(e.value)      # e quale nome aggiungere


def test_controlla_elenca_solo_i_mancanti():
    assert squadre.controlla(["AC Milan", "Real Madrid CF", "AS Roma"]) == ["Real Madrid CF"]
    assert squadre.controlla(["AC Milan", "AS Roma"]) == []


def test_tutte_le_squadre_della_stagione_sono_mappate():
    """Ogni squadra che compare nel calendario deve avere una corrispondenza.

    E' il test che si accorge di una promozione dimenticata prima che se ne
    accorga il gioco, di domenica pomeriggio.
    """
    stagione, _ = dati.carica()
    in_calendario = set()
    for partite in stagione["calendario"].values():
        for _, _, casa, ospite in partite:
            in_calendario.add(casa)
            in_calendario.add(ospite)
    conosciute = set(squadre.MAPPA.values())
    mancanti = sorted(in_calendario - conosciute)
    assert not mancanti, (
        f"queste squadre sono nel calendario ma non nella tabella: {mancanti}. "
        f"Aggiungi la riga corrispondente in ovalmo/squadre.py")


def test_nessun_nome_corto_duplicato_per_sbaglio():
    """Due nomi API diversi possono puntare alla stessa squadra (succede quando
    l'API cambia denominazione), ma non deve capitare per distrazione."""
    valori = list(squadre.MAPPA.values())
    doppi = {v for v in valori if valori.count(v) > 1}
    assert doppi <= {"Frosinone", "Venezia", "Monza"}, f"nomi corti ripetuti: {sorted(doppi)}"
