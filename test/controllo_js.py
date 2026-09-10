# -*- coding: utf-8 -*-
"""Un controllo minimo sul JavaScript che generiamo.

Serve a intercettare un errore che i test normali non vedono e che rompe la
pagina per intero: un apostrofo dentro una stringa fra apici singoli. In
italiano capita di continuo ("l'hai", "d'inizio", "un'ora") e il codice passa
per due livelli di virgolette prima di arrivare nel browser, quindi una barra
rovesciata si perde facilmente per strada.

E' successo davvero: "L'hai mandata" ha chiuso la stringa a meta' e tutto il
modulo dei pronostici ha smesso di funzionare. Nessun test se n'era accorto.

Non e' un interprete JavaScript: verifica soltanto che le stringhe si aprano e
si chiudano, che e' esattamente cio' che quel tipo di errore rompe.
"""


class JavaScriptRotto(Exception):
    pass


def controlla(js):
    """Alza JavaScriptRotto se una stringa resta aperta. Restituisce quante ne trova."""
    i, riga, quante = 0, 1, 0
    n = len(js)
    while i < n:
        c = js[i]
        if c == "\n":
            riga += 1
            i += 1
        elif c == "/" and i + 1 < n and js[i + 1] == "/":
            while i < n and js[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and js[i + 1] == "*":
            fine = js.find("*/", i + 2)
            if fine < 0:
                raise JavaScriptRotto(f"commento aperto e mai chiuso, riga {riga}")
            riga += js.count("\n", i, fine)
            i = fine + 2
        elif c in "'\"":
            apre, apre_riga = c, riga
            i += 1
            while True:
                if i >= n:
                    raise JavaScriptRotto(
                        f"stringa aperta con {apre} alla riga {apre_riga} e mai chiusa")
                if js[i] == "\\":
                    i += 2
                    continue
                if js[i] == "\n":
                    raise JavaScriptRotto(
                        f"stringa aperta con {apre} alla riga {apre_riga} arriva a fine riga "
                        f"senza chiudersi: quasi sempre e' un apostrofo non protetto")
                if js[i] == apre:
                    break
                i += 1
            quante += 1
            i += 1
        else:
            i += 1
    return quante


def estrai(html):
    """Il contenuto di tutti i <script> di una pagina o di un blocco."""
    pezzi, resto = [], html
    while "<script>" in resto:
        dentro = resto.split("<script>", 1)[1]
        corpo, resto = dentro.split("</script>", 1)
        pezzi.append(corpo)
    return pezzi
