/**
 * Trofeo Ovalmo - lo script che vive dentro Google.
 *
 * Fa due cose, e nessuna delle due potrebbe farla il sito da solo, perche'
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
 * Il token di football-data non sta qui dentro: sta nelle proprieta' del
 * progetto (Impostazioni progetto > Proprieta' script > FD_TOKEN), cosi' non
 * finisce ne' su GitHub ne' sotto gli occhi di chi apre questo file.
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
 *
 * ATTENZIONE: modificare il codice non basta. La distribuzione resta ferma
 * alla versione vecchia finche' non fai Distribuisci > Gestisci distribuzioni >
 * matita > Versione: Nuova versione > Distribuisci.
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
