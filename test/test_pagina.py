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
    # Berta indovina tutti e due i risultati esatti, e in tutti e due e' l'unica
    # ad averli scritti: siamo in giornata 7, quindi 6 + 6
    assert "in testa Berta con 12 punti" in html


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


def test_il_piede_di_pagina_ha_il_posto_per_la_prova_di_vita():
    html = genera(DATI, orari.quando("09/10/2026", "12:00"))
    assert 'Dati aggiornati il 09/10/2026 alle 12:00<span id="controllato"></span>' in html


def test_le_carte_coperte_si_riconoscono():
    """Servono alla diretta per sapere dove mettere le spunte."""
    coperta = genera(DATI, PRIMA)
    assert 'data-coperta="7"' in coperta
    svelata = genera(DATI, DOPO)
    assert "data-coperta=" not in svelata


# ---------------------------------------------------------------- rinvii
RINVIO = {
    "players": ["Berta", "Lippi"],
    "partite_per_giornata": 3,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],
                         ["11/10/2026", "15:00", "Roma", "Lazio"],
                         ["24/10/2026", "18:00", "Genoa", "Como"]],   # rinviata
                   "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                         ["18/10/2026", "15:00", "Genoa", "Parma"],
                         ["18/10/2026", "18:00", "Lecce", "Monza"]]},
    "risultati": {"G07-01": [2, 1], "G07-02": [0, 0]},                # le altre due giocate
    "pronostici": {"G07-01": {"Berta": ["1", 2, 1], "Lippi": ["2", 0, 1]}},
    "consegne": {"7": {"Berta": "x", "Lippi": "x"}},
}
DOPO_LA_SETTE = orari.quando("12/10/2026", "12:00")     # giornata 7 finita, resta il recupero


def test_un_rinvio_non_blocca_il_sito_sulla_giornata():
    """Senza questo, una partita rinviata al 24 terrebbe la schedina ferma
    sulla giornata 7 per due settimane."""
    html = genera(RINVIO, DOPO_LA_SETTE)
    assert "La schedina &mdash; giornata 8" in html
    assert "Giornate precedenti" in html


def test_al_posto_del_re_si_dice_che_manca_una_partita():
    html = genera(RINVIO, DOPO_LA_SETTE)
    archivio = html[html.index("Giornate precedenti"):]
    assert "da recuperare" in archivio
    assert "Genoa&ndash;Como" in archivio
    assert "re della giornata" not in archivio


def test_col_recupero_giocato_torna_il_re():
    dati = dict(RINVIO, risultati={**RINVIO["risultati"], "G07-03": [1, 0]})
    html = genera(dati, orari.quando("25/10/2026", "12:00"))
    archivio = html[html.index("Giornate precedenti"):]
    assert "re della giornata" in archivio
    assert "da recuperare" not in archivio


def test_una_partita_che_doveva_giocarsi_e_non_ha_risultato_blocca_ancora():
    """Diverso dal rinvio: se una partita di ieri non ha il risultato, qualcosa
    non ha funzionato e la giornata non e' finita."""
    dati = dict(RINVIO, calendario={**RINVIO["calendario"],
                                    "7": [["10/10/2026", "20:45", "Inter", "Milan"],
                                          ["11/10/2026", "15:00", "Roma", "Lazio"],
                                          ["11/10/2026", "18:00", "Genoa", "Como"]]})
    html = genera(dati, DOPO_LA_SETTE)
    assert "La schedina &mdash; giornata 7" in html


def test_si_pronostica_gia_la_giornata_dopo_anche_col_recupero_in_ballo():
    from ovalmo import schedina
    cal = {int(k): v for k, v in RINVIO["calendario"].items()}
    assert schedina.giornata_aperta(cal, DOPO_LA_SETTE) == 8


def test_la_freschezza_si_controlla_subito_non_fra_cinque_minuti():
    """Chi apre una copia vecchia tenuta in memoria dal browser deve
    ritrovarsi quella giusta subito, non dopo cinque minuti di attesa."""
    html = genera(DATI, orari.quando("09/10/2026", "12:00"))
    coda = html[html.index("var MIA ="):]
    assert coda.index("controlla();") < coda.index("setInterval(controlla")


def test_l_invito_a_compilare_si_puo_nascondere():
    """Serve un aggancio: chi ha gia' mandato non deve vedere ne' il pulsante
    ne' la nota sotto."""
    dati = dict(DATI, endpoint_pronostici="https://script.google.com/macros/s/ABC/exec")
    html = genera(dati, PRIMA)
    assert '<div id="invito">' in html
    dentro = html[html.index('<div id="invito">'):html.index("</div>", html.index('<div id="invito">'))]
    assert "Manda i tuoi pronostici" in dentro and "direttamente in questa pagina" in dentro


