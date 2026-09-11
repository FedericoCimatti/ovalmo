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


def test_la_pagina_si_porta_dietro_tutte_le_partite_da_giocare():
    """Quali seguire lo decide il browser mentre gira. Se lo decidesse questo
    file, una pagina rigenerata alle 16 non saprebbe di dover seguire la
    partita delle 21 - ed e' esattamente quello che e' successo il 7 settembre,
    quando GitHub ha saltato quasi tutti i giri."""
    d = cfg(diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT))
    assert set(d["partite"]) == {"G07-01", "G07-02", "G08-01", "G08-02"}
    assert d["partite"]["G07-01"]["inizio"].startswith("2026-10-10T20:45")


def test_il_ritmo_lo_decide_il_browser():
    d = cfg(diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT))
    assert d["ogniInGioco"] == diretta.OGNI_IN_GIOCO
    assert d["ogniARiposo"] == diretta.OGNI_A_RIPOSO
    html = diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT)
    assert "aperteAdesso()" in html


def test_ogni_partita_porta_con_se_squadre_e_orario():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["partite"]["G07-01"]["casa"] == "Inter"
    assert d["partite"]["G07-01"]["ospite"] == "Milan"


def test_porta_con_se_i_totali_gia_calcolati():
    """I conti veri restano in Python: la diretta somma solo il di piu'."""
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["base"] == {"Berta": {"pt": 0, "esatti": 0}, "Lippi": {"pt": 0, "esatti": 0}}


def test_i_pronostici_di_una_giornata_iniziata_servono_ai_conti():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["picks"]["G07-01"]["Berta"] == ["1", 2, 1]


def test_i_pronostici_coperti_non_finiscono_nella_diretta():
    """Prima del calcio d'inizio non deve uscire niente, nemmeno da qui."""
    prima = orari.quando("10/10/2026", "20:00")    # un'ora prima del fischio
    html = diretta.blocco(DATI, adesso=prima, endpoint=ENDPOINT)
    d = cfg(html)
    assert d["partite"], "la partita imminente dovrebbe essere nell'elenco"
    assert d["picks"] == {}
    assert "2, 1" not in html and '"1", 2' not in html


def test_traduce_i_nomi_dell_api():
    d = cfg(diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT))
    assert d["squadre"]["FC Internazionale Milano"] == "Inter"
    assert d["squadre"]["AC Milan"] == "Milan"
    assert "Hellas Verona FC" not in d["squadre"], "solo le squadre di questa stagione"


def test_una_partita_senza_risultato_resta_nell_elenco_anche_dopo():
    """Se il risultato non e' ancora stato scritto - rinvio, o GitHub fermo -
    la partita resta seguibile: e' il browser a smettere di guardarla."""
    tardi = orari.quando("11/10/2026", "03:00")
    assert "G07-01" in cfg(diretta.blocco(DATI, adesso=tardi, endpoint=ENDPOINT))["partite"]


def test_una_partita_col_risultato_gia_scritto_non_si_segue_piu():
    dati = dict(DATI, risultati={"G07-01": [2, 1]})
    d = cfg(diretta.blocco(dati, adesso=DURANTE, endpoint=ENDPOINT))
    assert "G07-01" not in d["partite"]


def test_i_conti_in_diretta_coincidono_con_quelli_veri():
    """L'invariante che tiene in piedi tutto: la classifica in diretta e' i
    totali calcolati da Python piu' i punti delle partite ancora aperte. Quando
    il giro orario scrivera' quei risultati, i due numeri devono coincidere,
    altrimenti la classifica "salterebbe" a ogni aggiornamento."""
    from ovalmo.punteggio import calcola, punti_partita

    in_corso = orari.quando("10/10/2026", "21:30")
    d = cfg(diretta.blocco(DATI, adesso=in_corso, endpoint=ENDPOINT))
    gol = [2, 1]        # com'e' finita davvero Inter-Milan

    # quello che farebbe la diretta nel browser: base + i punti di adesso,
    # punti coraggio compresi (siamo in giornata 7, la regola e' in vigore)
    adesso_g = punti_partita(d["picks"]["G07-01"], gol, 7, DATI["players"])
    live = {g: d["base"][g]["pt"] + adesso_g[g] for g in DATI["players"]}

    # quello che fara' Python quando il risultato sara' scritto nel JSON
    dopo = dict(DATI, risultati={"G07-01": gol})
    vero = {g: calcola(dopo)["stats"][g]["pt"] for g in DATI["players"]}

    # Berta aveva scritto 2-1 e nessun altro: risultato esatto da solo, 6
    assert live == vero == {"Berta": 6, "Lippi": 0}
    assert d["coraggioDa"] == 5


def test_c_e_la_prova_di_vita_in_fondo_alla_pagina():
    """La data in fondo dice quando i dati sono cambiati, non se il sistema e'
    vivo: puo' restare ferma per giorni legittimamente. La diretta ci scrive
    accanto l'ora dell'ultimo contatto con Google."""
    html = diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT)
    assert "disegnaControllo(stato.adesso" in html
    assert "getElementById('controllato')" in html


def test_anche_le_spunte_si_aggiornano_in_diretta():
    """La riga "hanno gia' mandato" e le spunte accanto ai nomi dicono la
    stessa cosa: non possono aggiornarsi a velocita' diverse."""
    html = diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT)
    assert "spunte(g, chi)" in html
    assert "data-coperta=" in html
    assert "sg-lock" in html and "sg-tbd" in html


def test_la_diretta_usa_le_stesse_parole_del_generatore():
    """La riga la scrivono in due: Python quando rigenera la pagina, la diretta
    quando arriva qualcuno di nuovo. Se dicessero parole diverse, la frase
    cambierebbe da sola sotto gli occhi di chi guarda."""
    js = diretta.blocco(DATI, adesso=LONTANO, endpoint=ENDPOINT)
    for pezzo in ["Non ha ancora mandato nessuno.", "Hanno mandato tutti e cinque.",
                  "Hanno mandato tutti.", "ha già mandato.", "Hanno già mandato ",
                  "Manca solo ", "Mancano ",
                  "Si sa solo chi ha consegnato: i pronostici restano coperti."]:
        assert pezzo in js, pezzo


def test_la_diretta_sa_da_che_giornata_valgono_i_punti_coraggio():
    """La regola dei punti coraggio e' scritta due volte: in punteggio.py per i conti
    veri e dentro la diretta per quelli in corso. Se si tocca una, va toccata
    l'altra - e almeno la giornata di partenza qui viene dalla stessa costante,
    non da un numero ricopiato a mano."""
    from ovalmo.punteggio import CORAGGIO_DA

    html = diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT)
    assert "function puntiPartita(" in html
    assert "giornata >= D.coraggioDa" in html
    assert cfg(html)["coraggioDa"] == CORAGGIO_DA


def test_la_diretta_colora_le_caselle_con_gli_stessi_metalli_della_pagina():
    """La mappa dei metalli viaggia nella configurazione: se pagina e diretta ne
    tenessero due copie, durante le partite una casella potrebbe cambiare colore
    e poi tornare indietro al primo aggiornamento del sito."""
    from ovalmo.pagina import MEDAGLIE

    html = diretta.blocco(DATI, adesso=DURANTE, endpoint=ENDPOINT, medaglie=MEDAGLIE)
    assert cfg(html)["medaglie"] == {str(k): v for k, v in MEDAGLIE.items()}
    assert "D.medaglie[valore]" in html
