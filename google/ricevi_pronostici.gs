/**
 * Trofeo Ovalmo - lo script che vive dentro Google.
 *
 * Fa tre cose, e nessuna delle tre potrebbe farla il sito da solo, perche'
 * GitHub Pages sa soltanto mostrare pagine:
 *
 *   RICEVE i pronostici mandati dalla pagina (doPost) e li scrive nel foglio
 *   "Pronostici". Non li restituisce mai a nessuno: si puo' solo scrivere.
 *
 *   RACCONTA alla pagina come vanno le partite adesso (doGet), cosi' i gol e i
 *   punti si vedono in diretta senza aspettare il giro orario. Restituisce i
 *   risultati e i NOMI di chi ha gia' consegnato: mai il contenuto di una
 *   schedina, che resta coperto fino al calcio d'inizio come sempre.
 *
 *   SVEGLIA IL SITO ogni cinque minuti (svegliaIlSito). GitHub ha una sua
 *   pianificazione, ma non la rispetta: ne chiedevamo 180 giri al giorno e ne
 *   faceva partire cinque, con due o tre ore di buco in mezzo. Risultato: il
 *   venerdi' i pronostici si svelavano cinquanta minuti dopo il calcio
 *   d'inizio invece che subito. Le sveglie di Google invece partono davvero,
 *   e un giro chiesto a mano GitHub lo esegue sempre.
 *
 * I due token non stanno qui dentro: stanno nelle proprieta' del progetto
 * (Impostazioni progetto > Proprieta' script), cosi' non finiscono ne' su
 * GitHub ne' sotto gli occhi di chi apre questo file. Servono FD_TOKEN, per
 * football-data, e GH_TOKEN, per svegliare il sito.
 *
 * COME SI INSTALLA (una volta sola):
 *   1. vai su script.google.com e crea un progetto nuovo
 *   2. incolla questo file al posto di quello che c'e'
 *   3. metti l'id del foglio in ID_FOGLIO (si legge nell'indirizzo del foglio,
 *      fra /d/ e /edit) e i codici veri in CODICI. Nel file su GitHub restano
 *      i segnaposto: il repository e' pubblico
 *   4. Impostazioni progetto > Proprieta' script > aggiungi FD_TOKEN
 *   5. Salva, poi Distribuisci > Nuova distribuzione > tipo "App web"
 *      - Esegui come: me stesso
 *      - Chi ha accesso: Chiunque
 *   6. copia l'indirizzo: va scritto in dati/stagione.json, endpoint_pronostici
 *   7. per la sveglia: crea su GitHub un token (Settings > Developer settings >
 *      Personal access tokens > Fine-grained), dandogli accesso al solo
 *      repository "ovalmo" e il solo permesso "Actions: Read and write".
 *      Mettilo nelle Proprieta' script come GH_TOKEN
 *   8. sempre qui: icona dell'orologio (Attivazioni) > Aggiungi attivazione >
 *      funzione "svegliaIlSito", origine "A tempo", "Timer a minuti",
 *      "Ogni 5 minuti"
 *
 * ATTENZIONE: modificare il codice non basta perche' cambi quello che la
 * PAGINA vede. La distribuzione resta ferma alla versione vecchia finche' non
 * fai Distribuisci > Gestisci distribuzioni > matita > Versione: Nuova
 * versione > Distribuisci. (La sveglia no: le attivazioni a tempo eseguono
 * sempre il codice salvato, quindi per quella basta salvare.)
 */

// nome del giocatore -> il suo codice personale a quattro cifre.
//
// ATTENZIONE: questo file sta su GitHub, che e' pubblico. I codici veri NON
// vanno scritti qui: si mettono solo nella copia che vive dentro Google, dove
// li vede soltanto chi ha accesso all'account. Qui restano i segnaposto.
// Se un codice finisse in questo file, chiunque potrebbe mandare pronostici
// fingendosi qualcun altro.
var CODICI = {
  'Berta': 'XXXX',
  'Super Gulp': 'XXXX',
  'Lenzuolo': 'XXXX',
  'Just Lele': 'XXXX',
  'Lippi': 'XXXX'
};

// id del foglio dei pronostici (nell'indirizzo del foglio, fra /d/ e /edit)
var ID_FOGLIO = 'INCOLLA_QUI_L_ID_DEL_FOGLIO';
var FOGLIO = 'Pronostici';
var PARTITE_PER_GIORNATA = 10;
var COMPETIZIONE = 'SA';
// per quanti secondi si tiene buona la risposta di football-data: con cinque
// persone che guardano, l'API viene chiamata due volte al minuto invece di
// dieci. Il limite del piano gratuito e' 10 richieste al minuto.
var CACHE_SECONDI = 30;