def test_mentre_si_gioca_il_modulo_e_chiuso():
    """Al primo calcio d'inizio il modulo sparisce per tutti, anche per chi non
    ha ancora mandato: si torna a pronosticare a giornata finita."""
    dati = dict(DATI, endpoint_pronostici="https://script.google.com/macros/s/ABC/exec",
                calendario={**DATI["calendario"],
                            "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                                  ["18/10/2026", "15:00", "Genoa", "Parma"]]})
    # giornata 7 iniziata (10/10 20:45) e non finita
    html = genera(dati, orari.quando("10/10/2026", "21:30"))
    assert "Si sta giocando la giornata 7" in html
    assert 'id="chisei"' not in html          # niente da compilare


def test_a_giornata_finita_il_modulo_torna():
    dati = dict(DATI, endpoint_pronostici="https://script.google.com/macros/s/ABC/exec",
                risultati={"G07-01": [2, 1], "G07-02": [0, 0]},
                calendario={**DATI["calendario"],
                            "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                                  ["18/10/2026", "15:00", "Genoa", "Parma"]]})
    html = genera(dati, orari.quando("12/10/2026", "12:00"))
    assert "Manda i tuoi pronostici &mdash; giornata 8" in html
    assert 'id="chisei"' in html


def test_prima_che_cominci_il_modulo_e_aperto():
    dati = dict(DATI, endpoint_pronostici="https://script.google.com/macros/s/ABC/exec")
    html = genera(dati, orari.quando("09/10/2026", "12:00"))
    assert "Manda i tuoi pronostici &mdash; giornata 7" in html


def test_se_la_giornata_dopo_e_vicina_il_modulo_si_apre_lo_stesso():
    """La valvola di sicurezza: se la giornata precedente restasse incagliata
    per un guasto, senza questa nessuno potrebbe piu' mandare niente."""
    dati = dict(DATI, endpoint_pronostici="https://script.google.com/macros/s/ABC/exec",
                calendario={**DATI["calendario"],
                            "8": [["12/10/2026", "20:45", "Napoli", "Como"]]})
    # la 7 e' iniziata e incagliata, ma la 8 comincia fra meno di 36 ore
    html = genera(dati, orari.quando("11/10/2026", "20:00"))
    assert "Manda i tuoi pronostici &mdash; giornata 8" in html
    assert 'id="chisei"' in html


def test_i_punti_coraggio_si_vedono_nelle_caselle():
    """Un 6 e un 2 nelle caselle, e la riga che li spiega sotto la classifica.

    Senza la spiegazione un 6 sembra un errore di conto.
    """
    dati = dict(DATI, pronostici={
        # Inter-Milan finisce 3-0: Berta ha scritto proprio 3-0 e nessun altro
        "G07-01": {"Berta": ["1", 3, 0], "Lippi": ["1", 2, 0], "Lenzuolo": ["1", 1, 0]},
        # Roma-Lazio finisce 1-1: sul pareggio c'e' solo Lenzuolo
        "G07-02": {"Berta": ["1", 2, 0], "Lippi": ["2", 0, 1], "Lenzuolo": ["X", 2, 2]},
    }, risultati={"G07-01": [3, 0], "G07-02": [1, 1]})
    html = genera(dati, DOPO)
    assert '<span class="pts">6</span>' in html      # esatto, e da solo
    assert '<span class="pts">2</span>' in html      # segno giusto, e da solo
    assert "Punti coraggio" in html
    assert "chi indovina da solo vale doppio" in html


def test_il_ritratto_e_le_icone_stanno_nella_pagina():
    """La faccia nella testata, e le tre immagini che le fanno da icona.

    Se un giorno uno rinomina un file dentro docs/ senza accorgersene, la pagina
    resta con il riquadro rotto e nessuno se ne accorge finche' non la apre
    qualcuno: qui i nomi sono controllati, e i file esistono davvero.
    """
    import os

    html = genera(DATI, DOPO)
    assert '<img class="faccia" src="palladino.jpg"' in html
    assert 'alt="Raffaele Palladino"' in html           # non e' un'immagine muta
    assert '<link rel="apple-touch-icon" href="palladino-180.jpg">' in html
    assert 'rel="icon" href="palladino-64.jpg"' in html
    assert 'og:image" content="https://federicocimatti.github.io/ovalmo/palladino.jpg"' in html

    for nome in ("palladino.jpg", "palladino-180.jpg", "palladino-64.jpg"):
        percorso = os.path.join(QUI, "docs", nome)
        assert os.path.exists(percorso), f"manca docs/{nome}, la pagina lo cerca"
        assert os.path.getsize(percorso) > 1000, f"docs/{nome} e' vuoto o quasi"


def test_i_colori_del_sito_non_sono_cambiati():
    """La foto non doveva portarsi dietro un'estetica nuova: il verde, l'ottone e
    la carta sono quelli di prima."""
    import os

    with open(os.path.join(QUI, "template.html"), encoding="utf-8") as f:
        modello = f.read()
    for colore in ("--accent:#0F6E4C", "--brass:#96701C", "--paper:#EDF0EC",   # chiaro
                   "--accent:#48AC81", "--brass:#D0A24E", "--paper:#0C1310"):  # scuro
        assert colore in modello, f"colore cambiato o sparito: {colore}"


# -------------------------------------------- il venerdi' sera non chiude niente
WEEKEND = {
    "players": ["Berta", "Lippi"],
    "partite_per_giornata": 3,
    "calendario": {"7": [["10/10/2026", "20:45", "Inter", "Milan"],      # anticipo
                         ["11/10/2026", "15:00", "Roma", "Lazio"],
                         ["12/10/2026", "20:45", "Genoa", "Como"]],      # posticipo
                   "8": [["17/10/2026", "20:45", "Napoli", "Como"],
                         ["18/10/2026", "15:00", "Genoa", "Parma"],
                         ["18/10/2026", "18:00", "Lecce", "Monza"]]},
    "risultati": {"G07-01": [2, 1]},                                     # solo l'anticipo
    "pronostici": {"G07-01": {"Berta": ["1", 2, 1], "Lippi": ["2", 0, 1]}},
    "consegne": {"7": {"Berta": "x", "Lippi": "x"}},
}
VENERDI_SERA = orari.quando("10/10/2026", "23:00")     # anticipo finito, il resto da giocare


def test_l_anticipo_del_venerdi_non_manda_la_giornata_in_archivio():
    """Il guaio visto dal vivo l'11 settembre 2026: finito l'anticipo, il sito
    metteva in cima la giornata dopo e spediva in archivio quella in corso,
    con le altre nove partite etichettate "da recuperare". Non erano da
    recuperare: si giocavano il giorno dopo."""
    html = genera(WEEKEND, VENERDI_SERA)
    assert "La schedina &mdash; giornata 7" in html
    archivio = html[html.index("Giornate precedenti"):] if "Giornate precedenti" in html else ""
    assert "Giornata 7" not in archivio
    assert "da recuperare" not in html


def test_a_weekend_finito_la_giornata_si_chiude():
    dati = dict(WEEKEND, risultati={"G07-01": [2, 1], "G07-02": [1, 1], "G07-03": [0, 2]})
    html = genera(dati, orari.quando("12/10/2026", "23:30"))
    assert "La schedina &mdash; giornata 8" in html
    assert "re della giornata" in html[html.index("Giornate precedenti"):]


def test_una_partita_fuori_dai_cinque_giorni_e_un_recupero_non_una_da_giocare():
    """E' il confine fra le due cose: dentro la finestra tiene aperta la
    giornata, fuori no. Senza un limite, non c'e' modo di distinguere il
    posticipo del lunedi' da una partita rinviata di tre settimane."""
    dentro = dict(WEEKEND, calendario={**WEEKEND["calendario"],
        "7": [["10/10/2026", "20:45", "Inter", "Milan"],
              ["11/10/2026", "15:00", "Roma", "Lazio"],
              ["14/10/2026", "20:45", "Genoa", "Como"]]})      # quattro giorni dopo
    fuori = dict(WEEKEND, calendario={**WEEKEND["calendario"],
        "7": [["10/10/2026", "20:45", "Inter", "Milan"],
              ["11/10/2026", "15:00", "Roma", "Lazio"],
              ["24/10/2026", "20:45", "Genoa", "Como"]]})      # due settimane dopo
    subito_dopo = orari.quando("11/10/2026", "18:00")
    risultati = {"G07-01": [2, 1], "G07-02": [1, 1]}

    html = genera(dict(dentro, risultati=risultati), subito_dopo)
    assert "La schedina &mdash; giornata 7" in html            # si aspetta il posticipo

    html = genera(dict(fuori, risultati=risultati), subito_dopo)
    assert "La schedina &mdash; giornata 8" in html            # il recupero non blocca
    assert "da recuperare" in html


def test_mentre_si_gioca_sparisce_anche_l_invito_a_compilare():
    """Il modulo e' chiuso durante la giornata: se l'invito restasse, chi lo
    tocca finirebbe su una schermata che gli dice di riprovare dopo."""
    dati = dict(WEEKEND, risultati={})
    prima = genera(dati, orari.quando("10/10/2026", "12:00"))     # non e' ancora cominciata
    durante = genera(dati, orari.quando("10/10/2026", "21:30"))   # si gioca l'anticipo
    assert 'id="invito"' in prima
    assert 'id="invito"' not in durante
    assert "La schedina &mdash; giornata 7" in durante            # la giornata resta in cima
