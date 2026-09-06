# -*- coding: utf-8 -*-
"""Il modulo dei pronostici dentro la pagina."""
import json
import re

from ovalmo import orari, schedina

DATI = {
    "players": ["Berta", "Lippi", "Lenzuolo"],
    "partite_per_giornata": 3,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"]],
                   "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                         ["18/10/2026", "15:00", "Genoa", "Parma"]]},
    "risultati": {},
    "pronostici": {"G07-01": {"Berta": ["1", 3, 0]}},
    "consegne": {"7": {"Berta": "09/10/2026 18:00"}},
}
ENDPOINT = "https://script.google.com/macros/s/ABC/exec"
PRIMA = orari.quando("09/10/2026", "12:00")
DOPO = orari.quando("10/10/2026", "21:00")


def test_giornata_aperta_e_la_prima_non_iniziata():
    cal = {int(k): v for k, v in DATI["calendario"].items()}
    assert schedina.giornata_aperta(cal, PRIMA) == 7
    assert schedina.giornata_aperta(cal, DOPO) == 8


def test_niente_da_pronosticare_a_stagione_finita():
    cal = {int(k): v for k, v in DATI["calendario"].items()}
    assert schedina.giornata_aperta(cal, orari.quando("01/12/2026", "12:00")) is None


def test_mostra_le_partite_della_giornata_aperta():
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "giornata 7" in html
    assert "Inter" in html and "Milan" in html
    assert "Napoli" not in html          # la giornata 8 non e' ancora aperta
    assert html.count('class="riga"') == 2


def test_il_modulo_non_lascia_trapelare_i_pronostici_degli_altri():
    """Sulla pagina il modulo e' pubblico: non deve contenere nessun pronostico,
    nemmeno quelli di chi ha gia' mandato."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert '"1", 3, 0' not in html and "3-0" not in html


def test_i_codici_dei_giocatori_non_finiscono_nella_pagina():
    """I codici vivono solo dentro lo script in Google. Se uno finisse nella
    pagina sarebbe pubblico su internet, e chiunque potrebbe mandare pronostici
    fingendosi qualcun altro."""
    import os
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(qui, "google", "ricevi_pronostici.gs"), encoding="utf-8") as f:
        script = f.read()
    codici = re.findall(r"':\s*'(\d{4})'", script) + re.findall(r"'(\d{4})'", script)
    assert codici, "non ho trovato nessun codice nello script: il test non sta controllando niente"
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    trovati = [c for c in set(codici) if c in html]
    assert not trovati, f"codici finiti nella pagina: {trovati}"


def test_senza_endpoint_si_ripiega_sul_modulo_google():
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint="", modulo_google="https://forms.gle/x")
    assert "https://forms.gle/x" in html
    assert 'id="schedina"' not in html


def test_la_scadenza_e_il_primo_calcio_dinizio():
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "10/10 alle 20:45" in html
    cfg = json.loads(re.search(r"var CFG = (\{.*?\}), PARTITE", html, re.S).group(1))
    assert cfg["scadenza"].startswith("2026-10-10T20:45")
    assert cfg["giornata"] == 7


def test_dopo_il_fischio_il_modulo_passa_alla_giornata_dopo():
    html = schedina.blocco(DATI, adesso=DOPO, endpoint=ENDPOINT)
    assert "giornata 8" in html and "Napoli" in html
    assert "Inter" not in html


def test_il_modulo_dice_chi_ha_gia_mandato_senza_dire_cosa():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {"Berta": "16/10/2026 18:00"}})
    html = schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)
    assert "Hanno gi&agrave; mandato Berta" in html
    assert "Mancano Lippi e Lenzuolo" in html
    assert "restano coperti" in html


def test_se_non_ha_mandato_nessuno_lo_dice():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]}, consegne={})
    assert "Non ha ancora mandato nessuno" in schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)


def test_quando_ci_sono_tutti_lo_dice():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {p: "x" for p in DATI["players"]}})
    assert "tutti e cinque" in schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)
