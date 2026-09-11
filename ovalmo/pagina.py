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

from . import diretta, grafico, orari, schedina
from .dati import id_partita
from .punteggio import (calcola, punti_partita, re_della_giornata, segno,
                        segno_pronosticato)

MODULO = "https://forms.gle/vuZK5rm6N8b8Z2Zc7"
# indirizzo pubblico della pagina: serve all'anteprima del link su WhatsApp.
# Se e' sbagliato la pagina funziona lo stesso, si presenta solo peggio.
SITO = "https://federicocimatti.github.io/ovalmo/"
# dopo quante ore dal calcio d'inizio una partita senza risultato diventa sospetta
ORE_PRIMA_DI_INSOSPETTIRSI = 4
# dopo quante ore dal calcio d'inizio una partita si considera finita: oltre,
# se manca il risultato, e' la giornata a essere bloccata e non un rinvio
ORE_PER_GIOCARE = 3
# quanto dura una giornata di campionato, dal primo calcio d'inizio: l'anticipo
# del venerdi' e il posticipo del lunedi' stanno dentro cinque giorni. Una
# partita fissata oltre questo termine non e' "non ancora giocata": e' un
# recupero, e non deve tenere ferma la giornata (vedi _mancanti)
GIORNI_DI_UNA_GIORNATA = 5

E = html.escape


def _giorn(n):
    # lo spazio unificatore tiene il numero attaccato alla parola: senza, il
    # sottotitolo va a capo dopo il "2" e lo lascia solo in fondo alla riga
    return "1&nbsp;giornata conclusa" if n == 1 else f"{n}&nbsp;giornate concluse"


def _inizio_giornata(calendario, g):
    """Il primo calcio d'inizio della giornata: da li' si contano i cinque giorni.

    Si prende il piu' presto e non la data della prima partita in elenco perche'
    l'elenco non cambia mai ordine, mentre gli orari si spostano di continuo.
    """
    return min(orari.quando(data, ora) for data, ora, _, _ in calendario[g])


def _mancanti(calendario, risultati, g, adesso):
    """Le partite senza risultato, in tre gruppi.

      scadute     dovevano essere finite e il risultato non e' arrivato
      da_giocare  si giocano in questi giorni: la giornata non e' finita
      recuperi    spostate oltre la fine della giornata: non la tengono ferma

    La distinzione fra le ultime due e' la ragione per cui questa funzione
    esiste. Prima non c'era, e il venerdi' sera bastava l'anticipo per far
    sembrare conclusa una giornata di cui restavano nove partite: il sito
    passava alla giornata dopo e metteva in archivio quella in corso.
    """
    fine = _inizio_giornata(calendario, g) + datetime.timedelta(days=GIORNI_DI_UNA_GIORNATA)
    scadute, da_giocare, recuperi = [], [], []
    for n in range(1, len(calendario[g]) + 1):
        mid = id_partita(g, n)
        if risultati.get(mid):
            continue
        data, ora, casa, ospite = calendario[g][n - 1]
        inizio = orari.quando(data, ora)
        partita = {"mid": mid, "casa": casa, "ospite": ospite, "data": data, "ora": ora}
        if (adesso - inizio).total_seconds() / 3600 > ORE_PER_GIOCARE:
            scadute.append(partita)
        elif inizio > fine:
            recuperi.append(partita)
        else:
            da_giocare.append(partita)
    return scadute, da_giocare, recuperi


def _scadute(calendario, risultati, g, adesso):
    """Partite che dovevano essere finite e non hanno un risultato."""
    return _mancanti(calendario, risultati, g, adesso)[0]


def _da_giocare(calendario, risultati, g, adesso):
    """Partite di questa giornata ancora in programma nei prossimi giorni."""
    return _mancanti(calendario, risultati, g, adesso)[1]


def _da_recuperare(calendario, risultati, g, adesso):
    """Partite della giornata rimandate ben oltre la fine della giornata."""
    return _mancanti(calendario, risultati, g, adesso)[2]


def _iniziate_non_finite(calendario, risultati, g, adesso):
    """Quante partite possono ancora dare punti adesso: quelle senza risultato
    il cui calcio d'inizio e' gia' passato."""
    scadute, da_giocare, recuperi = _mancanti(calendario, risultati, g, adesso)
    iniziate = [p for p in da_giocare + recuperi
                if orari.quando(p["data"], p["ora"]) <= adesso]
    return len(scadute) + len(iniziate)


