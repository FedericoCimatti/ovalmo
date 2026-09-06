# -*- coding: utf-8 -*-
"""Tabella di conversione dei nomi squadra.

football-data.org usa il nome ufficiale per esteso e in inglese
("FC Internazionale Milano"); il gioco usa il nome corto italiano ("Inter").
La corrispondenza e' scritta a mano qui, una riga per squadra: e' l'unico modo
onesto: qualsiasi tentativo di indovinare ("prendi la prima parola") sbaglia su
Milan/Inter, Hellas Verona, Como 1907 e mezza Serie B.

Se una squadra manca il job si ferma con un messaggio chiaro invece di scrivere
un nome sbagliato nel calendario. Aggiungerla e' una riga in questo file.
"""


class SquadraSconosciuta(Exception):
    """Alzata quando l'API nomina una squadra che non e' in tabella."""


# nome nell'API  ->  nome nel gioco
MAPPA = {
    # Serie A 2026/27
    "Atalanta BC": "Atalanta",
    "Bologna FC 1909": "Bologna",
    "Cagliari Calcio": "Cagliari",
    "Como 1907": "Como",
    "ACF Fiorentina": "Fiorentina",
    "Frosinone Calcio": "Frosinone",
    "Genoa CFC": "Genoa",
    "FC Internazionale Milano": "Inter",
    "Juventus FC": "Juventus",
    "SS Lazio": "Lazio",
    "US Lecce": "Lecce",
    "AC Milan": "Milan",
    "AC Monza": "Monza",
    "SSC Napoli": "Napoli",
    "Parma Calcio 1913": "Parma",
    "AS Roma": "Roma",
    "US Sassuolo Calcio": "Sassuolo",
    "Torino FC": "Torino",
    "Udinese Calcio": "Udinese",
    "Venezia FC": "Venezia",
    # squadre che entrano e escono dalla Serie A: gia' pronte per le prossime
    # promozioni, cosi' il job non si ferma la domenica di ferragosto
    "Hellas Verona FC": "Verona",
    "Empoli FC": "Empoli",
    "US Salernitana 1919": "Salernitana",
    "Spezia Calcio": "Spezia",
    "Pisa Sporting Club": "Pisa",
    "US Cremonese": "Cremonese",
    "Brescia Calcio": "Brescia",
    "SSD Palermo": "Palermo",
    "Calcio Padova": "Padova",
    "Modena FC": "Modena",
    "Delfino Pescara 1936": "Pescara",
    "AC Reggiana 1919": "Reggiana",
    "US Catanzaro 1929": "Catanzaro",
    "Juve Stabia": "Juve Stabia",
    "Bari 1908": "Bari",
    "Frosinone": "Frosinone",
    "Carrarese Calcio 1908": "Carrarese",
    "Cesena FC": "Cesena",
    "Mantova 1911": "Mantova",
    "US Avellino 1912": "Avellino",
    "Virtus Entella": "Entella",
    "AC Monza Brianza 1912": "Monza",
    "Venezia": "Venezia",
}


def italiano(nome_api):
    """Nome corto italiano di una squadra. Alza SquadraSconosciuta se manca."""
    nome = (nome_api or "").strip()
    if nome in MAPPA:
        return MAPPA[nome]
    raise SquadraSconosciuta(
        f"La squadra \"{nome}\" non e' nella tabella di conversione.\n"
        f"Aggiungi una riga in ovalmo/squadre.py:\n"
        f'    "{nome}": "<nome corto italiano>",'
    )


def controlla(nomi_api):
    """Verifica che un elenco di nomi sia tutto mappato.

    Restituisce la lista dei nomi mancanti (vuota se e' tutto a posto):
    serve al test della stagione e al controllo che il job fa a ogni giro.
    """
    return sorted({n.strip() for n in nomi_api if n.strip() not in MAPPA})
