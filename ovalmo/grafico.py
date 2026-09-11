# -*- coding: utf-8 -*-
"""L'andamento della classifica: una linea per giocatore, giornata per giornata.

E' l'unico disegno del sito, e racconta una cosa che i numeri da soli non
dicono: non chi e' davanti adesso, ma come ci e' arrivato. Le rimonte, i
crolli, chi e' scappato a novembre e chi l'ha ripreso a febbraio.

E' un SVG scritto a mano, senza librerie: pesa un paio di kilobyte, funziona
senza rete e cambia colore da solo fra tema chiaro e scuro come il resto della
pagina.

DUE COSE DA SAPERE SE UN GIORNO LO SI TOCCA

  La scala verticale ha gia' dentro lo spazio per i punti che le partite in
  corso possono ancora aggiungere. Serve perche' durante le partite la diretta
  muove l'ultimo punto di ogni linea a ogni gol: se la scala cambiasse, il
  grafico intero dovrebbe essere ridisegnato, e le due versioni (questa e
  quella nel browser) potrebbero divergere. Cosi' invece la geometria e' decisa
  una volta sola, qui.

  I colori sono quelli della tavolozza validata per daltonismo e contrasto, in
  ordine fisso: il primo giocatore prende sempre il primo colore. Non vanno
  riciclati ne' riordinati, altrimenti la stessa persona cambia colore da una
  giornata all'altra.
"""
import html
import json

E = html.escape

# tavolozza categoriale validata (blu, arancio, acqua, giallo, magenta):
# ordine fisso, un colore per giocatore, mai riciclati
COLORI = ["--gr1", "--gr2", "--gr3", "--gr4", "--gr5"]

LARGHEZZA, ALTEZZA = 720, 340
SOPRA, SOTTO, SINISTRA, DESTRA = 16, 30, 34, 14
# quanti punti puo' ancora fruttare una partita ancora aperta: 6, cioe' il
# risultato esatto indovinato da solo (vedi punteggio.CORAGGIO_DA)
MASSIMO_PER_PARTITA = 6


def _passo(ymax):
    """Ogni quanto mettere una tacca: numeri tondi, mai multipli di 6 o di 7."""
    for soglia, passo in ((30, 5), (60, 10), (150, 20), (300, 50), (600, 100)):
        if ymax <= soglia:
            return passo
    return 200


