# -*- coding: utf-8 -*-
"""Fuso orario: la fonte di bug silenziosi che nessuno vede finche' non sbaglia
una deadline. L'API parla UTC, il gioco ragiona in ora di Roma."""
from datetime import datetime

import pytest

from ovalmo import orari

CAL = {
    2: [["28/08/2026", "20:45", "Milan", "Venezia"],
        ["29/08/2026", "18:30", "Fiorentina", "Frosinone"]],
    3: [["04/09/2026", "20:45", "Genoa", "Como"],
        ["05/09/2026", "15:00", "Fiorentina", "Torino"]],
}


def test_ora_legale_due_ore_avanti():
    assert orari.in_italiano(orari.da_utc("2026-09-05T16:00:00Z")) == ("05/09/2026", "18:00")


def test_ora_solare_una_ora_avanti():
    assert orari.in_italiano(orari.da_utc("2026-12-05T16:00:00Z")) == ("05/12/2026", "17:00")


def test_il_cambio_dell_ora_e_gestito_dal_fuso_non_a_mano():
    # ultima domenica di ottobre 2026: il 24 e' ancora ora legale, il 26 e' solare
    assert orari.in_italiano(orari.da_utc("2026-10-24T13:00:00Z"))[1] == "15:00"
    assert orari.in_italiano(orari.da_utc("2026-10-26T13:00:00Z"))[1] == "14:00"


def test_partita_di_sera_non_scivola_al_giorno_dopo():
    # 20:45 italiane in inverno sono le 19:45 UTC: la data deve restare quella
    assert orari.in_italiano(orari.da_utc("2026-12-20T19:45:00Z")) == ("20/12/2026", "20:45")


def test_partita_a_mezzanotte_utc_e_ancora_il_giorno_prima_in_italia():
    assert orari.in_italiano(orari.da_utc("2026-09-06T23:30:00Z"))[0] == "07/09/2026"


def test_ora_ignota_vale_mezzanotte_cioe_la_deadline_piu_prudente():
    assert orari.quando("05/09/2026", "da definire").hour == 0
    assert orari.quando("05/09/2026", "").hour == 0


def test_giornata_dedotta_dal_timestamp():
    prima = orari.quando("28/08/2026", "18:00")     # prima della giornata 2
    assert orari.giornata_del_timestamp(CAL, prima) == 2


def test_invio_dopo_il_calcio_dinizio_scivola_alla_giornata_dopo():
    # e' il meccanismo che scarta i ritardatari: la verifica delle intestazioni
    # poi si accorge che il modulo non e' quello della giornata 3 e non importa
    dopo = orari.quando("28/08/2026", "21:00")
    assert orari.giornata_del_timestamp(CAL, dopo) == 3


def test_un_minuto_prima_del_fischio_vale_ancora():
    assert orari.giornata_del_timestamp(CAL, orari.quando("28/08/2026", "20:44")) == 2


def test_allo_scoccare_del_fischio_e_troppo_tardi():
    assert orari.giornata_del_timestamp(CAL, orari.quando("28/08/2026", "20:45")) == 3


def test_nessuna_giornata_dopo_lultima():
    assert orari.giornata_del_timestamp(CAL, orari.quando("30/12/2026", "12:00")) is None


def test_copertura_cade_al_primo_calcio_dinizio():
    assert orari.coperta(CAL, 3, orari.quando("04/09/2026", "20:44")) is True
    assert orari.coperta(CAL, 3, orari.quando("04/09/2026", "20:45")) is False


def test_la_copertura_guarda_la_prima_partita_non_la_prima_in_elenco():
    calendario = {1: [["10/01/2027", "20:45", "A", "B"], ["09/01/2027", "15:00", "C", "D"]]}
    # l'anticipo del 9 e' il vero calcio d'inizio, anche se e' secondo in elenco
    assert orari.coperta(calendario, 1, orari.quando("09/01/2027", "16:00")) is False


def test_quando_restituisce_sempre_un_orario_con_fuso():
    assert orari.quando("05/09/2026", "18:00").tzinfo is not None


# ------------------------------------------------ l'ordine vero, quello del campo
SPOSTATE = [["12/09/2026", "15:00", "Genoa", "Frosinone"],      # 1
            ["13/09/2026", "20:45", "Sassuolo", "Juventus"],    # 2, posticipo
            ["12/09/2026", "20:45", "Atalanta", "Cagliari"],    # 3, spostata qui dopo
            ["12/09/2026", "18:00", "Lazio", "Milan"]]          # 4


def test_le_partite_si_rimettono_in_ordine_di_campo():
    """Il calendario salvato non cambia mai ordine, gli orari si spostano di
    continuo: Atalanta-Cagliari si gioca prima di Sassuolo-Juventus ma sta
    scritta dopo. Si riordinano i numeri, non le righe."""
    assert orari.ordine_cronologico(SPOSTATE) == [1, 4, 3, 2]


def test_riordinare_non_sposta_le_righe():
    """Il numero e' il nome della partita: dietro al 3 deve restare l'Atalanta."""
    prima = [list(r) for r in SPOSTATE]
    ordine = orari.ordine_cronologico(SPOSTATE)
    assert SPOSTATE == prima
    assert SPOSTATE[ordine[2] - 1][2] == "Atalanta"


def test_si_possono_ordinare_solo_le_prime():
    """Se la giornata ha piu' partite di quante ne gioca il gruppo, le altre
    restano fuori: non entrano dalla porta di servizio dell'ordinamento."""
    assert orari.ordine_cronologico(SPOSTATE, 2) == [1, 2]


def test_senza_orario_si_gioca_all_inizio_del_giorno():
    cal = [["13/09/2026", "18:00", "Como", "Parma"],
           ["13/09/2026", "", "Torino", "Roma"]]
    assert orari.ordine_cronologico(cal) == [2, 1]


def test_a_parita_di_orario_vince_il_numero_piu_basso():
    """Due partite alla stessa ora non devono ballare da un giro all'altro."""
    cal = [["13/09/2026", "15:00", "Como", "Parma"],
           ["13/09/2026", "15:00", "Torino", "Roma"],
           ["13/09/2026", "15:00", "Lecce", "Monza"]]
    assert orari.ordine_cronologico(cal) == [1, 2, 3]
