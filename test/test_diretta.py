# -*- coding: utf-8 -*-
"""La diretta: i gol e i punti che si muovono mentre si gioca."""
import json
import re

from ovalmo import diretta, orari

ENDPOINT = "https://script.google.com/macros/s/ABC/exec"
DATI = {
    "players": ["Berta", "Lippi"],
    "partite_per_giornata": 2,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"]],
                   "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                         ["18/10/2026", "15:00", "Genoa", "Parma"]]},
    "risultati": {},
    "pronostici": {"G07-01": {"Berta": ["1", 2, 1], "Lippi": ["2", 0, 1]}},
    "consegne": {"7": {"Berta": "x", "Lippi": "x"}},
}
DURANTE = orari.quando("10/10/2026", "21:30")     # Inter-Milan in corso
LONTANO = orari.quando("08/10/2026", "12:00")     # due giorni prima


def cfg(html):
    return json.loads(re.search(r"var D = (\{.*?\});\n", html, re.S).group(1))


def test_senza_endpoint_niente_diretta():
    assert diretta.blocco(DATI, adesso=DURANTE, endpoint="") == ""


def test_senza_partite_in_corso_niente_diretta():
    """Di martedi' non c'e' niente da seguire: la pagina non chiama nessuno."""
    assert diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT) == ""


def test_segue_solo_le_partite_di_adesso():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert list(d["aperte"]) == ["G07-01"]
    assert d["aperte"]["G07-01"]["casa"] == "Inter"


def test_porta_con_se_i_totali_gia_calcolati():
    """I conti veri restano in Python: la diretta somma solo il di piu'."""
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["base"] == {"Berta": {"pt": 0, "esatti": 0}, "Lippi": {"pt": 0, "esatti": 0}}


def test_i_pronostici_di_una_giornata_iniziata_servono_ai_conti():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["picks"]["G07-01"]["Berta"] == ["1", 2, 1]


def test_i_pronostici_coperti_non_finiscono_nella_diretta():
    """Prima del calcio d'inizio non deve uscire niente, nemmeno da qui."""
    prima = orari.quando("10/10/2026", "20:00")    # un'ora prima: partita gia' "aperta"
    html = diretta.blocco(DATI, adesso=prima, endpoint=ENDPOINT)
    d = cfg(html)
    assert d["aperte"], "la partita imminente dovrebbe essere seguita"
    assert d["picks"] == {}
    assert "2, 1" not in html and '"1", 2' not in html


def test_traduce_i_nomi_dell_api():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["squadre"]["FC Internazionale Milano"] == "Inter"
    assert d["squadre"]["AC Milan"] == "Milan"
    assert "Hellas Verona FC" not in d["squadre"], "solo le squadre di questa stagione"


def test_smette_di_seguire_una_partita_finita_da_un_pezzo():
    tardi = orari.quando("11/10/2026", "03:00")     # sei ore dopo il fischio d'inizio
    assert "G07-01" not in diretta.blocco(DATI, adesso=tardi, endpoint=ENDPOINT)


def test_una_partita_col_risultato_gia_scritto_non_si_segue_piu():
    dati = dict(DATI, risultati={"G07-01": [2, 1]})
    assert diretta.blocco(dati, adesso=DURANTE, endpoint=ENDPOINT) == ""


def test_i_conti_in_diretta_coincidono_con_quelli_veri():
    """L'invariante che tiene in piedi tutto: la classifica in diretta e' i
    totali calcolati da Python piu' i punti delle partite ancora aperte. Quando
    il giro orario scrivera' quei risultati, i due numeri devono coincidere,
    altrimenti la classifica "salterebbe" a ogni aggiornamento."""
    from ovalmo.punteggio import calcola, punti

    in_corso = orari.quando("10/10/2026", "21:30")
    d = cfg(diretta.blocco(DATI, adesso=in_corso, endpoint=ENDPOINT))
    gol = [2, 1]        # com'e' finita davvero Inter-Milan

    # quello che farebbe la diretta nel browser: base + i punti di adesso
    live = {g: d["base"][g]["pt"] + punti(d["picks"]["G07-01"].get(g), gol)
            for g in DATI["players"]}

    # quello che fara' Python quando il risultato sara' scritto nel JSON
    dopo = dict(DATI, risultati={"G07-01": gol})
    vero = {g: calcola(dopo)["stats"][g]["pt"] for g in DATI["players"]}

    assert live == vero == {"Berta": 3, "Lippi": 0}
