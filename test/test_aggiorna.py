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