def _scala(massimo):
    """Il valore piu' alto dell'asse verticale: tondo, e mai sotto 5."""
    grezzo = max(5, massimo)
    passo = _passo(grezzo)
    return -(-grezzo // passo) * passo


def disegna(conti, giocatori, aperte_ora=0, giornata_viva=None):
    """L'HTML del grafico. Stringa vuota se non c'e' ancora niente da mostrare.

    aperte_ora   quante partite possono ancora dare punti adesso: serve a
                 lasciare spazio in alto, cosi' la scala non cambia mentre si gioca
    giornata_viva la giornata che si sta giocando. Va nel grafico anche se non ha
                 ancora nessun risultato: e' il punto che la diretta fa salire a
                 ogni gol, e senza di lui quei punti finirebbero sulla giornata
                 precedente, che e' gia' chiusa
    """
    giornate = [g for g in conti["giornate"]
                if conti["giocate_g"][g] > 0 or g == giornata_viva]
    if len(giornate) < 2:
        return ""          # con un punto solo non c'e' nessun andamento da vedere

    serie, totale = {}, {}
    for p in giocatori:
        corrente, valori = 0, []
        for g in giornate:
            corrente += conti["per_g"][g][p]
            valori.append(corrente)
        serie[p] = valori
        totale[p] = corrente

    ymax = _scala(max(totale.values()) + MASSIMO_PER_PARTITA * aperte_ora)
    dentro_x = LARGHEZZA - SINISTRA - DESTRA
    dentro_y = ALTEZZA - SOPRA - SOTTO
    passo = dentro_x / max(1, len(giornate) - 1)
    xs = [round(SINISTRA + i * passo, 1) for i in range(len(giornate))]

    def y(valore):
        return round(ALTEZZA - SOTTO - (valore / ymax) * dentro_y, 1)

    # ---- griglia e assi, in secondo piano ----
    pezzi = []
    for tacca in range(0, ymax + 1, _passo(ymax)):
        yy = y(tacca)
        pezzi.append(f'<line class="griglia" x1="{SINISTRA}" y1="{yy}" '
                     f'x2="{LARGHEZZA - DESTRA}" y2="{yy}"/>')
        pezzi.append(f'<text class="tacca" x="{SINISTRA - 8}" y="{yy + 4}" '
                     f'text-anchor="end">{tacca}</text>')
    # le giornate sull'asse: tutte se sono poche, altrimenti una ogni tot
    salto = 1 if len(giornate) <= 12 else (len(giornate) + 11) // 12
    for i, g in enumerate(giornate):
        if i % salto and i != len(giornate) - 1:
            continue
        pezzi.append(f'<text class="tacca" x="{xs[i]}" y="{ALTEZZA - 10}" '
                     f'text-anchor="middle">{g}</text>')

    # ---- le linee ----
    for n, p in enumerate(giocatori):
        colore = f"var({COLORI[n % len(COLORI)]})"
        punti = " ".join(f"{xs[i]},{y(v)}" for i, v in enumerate(serie[p]))
        pezzi.append(f'<polyline class="linea" data-chi="{E(p)}" points="{punti}" '
                     f'stroke="{colore}"/>')
        pezzi.append(f'<circle class="punta" data-chi="{E(p)}" cx="{xs[-1]}" '
                     f'cy="{y(serie[p][-1])}" r="4.5" fill="{colore}"/>')

    # ---- legenda: il nome porta l'identita', il numero resta in inchiostro ----
    voci = []
    for n, p in enumerate(giocatori):
        colore = f"var({COLORI[n % len(COLORI)]})"
        voci.append(f'<span class="voce"><i style="background:{colore}"></i>'
                    f'{E(p)} <b data-tot="{E(p)}">{totale[p]}</b></span>')

    # La geometria sta nel DOM, non in una variabile: cosi' il disegno qui e la
    # diretta nel browser leggono la stessa fonte, e quando i punti si muovono
    # non ci sono due copie che possono divergere.
    cfg = E(json.dumps({
        "xs": xs, "giornate": giornate, "ymax": ymax,
        "y0": ALTEZZA - SOTTO, "dentroY": dentro_y,
        "serie": serie, "giocatori": giocatori,
    }, ensure_ascii=False), quote=True)

    return f"""<details class="g andamento">
      <summary><span class="gname">Andamento</span>
      <span class="gre">chi era davanti,<br>giornata per giornata</span>
      <span class="caret">&rsaquo;</span></summary>
      <div class="gbody">
        <div class="graf">
          <svg id="andamento" data-cfg="{cfg}" viewBox="0 0 {LARGHEZZA} {ALTEZZA}" role="img"
               aria-label="Punti accumulati da ogni giocatore, giornata per giornata">
            {"".join(pezzi)}
            <line class="mirino" x1="0" y1="{SOPRA}" x2="0" y2="{ALTEZZA - SOTTO}" hidden/>
          </svg>
          <div class="bolla" id="bolla" hidden></div>
        </div>
        <div class="leg">{"".join(voci)}</div>
      </div>
    </details>
    <script>{_script()}</script>"""


def _script():
    """Il mirino che segue il dito, e i numeri della giornata toccata."""
    return """
(function(){
  var svg = document.getElementById('andamento');
  var bolla = document.getElementById('bolla');
  if(!svg || !bolla) return;
  function config(){ try { return JSON.parse(svg.dataset.cfg) } catch(e){ return null } }
  var mirino = svg.querySelector('.mirino');

  function vicino(G, px){
    var quale = 0, minimo = Infinity;
    G.xs.forEach(function(x, i){
      var d = Math.abs(x - px);
      if(d < minimo){ minimo = d; quale = i }
    });
    return quale;
  }

  function mostra(ev){
    var G = config();
    if(!G) return;
    var r = svg.getBoundingClientRect();
    var px = (ev.clientX - r.left) / r.width * svg.viewBox.baseVal.width;
    var i = vicino(G, px);
    mirino.setAttribute('x1', G.xs[i]);
    mirino.setAttribute('x2', G.xs[i]);
    mirino.hidden = false;
    var righe = G.giocatori.map(function(p){
      return {chi: p, pt: G.serie[p][i]};
    }).sort(function(a, b){ return b.pt - a.pt });
    bolla.innerHTML = '<b>Giornata ' + G.giornate[i] + '</b>' +
      righe.map(function(r){ return '<span>' + r.chi + ' <b>' + r.pt + '</b></span>' }).join('');
    bolla.hidden = false;
    bolla.style.left = Math.min(Math.max(G.xs[i] / svg.viewBox.baseVal.width * 100, 12), 88) + '%';
  }

  function nascondi(){ mirino.hidden = true; bolla.hidden = true }

  svg.addEventListener('pointermove', mostra);
  svg.addEventListener('pointerdown', mostra);
  svg.addEventListener('pointerleave', nascondi);
  svg.addEventListener('pointercancel', nascondi);
})();
"""