// ===========================================================================
// RICEVERE I PRONOSTICI
// ===========================================================================

function doPost(e) {
  try {
    var dati = JSON.parse(e.postData.contents);
    var nome = String(dati.giocatore || '').trim();
    var codice = String(dati.codice || '').trim();
    var giornata = parseInt(dati.giornata, 10);
    var pronostici = dati.pronostici || {};

    // La pagina chiede qui se il codice e' giusto, prima di aprire la schedina.
    // Senza questo, chiunque potrebbe aprire la schedina di chiunque: il codice
    // verrebbe controllato solo all'invio, cioe' troppo tardi.
    if (dati.azione === 'controlla') {
      return risposta({ok: !!CODICI[nome] && CODICI[nome] === codice});
    }

    if (!CODICI[nome]) return risposta({ok: false, errore: 'nome sconosciuto'});
    if (CODICI[nome] !== codice) return risposta({ok: false, errore: 'codice sbagliato'});
    if (!(giornata >= 1 && giornata <= 38)) return risposta({ok: false, errore: 'giornata non valida'});

    var foglio = preparaFoglio();
    var riga = [new Date().toISOString(), nome, giornata];
    for (var i = 1; i <= PARTITE_PER_GIORNATA; i++) {
      var chiave = 'P' + (i < 10 ? '0' + i : i);
      riga.push(String(pronostici[chiave] || '').substring(0, 20));
    }
    foglio.appendRow(riga);
    return risposta({ok: true});
  } catch (errore) {
    return risposta({ok: false, errore: String(errore)});
  }
}

/** Il foglio dove finiscono i pronostici, creato al primo invio. */
function preparaFoglio() {
  var libro = SpreadsheetApp.openById(ID_FOGLIO);
  var foglio = libro.getSheetByName(FOGLIO);
  if (!foglio) {
    foglio = libro.insertSheet(FOGLIO);
    var intestazioni = ['Timestamp', 'Giocatore', 'Giornata'];
    for (var i = 1; i <= PARTITE_PER_GIORNATA; i++) {
      intestazioni.push('P' + (i < 10 ? '0' + i : i));
    }
    foglio.appendRow(intestazioni);
    foglio.setFrozenRows(1);
  }
  return foglio;
}


// ===========================================================================
// RACCONTARE COME VA ADESSO
// ===========================================================================

/**
 * Risponde alla pagina con i risultati aggiornati e i nomi di chi ha consegnato.
 *
 * Quello che NON esce mai da qui e' il contenuto delle schedine: chi chiama
 * questo indirizzo ottiene soltanto nomi e punteggi delle partite.
 */
function doGet(e) {
  var azione = (e && e.parameter && e.parameter.azione) || '';
  if (azione !== 'stato') {
    return ContentService
      .createTextOutput('Trofeo Ovalmo: qui si mandano i pronostici, non si leggono.')
      .setMimeType(ContentService.MimeType.TEXT);
  }
  try {
    return risposta({
      ok: true,
      adesso: new Date().toISOString(),
      partite: partiteDiOggi(),
      consegne: chiHaConsegnato()
    });
  } catch (errore) {
    return risposta({ok: false, errore: String(errore)});
  }
}

/** I risultati correnti, presi da football-data e tenuti in cache 30 secondi. */
function partiteDiOggi() {
  var cache = CacheService.getScriptCache();
  var pronta = cache.get('partite');
  if (pronta) return JSON.parse(pronta);

  var token = PropertiesService.getScriptProperties().getProperty('FD_TOKEN');
  if (!token) throw new Error('manca la proprieta di script FD_TOKEN');

  var oggi = Utilities.formatDate(new Date(), 'Europe/Rome', 'yyyy-MM-dd');
  var ieri = Utilities.formatDate(new Date(Date.now() - 36 * 3600 * 1000), 'Europe/Rome', 'yyyy-MM-dd');
  var url = 'https://api.football-data.org/v4/competitions/' + COMPETIZIONE +
            '/matches?dateFrom=' + ieri + '&dateTo=' + oggi;
  var risp = UrlFetchApp.fetch(url, {
    headers: {'X-Auth-Token': token},
    muteHttpExceptions: true
  });
  if (risp.getResponseCode() !== 200) {
    throw new Error('football-data ha risposto ' + risp.getResponseCode());
  }
  var partite = (JSON.parse(risp.getContentText()).matches || []).map(function(m) {
    var pieno = (m.score && m.score.fullTime) || {};
    return {
      giornata: m.matchday,
      casa: m.homeTeam.name,
      ospite: m.awayTeam.name,
      stato: m.status,
      gol: (pieno.home === null || pieno.home === undefined) ? null : [pieno.home, pieno.away]
    };
  });
  cache.put('partite', JSON.stringify(partite), CACHE_SECONDI);
  return partite;
}