def _etichetta_recuperi(partite):
    """Che cosa si scrive al posto del re della giornata, quando manca qualcosa."""
    if len(partite) == 1:
        p = partite[0]
        return (f'{E(p["casa"])}&ndash;{E(p["ospite"])}<br>da recuperare &middot; '
                f'{E(quando_si_gioca(p["data"], p["ora"], orari.adesso()))}')
    return (f'{len(partite)} partite da recuperare<br>'
            'il re della giornata si sapr&agrave; allora')


def quando_si_gioca(data, ora, adesso):
    """Come si scrive l'orario di una partita non ancora giocata.

    "Oggi 18:30", "Domani 20:45", "12/09 15:00". L'anno non serve: nessuno
    pronostica una partita dell'anno prossimo.
    """
    giorno = orari.quando(data, ora).date()
    mancano = (giorno - adesso.date()).days
    if mancano == 0:
        etichetta = "Oggi"
    elif mancano == 1:
        etichetta = "Domani"
    else:
        etichetta = f"{giorno:%d/%m}"
    testo = str(ora).strip()
    if not testo or ":" not in testo:
        return f"{etichetta} &middot; orario ancora da definire"
    return f"{etichetta} {testo}"


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
    # indirizzo dello script Google che riceve i pronostici. Finche' e' vuoto la
    # pagina rimanda al vecchio modulo Google invece di mostrare una schedina
    # che non saprebbe dove mandare niente.
    endpoint = dati.get("endpoint_pronostici") or ""

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
            ris = risultati.get(mid)
            esito = (f'<span class="ris">{ris[0]}&ndash;{ris[1]} {chip(segno(*ris))}</span>' if ris
                     else f'<span class="ora">{quando_si_gioca(data, ora, adesso)}</span>')
            # i punti li fa punteggio.py, anche qui: il punto coraggio si puo'
            # decidere solo guardando tutti e cinque insieme
            valori = punti_partita(picks, ris, g, giocatori) if ris else {}
            celle = []
            for p_ in giocatori:
                pr = picks.get(p_)
                s = segno_pronosticato(pr)
                _, ph, pa = (pr or [None, None, None])
                pts = valori.get(p_) if ris else None
                klass = (" pk3" if (pts or 0) >= 3 else (" pk2" if pts else ""))
                if s is None:
                    klass += " attesa-p"
                if nascosta:
                    # consegnato ma non ancora svelato: spunta se ha mandato, TBD se no
                    mandato = ha_consegnato(g, p_)
                    segnino = ('<span class="sg sg-lock">&#10003;</span>' if mandato
                               else '<span class="sg sg-tbd">TBD</span>')
                    celle.append(
                        f'<div class="pick{"" if mandato else " attesa-p"}" data-chi="{E(p_)}">'
                        f'<span class="who">{E(p_)}</span>'
                        f'{segnino}<span class="sc">&nbsp;</span></div>')
                    continue
                celle.append(
                    f'<div class="pick{klass}" data-chi="{E(p_)}"><span class="who">{E(p_)}</span>{chip(s)}'
                    f'<span class="sc">{"&nbsp;" if ph is None else f"{ph}&ndash;{pa}"}</span>'
                    + (f'<span class="pts">{pts}</span>' if pts is not None else '') + '</div>')
            out.append(
                f'<article class="match" data-mid="{mid}"'
                + (f' data-coperta="{g}"' if nascosta else '') + '><header>'
                f'<div class="meta"><span class="num">{m:02d}</span>{esito}</div>'
                f'<h3>{E(casa)} <span class="v">&ndash;</span> {E(osp)}</h3></header>'
                + f'<div class="picks">{"".join(celle)}</div></article>')
        return out

    # Quando una giornata e' finita, anche se un recupero e' ancora in ballo.
    #
    # Una partita rinviata non blocca la giornata: l'API le cambia la data, e
    # quindi diventa una partita di un altro giorno. Una giornata e' "chiusa"
    # quando tutto cio' che doveva giocarsi si e' giocato, anche se restano
    # recuperi in calendario. Senza questa distinzione un rinvio terrebbe il
    # sito fermo su quella giornata per settimane.
    da_recuperare = {g: _da_recuperare(calendario, risultati, g, adesso) for g in giornate}
    scadute = {g: _scadute(calendario, risultati, g, adesso) for g in giornate}
    da_giocare = {g: _da_giocare(calendario, risultati, g, adesso) for g in giornate}

    def chiusa(g):
        # finita davvero: qualcosa si e' giocato, non manca nessun risultato e
        # non c'e' altro in programma. Un recupero fra tre settimane non conta:
        # se contasse, una giornata resterebbe in cima al sito fino ad allora
        return giocate_g[g] > 0 and not scadute[g] and not da_giocare[g]

    aperte = [g for g in giornate if not chiusa(g)]
    g_feat = min(aperte) if aperte else None
    chiuse_desc = sorted((g for g in giornate if chiusa(g)), reverse=True)
    archivio = [g for g in chiuse_desc if g != g_feat]
    g_show = g_feat if g_feat is not None else (chiuse_desc[0] if chiuse_desc else giornate[0])

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
            righe.append(f'<tr{lead} data-chi="{E(p)}"><td class="pos">{pos[p]}</td><td class="nome">{E(p)}</td>'
                         f'<td class="num-pt">{s["pt"]}</td><td class="num">{s["segni"]}</td>'
                         f'<td class="num">{s["esatti"]}</td></tr>')
        tabella = ('<p class="live" id="inGioco" hidden></p>'
                   '<div class="tw"><table id="classifica"><thead><tr><th></th><th>Giocatore</th>'
                   '<th class="num-pt">Punti</th><th class="num">Segni</th>'
                   '<th class="num">Esatti</th></tr></thead><tbody>'
                   + "".join(righe) + '</tbody></table></div>')
        lede = (f'Dopo {giocate_tot} partite'
                + (f' e {_giorn(len(concluse))}' if concluse else '') + '.')

    # "si gioca" vuol dire che il primo calcio d'inizio e' passato, non che c'e'
    # gia' un risultato: fra il fischio e il primo gol passa un'ora buona
    si_gioca = g_feat if (g_feat is not None and not coperta.get(g_feat, True)) else None

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
        # Mentre si gioca il modulo e' chiuso: invitare a compilarlo manderebbe
        # la gente a sbattere contro una schermata che dice di riprovare dopo.
        invito = '' if si_gioca else (
            f'<div id="invito"><a class="cta" href="#modulo">Manda i tuoi pronostici</a>'
            '<p class="cta-note">Si compila qui sotto, direttamente in questa pagina.</p></div>')
        featured = (f'<h2>La schedina &mdash; giornata {g_feat}</h2>'
                    f'<p class="lede">{occhiello}</p>'
                    + (invito
                       if endpoint else
                       f'<a class="cta" href="{MODULO}" target="_blank" rel="noopener">Manda i tuoi pronostici</a>'
                       '<p class="cta-note">Nel modulo trovi le stesse dieci partite, nello stesso ordine. '
                       'Si risponde cos&igrave;: <strong>1 (2-1)</strong>.</p>')
                    +
                    '<div class="matches">' + "\n      ".join(carte(g_feat)) + '</div>')
    else:
        featured = ('<h2>La schedina</h2><p class="lede">Tutte le giornate in calendario sono gi&agrave; '
                    'giocate. Appena esce il calendario della prossima, compare qui.</p>')

    # ---------- archivio giornate concluse ----------
    if archivio:
        blocchi = []
        for g in archivio:
            if da_recuperare[g]:
                etichetta = _etichetta_recuperi(da_recuperare[g])
            else:
                re_g, mx = re_della_giornata(conti, giocatori, g)
                etichetta = (f'{E(_elenco(re_g))}<br>re della giornata &middot; {mx} punti'
                             if re_g else 'nessun punto')
            blocchi.append(
                # tutte chiuse: chi vuole rivedere una giornata la apre
                '<details class="g">'
                f'<summary><span class="gname">Giornata {g}</span>'
                f'<span class="gre">{etichetta}</span><span class="caret">&rsaquo;</span></summary>'
                f'<div class="gbody">' + "\n        ".join(carte(g)) + '</div></details>')
        archivio_html = ('<section><h2>Giornate precedenti</h2>'
                         '<p class="lede">Tocca una giornata per riaprire la schedina completa, con i punti assegnati.</p>'
                         '<div class="arch">' + "\n      ".join(blocchi) + '</div></section>')
    else:
        archivio_html = ''

    aperte_ora = sum(_iniziate_non_finite(calendario, risultati, g, adesso)
                     for g in giornate)
    andamento = grafico.disegna(conti, giocatori, aperte_ora=aperte_ora,
                                giornata_viva=si_gioca)

    tag = f"Giornata {g_show}" + (" &middot; in attesa dei risultati" if giocate_g.get(g_show, 0) == 0 else "")
    # due righe pulite, senza il punto in mezzo: "Serie A 2026/27" e sotto
    # "2 giornate concluse", col numero attaccato alla sua parola
    sub = "Serie A 2026/27<br>" + (_giorn(len(concluse)) if concluse else "si comincia dalla seconda")

    # riga che compare nell'anteprima del link (WhatsApp, Telegram, iMessage)
    if giocate_tot == 0:
        og = f"Serie A 2026/27. Si comincia dalla giornata {g_show}: pronostici aperti."
    else:
        primi = [p for p in ordine if pos[p] == 1]
        pt1 = stats[primi[0]]["pt"]
        og = (f"Classifica dopo {giocate_tot} partite: "
              + (f"in testa {_elenco(primi)} a pari merito con {pt1} punti."
                 if len(primi) > 1 else f"in testa {primi[0]} con {pt1} punti."))

    # la giornata che si sta giocando: se ce n'e' una, il modulo dei pronostici
    # resta chiuso finche' non finisce
    modulo = schedina.blocco(dati, adesso=adesso, endpoint=endpoint, modulo_google=MODULO,
                             in_corso=si_gioca)
    in_diretta = diretta.blocco(dati, conti=conti, adesso=adesso, endpoint=endpoint)
    avviso = _script_avviso(calendario, risultati, giornate) + _script_freschezza(aggiornato)
    # Due informazioni diverse, e servono tutte e due:
    #   la data dice quando i DATI sono cambiati l'ultima volta. Non si tocca a
    #   ogni controllo, altrimenti si farebbe un commit ogni cinque minuti;
    #   accanto, la diretta scrive quando ha parlato con Google l'ultima volta.
    #   E' la prova che il sistema e' vivo. Se resta vuoto, qualcosa non va.
    fine = (f"Dati aggiornati il {aggiornato:%d/%m/%Y} alle {aggiornato:%H:%M}"
            '<span id="controllato"></span>')

    page = template
    for k, v in [("__OG__", E(og)), ("__URL__", E(SITO)), ("__AVVISO__", avviso),
                 ("__MODULO__", modulo), ("__DIRETTA__", in_diretta),
                 ("__ANDAMENTO__", andamento),
                 ("__TAG__", tag), ("__SUB__", sub), ("__LEDE__", lede), ("__TABELLA__", tabella),
                 ("__FEATURED__", featured), ("__ARCHIVIO__", archivio_html),
                 ("__FINE__", fine)]:
        page = page.replace(k, v)
    resti = [k for k in ("__OG__", "__URL__", "__AVVISO__", "__MODULO__", "__DIRETTA__",
                         "__ANDAMENTO__", "__TAG__", "__SUB__", "__LEDE__",
                         "__TABELLA__", "__FEATURED__", "__ARCHIVIO__", "__FINE__")
             if k in page]
    assert not resti, f"segnaposto non sostituiti: {resti}"
    return page


