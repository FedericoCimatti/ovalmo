# -*- coding: utf-8 -*-
"""Calendario e risultati dall'API.

Il test piu' importante e' quello sulla numerazione: G03-01 deve restare la
stessa partita per sempre, anche quando i posticipi riordinano la giornata.
Se si muove, pronostici e risultati gia' archiviati cambiano significato.
"""
import pytest

from ovalmo import risultati, squadre


def partita(id_, giornata, utc, casa, ospite, stato="TIMED", gol=None):
    punteggio = {"fullTime": {"home": None, "away": None}}
    if gol:
        punteggio = {"fullTime": {"home": gol[0], "away": gol[1]}}
    return {"id": id_, "matchday": giornata, "utcDate": utc, "status": stato,
            "homeTeam": {"name": casa}, "awayTeam": {"name": ospite}, "score": punteggio}


def stagione_vuota():
    return {"prima_giornata": 3, "calendario": {}, "risultati": {}, "id_partite": {}}


GIORNATA_3 = [
    partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907"),
    partita(102, 3, "2026-09-05T13:00:00Z", "ACF Fiorentina", "Torino FC"),
    partita(103, 3, "2026-09-05T16:00:00Z", "FC Internazionale Milano", "SSC Napoli"),
]


def test_prima_importazione_numera_in_ordine_di_orario():
    s = stagione_vuota()
    risultati.aggiorna(s, GIORNATA_3)
    assert s["calendario"]["3"][0] == ["04/09/2026", "20:45", "Genoa", "Como"]
    assert s["calendario"]["3"][2] == ["05/09/2026", "18:00", "Inter", "Napoli"]
    assert s["id_partite"]["G03-01"] == 101


def test_un_posticipo_non_rinumera_la_giornata():
    s = stagione_vuota()
    risultati.aggiorna(s, GIORNATA_3)
    # Genoa-Como viene spostata in coda alla giornata: cambia la data, non il numero
    spostata = [partita(101, 3, "2026-09-07T18:45:00Z", "Genoa CFC", "Como 1907"),
                GIORNATA_3[1], GIORNATA_3[2]]
    note = risultati.aggiorna(s, spostata)
    assert s["calendario"]["3"][0] == ["07/09/2026", "20:45", "Genoa", "Como"]
    assert s["id_partite"]["G03-01"] == 101
    assert any("spostata" in n for n in note)


def test_i_pronostici_gia_dati_restano_sulla_partita_giusta():
    """La prova del nove: un pronostico agganciato a G03-01 deve continuare a
    riferirsi a Genoa-Como anche dopo che la giornata e' stata riordinata."""
    s = stagione_vuota()
    risultati.aggiorna(s, GIORNATA_3)
    prima = {mid: (s["calendario"]["3"][int(mid[-2:]) - 1][2:])
             for mid in ("G03-01", "G03-02", "G03-03")}
    riordinata = [GIORNATA_3[2], GIORNATA_3[1],
                  partita(101, 3, "2026-09-09T18:45:00Z", "Genoa CFC", "Como 1907")]
    risultati.aggiorna(s, riordinata)
    dopo = {mid: (s["calendario"]["3"][int(mid[-2:]) - 1][2:])
            for mid in ("G03-01", "G03-02", "G03-03")}
    assert prima == dopo


def test_il_risultato_arriva_solo_a_partita_finita():
    s = stagione_vuota()
    in_corso = [partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907",
                        stato="IN_PLAY", gol=(1, 0))] + GIORNATA_3[1:]
    risultati.aggiorna(s, in_corso)
    assert "G03-01" not in s["risultati"]

    finita = [partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907",
                      stato="FINISHED", gol=(1, 0))] + GIORNATA_3[1:]
    note = risultati.aggiorna(s, finita)
    assert s["risultati"]["G03-01"] == [1, 0]
    assert any("1-0" in n for n in note)


def test_partita_rinviata_resta_in_calendario_senza_risultato():
    s = stagione_vuota()
    rinviata = [partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907",
                        stato="POSTPONED")] + GIORNATA_3[1:]
    note = risultati.aggiorna(s, rinviata)
    assert "G03-01" not in s["risultati"]
    assert len(s["calendario"]["3"]) == 3
    assert any("recupero" in n for n in note)


def test_un_risultato_corretto_dall_api_viene_aggiornato():
    s = stagione_vuota()
    risultati.aggiorna(s, [partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907",
                                   stato="FINISHED", gol=(1, 0))] + GIORNATA_3[1:])
    note = risultati.aggiorna(s, [partita(101, 3, "2026-09-04T18:45:00Z", "Genoa CFC", "Como 1907",
                                          stato="FINISHED", gol=(2, 0))] + GIORNATA_3[1:])
    assert s["risultati"]["G03-01"] == [2, 0]
    assert any("corretto" in n for n in note)


def test_squadra_non_mappata_ferma_tutto_prima_di_scrivere():
    s = stagione_vuota()
    con_sconosciuta = GIORNATA_3 + [partita(104, 3, "2026-09-06T18:45:00Z", "Real Madrid CF", "SS Lazio")]
    with pytest.raises(squadre.SquadraSconosciuta):
        risultati.aggiorna(s, con_sconosciuta)
    assert s["calendario"] == {}      # non ha scritto niente a meta'


def test_si_tiene_la_giornata_in_corso_piu_una():
    partite = []
    for g in range(1, 8):
        stato = "FINISHED" if g < 4 else "TIMED"
        gol = (1, 0) if g < 4 else None
        partite.append(partita(g * 10, g, f"2026-09-{g:02d}T18:45:00Z",
                               "Genoa CFC", "Como 1907", stato=stato, gol=gol))
    # la 4 e' la prima non finita: si tengono la 3 (prima giornata del gioco), la 4 e la 5
    assert risultati.giornate_da_tenere(partite, 3) == [3, 4, 5]


def test_a_stagione_finita_non_si_inventa_una_giornata_39():
    partite = [partita(g * 10, g, f"2026-09-{g:02d}T18:45:00Z", "Genoa CFC", "Como 1907",
                       stato="FINISHED", gol=(1, 0)) for g in range(1, 6)]
    assert risultati.giornate_da_tenere(partite, 3) == [3, 4, 5]
