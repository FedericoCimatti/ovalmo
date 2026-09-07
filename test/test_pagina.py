# -*- coding: utf-8 -*-
"""La copertura dei pronostici: la regola piu' importante del gioco.

Finche' la giornata non e' iniziata, la pagina non deve lasciar trapelare
NIENTE dei pronostici di nessuno: chi ha mandato si vede solo dalla spunta.
"""
import os
import re

import pytest

from ovalmo import orari, pagina

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(QUI, "template.html"), encoding="utf-8") as f:
    TEMPLATE = f.read()

DATI = {
    "players": ["Berta", "Lippi", "Lenzuolo"],
    "partite_per_giornata": 2,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"]]},
    "risultati": {},
    "pronostici": {"G07-01": {"Berta": ["1", 3, 0], "Lippi": ["2", 0, 1]},
                   "G07-02": {"Berta": ["X", 1, 1], "Lippi": ["1", 2, 0]}},
    "consegne": {"7": {"Berta": "09/10/2026 18:00", "Lippi": "09/10/2026 19:30"}},
}

PRIMA = orari.quando("10/10/2026", "12:00")     # coperta
DOPO = orari.quando("10/10/2026", "21:00")      # svelata


def genera(dati, quando):
    return pagina.genera(dati, TEMPLATE, adesso=quando, aggiornato=quando)


def test_prima_del_fischio_nessun_pronostico_trapela():
    html = genera(DATI, PRIMA)
    schedina = html[html.index("La schedina"):]
    assert 'sg-1' not in schedina and 'sg-2' not in schedina and 'sg-x' not in schedina
    assert "3&ndash;0" not in schedina and "0&ndash;1" not in schedina


def test_prima_del_fischio_la_spunta_dice_chi_ha_mandato():
    html = genera(DATI, PRIMA)
    schedina = html[html.index("La schedina"):]
    assert schedina.count("sg-lock") == 4        # 2 giocatori x 2 partite
    assert schedina.count("sg-tbd") == 2         # Lenzuolo non ha mandato


def test_prima_del_fischio_si_dice_chi_manca():
    html = genera(DATI, PRIMA)
    assert "Mancano ancora i pronostici di Lenzuolo" in html
    assert "si svela al primo calcio d" in html


def test_al_fischio_i_pronostici_si_svelano():
    html = genera(DATI, DOPO)
    schedina = html[html.index("La schedina"):]
    assert "sg-1" in schedina and "sg-2" in schedina
    assert "3&ndash;0" in schedina
    assert "sg-lock" not in schedina


def test_la_spunta_funziona_anche_senza_i_pronostici_nel_file():
    """E' il caso vero: prima del fischio i pronostici NON sono nel repository,
    ci sono solo le consegne. La spunta deve funzionare lo stesso."""
    senza = dict(DATI, pronostici={})
    html = genera(senza, PRIMA)
    schedina = html[html.index("La schedina"):]
    assert schedina.count("sg-lock") == 4
    assert schedina.count("sg-tbd") == 2


def test_chi_non_ha_consegnato_resta_tbd_anche_dopo_il_fischio():
    html = genera(DATI, DOPO)
    schedina = html[html.index("La schedina"):]
    assert "sg-tbd" in schedina                  # Lenzuolo