def _script_freschezza(aggiornato):
    """Ricarica la pagina quando ne esiste una piu' nuova.

    Il browser tiene in memoria la pagina scaricata e continua a mostrarla anche
    quando sul sito ce n'e' una nuova: chi la lascia aperta la sera se la ritrova
    identica il giorno dopo, e pensa che il sistema sia fermo. Qui la pagina
    controlla da sola se e' invecchiata e in quel caso si ricarica.

    Non lo fa mai mentre qualcuno sta compilando la schedina: si perderebbe
    quello che ha scritto.
    """
    mia = f"Dati aggiornati il {aggiornato:%d/%m/%Y} alle {aggiornato:%H:%M}"
    return (
        "(function(){\n"
        f"  var MIA = {json.dumps(mia)};\n"
        "  var OGNI = 5 * 60 * 1000;\n"
        "  function stoCompilando(){\n"
        "    var f = document.getElementById('schedina');\n"
        "    return f && !f.hidden;\n"
        "  }\n"
        "  function controlla(){\n"
        "    if(document.hidden || stoCompilando()) return;\n"
        "    fetch(location.pathname + '?t=' + Date.now(), {cache: 'no-store'})\n"
        "      .then(function(r){ return r.text() })\n"
        "      .then(function(testo){\n"
        "        var trovato = testo.match(/Dati aggiornati il \\d{2}\\/\\d{2}\\/\\d{4} alle \\d{2}:\\d{2}/);\n"
        "        if(trovato && trovato[0] !== MIA) location.reload();\n"
        "      }).catch(function(){});\n"
        "  }\n"
        # subito, non fra cinque minuti: chi apre una copia vecchia tenuta dal
        # browser deve ritrovarsi quella giusta nel giro di un secondo
        "  controlla();\n"
        "  setInterval(controlla, OGNI);\n"
        "  document.addEventListener('visibilitychange', function(){ if(!document.hidden) controlla() });\n"
        "})();"
    )


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
