# -*- coding: utf-8 -*-
"""Genera la pagina web della classifica.

Il layout sta in template.html: qui si riempiono i segnaposto __NOME__.
E' il vecchio pagina.py, con tre differenze:

  1. i conti li fa punteggio.py, non piu' questo file
  2. la copertura dei pronostici guarda le CONSEGNE (chi ha mandato) e non i
     pronostici, che prima del calcio d'inizio non sono nemmeno nel repository
  3. in fondo c'e' un avviso che compare da solo se i risultati smettono di
     arrivare, cosi' la pagina non spaccia mai per fresco un dato vecchio
"""
import datetime
import html
import json

from . import orari
from .dati import id_partita
from .punteggio import calcola, re_della_giornata, segno, segno_pronosticato

MODULO = "https://forms.gle/vuZK5rm6N8b8Z2Zc7"
# indirizzo pubblico della pagina: serve all'anteprima del link su WhatsApp.
# Se e' sbagliato la pagina funziona lo stesso, si presenta solo peggio.
SITO = "https://federicocimatti.github.io/ovalmo/"
# dopo quante ore dal calcio d'inizio una partita senza risultato diventa sospetta
ORE_PRIMA_DI_INSOSPETTIRSI = 4

E = html.escape


def _giorn(n):
    return "1 giornata conclusa" if n == 1 else f"{n} giornate concluse"


