/**
 * Trofeo Ovalmo - riceve i pronostici mandati dal sito.
 *
 * Questo pezzo di codice NON gira su GitHub: vive dentro Google, agganciato al
 * foglio dei pronostici, ed e' l'unica cosa che sa ricevere qualcosa. Il sito
 * su GitHub Pages sa solo mostrare pagine, non puo' salvare niente.
 *
 * Cosa fa: riceve un pronostico dal sito, controlla nome e codice, e scrive
 * una riga nel foglio "Pronostici". Non restituisce mai i pronostici a nessuno:
 * si puo' solo scrivere. E' cio' che impedisce di leggere le schedine altrui
 * chiamando questo indirizzo, che sulla pagina e' pubblico.
 *
 * COME SI INSTALLA (una volta sola):
 *   1. vai su script.google.com e crea un progetto nuovo
 *   2. incolla questo file al posto di quello che c'e'
 *   3. metti l'id del foglio in ID_FOGLIO qui sotto (si legge nell'indirizzo
 *      del foglio, fra /d/ e /edit). Nel file su GitHub resta il segnaposto:
 *      l'id non e' un segreto, ma non ha motivo di stare su una pagina pubblica
 *   4. Salva, poi Distribuisci > Nuova distribuzione > tipo "App web"
 *      - Esegui come: me stesso
 *      - Chi ha accesso: Chiunque
 *   5. copia l'indirizzo che compare: va scritto in dati/stagione.json,
 *      campo endpoint_pronostici
 *
 * Se un giorno cambiano i giocatori o i codici, si modifica la tabella qui
 * sotto e si rifa' Distribuisci > Gestisci distribuzioni.
 */

// nome del giocatore -> il suo codice personale a quattro cifre.
// Questi codici NON sono pubblici: stanno solo qui dentro.
var CODICI = {
  'Berta': '2308',
  'Super Gulp': '6684',
  'Lenzuolo': '2815',
  'Just Lele': '6398',
  'Lippi': '6583'
};

// id del foglio dove finiscono i pronostici (nell'indirizzo, fra /d/ e /edit)
var ID_FOGLIO = 'INCOLLA_QUI_L_ID_DEL_FOGLIO';
var FOGLIO = 'Pronostici';
var PARTITE_PER_GIORNATA = 10;

function doPost(e) {
  try {
    var dati = JSON.parse(e.postData.contents);
    var nome = String(dati.giocatore || '').trim();
    var codice = String(dati.codice || '').trim();
    var giornata = parseInt(dati.giornata, 10);
    var pronostici = dati.pronostici || {};

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

function risposta(oggetto) {
  return ContentService
    .createTextOutput(JSON.stringify(oggetto))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Chi arriva qui col browser non deve poter leggere niente: i pronostici degli
 * altri si guardano sul sito, dopo il calcio d'inizio, e non un minuto prima.
 */
function doGet() {
  return ContentService
    .createTextOutput("Trofeo Ovalmo: qui si mandano i pronostici, non si leggono.")
    .setMimeType(ContentService.MimeType.TEXT);
}
