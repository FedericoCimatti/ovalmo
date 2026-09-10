# Trofeo Ovalmo

Gioco di pronostici sulla Serie A fra cinque amici, con un sito che si aggiorna
da solo: **https://federicocimatti.github.io/ovalmo/**

Nessuno deve lanciare niente. Un'automazione di GitHub gira ogni ora, prende i
risultati e i pronostici, ricalcola e ripubblica la pagina solo se e' cambiato
qualcosa.

## Le regole del gioco

- **3 punti** segno e risultato esatto
- **1 punto** solo il segno giusto (non si somma ai 3)
- **0 punti** segno sbagliato, o pronostico non mandato

Deadline al primo calcio d'inizio della giornata. A pari punti passa avanti chi
ha piu' risultati esatti. "Re della giornata" e' chi fa piu' punti in una
giornata conclusa.

**I pronostici restano coperti** fino al primo calcio d'inizio: sulla pagina si
vede solo chi ha mandato (spunta) e chi no (TBD). Serve a impedire che uno copi
dagli altri, ed e' la regola da non rompere mai.

## Come funziona, in due minuti

```
football-data.org  ──┐
(calendario e        │
 risultati)          ├──>  aggiorna.py  ──>  dati/*.json  ──>  docs/index.html
                     │      (ogni ora)                          docs/Trofeo_Ovalmo.xlsx
foglio Google  ──────┘                                                │
(pronostici)                                                          v
                                                              GitHub Pages
```

I file, uno per mestiere:

| file | cosa fa |
|---|---|
| `aggiorna.py` | il giro completo. E' l'unica cosa che il robot lancia |
| `ovalmo/risultati.py` | calendario e risultati da football-data.org |
| `ovalmo/modulo.py` | legge i pronostici dal foglio Google |
| `ovalmo/schedina.py` | il modulo per mandare i pronostici, dentro la pagina |
| `ovalmo/diretta.py` | i gol e i punti che si muovono mentre si gioca |
| `google/ricevi_pronostici.gs` | lo script dentro Google che riceve i pronostici |
| `ovalmo/punteggio.py` | punti e classifica |
| `ovalmo/pagina.py` | riempie `template.html` e produce la pagina |
| `ovalmo/excel.py` | il foglio Excel con formule e grafico |
| `ovalmo/squadre.py` | tabella nomi API -> nomi italiani |
| `ovalmo/orari.py` | date, orari, fuso di Roma |
| `ovalmo/dati.py` | lettura e scrittura dei file in `dati/` |
| `dati/stagione.json` | calendario, risultati, giocatori |
| `dati/pronostici.json` | pronostici e consegne |
| `dati/stato.json` | impronte per capire se e' cambiato qualcosa |
| `docs/` | quello che il sito pubblica |
| `test/` | i test |

`docs` e' un nome brutto per la cartella del sito, ma GitHub Pages sa servire
solo dalla radice o da `docs/`: e' un vincolo loro.

## I due segreti da configurare

Si mettono in **Settings > Secrets and variables > Actions > New repository secret**.

| nome | cos'e' | dove si prende |
|---|---|---|
| `FD_TOKEN` | token di football-data.org | registrazione gratuita su football-data.org/client/register, arriva per mail |
| `FOGLIO_CSV` | indirizzo del foglio dei pronostici pubblicato in CSV | nel foglio: File > Condividi > Pubblica sul web > foglio "Pronostici" > formato "Valori separati da virgola (.csv)" > Pubblica |

L'indirizzo del foglio **non va scritto nel codice**: il repository e' pubblico
e chi ha quell'indirizzo legge tutti i pronostici, anche quelli coperti.

## L'impostazione di GitHub Pages

**Settings > Pages > Build and deployment**: Source "Deploy from a branch",
Branch `main`, cartella `/docs`, poi Save.

## Quando qualcosa va storto

Se un giro fallisce, il robot **apre una issue** sul repository (una sola, che
viene commentata ai giri successivi) e GitHub ti manda la mail. Nel frattempo
il sito continua a mostrare gli ultimi dati buoni: non diventa mai bianco.

