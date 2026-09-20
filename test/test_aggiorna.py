# -*- coding: utf-8 -*-
"""Idempotenza e file Excel: girare due volte di fila non deve produrre
due commit, e il foglio non deve mai essere committato rotto."""
import os

import aggiorna
from ovalmo import dati, excel, orari, pagina

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_l_impronta_ignora_la_data_in_fondo():
    a = '<p class="fine">Dati aggiornati il 06/09/2026 alle 19:20 &middot; ecc</p>'
    b = '<p class="fine">Dati aggiornati il 07/09/2026 alle 08:00 &middot; ecc</p>'
    assert aggiorna.impronta_pagina(a) == aggiorna.impronta_pagina(b)


def test_l_impronta_si_accorge_di_un_punto_in_piu():
    a = '<td class="num-pt">9</td>Dati aggiornati il 06/09/2026 alle 19:20'
    b = '<td class="num-pt">12</td>Dati aggiornati il 06/09/2026 alle 19:20'
    assert aggiorna.impronta_pagina(a) != aggiorna.impronta_pagina(b)


def test_la_pagina_generata_due_volte_ha_la_stessa_impronta():
    stagione, pronostici = dati.carica()
    with open(os.path.join(QUI, "template.html"), encoding="utf-8") as f:
        template = f.read()
    uniti = dati.unisci(stagione, pronostici)
    una = pagina.genera(uniti, template, adesso=orari.quando("06/09/2026", "10:00"),
                        aggiornato=orari.quando("06/09/2026", "10:00"))
    due = pagina.genera(uniti, template, adesso=orari.quando("06/09/2026", "23:00"),
                        aggiornato=orari.quando("06/09/2026", "23:00"))
    assert aggiorna.impronta_pagina(una) == aggiorna.impronta_pagina(due)


def test_l_excel_si_genera_e_si_riapre_senza_formule_rotte(tmp_path):
    stagione, pronostici = dati.carica()
    percorso = str(tmp_path / "Trofeo_Ovalmo.xlsx")
    excel.genera(dati.unisci(stagione, pronostici), percorso)
    esito = excel.verifica(percorso)
    assert esito["formule"] > 100
    assert "Classifica" in esito["fogli"]


def test_l_excel_si_rifa_anche_quando_cambiano_solo_le_regole(tmp_path, monkeypatch):
    """E' successo due volte, il 12 e il 20 settembre 2026: le regole sono
    cambiate a risultati fermi. Senza questo, il file da scaricare sarebbe
    rimasto a quelle vecchie fino al primo gol della settimana dopo."""
    uniti = dati.unisci(*dati.carica())
    prima = aggiorna.impronta_excel(uniti)

    regola = tmp_path / "punteggio.py"
    regola.write_text("ESATTO = 3\n", encoding="utf-8")
    monkeypatch.setattr(aggiorna, "FILE_DELLE_REGOLE", [str(regola)])
    assert aggiorna.impronta_excel(uniti) != prima

    regola.write_text("ESATTO = 9\n", encoding="utf-8")
    dopo = aggiorna.impronta_excel(uniti)
    regola.write_text("ESATTO = 3\n", encoding="utf-8")
    assert aggiorna.impronta_excel(uniti) != dopo
