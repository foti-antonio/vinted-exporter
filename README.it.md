# Vinted Exporter — Guida italiana

**Un piccolo programma Python per esportare foto e testi degli annunci di un profilo Vinted, quando hai l'autorizzazione necessaria.**

[Read in English](README.md)

> [!WARNING]
> **Attenzione:** i [termini attuali di Vinted](https://www.vinted.com/terms-and-conditions) vietano l'uso non autorizzato di strumenti di scraping e la copia di contenuti del sito. Usa lo script solo se Vinted ha autorizzato l'automazione e possiedi i diritti sui materiali. Non è un progetto ufficiale di Vinted, non aggira CAPTCHA o controlli di accesso e potrebbe non funzionare se il sito cambia.

## Funzioni

- Cerca i link degli annunci visibili sul profilo e quelli che il sito carica scorrendo o tramite «Mostra altri», dove disponibile.
- Visita gli annunci usando Chromium visibile.
- Prova a estrarre **titolo, descrizione, prezzo, valuta, marca e foto**.
- Organizza i prodotti in cartelle separate con `descrizione.txt` e `prodotto.json`.
- Crea `indice.json`, per consultare i risultati insieme.
- Permette di specificare un numero massimo di annunci, la cartella di output e la pausa tra le visite.
- In caso di una nuova esecuzione, salta gli articoli già esportati e contrassegnati come `completo: true`.

**Stato:** versione sperimentale. I test locali non verificano la compatibilità con il sito live, che può modificare pagine e struttura senza preavviso.

## Installazione su Arch Linux

Richiede Python 3.10+ e un ambiente grafico che possa aprire Chromium.

```bash
sudo pacman -S --needed python python-pip

# Entra nella cartella del progetto
cd vinted-exporter

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Per Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd vinted-exporter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
```

Su Windows o macOS crea un ambiente virtuale e lancia `python -m pip install -r requirements.txt` e `python -m playwright install chromium` dalla cartella del progetto. Su Windows PowerShell attiva l'ambiente con `.venv\Scripts\Activate.ps1`.

## Avvio

```bash
python vinted_export.py "https://www.vinted.it/member/123456-nomeutente"
```

Per una prova con i primi 5 annunci trovati:

```bash
python vinted_export.py "https://www.vinted.it/member/123456-nomeutente" --max 5
```

Per scegliere cartella e pausa tra gli annunci:

```bash
python vinted_export.py "https://www.vinted.it/member/123456-nomeutente" --output exports/profilo --delay 4
```

Sostituisci il link d'esempio con quello di un profilo che sei autorizzato a elaborare. Il programma apre il browser e aspetta che premi **Invio nel terminale** prima di scorrere gli annunci. Non aggira CAPTCHA o limitazioni del sito.

## Parametri

| Parametro | Predefinito | Uso |
| --- | --- | --- |
| `profilo` | obbligatorio | URL HTTPS di un profilo Vinted, formato `/member/123...` |
| `--max N` | `0` | Numero massimo di annunci (`0` = nessun limite esplicito) |
| `--output CARTELLA` | `vinted_export` | Directory dei file esportati |
| `--delay SECONDI` | `2` | Pausa tra gli annunci |
| `--help` | — | Mostra la guida ai comandi |

`--max 0` si applica agli annunci individuati, **non garantisce** di trovare l'intero catalogo.

## File prodotti

```text
vinted_export/
├── 123456789-giacca-nike-blu/
│   ├── 01.webp
│   ├── 02.jpg
│   ├── descrizione.txt
│   └── prodotto.json
├── 123456790-felpa-adidas/
│   ├── 01.webp
│   ├── descrizione.txt
│   └── prodotto.json
└── indice.json
```

I file immagine possono essere JPG, PNG o WebP in base alla risposta del server: **non** vengono compressi o modificati automaticamente. Il JSON di ogni annuncio contiene `titolo`, `descrizione`, `prezzo`, `valuta`, `marca`, `urls_foto`, `id`, `url`, `foto`, `errori` e `completo`. Alcuni campi possono essere vuoti o nulli.

`completo` vale `true` solo quando la descrizione e almeno una foto sono state trovate senza errori di download. Se interrompi il processo, `indice.json` potrebbe non essere stato scritto perché viene creato alla fine del ciclo.

## Test

```bash
python -m unittest discover -s tests -v
python -m compileall -q vinted_export.py
```

I test non effettuano chiamate a Vinted e non aprono un browser.

## Problemi comuni

- **Manca Playwright:** attiva `.venv` e installa `requirements.txt`.
- **Chromium non trovato:** esegui `python -m playwright install chromium`.
- **Browser non si apre:** verifica di essere in una sessione grafica, non in un terminale remoto senza display.
- **Nessun annuncio:** verifica che gli articoli siano visibili; potrebbero essere cambiati i selettori o l'accesso potrebbe essere limitato. Non aggirare blocchi.
- **Foto o descrizioni mancanti:** non tutti i dati sono necessariamente disponibili e il sito può cambiare struttura.
- **Annuncio già esportato:** se `prodotto.json` ha `completo: true`, lo script lo salta; cancella la cartella di quel prodotto per ripetere l'esportazione.

## Privacy, utilizzo e contributi

Il codice non richiede password o token API, non usa endpoint privati e non implementa sistemi per superare anti-bot. La cartella di output di default e la cartella `exports/` sono escluse da Git, ma verifica sempre `git status` prima di pubblicare i file. Non distribuire foto o descrizioni di altre persone senza i diritti e le autorizzazioni necessari.

Issue e pull request sono benvenute se includono casi riproducibili e non pubblicano dati personali o materiale di altri venditori. Non sono accettate modifiche per aggirare CAPTCHA, autenticazione o limitazioni del sito.

## Licenza

Il **codice** è distribuito con licenza MIT: consulta [LICENSE](LICENSE). Foto e testi degli annunci non diventano riutilizzabili per effetto di questa licenza.