Se i risultati smettono di arrivare, la pagina se ne accorge da sola e mostra in
cima un avviso "mancano dei risultati": e' il browser di chi guarda a
controllare, quindi funziona anche se il robot e' morto del tutto.

La pagina si ricarica anche da sola quando sul sito ne esiste una piu' nuova.
Senza, chi la lascia aperta continua a vedere la copia che il browser si e'
tenuto in memoria e pensa che il sito sia fermo - e' successo davvero, il primo
giorno. Non lo fa mentre qualcuno sta compilando la schedina.

Le cause probabili, in ordine di frequenza:

1. **Una squadra nuova non e' in tabella.** Succede dopo le promozioni. Il
   messaggio d'errore dice esattamente quale riga aggiungere in
   `ovalmo/squadre.py`.
2. **Il modulo Google non e' stato rinominato** con le partite della nuova
   giornata. Il job non importa niente e lo scrive nel riepilogo: e' voluto,
   meglio nessun dato che pronostici attribuiti alla partita sbagliata.
3. **Il foglio non e' piu' pubblicato sul web.** Ricontrolla File > Condividi >
   Pubblica sul web.
4. **Token scaduto o piano cambiato** su football-data.org.
5. **API momentaneamente giu'.** Non fare niente: il giro dopo recupera.

### Rilanciare a mano

Scheda **Actions > Aggiorna il sito > Run workflow**. E' lo stesso identico giro
di quelli automatici.

### Attenzione, una volta all'anno

GitHub **disattiva i workflow schedulati dopo 60 giorni** senza attivita' su un
repository pubblico. A stagione finita, dopo un paio di mesi di pausa estiva, il
sito si ferma: arriva una mail da GitHub e si riattiva con un clic dalla scheda
Actions. Non e' un guasto.

## Lavorare in locale

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m pytest test/ -q      # i test
./.venv/bin/python aggiorna.py             # il giro completo
```

Senza le variabili `FD_TOKEN` e `FOGLIO_CSV` il giro non si ferma: salta la
parte che non puo' fare e rigenera pagina ed Excel dai dati gia' presenti.

## Correggere un dato a mano

I dati sono file di testo: si aprono, si modificano e si committa.

- un risultato sbagliato: `dati/stagione.json`, sezione `risultati`,
  `"G03-07": [2, 1]`
- un pronostico da correggere: `dati/pronostici.json`, sezione `pronostici`,
  `"G03-07": {"Berta": ["1", 2, 1]}` (usa `null` per i campi non dati)

Il giro successivo **non** sovrascrive quello che hai scritto a mano: i
risultati vengono riscritti solo se l'API dice qualcosa di diverso, e i
pronostici non vengono mai cancellati.

## Partite rinviate

Un rinvio non blocca il sito. Quando la Lega sposta una partita, football-data
le cambia la data: da quel momento non e' piu' una partita di ieri senza
risultato, e' una partita del 24. La giornata viene considerata **chiusa**
quando tutto cio' che doveva giocarsi si e' giocato, e finisce in archivio con
scritto quale partita manca invece del re della giornata. Il re compare quando
il recupero e' stato giocato.

Nel frattempo si pronostica normalmente la giornata successiva: le due cose
sono indipendenti.

La differenza che conta: una partita di ieri **senza** risultato e senza nuova
data non e' un rinvio, e' un guasto - li' la giornata resta aperta e la pagina
mostra l'avviso "mancano dei risultati".

## Le cose che sembrano strane ma sono volute

- **L'ID di una partita e' la sua posizione nella giornata** (`G03-01`), e viene
  assegnato una volta sola alla prima importazione. Anticipi e posticipi
  cambiano le date, non i numeri: se cambiassero, tutti i pronostici gia'
  archiviati si riferirebbero alla partita sbagliata.
- **Prima del calcio d'inizio nel repository non c'e' nessun pronostico**, solo
  l'elenco di chi ha mandato. Il repository e' pubblico: se ci fossero, chiunque
  potrebbe leggerli, e anche cancellandoli resterebbero nello storico git.
- **Il file Excel si rigenera solo quando i dati cambiano.** Un `.xlsx`
  contiene degli orari suoi e cambia byte per byte a ogni generazione: senza
  questo controllo ci sarebbe un commit ogni ora, per sempre.
- **La data in fondo alla pagina non conta** per decidere se ripubblicare,
  altrimenti sarebbe sempre "cambiata".

## Come si mandano i pronostici

Direttamente sul sito. Le dieci partite compaiono da sole, prese dal calendario
dell'API: non c'e' niente da rinominare prima di ogni giornata.

Il giro completo:

```
la pagina  ->  google/ricevi_pronostici.gs  ->  foglio "Pronostici"
                                                       |
                        il giro orario lo rilegge  <---+