def _elenco(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " e " + xs[-1]


def genera(dati, template, adesso=None, aggiornato=None):
    """Restituisce l'HTML della pagina.

    dati       stagione e pronostici uniti (vedi dati.unisci)
    template   il contenuto di template.html
    adesso     per i test: che ora e' (default: adesso, a Roma)
    aggiornato quando i dati sono stati aggiornati l'ultima volta
    """
    adesso = adesso or orari.adesso()
    aggiornato = aggiornato or adesso
    giocatori = dati["players"]
    per_giornata = dati["partite_per_giornata"]
    calendario = {int(k): v for k, v in dati["calendario"].items()}
    risultati = dati.get("risultati", {}) or {}
    pronostici = dati.get("pronostici", {}) or {}
    consegne = dati.get("consegne", {}) or {}
    giornate = sorted(calendario)

    conti = calcola(dati)
    stats, per_g, giocate_g = conti["stats"], conti["per_g"], conti["giocate_g"]
    ordine, pos, concluse = conti["ordine"], conti["pos"], conti["concluse"]
    giocate_tot = conti["giocate"]

    coperta = {g: orari.coperta(calendario, g, adesso) for g in calendario}

    def ha_consegnato(g, giocatore):
        """Vero se ha mandato la schedina di quella giornata.

        Si guarda l'elenco delle consegne; per le giornate vecchie, importate
        quando le consegne non venivano ancora registrate, vale la presenza di
        un pronostico qualsiasi.
        """
        if giocatore in (consegne.get(str(g)) or {}):
            return True
        return any((pronostici.get(id_partita(g, m)) or {}).get(giocatore)
                   for m in range(1, len(calendario[g]) + 1))

    def chip(sg):
        return f'<span class="sg sg-{sg.lower()}">{sg}</span>' if sg else '<span class="sg sg-tbd">TBD</span>'

    def carte(g):
        nascosta = coperta.get(g, False)
        out = []
        for m in range(1, min(per_giornata, len(calendario[g])) + 1):
            mid = id_partita(g, m)
            data, ora, casa, osp = calendario[g][m - 1]
            picks = pronostici.get(mid) or {}
            sgs = [segno_pronosticato(picks.get(p_)) for p_ in giocatori]
            unanime = (not nascosta) and all(sgs) and len(set(sgs)) == 1
            ris = risultati.get(mid)
            esito = (f'<span class="ris">{ris[0]}&ndash;{ris[1]} {chip(segno(*ris))}</span>' if ris
                     else f'<span class="ora">{E(str(ora))}</span>')
            celle = []
            for p_ in giocatori:
                pr = picks.get(p_)
                s = segno_pronosticato(pr)
                _, ph, pa = (pr or [None, None, None])
                pts = None
                if ris:
                    gh, ga = ris
                    pts = 3 if (ph is not None and pa is not None and ph == gh and pa == ga) else (
                        1 if s == segno(gh, ga) else 0)
                klass = " pk3" if pts == 3 else (" pk2" if pts == 1 else "")
                if s is None:
                    klass += " attesa-p"
                if nascosta:
                    # consegnato ma non ancora svelato: spunta se ha mandato, TBD se no
                    mandato = ha_consegnato(g, p_)
                    segnino = ('<span class="sg sg-lock">&#10003;</span>' if mandato
                               else '<span class="sg sg-tbd">TBD</span>')
                    celle.append(
                        f'<div class="pick{"" if mandato else " attesa-p"}"><span class="who">{E(p_)}</span>'
                        f'{segnino}<span class="sc">&nbsp;</span></div>')
                    continue
                celle.append(
                    f'<div class="pick{klass}"><span class="who">{E(p_)}</span>{chip(s)}'
                    f'<span class="sc">{"&nbsp;" if ph is None else f"{ph}&ndash;{pa}"}</span>'
                    + (f'<span class="pts">{pts}</span>' if pts is not None else '') + '</div>')
            out.append(
                '<article class="match"><header>'
                f'<div class="meta"><span class="num">{m:02d}</span>{esito}</div>'
                f'<h3>{E(casa)} <span class="v">&ndash;</span> {E(osp)}</h3></header>'
                + ('<p class="unan">tutti e cinque sullo stesso segno</p>' if unanime else '')
                + f'<div class="picks">{"".join(celle)}</div></article>')
        return out

    # giornata in corso = la prima non ancora completata
    pendenti = [g for g in giornate if giocate_g[g] < len(calendario[g])]
    g_feat = min(pendenti) if pendenti else None
    concluse_desc = sorted(concluse, reverse=True)
    archivio = [g for g in concluse_desc if g != g_feat]
    g_show = g_feat if g_feat is not None else (concluse_desc[0] if concluse_desc else giornate[0])

    if giocate_tot == 0:
        prima = calendario[g_show][0]
        lede = "Nessuna partita ancora giocata: i punti arrivano col primo fischio finale."
        tabella = (f'<p class="attesa">Si parte da {E(prima[2])}&ndash;{E(prima[3])}, '
                   f'{E(str(prima[0]))} alle {E(str(prima[1]))}. Fino ad allora ci sono solo i pronostici, '
                   'qui sotto. In gara:</p><ul class="roster">'
                   + "".join(f"<li>{E(p)}</li>" for p in giocatori) + "</ul>")
    else:
        righe = []
        for p in ordine:
            s = stats[p]
            lead = ' class="leader"' if pos[p] == 1 else ''
            righe.append(f'<tr{lead}><td class="pos">{pos[p]}</td><td class="nome">{E(p)}</td>'
                         f'<td class="num-pt">{s["pt"]}</td><td class="num">{s["segni"]}</td>'
                         f'<td class="num">{s["esatti"]}</td></tr>')
        tabella = ('<div class="tw"><table><thead><tr><th></th><th>Giocatore</th>'
                   '<th class="num-pt">Punti</th><th class="num">Segni</th>'
                   '<th class="num">Esatti</th></tr></thead><tbody>'
                   + "".join(righe) + '</tbody></table></div>')
        lede = (f'Dopo {giocate_tot} partite'
                + (f' e {_giorn(len(concluse))}' if concluse else '') + '.')

    # ---------- blocco giornata in corso ----------
    if g_feat is not None:
        mancanti = [p_ for p_ in giocatori if not ha_consegnato(g_feat, p_)]
        if len(mancanti) == len(giocatori):
            occhiello = "Nessuno ha ancora mandato i pronostici. Le caselle TBD si riempiono man mano."
        elif mancanti:
            occhiello = ("Mancano ancora i pronostici di " + _elenco(E(x) for x in mancanti)
                         + ": le loro caselle sono TBD.")
        else:
            occhiello = "Tutti e cinque hanno mandato. Il segno grande &egrave; l&rsquo;esito, sotto il risultato esatto."
        if coperta.get(g_feat):
            occhiello += (" Nessuno vede i pronostici degli altri: il segno di chi ha gi&agrave; mandato resta "
                          "coperto con una spunta e si svela al primo calcio d&rsquo;inizio.")
        featured = (f'<h2>La schedina &mdash; giornata {g_feat}</h2>'
                    f'<p class="lede">{occhiello}</p>'
                    f'<a class="cta" href="{MODULO}" target="_blank" rel="noopener">Manda i tuoi pronostici</a>'
                    '<p class="cta-note">Nel modulo trovi le stesse dieci partite, nello stesso ordine. '
                    'Si risponde cos&igrave;: <strong>1 (2-1)</strong>.</p>'
                    '<div class="matches">' + "\n      ".join(carte(g_feat)) + '</div>')
    else:
        featured = ('<h2>La schedina</h2><p class="lede">Tutte le giornate in calendario sono gi&agrave; '
                    'giocate. Appena esce il calendario della prossima, compare qui.</p>')

    # ---------- archivio giornate concluse ----------
    if archivio:
        blocchi = []
        for i, g in enumerate(archivio):
            re_g, mx = re_della_giornata(conti, giocatori, g)
            etichetta = (f'{E(_elenco(re_g))}<br>re della giornata &middot; {mx} punti' if re_g else 'nessun punto')
            blocchi.append(
                f'<details class="g"{" open" if i == 0 else ""}>'
                f'<summary><span class="gname">Giornata {g}</span>'
                f'<span class="gre">{etichetta}</span><span class="caret">&rsaquo;</span></summary>'
                f'<div class="gbody">' + "\n        ".join(carte(g)) + '</div></details>')
        archivio_html = ('<section><h2>Giornate precedenti</h2>'
                         '<p class="lede">Tocca una giornata per riaprire la schedina completa, con i punti assegnati.</p>'
                         '<div class="arch">' + "\n      ".join(blocchi) + '</div></section>')
    else:
        archivio_html = ''

    # ---------- tabella punti per giornata ----------
    con_punti = [g for g in giornate if giocate_g[g] > 0]
    if con_punti:
        intest = "".join(f'<th class="num">{E(p_)}</th>' for p_ in giocatori)
        righe_g = []
        for g in con_punti:
            mx = max(per_g[g].values())
            re_g, _ = re_della_giornata(conti, giocatori, g)
            celle = "".join(
                f'<td class="{"best" if per_g[g][p_] == mx and mx > 0 else ""}">{per_g[g][p_]}</td>'
                for p_ in giocatori)
            righe_g.append(f'<tr><td class="g">{g}</td>{celle}'
                           f'<td class="re">{E(_elenco(re_g)) if re_g else "&mdash;"}</td></tr>')
        tabella_g = ('<div class="gtab"><div class="tw"><table><thead><tr><th>G.</th>' + intest
                     + '<th>Re</th></tr></thead><tbody>'
                     + "".join(righe_g) + '</tbody></table></div></div>')
    else:
        tabella_g = ''

    tag = f"Giornata {g_show}" + (" &middot; in attesa dei risultati" if giocate_g.get(g_show, 0) == 0 else "")
    sub = "Serie A 2026/27 &middot; " + (_giorn(len(concluse)) if concluse else "si comincia dalla seconda")

    # riga che compare nell'anteprima del link (WhatsApp, Telegram, iMessage)
    if giocate_tot == 0:
        og = f"Serie A 2026/27. Si comincia dalla giornata {g_show}: pronostici aperti."
    else:
        primi = [p for p in ordine if pos[p] == 1]
        pt1 = stats[primi[0]]["pt"]
        og = (f"Classifica dopo {giocate_tot} partite: "
              + (f"in testa {_elenco(primi)} a pari merito con {pt1} punti."
                 if len(primi) > 1 else f"in testa {primi[0]} con {pt1} punti."))

    avviso = _script_avviso(calendario, risultati, giornate)
    fine = (f"Dati aggiornati il {aggiornato:%d/%m/%Y} alle {aggiornato:%H:%M} &middot; "
            "aggiornamento automatico ogni ora &middot; "
            "i punti li calcola il foglio, non la memoria di nessuno")

    page = template
    for k, v in [("__OG__", E(og)), ("__URL__", E(SITO)), ("__AVVISO__", avviso),
                 ("__TAG__", tag), ("__SUB__", sub), ("__LEDE__", lede), ("__TABELLA__", tabella),
                 ("__TABELLA_G__", tabella_g), ("__FEATURED__", featured), ("__ARCHIVIO__", archivio_html),
                 ("__FINE__", fine)]:
        page = page.replace(k, v)
    resti = [k for k in ("__OG__", "__URL__", "__AVVISO__", "__TAG__", "__SUB__", "__LEDE__",
                         "__TABELLA__", "__TABELLA_G__", "__FEATURED__", "__ARCHIVIO__", "__FINE__")
             if k in page]
    assert not resti, f"segnaposto non sostituiti: {resti}"
    return page


def _script_avviso(calendario, risultati, giornate):
    """Il codice che fa comparire l'avviso "aggiornamento fermo".

    Nella pagina finisce l'elenco delle partite senza risultato, con l'ora del
    calcio d'inizio. E' il browser di chi guarda, non il job, a decidere se sono
    passate troppe ore: cosi' l'avviso compare anche quando il job e' morto e
    non ha piu' pubblicato niente. E' il punto in cui la pagina si rifiuta di
    far passare per fresco un dato vecchio.
    """
    attese = []
    for g in giornate:
        for m in range(1, len(calendario[g]) + 1):
            mid = id_partita(g, m)
            if risultati.get(mid):
                continue
            data, ora, casa, osp = calendario[g][m - 1]
            attese.append({"q": orari.quando(data, ora).isoformat(), "n": f"{casa}-{osp}"})
    return (
        "(function(){\n"
        f"  var attese = {json.dumps(attese, ensure_ascii=False)};\n"
        f"  var ORE = {ORE_PRIMA_DI_INSOSPETTIRSI};\n"
        "  var adesso = new Date();\n"
        "  var vecchie = attese.filter(function(p){\n"
        "    return (adesso - new Date(p.q)) > ORE*3600*1000;\n"
        "  });\n"
        "  if(!vecchie.length) return;\n"
        "  var box = document.getElementById('avviso');\n"
        "  if(!box) return;\n"
        "  var quali = vecchie.slice(0,3).map(function(p){return p.n}).join(', ');\n"
        "  box.innerHTML = '<b>Attenzione: mancano dei risultati.</b> ' +\n"
        "    (vecchie.length === 1 ? 'La partita ' : 'Le partite ') + quali +\n"
        "    (vecchie.length > 3 ? ' e altre ' + (vecchie.length-3) : '') +\n"
        "    (vecchie.length === 1 ? ' e finita' : ' sono finite') + ' da un pezzo ma il "
        "risultato non e ancora arrivato: l\\'aggiornamento automatico potrebbe essersi fermato. "
        "I dati qui sotto sono gli ultimi buoni.';\n"
        "  box.hidden = false;\n"
        "})();"
    )
