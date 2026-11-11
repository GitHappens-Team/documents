# Documents

Repo per la documentazione del team Git Happens SWE 2026-2027 | 1o Lotto.

_La seguente guida assume la clonazione locale del repository per apportarne modifiche. L'uso di strumenti di editing online previsti da GitHub è sconsigliato se non per piccole modifiche a file pre-esistenti._

_Per ogni dubbio fare riferimento al doc. di Norme del Progetto_

## Utilizzo del repository

### 1. Preparazione dell'ambiente locale

1. Assicurarsi di disporre di un'installazione di git autorizzata presso l'organizzazione del team.
2. Clonare il repository corrente
3. (Consigliato) Al fine di poter accedere alla preview in tempo reale delle proprie modifiche, installare l'estensione [Latex Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop) per Visual Studio Code e i suoi prerequisiti.

#### Prerequisiti dell'estensione

L'estensione richiede una distribuzione LaTeX completa e alcuni strumenti di supporto:

- **Distribuzione TeX** (fornisce `pdflatex`, `bibtex`, ecc.);
- **`latexmk`**, usato dall'estensione per compilare i documenti (richiede **Perl**);
- **`chktex`** (opzionale), per il linting del codice;
- **`latexindent`** (opzionale), per la formattazione automatica (richiede Perl).

Dopo l'installazione, **riavviare Visual Studio Code** (o il terminale) in modo che i nuovi comandi risultino nel `PATH`, e verificare con:

```bash
pdflatex --version
latexmk --version
```

##### Windows