```

Ognuno la prima volta sceglie il suo nome e scrive un codice di quattro cifre;
il telefono se lo ricorda e non lo chiede piu'. Il pulsante **Annulla** esce e
obbliga a rimettere il codice, cosi' la schedina non resta aperta sul telefono.

**Si manda una volta sola.** Una schedina inviata non si puo' piu' correggere:
la pagina la blocca e, se qualcuno rimandasse aggirandola, il lettore tiene
comunque il PRIMO invio e ignora gli altri. Gli altri giocatori vedono che hai
mandato, mai che cosa hai scritto. I codici stanno **solo** dentro
lo script in Google, mai nella pagina: c'e' un test che lo verifica.

L'indirizzo dello script va scritto in `dati/stagione.json`, campo
`endpoint_pronostici`. Finche' e' vuoto, la pagina rimanda al vecchio modulo
Google invece di mostrare una schedina che non saprebbe dove mandare niente.

Il lettore riconosce da solo quale dei due fogli sta leggendo (vecchio modulo o
nuovo), quindi il passaggio dall'uno all'altro non richiede di cambiare codice.

## La diretta

Chi manda la schedina compare agli altri entro un minuto e mezzo - riga e
spunte verdi insieme, senza che nessuno ricarichi.

Mentre si gioca, la pagina non aspetta il giro automatico: ogni 45 secondi chiede
allo script dentro Google come vanno le partite e aggiorna punteggi, punti e
classifica sotto gli occhi di chi guarda. Si ferma da sola quando la scheda del
browser non e' in primo piano, e quando non c'e' nessuna partita in corso non
chiama nessuno.

I conti veri restano in `punteggio.py`: la diretta parte dai totali gia'
calcolati e somma soltanto le partite ancora aperte. E' quello che impedisce
alla classifica in diretta di divergere da quella vera - c'e' un test apposta.

La pagina si porta dietro **tutte** le partite non ancora giocate con i loro
orari, e quali seguire lo decide il browser mentre gira. Se lo decidesse il
generatore, una pagina rigenerata alle 16 non saprebbe di dover seguire la
partita delle 21 - ed e' esattamente quello che e' successo il 7 settembre,
quando GitHub aveva saltato quasi tutti i giri e durante Cagliari-Lecce la
diretta non era nemmeno nella pagina.

Resta un limite inevitabile: durante la PRIMA partita di una giornata si vedono
i gol ma non i punti, perche' i pronostici sono ancora coperti e non stanno
nella pagina. Compaiono al primo giro dopo il calcio d'inizio.

Serve il token di football-data anche dentro Google: **Impostazioni progetto >
Proprieta' script > FD_TOKEN**. Se manca, la diretta semplicemente non si
attiva e la pagina resta quella del giro orario.

### Cancellare un pronostico mandato per sbaglio

Cancellare la riga dal foglio **non basta**: il giro non toglie mai niente da
`dati/pronostici.json`, per non perdere dati se il foglio diventa irraggiungibile.
Vanno tolti tutti e due: la riga nel foglio "Pronostici" e la voce corrispondente
in `dati/pronostici.json` (sezione `consegne` e, se la giornata e' gia' iniziata,
anche `pronostici`).

### Se un giorno cambiano i giocatori o i codici

Si modifica la tabella in cima a `google/ricevi_pronostici.gs`, poi dentro Apps
Script: Distribuisci > Gestisci distribuzioni > modifica > Distribuisci.
