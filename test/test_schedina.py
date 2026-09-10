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


def test_nel_repository_non_ci_sono_codici_veri():
    """I codici vivono solo dentro lo script in Google. Questo repository e'
    pubblico: se un codice finisse qui, chiunque potrebbe mandare pronostici
    fingendosi qualcun altro. E' l'errore che abbiamo gia' fatto una volta."""
    import os
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(qui, "google", "ricevi_pronostici.gs"), encoding="utf-8") as f:
        script = f.read()
    codici = re.findall(r"'(\d{4})'", script)
    assert not codici, (
        f"nel file su GitHub ci sono dei codici veri: {codici}. Il repository e' pubblico: "
        f"i codici vanno solo nella copia dentro Google, qui devono restare i segnaposto XXXX")
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "codice" not in html or "io.codice" in html


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


def test_se_ha_mandato_una_persona_sola_si_usa_il_singolare():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {"Berta": "16/10/2026 18:00"}})
    html = schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)
    assert "Berta ha gi&agrave; mandato." in html
    assert "Hanno gi&agrave; mandato Berta" not in html
    assert "Mancano Lippi e Lenzuolo." in html
    assert "restano coperti" in html


def test_se_hanno_mandato_in_piu_si_torna_al_plurale():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {"Berta": "x", "Lippi": "x"}})
    html = schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)
    assert "Hanno gi&agrave; mandato Berta e Lippi." in html
    assert "Manca solo Lenzuolo." in html
    assert "Mancano Lenzuolo" not in html


def test_se_non_ha_mandato_nessuno_lo_dice():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]}, consegne={})
    assert "Non ha ancora mandato nessuno" in schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)


def test_quando_ci_sono_tutti_lo_dice():
    dati = dict(DATI, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {p: "x" for p in DATI["players"]}})
    assert "Hanno mandato tutti." in schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)


def test_coi_cinque_veri_si_dice_tutti_e_cinque():
    cinque = ["Berta", "Super Gulp", "Lenzuolo", "Just Lele", "Lippi"]
    dati = dict(DATI, players=cinque, calendario={"8": DATI["calendario"]["8"]},
                consegne={"8": {p: "x" for p in cinque}})
    assert "Hanno mandato tutti e cinque." in schedina.blocco(dati, adesso=PRIMA, endpoint=ENDPOINT)


def test_il_modulo_dice_che_non_si_puo_correggere():
    html = re.sub(r"\s+", " ", schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT))
    assert "non si pu&ograve; pi&ugrave; cambiare" in html
    assert "vedono che hai mandato, non che cosa hai scritto" in html


def test_c_e_il_pulsante_annulla_accanto_a_invia():
    """Annulla riporta alla schermata iniziale e obbliga a rimettere il codice:
    senza, la schedina resterebbe aperta sul telefono per giorni."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert 'id="annulla"' in html and 'id="invia"' in html
    assert "localStorage.removeItem(IO)" in html      # esce davvero
    assert "$('codice').value = ''" in html           # e ripulisce il codice


def test_dopo_l_invio_la_sezione_sparisce_tutta():
    """Non resta niente: ne' istruzioni, ne' nomi, ne' pulsanti. Ricompare da
    sola alla giornata successiva."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "chiaveInviato" in html
    assert "function chiudiModulo(){" in html
    assert "pezzo.hidden = chiuso" in html
    assert 'id="fatto"' not in html and 'id="esci"' not in html


def test_il_codice_si_verifica_prima_di_aprire_la_schedina():
    """Il buco che c'era: bastavano quattro cifre qualsiasi per aprire la
    schedina di chiunque. Ora il codice viene chiesto allo script in Google
    prima di far entrare."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "azione: 'controlla'" in html
    assert "sbagliato('Codice sbagliato.')" in html
    # e non si entra piu' solo perche' sono quattro cifre
    fra = html[html.index("$('entra').onclick"):html.index("$('annulla').onclick")]
    assert fra.index("verifica(scelto, codice)") < fra.index("scrivi(IO,")


def test_il_codice_si_ricontrolla_anche_a_pagina_riaperta():
    """La memoria del telefono non basta: chi fosse entrato una volta con un
    codice sbagliato resterebbe dentro per sempre."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    coda = html[html.index("var io = leggi(IO);"):]
    assert "verifica(io.nome, io.codice)" in coda
    assert "else esci()" in coda


def test_c_e_il_trattino_fra_le_due_caselle_dei_gol():
    """Senza, non si capisce che quelle due caselle sono un risultato."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert html.count('<span class="tra">&ndash;</span>') == 2   # una per partita
    fra = html[html.index('data-p="P01"'):html.index('data-p="P02"')]
    assert fra.index('class="gol"') < fra.index('class="tra"') < fra.rindex('class="gol"')


def test_non_c_e_piu_il_pulsante_esci():
    """Sparisce con tutta la sezione: dopo l'invio non c'e' piu' niente da fare."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "Esci" not in html
    assert 'id="annulla"' in html          # Annulla resta: serve PRIMA di mandare


def test_chi_ha_gia_mandato_non_rivede_la_schermata_di_compilazione():
    """Sparisce la sezione intera: non c'e' piu' niente da fare fino alla
    giornata dopo."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "mostraMie(); chiudiModulo();" in html
    # e annullando prima di mandare si torna a vedere tutto
    fra = html[html.index("function esci()"):html.index("$('annulla').onclick")]
    assert "apriModulo();" in fra


def test_il_proprio_pronostico_prende_il_posto_della_propria_spunta():
    """Nella schedina coperta ognuno rivede il suo, degli altri resta la spunta."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "function mostraMie()" in html
    assert "data-coperta" in html                  # tocca solo le giornate coperte
    assert "cella.dataset.mio = '1'" in html       # e la diretta non lo ricopre


def test_i_pronostici_altrui_non_sono_da_nessuna_parte_nel_modulo():
    """mostraMie legge solo la memoria di questo telefono: nel sito i pronostici
    coperti non ci sono, e nessuno puo' chiederli allo script."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "leggi(BOZZA)" in html
    assert "azione: 'mie'" not in html


def test_chi_ha_gia_mandato_non_dipende_dalla_rete():
    """Aprire la schedina richiede il codice, e quindi la rete. Ma a chi ha gia'
    mandato non si deve aprire niente: se si chiedesse comunque il codice, con
    la rete assente la sezione resterebbe li' aperta a chiedere di mandare una
    schedina gia' mandata."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    coda = html[html.index("var io = leggi(IO);"):]
    assert "if(io && io.nome && leggi(chiaveInviato(io.nome)))" in coda
    assert coda.index("chiaveInviato") < coda.index("verifica(io.nome")


def test_si_aspetta_che_la_pagina_sia_pronta():
    """Lo script del modulo sta piu' in alto delle schede delle partite: al
    caricamento quelle caselle non esistono ancora."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "document.readyState === 'loading'" in html
    assert "DOMContentLoaded" in html


def test_sparisce_anche_l_invito_dentro_la_schedina():
    """Il pulsante "Manda i tuoi pronostici" dentro la schedina e la sezione del
    modulo sono la stessa cosa detta in due punti: chi ha mandato non deve
    trovarsi ne' l'una ne' l'altro."""
    html = schedina.blocco(DATI, adesso=PRIMA, endpoint=ENDPOINT)
    assert "['modulo', 'invito']" in html