1. Installare [MiKTeX](https://miktex.org/download) e [Strawberry Perl](https://strawberryperl.com/). Da PowerShell:

   ```powershell
   winget install MiKTeX.MiKTeX
   winget install StrawberryPerl.StrawberryPerl
   ```

2. Aprire la _MiKTeX Console_ e impostare **Settings → General → Install missing packages on-the-fly** su **Always**, così i pacchetti mancanti vengono scaricati automaticamente alla prima compilazione.
3. Da _MiKTeX Console_, nella scheda **Packages**, assicurarsi che siano installati `latexmk`, `chktex` e `latexindent`.

##### macOS

1. Installare [Homebrew](https://brew.sh/), poi [BasicTeX](https://tug.org/mactex/morepackages.html) (distribuzione leggera, richiede la password di amministratore):

   ```bash
   brew install --cask basictex
   ```

2. Aprire un nuovo terminale (così `/Library/TeX/texbin` entra nel `PATH`) e installare gli strumenti e i pacchetti necessari:

   ```bash
   sudo tlmgr update --self
   sudo tlmgr install latexmk latexindent chktex biber collection-latexrecommended collection-latexextra collection-fontsrecommended collection-langitalian
   ```

   In alternativa è possibile installare la distribuzione completa (circa 5 GB) con `brew install --cask mactex-no-gui`.

##### Linux

Installare i pacchetti dal gestore della propria distribuzione. Perl è già presente nella maggior parte delle distribuzioni.

- **Debian / Ubuntu**

   ```bash
   sudo apt update
   sudo apt install texlive-latex-extra texlive-fonts-recommended texlive-lang-italian latexmk chktex perl
   ```

- **Fedora**

   ```bash
   sudo dnf install texlive-scheme-medium latexmk perl-Log-Dispatch perl-File-HomeDir perl-Unicode-LineBreak perl-YAML-Tiny
   ```

- **Arch Linux**

   ```bash
   sudo pacman -S texlive texlive-lang chktex
   ```

#### Installazione dell'estensione

Da Visual Studio Code aprire la scheda _Extensions_, cercare **LaTeX Workshop** (autore: James Yu) e premere **Install**. In alternativa, da terminale:

```bash
code --install-extension James-Yu.latex-workshop
```

Aprendo un file `.tex` e salvandolo, il documento viene compilato e la preview PDF è disponibile dal pulsante _View LaTeX PDF_ o con `Ctrl+Alt+V` (`Cmd+Option+V` su macOS).

### 2. Struttura standard dei documenti

_in accordo con il doc. di norme di progetto_

Le cartelle root del repository (eccetto quelle di sistema, quali ".vscode", ".latex", ".github") costituiscono una categoria di documenti e saranno visualizzate nel sito come tali.
Ogni sotto cartella è considerata una sottocategoria, a meno che non contenga direttamente un documento.

Ogni documento è costituito da un file `main.tex` contenuto in una cartella il cui nome corrisponde al nome del documento, fatta eccezione per l'uso del carattere underscore "\_" al posto degli spazi.
L'uso dell'underscore si applica anche a categorie e sottocategorie. Il sito web inverte questa sostituzione in automatico per una miglior visualizzazione.

Oltre al file `main.tex`, ogni documento possiede un file `metadata.json`, una cartella `capitoli` e opzionalmente una cartella `assets`.
Di seguito il ruolo di ognuno di questi elementi:

- `main.tex`: contiene la chiamata al template di documento, le istruzioni di definizione titolo, autore, scopo, destinatari, ecc.. . Contiene anche le inclusioni dei vari capitoli definiti nella cartella omonima.
- `capitoli`: contiene file nominati `xx_nome.tex`, dove `xx` è un numero espresso in 2 cifre (e.g. `01`) che rappresenta il numero di sequenza di capitolo a partire da `00`.
- `assets`: qualora presenti, contiene immagini/allegati. Le immagini e gli asset più comuni riguardanti il team sono raggiungibili dalla cartella `.latex/assets` nel root del repository.
- `metadata.json`: contiene informazioni aggiuntive volte ad una migliore e più informativa visualizzazione presso il sito web di documentazione.

#### Eccezioni alla struttura

In caso di documenti consolidati e non modificabili (e.g. verbali o documenti firmati) è possibile inserire un documento .pdf semplicemente accompagnato dal file `metadata.json`.
Il funzionamento delle directory resta invariato.

#### main.tex

Il file `main.tex` si compone, nell'ordine, di: dichiarazione del template, (eventuali) pacchetti aggiuntivi, comandi di intestazione, corpo del documento.

Esempio di `main.tex` valido (verbale interno):

```latex
\documentclass{gh}

\tipodoc{Verbale Interno}
\datadoc{03/11/2026}
\modalita{In presenza}
\redattori{G. Grinovero}
\verificatori{G. Gambarro}
\amministratore{T. Caon}
\responsabile{D. Grosselle}
\destinatari{Prof. T. Vardanega \\ Prof. R. Cardin}
\partecipanti{D. Grosselle \\ G. Grinovero \\ C. Antoniazzo}

\begin{document}

\makeheader
\input{capitoli/02_modifiche.tex}
\input{capitoli/03_indice.tex}
\input{capitoli/04_attivita.tex}
\input{capitoli/05_ToDo.tex}

\end{document}
```

Un template di partenza per i verbali è disponibile in `.latex/template-verbale`.

##### Template `gh`

La prima istruzione è sempre `\documentclass{gh}`. La classe `gh` (file `.latex/gh.cls`) estende `article` (11pt, A4) e carica in automatico lingua italiana, margini, intestazione/piè di pagina con logo, collegamenti ipertestuali e i pacchetti `graphicx`, `tabularx`, `booktabs`, `fancyhdr`, `hyperref`, `xcolor`, `tikz` e `xspace`. Non è quindi necessario ricaricarli.

Pacchetti ulteriori richiesti da un singolo documento (e.g. `\usepackage{eurosym}`, `\usepackage{longtable}`, `\usepackage{numprint}`) vanno dichiarati subito dopo `\documentclass{gh}`.

##### Comandi di intestazione

Vanno inseriti prima di `\begin{document}`. Tutti sono opzionali: **una riga della tabella "Informazioni documento" compare in prima pagina solo se il relativo comando è presente**. Per inserire più valori in un campo, separarli con `\\` (e.g. `\redattori{F. Lissandrin \\ G. Gambarro}`).

| Comando                | Descrizione                                                          | Compare in                                   |
| ---------------------- | -------------------------------------------------------------------- | -------------------------------------------- |
| `\tipodoc{...}`        | Tipo/titolo del documento (e.g. `Verbale Interno`)                   | Titolo di prima pagina e piè di pagina       |
| `\datadoc{...}`        | Data del documento, formato `GG/MM/AAAA`                             | Titolo di prima pagina (`Data: ...`)         |
| `\versione{...}`       | Versione corrente, formato `x.y.z`                                   | Riga "Versione"                              |
| `\modalita{...}`       | Modalità di svolgimento (e.g. `Online - Google Meet`, `In presenza`) | Riga "Modalità"                              |
| `\orario{...}`         | Orario di inizio e fine (e.g. `HH:MM - HH:MM`)                       | Riga "Orario"                                |
| `\redattori{...}`      | Redattori del documento                                              | Riga "Redattori"                             |
| `\verificatori{...}`   | Verificatori del documento                                           | Riga "Verificatori"                          |
| `\amministratore{...}` | Amministratore del gruppo                                            | Riga "Amministratore"                        |
| `\responsabile{...}`   | Responsabile del gruppo                                              | Riga "Responsabile" e piè della prima pagina |
| `\destinatari{...}`    | Destinatari del documento                                            | Riga "Destinatari"                           |
| `\partecipanti{...}`   | Partecipanti alla riunione (verbali)                                 | Riga "Partecipanti"                          |

I valori dei campi vanno scritti nel formato `N. Cognome` per le persone (e.g. `F. Lissandrin`) e `Prof. N. Cognome` per i docenti.

##### Altri comandi del template

- `\makeheader`: da inserire subito dopo `\begin{document}`. Genera la prima pagina (logo, contatti, titolo e tabella "Informazioni documento") e termina con un salto pagina.
- `\lista{A \\ B}`: mostra più righe all'interno di una cella di tabella; utile per riportare elenchi (e.g. nomi) in una colonna di `tabularx`.
- `\documento`: contiene il valore impostato con `\tipodoc` ed è utilizzabile nel testo (e.g. per richiamare il nome del documento).

I comandi `\inforow` e `\@ifdatadoc` sono ad uso interno della classe e non vanno utilizzati nei documenti.

##### Corpo del documento

Dopo `\makeheader` si includono, nell'ordine, i capitoli presenti nella cartella `capitoli` con `\input{capitoli/xx_nome.tex}`. Se il documento prevede un indice, inserire `\tableofcontents` (seguito da `\newpage`) subito dopo il registro delle modifiche, come fanno i documenti in `candidatura/`.

Le immagini del team (`Logo.png`, `LogoNoBg.png`, `LogoSmall.png`, `LogoSmallNoBg.png`) sono raggiungibili dalla cartella `.latex/assets` e non vanno copiate nei singoli documenti.

##### Compilazione

L'estensione e il workflow di GitHub Actions compilano `main.tex` con `latexmk`, includendo la cartella `.latex` nel percorso di ricerca dei file (`TEXINPUTS`), così che `gh.cls` e le immagini del team siano sempre trovati. Per compilare manualmente da terminale:

```bash
.latex/build.sh <cartella-documento>
```

#### metadata.json

Campi utili al sito web in formato `json`.
Esempio di `metadata.json` valido:

```json
{
	"title": "Definizione del Way Of Working",
	"description": "Documento di definizione incrementale del way of working.",
	"important": true,
	"version": {
		"version": "0.0.1",
		"atTimestamp": "2026-10-28T00:00:00Z"
	}
}
```

Campi, valori e loro tipo/formato:

- `title` (string): Titolo UTF-8 del documento;
- `description` (string): Descrizione UTF-8 del documento;
- `important` (bool): `true` se è un documento di rilievo nel progetto, `false` se è un documento ordinario o secondario.
- `version` (object):
   - `version`: numero di versione in formato `x.y.z` (vedi documento di norme di progetto, sez. di versionamento)
   - `atTimestamp`: data di assegnamento della versione `version` in formato ISO 8601 UTC (usare la mezzanotte UTC in caso di assenza di informazioni orarie specifiche).

#### Checklist di creazione file

1. Creare/aprire la cartella di categoria e sottocategoria (se presente) del documento;
2. Creare una cartella denominata `nome_del_documento`;
3. Creare il file `main.tex`, seguire le istruzioni di compilazione preliminare al punto sopra;
4. Creare la cartella `capitoli` e un file per ogni capitolo, poi importarla nel file `main.tex` seguendo le convenzioni definite nel documento di norme di progetto e riportate nei punti superiori;
5. Creare il file `metadata.json` e compilarlo in modo appropriato.

### 3. Contribuzione

Seguire la sezione di contribuzione del documento di norme del progetto, in particolare la procedura di branch-out, commit semantiche e creazione di PR.

Alla creazione della pull request (e ad ogni successivo commit in essa) si attiva l'automazione di build automatica dei pdf.
Ogni file `main.tex` viene compilato nel pdf finale.
I file di output del processo di build sono ispezionabili tramite gli _artifacts_ della _GitHub Action_, utile a scopo di revisione pre-merge.

#### Merge della PR verso il branch `main`

Al merge di ogni PR si innesca nuovamente il processo di build.
Al termine di esso, solo all'interno del branch main, si attiva l'automazione di `deploy` che effettua una commit nel branch `main` della repository contenente il sito web pubblico.

Tale commit aggiorna i pdf disponibili nel sito, i metadati auto generati (data di creazione, data di approvazione e revisori della PR) per ogni documento e i metadati forniti tramite i file `metadata.json`.

A sua volta, tale commit scatena il deployment del sito web.

#### Automazioni nel dettaglio

Le automazioni sono definite nel workflow `.github/workflows/build.yml` (nome: _Build documenti_) e nello script `.github/scripts/metadata.py`. Il workflow è composto da due job in sequenza: `build` e `publish`.

##### Job `build`

Si attiva ad ogni `push`, ad ogni `pull_request` e manualmente (`workflow_dispatch`). Se arrivano più commit consecutivi sullo stesso branch, l'esecuzione in corso viene annullata a favore dell'ultima (tranne su `main`, dove ogni esecuzione viene portata a termine).

1. **Checkout con history completa** (`fetch-depth: 0`): serve a `metadata.py` per ricostruire la storia di ogni documento.
2. **Ricerca dei documenti**: ogni cartella contenente un file `main.tex` (escluso `.latex`, che contiene solo il template) è considerata un documento.
3. **Compilazione**: ogni documento viene compilato in un container Docker `texlive/texlive:latest` con `latexmk -pdf -halt-on-error`, con la cartella `.latex` aggiunta al percorso di ricerca (`TEXINPUTS`) per trovare `gh.cls` e le immagini del team. **Un errore di compilazione in un solo documento fa fallire l'intera build.** Il risultato è `out/content/<percorso>/<nome_cartella>.pdf`.
4. **Metadati**: se la cartella contiene un `metadata.json`, `metadata.py` ne produce la versione finale da pubblicare (vedi sotto).
5. **PDF precompilati**: i PDF già presenti nel repository (e.g. verbali firmati da stakeholder esterni al team) vengono copiati così come sono, con il relativo `metadata.json`. Valgono due regole:
   - se la cartella contiene anche un `main.tex`, il PDF è ignorato (con un _warning_), perché prevale il sorgente;
   - in ogni cartella è ammesso **un solo** PDF, altrimenti la build fallisce.
6. **Artifact**: la cartella `out/content` è caricata come _artifact_ `content`, scaricabile dalla pagina dell'esecuzione della _GitHub Action_ (utile per rivedere i PDF di una PR prima del merge).

##### Metadati generati (`metadata.py`)

Lo script parte dal `metadata.json` della cartella e aggiunge, ricavandoli dalla history di git e dalle API di GitHub, i campi:

- `createdAt`: data del commit con cui il documento è stato introdotto nel repository (gli spostamenti di cartella non lo modificano);
- `approved`: informazioni sulla PR dell'**ultima modifica** al documento: data (`approvedAt`), approvatori (`by`), link (`prLink`) e numero (`prNumber`) della PR. Se la PR non ha approvazioni, `by` contiene chi ha eseguito il merge. Conta solo l'ultimo verdetto di ciascun revisore.

Le modifiche al solo `metadata.json` e i semplici spostamenti di file non contano come modifiche al documento.
I campi già presenti nel `metadata.json` scritto a mano (e.g. `version`, `important`) hanno la precedenza: `createdAt` e `approved` non vanno quindi inseriti manualmente, a meno di volerne forzare il valore.

##### Job `publish`

Si esegue solo dopo un `build` riuscito e solo per i `push` sul branch `main` (mai per le PR):

1. controlla che siano configurati la variabile `WEBSITE_REPO` (repository del sito, formato `owner/nome`) e il segreto `WEBSITE_DEPLOY_KEY` (chiave privata di una _deploy key_ con permesso di scrittura sul repository del sito); in caso contrario fallisce con un messaggio esplicativo;
2. scarica l'artifact `content` e fa il checkout del branch `main` del repository del sito;
3. sincronizza `built/` con `website/content/` (`rsync --delete`): **i documenti rimossi dal repository vengono rimossi anche dal sito**;
4. se c'è almeno una differenza, crea la commit `docs: update content from <repo>@<sha>` come `github-actions[bot]` e la pubblica su `main` del sito; altrimenti non fa nulla.

La commit sul repository del sito fa partire il deployment del sito web.

##### In caso di problemi

- **La build fallisce su un documento**: aprire il log del job `build` e cercare la prima riga di errore di LaTeX; riprodurre in locale con `.latex/build.sh <cartella-documento>`.
- **"Più di un pdf nella cartella"**: lasciare un solo PDF nella cartella del documento precompilato.
- **Il documento non compare nel sito**: verificare che la PR sia stata mergiata su `main` e che il job `publish` sia riuscito; controllare che la cartella contenga `main.tex` (o un unico PDF).
- **Errori di `publish` su configurazione**: variabile `WEBSITE_REPO` o segreto `WEBSITE_DEPLOY_KEY` mancanti nelle impostazioni del repository (_Settings → Secrets and variables → Actions_); servono permessi di amministrazione.