/** {giornata: [nomi]} di chi ha gia' mandato. Solo i nomi. */
function chiHaConsegnato() {
  var foglio = SpreadsheetApp.openById(ID_FOGLIO).getSheetByName(FOGLIO);
  if (!foglio) return {};
  var righe = foglio.getDataRange().getValues();
  var fuori = {};
  for (var i = 1; i < righe.length; i++) {
    var nome = String(righe[i][1] || '').trim();
    var giornata = String(righe[i][2] || '').trim();
    if (!nome || !giornata) continue;
    if (!fuori[giornata]) fuori[giornata] = [];
    if (fuori[giornata].indexOf(nome) < 0) fuori[giornata].push(nome);
  }
  return fuori;
}

function risposta(oggetto) {
  return ContentService
    .createTextOutput(JSON.stringify(oggetto))
    .setMimeType(ContentService.MimeType.JSON);
}


// ===========================================================================
// SVEGLIARE IL SITO
// ===========================================================================

var GH_REPO = 'FedericoCimatti/ovalmo';
// il nome del FILE del workflow, non il titolo che si legge nella scheda Actions
var GH_WORKFLOW = 'aggiorna.yml';
var GH_RAMO = 'main';
// dalle 9 all'una di notte, ora italiana: nel mezzo non si gioca e non si
// consegna, e un giro a vuoto alle quattro del mattino non serve a nessuno
var SVEGLIA_DA = 9, SVEGLIA_A = 1;

/**
 * Chiede a GitHub di rigenerare il sito. La chiama l'attivazione a tempo.
 *
 * E' una richiesta esplicita, non una pianificazione: quelle GitHub le esegue
 * sempre. E' lo stesso pulsante "Run workflow" della scheda Actions.
 *
 * Il token puo' fare una cosa sola, su questo solo repository: far partire i
 * giri. Non legge il codice, non lo modifica, non vede gli altri segreti.
 */
function svegliaIlSito() {
  var ora = Number(Utilities.formatDate(new Date(), 'Europe/Rome', 'H'));
  if (!(ora >= SVEGLIA_DA || ora <= SVEGLIA_A)) return;

  var proprieta = PropertiesService.getScriptProperties();
  var token = proprieta.getProperty('GH_TOKEN');
  if (!token) {
    // Senza token la sveglia non suona, ma non si ferma con un errore: il
    // resto dello script (i pronostici, la diretta) deve continuare a
    // funzionare comunque. Lo SCRIVE pero', perche' una funzione che parte,
    // finisce subito e non dice niente e' impossibile da capire da fuori.
    // Si stampano i NOMI delle proprieta', mai i valori: servono a scoprire
    // un GH-TOKEN scritto col trattino sbagliato, e non sono segreti.
    console.warn('manca GH_TOKEN nelle Proprieta script, la sveglia non fa niente. ' +
                 'Qui dentro trovo: ' + (Object.keys(proprieta.getProperties()).join(', ') || 'niente'));
    return;
  }

  var url = 'https://api.github.com/repos/' + GH_REPO +
            '/actions/workflows/' + GH_WORKFLOW + '/dispatches';
  var risp = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: {Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json'},
    payload: JSON.stringify({ref: GH_RAMO}),
    muteHttpExceptions: true
  });

  var codice = risp.getResponseCode();
  if (codice === 204) return;          // 204 = accettato, e' l'esito giusto

  // Un token scaduto, revocato o senza il permesso giusto da' 401, 403 o 404
  // (GitHub risponde 404 anche quando il token non basta, per non far sapere
  // a un estraneo che il repository esiste). Sono guasti che non passano da
  // soli: meglio fermarsi, cosi' Google manda la mail di errore e si scopre
  // subito invece che dopo settimane di sito fermo.
  if (codice === 401 || codice === 403 || codice === 404) {
    throw new Error('GitHub ha rifiutato la sveglia (' + codice + '): controlla GH_TOKEN ' +
                    'nelle Proprieta script, e che abbia il permesso Actions sul repository ' +
                    GH_REPO + '. Risposta: ' + risp.getContentText().slice(0, 300));
  }
  // tutto il resto (500, timeout, GitHub che fa i capricci) passa da solo:
  // fra cinque minuti ci riprova
  console.warn('sveglia non riuscita, riprovo al prossimo giro: ' + codice);
}
