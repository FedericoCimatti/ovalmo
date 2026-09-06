# -*- coding: utf-8 -*-
"""Lettura e scrittura dei file in dati/.

I dati stanno in due file, e la divisione non e' estetica: e' la regola del
gioco. Il repository e' pubblico, quindi tutto cio' che viene scritto qui e'
leggibile da chiunque, anche nello storico git.

  dati/stagione.json    calendario, risultati, giocatori. Pubblico per natura.
  dati/pronostici.json  i pronostici veri, che entrano SOLO dopo il calcio
                        d'inizio della loro giornata, piu' le "consegne"
                        (chi ha mandato e quando, senza il contenuto).

Prima della deadline nel repository c'e' scritto solo "Berta ha mandato alle
18:22": abbastanza per la spunta verde sulla pagina, inutile per copiare.

In memoria i due file vengono uniti in un dizionario solo, con la stessa forma
del vecchio dati_ovalmo.json, cosi' pagina.py e excel.py funzionano come prima.
"""
import json
import os

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARTELLA = os.path.join(QUI, "dati")
STAGIONE = os.path.join(CARTELLA, "stagione.json")
PRONOSTICI = os.path.join(CARTELLA, "pronostici.json")


def _leggi(percorso, vuoto):
    if not os.path.exists(percorso):
        return json.loads(json.dumps(vuoto))
    with open(percorso, encoding="utf-8") as f:
        return json.load(f)


def _scrivi(percorso, contenuto):
    """Scrive JSON stabile: stesse chiavi nello stesso ordine a ogni giro.

    Serve all'idempotenza: senza ordinamento due giri identici produrrebbero
    file diversi byte per byte, e quindi un commit inutile ogni ora.
    """
    testo = json.dumps(contenuto, ensure_ascii=False, indent=1, sort_keys=True)
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(testo + "\n")


def carica():
    """Restituisce (stagione, pronostici) come sono su disco."""
    stagione = _leggi(STAGIONE, {})
    pronostici = _leggi(PRONOSTICI, {"consegne": {}, "pronostici": {}})
    pronostici.setdefault("consegne", {})
    pronostici.setdefault("pronostici", {})
    return stagione, pronostici


def unisci(stagione, pronostici):
    """I due file in un dizionario solo, nella forma che si aspettano
    pagina.py e excel.py (le chiavi del vecchio dati_ovalmo.json)."""
    d = dict(stagione)
    d["pronostici"] = pronostici.get("pronostici", {})
    d["consegne"] = pronostici.get("consegne", {})
    return d


def salva(stagione, pronostici):
    _scrivi(STAGIONE, stagione)
    _scrivi(PRONOSTICI, pronostici)


def calendario(stagione):
    """Il calendario con le giornate come numeri interi (nel JSON sono testo)."""
    return {int(k): v for k, v in stagione.get("calendario", {}).items()}


def id_partita(giornata, numero):
    """G03-07: giornata a due cifre, numero della partita a due cifre."""
    return f"G{int(giornata):02d}-{int(numero):02d}"
