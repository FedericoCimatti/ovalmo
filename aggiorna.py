# -*- coding: utf-8 -*-
"""Il giro completo: risultati, pronostici, pagina, Excel.

E' l'unico programma che il workflow lancia, e l'unico da lanciare a mano se
un giorno bisogna intervenire:

    python aggiorna.py

Cosa fa, in ordine:
  1. scarica calendario e risultati da football-data.org  (serve FD_TOKEN)
  2. scarica i pronostici dal foglio Google pubblicato    (serve FOGLIO_CSV)
  3. ricalcola punti e classifica
  4. riscrive docs/index.html, ma solo se e' davvero cambiata
  5. rigenera docs/Trofeo_Ovalmo.xlsx, ma solo se i dati sono cambiati
  6. stampa un riepilogo di cosa e' successo

Senza le due variabili d'ambiente il programma non si ferma: salta il pezzo che
non puo' fare e lo dice. Serve a poter rigenerare la pagina dai dati che ci
sono gia', anche senza rete.
"""
import hashlib
import json
import os
import re
import sys
import traceback

from ovalmo import dati, modulo, orari, pagina, risultati

QUI = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(QUI, "template.html")
DOCS = os.path.join(QUI, "docs")
INDEX = os.path.join(DOCS, "index.html")
XLSX = os.path.join(DOCS, "Trofeo_Ovalmo.xlsx")
STATO = os.path.join(QUI, "dati", "stato.json")

# la data in fondo alla pagina cambia a ogni giro: neutralizzarla e' cio' che
# impedisce di fare un commit all'ora anche quando non e' successo niente
DATA_IN_FONDO = re.compile(r"Dati aggiornati il \d{2}/\d{2}/\d{4} alle \d{2}:\d{2}")


def impronta(testo):
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:16]


def impronta_pagina(html):
    return impronta(DATA_IN_FONDO.sub("Dati aggiornati il --", html))


def leggi_stato():
    if os.path.exists(STATO):
        with open(STATO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def scrivi_stato(stato):
    with open(STATO, "w", encoding="utf-8") as f:
        f.write(json.dumps(stato, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def giro(token=None, foglio_csv=None):
    """Il giro completo. Restituisce le righe del riepilogo."""
    riepilogo = []
    stagione, pronostici = dati.carica()
    stato = leggi_stato()
    impronta_dati_prima = stato.get("impronta_dati")
    adesso = orari.adesso()

    # ---- 1. calendario e risultati ----
    if token:
        partite = risultati.scarica(token, stagione.get("competizione", "SA"))
        note = risultati.aggiorna(stagione, partite)
        riepilogo += note or ["nessun risultato nuovo"]
    else:
        riepilogo.append("FD_TOKEN assente: calendario e risultati non aggiornati")

    # ---- 2. pronostici ----
    if foglio_csv:
        testo = modulo.scarica(foglio_csv)
        consegne, nuovi, note, scarti = modulo.leggi(testo, stagione, adesso)
        cambiato = modulo.unisci(pronostici, consegne, nuovi)
        riepilogo += note or ["nessun pronostico nuovo"]
        riepilogo += ["SCARTATO: " + s for s in scarti]
        if not cambiato:
            riepilogo.append("i pronostici erano gia' tutti al loro posto")
    else:
        riepilogo.append("FOGLIO_CSV assente: pronostici non aggiornati")

    dati.salva(stagione, pronostici)
    uniti = dati.unisci(stagione, pronostici)

    # ---- 3. la pagina ----
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    html = pagina.genera(uniti, template, adesso=adesso, aggiornato=adesso)
    nuova = impronta_pagina(html)
    vecchia = None
    if os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as f:
            vecchia = impronta_pagina(f.read())
    if nuova != vecchia:
        os.makedirs(DOCS, exist_ok=True)
        with open(INDEX, "w", encoding="utf-8") as f:
            f.write(html)
        riepilogo.append(f"pagina riscritta ({vecchia} -> {nuova})")
    else:
        riepilogo.append("pagina identica a quella pubblicata: non la tocco")

    # ---- 4. l'Excel ----
    # il file .xlsx cambia byte per byte a ogni generazione (contiene degli
    # orari suoi), quindi si confrontano i dati, non il file
    con_dati = impronta(json.dumps(uniti, ensure_ascii=False, sort_keys=True))
    if con_dati != impronta_dati_prima or not os.path.exists(XLSX):
        from ovalmo import excel
        os.makedirs(DOCS, exist_ok=True)
        excel.genera(uniti, XLSX)
        controllo = excel.verifica(XLSX)
        riepilogo.append(f"Excel rigenerato e verificato ({controllo['formule']} formule)")
    else:
        riepilogo.append("dati invariati: Excel lasciato com'e'")

    stato.update({
        "impronta_dati": con_dati,
        "impronta_pagina": nuova,
        "ultimo_aggiornamento": f"{adesso:%d/%m/%Y %H:%M}",
    })
    # lo stato si salva solo se e' cambiato qualcosa d'altro, altrimenti
    # basterebbe lui a produrre un commit all'ora
    if nuova != vecchia or con_dati != impronta_dati_prima:
        scrivi_stato(stato)
    return riepilogo


def main():
    token = os.environ.get("FD_TOKEN") or None
    foglio = os.environ.get("FOGLIO_CSV") or None
    try:
        righe = giro(token, foglio)
    except Exception as e:
        print("GIRO FALLITO:", e, file=sys.stderr)
        traceback.print_exc()
        # il messaggio finisce nella issue aperta dal workflow
        with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as f:
            f.write(f"## Aggiornamento fallito\n\n```\n{e}\n```\n")
        return 1
    print("\n".join("  " + r for r in righe))
    riassunto = os.environ.get("GITHUB_STEP_SUMMARY")
    if riassunto:
        with open(riassunto, "a") as f:
            f.write("## Riepilogo\n\n" + "\n".join(f"- {r}" for r in righe) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