def test_le_giornate_in_archivio_si_vedono_sempre_per_intero():
    dati = dict(DATI, risultati={"G07-01": [2, 1], "G07-02": [0, 0]},
                calendario={**DATI["calendario"],
                            "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                                  ["18/10/2026", "15:00", "Genoa", "Parma"]]})
    html = genera(dati, orari.quando("15/10/2026", "12:00"))
    assert "Giornate precedenti" in html
    archivio = html[html.index("Giornate precedenti"):]
    assert "3&ndash;0" in archivio               # i pronostici della 7 si vedono
    assert "re della giornata" in archivio


def test_l_unanimita_non_si_annuncia_mentre_e_coperta():
    tutti_uguali = dict(DATI, pronostici={
        "G07-01": {p: ["1", 1, 0] for p in DATI["players"]},
        "G07-02": {p: ["1", 1, 0] for p in DATI["players"]}})
    assert "stesso segno" not in genera(tutti_uguali, PRIMA)
    assert "stesso segno" in genera(tutti_uguali, DOPO)


def test_avviso_dati_fermi_solo_se_ci_sono_partite_senza_risultato():
    html = genera(DATI, PRIMA)
    assert "Inter-Milan" in html                 # finisce nell'elenco delle attese
    finito = dict(DATI, risultati={"G07-01": [2, 1], "G07-02": [0, 0]})
    html = genera(finito, DOPO)
    assert "var attese = []" in html             # niente da segnalare


def test_nessun_segnaposto_rimasto():
    html = genera(DATI, PRIMA)
    assert not re.search(r"__[A-Z_]+__", html)


def test_classifica_in_cima_alla_pagina():
    dati = dict(DATI, risultati={"G07-01": [3, 0], "G07-02": [1, 1]})
    html = genera(dati, DOPO)
    # Berta: 3 + 3 = 6 punti, in testa
    assert "in testa Berta con 6 punti" in html


def test_le_giornate_in_archivio_sono_tutte_chiuse():
    """Nessuna giornata precedente si apre da sola: la pagina si apre sulla
    classifica e sulla giornata in corso, il resto lo si apre se si vuole."""
    dati = dict(DATI, risultati={"G07-01": [2, 1], "G07-02": [0, 0]},
                calendario={**DATI["calendario"],
                            "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                                  ["18/10/2026", "15:00", "Genoa", "Parma"]]})
    html = genera(dati, orari.quando("15/10/2026", "12:00"))
    assert "<details class=\"g\">" in html
    assert "<details class=\"g\" open>" not in html and " open>" not in html


def test_una_partita_di_oggi_si_legge_oggi():
    adesso = orari.quando("10/10/2026", "09:00")
    assert pagina.quando_si_gioca("10/10/2026", "20:45", adesso) == "Oggi 20:45"


def test_una_partita_di_domani_si_legge_domani():
    adesso = orari.quando("10/10/2026", "09:00")
    assert pagina.quando_si_gioca("11/10/2026", "15:00", adesso) == "Domani 15:00"


def test_piu_in_la_si_legge_giorno_e_mese():
    adesso = orari.quando("10/10/2026", "09:00")
    assert pagina.quando_si_gioca("14/10/2026", "18:30", adesso) == "14/10 18:30"
    assert "2026" not in pagina.quando_si_gioca("14/10/2026", "18:30", adesso)


def test_una_partita_rinviata_mostra_la_sua_data():
    adesso = orari.quando("12/10/2026", "09:00")
    assert pagina.quando_si_gioca("10/10/2026", "20:45", adesso) == "10/10 20:45"


def test_orario_non_ancora_deciso():
    adesso = orari.quando("10/10/2026", "09:00")
    assert pagina.quando_si_gioca("17/10/2026", "da definire", adesso) == "17/10 &middot; orario ancora da definire"


def test_la_schedina_mostra_il_giorno_delle_partite_da_giocare():
    html = genera(DATI, orari.quando("09/10/2026", "12:00"))
    assert "Domani 20:45" in html          # Inter-Milan, 10/10
    assert "11/10 15:00" in html           # Roma-Lazio, dopodomani


def test_la_pagina_si_ricarica_quando_ne_esiste_una_piu_nuova():
    """Il browser tiene in memoria la pagina vecchia e sembra che il sito sia
    fermo. La pagina controlla da sola e si ricarica."""
    quando = orari.quando("09/10/2026", "12:00")
    html = genera(DATI, quando)
    assert 'var MIA = "Dati aggiornati il 09/10/2026 alle 12:00"' in html
    assert "location.reload()" in html
    assert "stoCompilando" in html          # mai mentre uno sta scrivendo


def test_due_pagine_a_ore_diverse_restano_indistinguibili_per_l_impronta():
    """La data compare ora in due punti (il piede e il controllo automatico):
    l'impronta deve neutralizzarli entrambi, altrimenti si farebbe un commit
    ogni ora anche senza novita'."""
    import aggiorna
    una = genera(DATI, orari.quando("09/10/2026", "12:00"))
    due = genera(DATI, orari.quando("09/10/2026", "23:00"))
    assert aggiorna.impronta_pagina(una) == aggiorna.impronta_pagina(due)
