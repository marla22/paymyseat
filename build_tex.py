import os

# Gather code files to append
code_files = []
base_dir = r"c:\Users\valer\Documents\Università\Sistemi Cloud\PayMySeat"

include_files = [
    r"services\payment_api\app.py",
    r"services\refund_worker\app.py",
    r"services\payment_api\outbox_relay.py",
    r"services\gateway_adapter\app.py",
    r"docker-compose.yml",
    r"init-db.sql",
    r"demo_idempotenza.py"
]

for root, dirs, files in os.walk(base_dir):
    if "node_modules" in root or ".venv" in root or ".git" in root:
        continue
    for file in files:
        path = os.path.join(root, file)
        rel_path = os.path.relpath(path, base_dir)
        if any(rel_path.endswith(inc) for inc in include_files) or rel_path.endswith(".tf") or rel_path.endswith(".yml"):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            code_files.append((rel_path, content))

appendix_latex = ""
for name, content in code_files:
    escaped_name = name.replace("_", "\\_")
    appendix_latex += "\\section{" + escaped_name + "}\n\\begin{lstlisting}\n" + content + "\n\\end{lstlisting}\n\n"

tex_content = r'''\documentclass[11pt,a4paper]{report}
\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{geometry}
\usepackage{titlesec}
\usepackage{float}
\usepackage{setspace}
\geometry{a4paper, margin=2.5cm}
\onehalfspacing

\definecolor{codegreen}{rgb}{0,0.6,0}
\definecolor{codegray}{rgb}{0.5,0.5,0.5}
\definecolor{codepurple}{rgb}{0.58,0,0.82}
\definecolor{backcolour}{rgb}{0.95,0.95,0.92}

\lstdefinestyle{mystyle}{
    backgroundcolor=\color{backcolour},   
    commentstyle=\color{codegreen},
    keywordstyle=\color{blue},
    numberstyle=\tiny\color{codegray},
    stringstyle=\color{codepurple},
    basicstyle=\ttfamily\footnotesize,
    breakatwhitespace=false,         
    breaklines=true,                 
    captionpos=b,                    
    keepspaces=true,                 
    numbers=left,                    
    numbersep=5pt,                  
    showspaces=false,                
    showstringspaces=false,
    showtabs=false,                  
    tabsize=2
}
\lstset{style=mystyle}

\begin{document}

\begin{titlepage}
    \begin{center}
        \includegraphics[width=0.4\textwidth]{logo_unict.png} \\
        \vspace{0.5cm}
        {\Large \textsc{Universit\`a degli Studi di Catania}} \\
        \vspace{0.4cm}
        {\large Dipartimento di Matematica e Informatica} \\
        \vspace{0.4cm}
        {\large Corso di Laurea Magistrale in Informatica (LM-18)} \\
        
        \vspace{1.5cm}
        
        {\large \textsc{Relazione di progetto}} \\
        \vspace{0.4cm}
        {\large \textbf{Sistemi Cloud}} \\
        
        \vspace{1cm}
        
        \noindent\makebox[\linewidth]{\rule{\textwidth}{0.4pt}}
        \vspace{0.8cm} \\
        {\Huge \textbf{PayMySeat}} \\
        \vspace{1cm}
        {\Large Gestione della transazionalit\`a economica e della coerenza \\ 
        in un'architettura cloud-native a microservizi} \\
        \vspace{0.5cm}
        \noindent\makebox[\linewidth]{\rule{\textwidth}{0.4pt}}
        
        \vspace{2cm}
        
        \begin{minipage}[t]{0.4\textwidth}
            \begin{flushleft}
                \textbf{Docenti} \\
                Prof. Giuseppe Pappalardo \\
                Prof. Salvatore Nicotra
            \end{flushleft}
        \end{minipage}
        \hfill
        \begin{minipage}[t]{0.4\textwidth}
            \begin{flushright}
                \textbf{Candidata} \\
                Valeria Platania \\
                Matricola 1000081895
            \end{flushright}
        \end{minipage}
        
        \vfill
        
        {\large Anno Accademico 2025/2026} \\
        \vspace{0.5cm}
        {\small \url{https://github.com/ValeriaPlatania/PayMySeat}}
    \end{center}
\end{titlepage}

\tableofcontents
\newpage

\chapter{Introduzione}
\section{Il contesto e il problema del dominio}
Nel contesto dei sistemi distribuiti su larga scala, la gestione delle transazioni economiche presenta sfide architetturali non trascurabili. In un ecosistema a microservizi in cui le responsabilit\`a sono suddivise tra molteplici attori, garantire l'atomicit\`a, la consistenza, l'isolamento e la durabilit\`a (le canoniche propriet\`a ACID dei database relazionali) su database separati fisicamente e logicamente \`e impossibile senza ricorrere a complessi protocolli di coordinamento distribuito. Protocolli come il \textit{Two-Phase Commit} (2PC), tuttavia, introducono latenze inaccettabili e single point of failure (SPOF), andando diametralmente contro i principi del paradigma \textit{Cloud-Native}, che predilige la disponibilit\`a e la partizionabilit\`a (secondo il ben noto Teorema CAP).

Il progetto \textbf{PayMySeat} nasce per affrontare specificamente e puntualmente questo problema in collaborazione (e parziale contrapposizione) con il sistema di biglietteria \textbf{HoldMySeat}. Mentre HoldMySeat si occupa della complessa gestione della concorrenza sui posti fisici all'interno di una mappa (gestendo le prenotazioni per risorse strettamente non replicabili), PayMySeat opera come un gateway di pagamento asincrono e autonomo, un vero e proprio sistema bancario simulato ma architetturalmente reale. 

Il problema fondamentale che \`e scaturito da questa interazione \`e il seguente: quando un utente acquista un posto, il pagamento deve essere addebitato una volta sola, e il sistema di biglietteria deve essere notificato con l'assoluta certezza dell'avvenuto incasso. Se si verifica un timeout di rete (che impedisce alla risposta HTTP di tornare al client), se l'utente aggiorna compulsivamente la pagina in attesa di un feedback visivo, o se un servizio si riavvia improvvisamente (causa scaling autogestito da un orchestratore come Kubernetes o un blocco dell'interprete), si potrebbe facilmente verificare un doppio addebito (perdita economica per il cliente e conseguente danno d'immagine e potenziale frode) o, viceversa, un addebito senza l'emissione effettiva del biglietto (perdita del servizio erogato).

La \textit{coerenza distribuita} diventa quindi il nucleo centrale attorno a cui ruota l'intero ciclo di vita del progetto. Occorre passare da un obsoleto modello di transazionalit\`a forte e bloccante a un pi\`u resiliente modello di \textit{Eventual Consistency} (coerenza eventuale), supportato da pattern architetturali robusti in grado di dirimere le inevitabili race conditions imposte dalla concorrenza asincrona.

\section{Obiettivi primari e secondari del progetto}
Il progetto persegue molteplici macro-obiettivi tecnici e metodologici, strutturati per fornire un prodotto pronto per la produzione. Tali obiettivi vengono esplicati qui di seguito in ordine di priorit\`a architetturale:

\begin{enumerate}
    \item \textbf{Idempotenza transazionale:} Questa propriet\`a \`e essenziale per qualsiasi sistema finanziario. Il sistema deve essere in grado di ricevere molteplici richieste identiche per lo stesso ordine (identificato in modo univoco), e deve garantire che, indipendentemente da quante volte la richiesta venga processata in parallelo da nodi distribuiti, l'effetto sul database e sulle finanze dell'utente sia esattamente equivalente a quello di una singola e isolata richiesta.
    \item \textbf{Resilienza e gestione dei guasti (Fault Tolerance):} L'assenza di single point of failure (SPOF) \`e un mandato fondamentale per i sistemi cloud-native. PayMySeat deve potersi riprendere da un crash senza l'intervento umano. Se il message broker (RabbitMQ) cade o diviene inaccessibile per un taglio di rete, i pagamenti appena processati non devono andare persi n\'e restare in uno stato inconsistente. Se l'API cade durante la notifica al sistema esterno, le notifiche devono comunque essere inviate al ripristino. Per fare ci\`o, il progetto implementa rigorosamente il pattern \textit{Transactional Outbox}.
    \item \textbf{Automazione totale del ciclo di vita (Infrastructure as Code - IaC):} L'era in cui un sistemista entrava via SSH in una macchina per installare pacchetti a mano \`e tramontata. L'obiettivo qui \`e poter costruire e distruggere l'intero ambiente di esecuzione, partendo dalle reti virtuali (VPC) fino ai cluster Docker, passando per le regole firewall (Security Groups e NACL), attraverso codice dichiarativo e versionato. Non devono esistere server ''pets'' (creati, battezzati e curati a mano), ma solo server ''cattle'' (sostituibili, numerati e identici).
    \item \textbf{Disaccoppiamento, incapsulamento e scalabilit\`a orizzontale:} PayMySeat \`e un dominio a s\'e stante. Non deve, in nessun caso, condividere lo stesso database logico o fisico n\'e la stessa area di memoria con HoldMySeat. Le comunicazioni devono avvenire scavalcando confini di rete rigidi. I comandi di pagamento o rimborso avvengono tramite chiamate HTTP RESTful sincrone, mentre le notifiche di esito viaggiano come eventi asincroni tramite Webhook. Questo garantisce che i due team di sviluppo possano rilasciare versioni, eseguire manutenzioni e scalare orizzontalmente in modo completamente asincrono e indipendente, preservando la pura architettura a microservizi.
\end{enumerate}

\chapter{Architettura e Pattern Architetturali}

Questo capitolo illustra nel dettaglio l'infrastruttura logica pensata per assolvere ai requisiti definiti precedentemente, soffermandosi in particolare sui concetti chiave del Domain-Driven Design e della messaggistica asincrona.

\section{Visione d'insieme e scomposizione dei microservizi}
L'architettura di PayMySeat si basa sul paradigma dei microservizi orientati agli eventi (\textit{Event-Driven Microservices} o EDA). La suddivisione delle responsabilit\`a \`e stata effettuata seguendo i principi del \textit{Domain-Driven Design} (DDD), definendo in modo inequivocabile i Bounded Contexts. Il dominio di PayMySeat comprende le entit\`a core di Pagamento (Payment), Rimborso (Refund) ed Evento tracciabile (Event).

La topologia di deployment e di interazione a runtime \`e composta dai seguenti componenti principali:
\begin{itemize}
    \item \textbf{Payment API:} Rappresenta il cuore sincrono e front-facing del sistema. Espone gli endpoint HTTP POST consumati dal client. \`E l'attore incaricato di validare il lock di idempotenza e di orchestrare l'inserimento sul database relazionale primario garantendone le propriet\`a ACID.
    \item \textbf{Outbox Relay:} Un demone in background (poller/worker) che agisce come collante tra il mondo sincrono del database e quello asincrono della messaggistica, rendendo possibile una comunicazione affidabile. Esegue query continue (polling) per recuperare messaggi appena scritti e li instrada al message broker.
    \item \textbf{Refund Worker:} Un worker puro, che si comporta da consumer asincrono per l'infrastruttura. Reagisce ai messaggi di cancellazione o timeout delle prenotazioni presenti nel broker ed esegue l'operazione di compensazione (rimborso), interfacciandosi in modo sicuro con le API bancarie di terze parti.
    \item \textbf{Gateway Adapter:} Questo componente agisce sia da \textit{Anti-Corruption Layer} che da \textit{Webhook dispatcher}. Si interpone fingendo di essere il provider bancario esterno (ad esempio Stripe o PayPal) e assume l'importante responsabilit\`a di generare e applicare le firme crittografiche (signatures) per la chiamata asincrona di callback (Webhook) verso HoldMySeat.
\end{itemize}

\section{La scelta della persistenza poliglotta}
Nell'ambito dei database, ''one size fits all'' \`e un antipattern in ambito Cloud-Native. Costringere tipi di dato diametralmente opposti nello stesso datastore porta inevitabilmente a compromessi inaccettabili in termini di performance. PayMySeat sposa il paradigma della persistenza poliglotta:

\begin{itemize}
    \item \textbf{MySQL (Relational Database):} Lo store relazionale \`e stato scelto come \textit{Single Source of Truth} per il dominio economico. La struttura delle tabelle, segnatamente quelle dei Pagamenti e della Outbox, \`e rigidamente normalizzata per evitare anomalie di inserimento, duplicazione e cancellazione. In un dominio finanziario, le foreign keys e i vincoli di consistenza (come i vincoli \texttt{UNIQUE}) del motore InnoDB sono l'unica linea di difesa invalicabile per il salvataggio effettivo del denaro.
    \item \textbf{Redis (In-Memory Key-Value Store):} Scelto esclusivamente per le sue incredibili performance sub-millisecondo in operazioni di lock. Redis implementa nativamente comandi atomici come \texttt{SETNX} (Set if Not eXists) e semantiche di scadenza autonoma dei record (TTL - Time To Live). Questa combinazione \`e il tassello perfetto per costruire un sistema di validazione preliminare dell'idempotenza, riducendo quasi a zero il carico su MySQL derivato da flood di richieste duplicate (ad esempio per l'esaurimento dei click di un utente spazientito).
    \item \textbf{MongoDB (NoSQL Document Store):} Svolge il ruolo cruciale di archivio storico o di \textit{Audit Trail}. Nel corso del tempo, la struttura dei pagamenti e dei log pu\`o evolvere. MongoDB archivia ricevute e log transazionali registrando documenti JSON eterogenei e profondamente nidificati. In caso di dispute legali, failure analysis o scopi di conformit\`a (compliance), MongoDB detiene la storia immutabile di ogni transito attraverso il broker di messaggi. In cloud, il suo diretto equivalente nativo \`e Amazon DocumentDB.
\end{itemize}

\section{Il Pattern Transactional Outbox (Spiegazione dettagliata)}
In un'architettura a microservizi asincroni, una delle azioni in assoluto pi\`u comuni e al contempo complesse \`e l'aggiornamento simultaneo di uno stato locale su database accoppiato alla pubblicazione di un evento verso il resto del mondo.

Prendiamo l'esempio vitale di PayMySeat. Quando la \textit{Payment API} processa un ordine, la sua responsabilit\`a logica si articola in due step:
\begin{enumerate}
    \item Inserire o aggiornare il record con status \texttt{PAID} nel proprio database relazionale MySQL.
    \item Segnalare a tutti gli altri servizi e subscriber (in particolare a HoldMySeat) che il pagamento si \`e concluso inviando un evento \texttt{PaymentSucceeded} su RabbitMQ.
\end{enumerate}

Poich\'e il commit su MySQL e la pubblicazione su RabbitMQ sono operazioni afferenti a due server fisici distinti, dotati di driver e protocolli dissimili (SQL vs AMQP), il sistema \`e soggetto al classico problema della \textbf{dual-write}.
Se il passo 1 ha pieno successo e i dati vengono committati, ma il passo 2 fallisce perch\'e il broker \`e in manutenzione o ha la RAM saturata, il pagamento \`e stato correttamente salvato ed esatto dal conto del cliente, ma il sistema HoldMySeat non verr\`a mai notificato, non emetter\`a il biglietto, e lascer\`a la risorsa appesa e irraggiungibile per sempre (o peggio, il timeout locale della prenotazione liberer\`a il posto rendendolo acquistabile da qualcun altro, generando overbooking o furto manifesto).
Al contrario, se lo sviluppatore invertisse l'ordine (prima scrivo sul broker, poi sul DB), e il DB rifiutasse il commit per un dead-lock, il broker emetterebbe un successo inesistente, e HoldMySeat cederebbe gratis il prezioso biglietto.

\textbf{Soluzione adottata: Il Transactional Outbox pattern.}
Questo elegantissimo e consolidato pattern elimina il dual-write delegando il problema alle garanzie transazionali del singolo database relazionale.

L'inserimento del record del pagamento e l'inserimento dell'evento avvengono contestualmente all'interno della medesima transazione locale (\texttt{BEGIN TRANSACTION ... COMMIT}) in MySQL. 

La tabella aggiuntiva, che chiamiamo \texttt{outbox\_events}, agisce come coda temporanea.
Se la transazione dovesse fallire per qualsivoglia motivo (timeout del lock, constraint violati), anche l'evento scartato subirebbe un \texttt{ROLLBACK} scomparendo nel nulla. Se la transazione ha successo, il pagamento e la volont\`a di spedire un messaggio diventano persistenti, immutabili e resistenti anche a disconnessioni di corrente del datacenter.

\begin{lstlisting}[language=SQL, caption=Rappresentazione pseudo-codice del Transactional Outbox]
BEGIN TRANSACTION;
  -- Il record di dominio
  INSERT INTO payments (id, amount, status) 
  VALUES ('PAY-123', 5000, 'COMPLETED');
  
  -- L'intenzione di evento da comunicare
  INSERT INTO outbox_events (event_type, payload, status) 
  VALUES ('payment.succeeded', '{"payment_id":"PAY-123"...}', 'PENDING');
COMMIT;
\end{lstlisting}

Un servizio totalmente separato dal thread di ricezione API, denominato \textit{Outbox Relay} (o Message Relay), si avvia in esecuzione perenne. Il suo unico scopo \`e eseguire un polling continuo (o, in architetture pi\`u evolute, un listening sul transaction log - \textit{CDC}): recupera gli eventi marcati \texttt{PENDING}, li preleva e li trasmette a RabbitMQ. Soltanto dopo aver ricevuto con certezza la ricevuta di ritorno (\textit{Acknowledgement} o ACK) a livello TCP da RabbitMQ, il relay si volta verso il database MySQL aggiornando il flag dell'evento in \texttt{PROCESSED}, cos\`i che al giro successivo di polling venga ignorato.
Questo processo assicura matematicamente la semantica di consegna \textit{At-Least-Once} (Almeno una volta), un cardine dell'EDA. Nel peggiore dei casi (il relay crasha un nanosecondo dopo aver inviato il messaggio ma prima di marcare PROCESSED), l'evento verr\`a inviato due volte, circostanza tollerabile e arginabile dall'idempotenza a valle.

\section{Il Pattern Saga e la Coreografia per i rimborsi}
L'acquisto di un posto pu\`o non andare a buon fine lato utente, oppure la riserva temporanea su HoldMySeat (tipicamente di pochi minuti) pu\`o scadere fatalmente un istante prima che l'integrazione del pagamento giunga a conclusione. In queste circostanze di disallineamento temporale, \`e imperativo che il sistema provveda ad avviare un riaccredito dei fondi verso la carta del cliente, operazione nota come \textit{Compensating Transaction} (transazione di compensazione).

In ambienti cloud, non \`e possibile applicare un Rollback globale, perch\'e il primo pezzo del puzzle \`e gi\`a terminato ed ha prodotto esiti concreti esterni. 
Pertanto, si impiega il pattern \textbf{Saga}, implementato in questo progetto secondo lo stile della \textbf{Coreografia} (rispetto all'alternativa dell'Orchestrazione). Non esiste un supervisore centrale: ogni servizio genera un evento di errore al quale gli altri interessati reagiscono passivamente.

Il \textit{Refund Worker} vive costantemente in ascolto asincrono sulle code RabbitMQ preposte alle cancellazioni (\texttt{refund\_queue}). Al sopraggiungere di un evento, il worker emula un'invocazione di basso livello al provider esterno della banca. Poich\'e un server bancario non \`e sotto il nostro controllo, potrebbe rifiutare la chiamata con HTTP 500, impiegare troppo tempo a rispondere (timeout), o droppare i pacchetti. 
Se il tentativo fallisce, il worker solleva un'eccezione locale e restituisce deliberatamente un \texttt{NACK} (Negative Acknowledgement) al canale AMQP di RabbitMQ. RabbitMQ, istruito appositamente, comprender\`a che il task \`e andato in fumo e provveder\`a a \textit{riaccodare} (re-queue) celermente il messaggio per un tentativo successivo, in modo invisibile all'utente che ormai avr\`a gi\`a proseguito la sua navigazione. Questo realizza una coerenza eventuale molto solida.

\chapter{L'Idempotenza e la gestione della Concorrenza}

L'architettura distribuita descritta sopra introduce come compromesso essenziale la semantica "At-Least-Once". A sua volta, questa semantica obbliga tassativamente ogni nodo a supportare l'idempotenza. In questo capitolo svisceriamo i meccanismi software adottati in PayMySeat per difendersi dalla concorrenza dannosa.

\section{Concetto teorico e utilit\`a dell'Idempotenza}
L'idempotenza \`e la propriet\`a per cui la reiterazione o moltiplicazione dell'esecuzione di una singola intenzione operativa non modifica lo stato finale oltre l'impronta generata dalla prima e singola esecuzione utile. 

Nello standard HTTP REST, verbi quali \texttt{GET}, \texttt{PUT}, e \texttt{DELETE} sono contrattualmente assunti come idempotenti dal protocollo. Aggiornare un record con lo stesso valore per 100 volte genera sempre il medesimo record aggiornato e non altera il numero totale di record n\'e incrementa valori.
Al contrario, il verbo \texttt{POST}, largamente impiegato per la creazione di nuovi record (e usato universalmente nei gateway di checkout del carrello, \textit{Create Payment}), non possiede questa propriet\`a. Se un client invia lo stesso body \texttt{POST} ripetutamente in un ciclo \texttt{while}, il backend creer\`a senza remore un nuovo addebito alla banca ad ogni girata di ciclo.

Il disastro si concretizza tipicamente quando la comunicazione va in timeout per packet loss sul nodo di ritorno (il client spedisce il payload, il server incassa, la banca manda l'ok al server, il server manda l'ok al client, ma la rete fa decadere l'ultimo miglio TCP). Il browser del client va in stallo e un utente apprensivo, osservando la rotellina in caricamento, compie l'azione pi\`u umana e deleteria possibile: ricarica la pagina per intero ignorando gli avvisi del browser e inviando due (o pi\`u) pacchetti POST identici e letali.

\section{Primo scudo protettivo: La Cache Redis ad alte prestazioni}
Per arginare chirurgicamente questo fenomeno, viene introdotto l'obbligo, per il frontend o per il chiamante, di specificare uno string header univoco, denominato \texttt{Idempotency-Key} (solitamente un UUIDv4 o un hash MD5 derivato dall'ordine).
Il primissimo step operativo compiuto dal controller di \textit{Payment API} \`e instradare la chiave verso il demone **Redis**, con il quale controlla un database in memoria RAM ad alte prestazioni:
\begin{itemize}
    \item La API interroga Redis: \texttt{GET idempotency:a1b2c3d4}.
    \item Se la chiave \textbf{esiste gi\`a}, significa che stiamo affrontando un replay (volontario o involontario). L'API interrompe bruscamente il flusso, preleva il vecchio risultato JSON precedentemente salvato in RAM da Redis (la ''memoria'' del successo passato), e lo sputa verso il client senza accendere alcuna connessione verso il database primario e ignorando tutto.
    \item Se la chiave \textbf{non esiste}, la API prosegue in modo indisturbato con il processo pesante, contatta MySQL, crea gli eventi, e per ultimissima cosa, \textit{salva l'esito} in Redis agganciandolo alla \texttt{Idempotency-Key}, impostando un TTL (Time-To-Live) utile di 24-48 ore per risparmiare preziosa RAM.
\end{itemize}
Il controllo su Redis richiede tra gli 0.2 e i 2 millisecondi. Di contro, processare l'intera transazione su disco con MySQL ne richiederebbe decine. In presenza di 10.000 utenti concorrenti, Redis fa da paraurti disperdendo il traffico DDoS indesiderato senza penalizzare lo spazio e i log.

\section{Secondo scudo protettivo: I vincoli di unicit\`a nel database Relazionale}
Ma Redis presenta dei difetti congeniti da cui un ingegnere software deve sempre tutelarsi: non offre isolamento transazionale completo rispetto alle race-conditions estremamente ridotte (nell'ordine dei microsecondi) e pu\`o essere svuotato improvvisamente a causa di un crash e riavvio del demone, essendo un sistema volatile a meno di accorgimenti AOF (Append-Only File).

Se due macchine separate avviano due transazioni nel medesimo istante (poich\'e magari bilanciate round-robin dall'Ingress di Kubernetes) e leggono Redis in perfetta contemporaneit\`a prima che la prima istanza abbia il tempo materiale di scrivervi l'esito, si verificher\`a la temibile Race Condition. Ambedue concluderanno che la chiave non esiste, e ambedue contatteranno allegramente MySQL scatenando il duplice addebito.

A proteggere irrevocabilmente i conti degli utenti vi \`e dunque il secondo livello, ovvero lo schema logico del DBMS Relazionale (RDBMS). 
Nel DDL di MySQL, la colonna \texttt{idempotency\_key} possiede la qualifica rigorosa \texttt{UNIQUE CONSTRAINT}. Quando le due transazioni proveranno a eseguire un \texttt{INSERT}, il motore InnoDB di MySQL, che assicura internamente isolamento serializzabile sui blocchi e garanzie ACID globali, far\`a transitare la prima operazione bloccando e gettando nel cestino la seconda, lanciando un'eccezione insormontabile di tipo \texttt{IntegrityError}. L'applicazione software catturer\`a tale eccezione e sapr\`a abortire l'esecuzione con un messaggio HTTP \texttt{409 Conflict}, sanando il disastro prima che si manifesti.


\chapter{Sicurezza Logica e Webhook Crittografici}

Il confine asincrono fra PayMySeat e HoldMySeat \`e gestito dal paradigma dei Webhook. Anzich\'e costringere il sistema di biglietteria a invocare periodicamente e faticosamente un endpoint per sapere lo status dell'ordine (approccio \textit{Polling}, dispendioso per la rete ed erratico nella latenza), PayMySeat effettua chiamate Push in stile callback.

\section{Il vettore d'attacco dello Spoofing}
Il meccanismo dei Webhook \`e per sua natura passibile di gravi e grossolani attacchi informatici. Poich\'e il server HTTP ricevente di HoldMySeat \`e un URL pubblicamente instradabile su internet, chiunque disponga della url e formatti un payload JSON in modo plausibile potrebbe lanciare un banale attacco usando un tool come \texttt{curl}, iniettando pacchetti \texttt{POST} che recitano falsit\`a come "Il carrello numero 53 \`e appena stato regolarmente saldato per l'importo di 200 euro". Se il ricevitore accettasse passivamente questi payload basandosi solo sul formato corretto, l'attaccante esfiltrerebbe biglietti VIP totalmente gratuiti a spese dell'organizzatore.

\section{Prevenzione mediante firma crittografica HMAC}
Per validare autenticit\`a, provenienza e integrit\`a del Webhook respingendo il \textit{Payload Spoofing} o gli attacchi di tipo \textit{Man In The Middle} (MitM), l'Adapter di Gateway implementa lo standard di sicurezza adottato da Stripe.

A tempo zero, fra le parti (o come variabile d'ambiente sicura \texttt{WEBHOOK\_SECRET} nei segreti di infrastruttura) viene registrata e concordata una stringa alfanumerica di notevole lunghezza, lo \textit{Shared Secret}. Questo segreto non viaggia mai lungo i cavi di rete e resta custodito nel Vault o in memorie segrete.

L'operazione svolta dall'Adapter, un attimo prima della chiamata HTTP al partner, segue i passi:
\begin{enumerate}
    \item Serializza l'oggetto da inviare ottenendo la stringa esatta di testo che comporr\`a il body della \texttt{POST}.
    \item Inizializza l'oggetto della funzione crittografica di hash \textbf{HMAC} utilizzando lo Shared Secret come chiave, il testo come messaggio base e il digest SHA-256 come algoritmo matematico unidirezionale (one-way).
    \item Estrapola la rappresentazione esadecimale (hexdigest) lunga 64 caratteri prodotta dall'algoritmo.
    \item Inserisce il digest calcolato all'interno di un custom header nella richiesta HTTP finale (ad esempio \texttt{X-PayMySeat-Signature}).
\end{enumerate}

Dal lato opposto della barricata, il software di HoldMySeat estrarr\`a l'header e il corpo raw della richiesta (\textit{senza formatarlo o alterarvi neppure uno spazio vuoto}). Proceder\`a ricalcolando localmente in autonomia il digest HMAC-SHA256, usando la copia in suo possesso dello Shared Secret.
L'uguaglianza rigorosa fra il digest calcolato e quello intercettato nell'header certifica tre cose in modo assolutamente matematico e irrevocabile:
\begin{itemize}
    \item L'autore del messaggio conosce intimamente il segreto, pertanto l'autore pu\`o essere solo e unicamente PayMySeat.
    \item Il messaggio non ha subito la minima alterazione da parte di terzi intermediari, giacch\'e anche l'aggiunta di un singolo virgola al payload provocherebbe uno smottamento a valanga stravolgendo interamente la digest string (effetto valanga tipico delle \textit{hash functions}).
\end{itemize}
Qualsiasi payload generato con segreto mancante, scorretto o manomesso viene troncato severamente con lo status code \texttt{401 Unauthorized}.

\chapter{Containerizzazione e Infrastruttura di Esecuzione}

La transizione verso un ambiente Cloud non prescinde dalle tecnologie di astrazione dell'OS che favoriscono un deploy agile e svincolato dai colli di bottiglia del bare metal. Questo capitolo sviscera l'integrazione di Docker per l'approccio container-first e la conseguente orchestrazione logica dell'intero ecosistema.

\section{Riproducibilità totale tramite Docker}
Tutto il software compilato e sviluppato per PayMySeat \`e contenuto e pacchettizzato in container \textbf{Docker}. A nessun livello di deploy \`e consentito (o reso necessario) lanciare i comandi standard via terminale ospite per installare runtime Python, Node.js, versioni arcane del database o tool di supporto. La dipendenza esterna esclusiva si riduce alla sola esistenza del demone Docker sul nodo di calcolo. Questo paradigma si definisce \textit{Immutable Infrastructure}.

Il confezionamento (build phase) \`e gestito minuziosamente all'interno dei file testuali denominati \texttt{Dockerfile}, ciascuno afferente al suo microservizio.
Nella pipeline di creazione delle immagini sono state adottate le best practice globali relative sia alla sicurezza dell'immagine sia all'ottimizzazione del builder cache:
\begin{itemize}
    \item Viene ereditata come root image la distruzione \texttt{python:3.12-slim}, limitando drasticamente i vettori d'attacco rispetto a versioni \textit{fat}, grazie all'esclusione di software in eccesso o pacchetti di rete superflui.
    \item L'ordinamento logico dei comandi RUN, ADD e COPY \`e tutt'altro che casuale. Le istruzioni che cambiano meno di frequente sono impilate in cima. Le dipendenze di terze parti elencate in \texttt{requirements.txt} vengono copiate e subito installate (tramite \texttt{pip install}) \textbf{molto prima} dell'ingestione del codice sorgente di PayMySeat. 
    L'ecosistema di build di Docker rileva che il file \texttt{requirements.txt} non subisce variazioni, e carica istantaneamente dalla memoria i binari pip precompilati in cache. Conseguentemente, quando un operatore o sviluppatore altera un banale file \texttt{.py} o aggiunge una rotta al framework Flask, il processo di deploy si limiter\`a ad accodare in millisecondi solo un infinitesimo layer aggiuntivo in fondo allo stack. Ci\`o che in un pattern monolitico male architettato avrebbe impiegato tra i tre e i cinque minuti per reinstallare tutti i binari Python, si avvera ora nella vertiginosa frazione di un secondo.
\end{itemize}

\section{Orchestrazione locale con Docker Compose}
Prima di migrare a un orchestratore enterprise come Kubernetes su grande scala cloud, le relazioni e i flussi interni vengono cablati logicamente a livello infrastrutturale locale avvalendosi di \texttt{docker-compose.yml}. 
Esso unisce e intreccia 7 contenitori fisicamente isolati, costruendo bridge e reti logiche fittizie (\texttt{cloud-project-net}). Il grande vantaggio \`e la risoluzione dei nomi DNS \textit{out-of-the-box}: un container \texttt{payment\_api} si pu\`o semplicemente connettere a un \texttt{rabbitmq} senza mai doversi domandare quale sia l'indirizzo IP virtuale effettivo sottostante.

Il setup rivela il suo punto focale nella corretta sincronizzazione e gestione dell'ordine di accensione. Un servizio debole in architetture SOA cade qualora la sua base dati dovesse presentare interruzioni temporanee o rallentamenti in avvio. Per cui, la clausola \texttt{depends\_on} introdotta nei descrittori di servizio per le APIs subordina severamente l'avvio alla condizione di salute \texttt{service\_healthy} dei macro nodi (MySQL, Redis, RabbitMQ). Solo se i contenitori dichiarano all'engine di aver superato un tcp-ping sulla porta target, Docker sar\`a autorizzato a fare fuoco sui processi Python a valle, evitando cascate di fatali stack trace di tipo \texttt{ConnectionRefusedError}.

\chapter{Infrastructure as Code e Distribuzione su AWS Cloud}

Slegarsi dal paradigma on-premise \`e condizione indispensabile in architetture cloud-native. L'esigenza architetturale non consisteva soltanto nello spostare container funzionanti localmente verso la nuvola Amazon Web Services (AWS), bens\`i nel fare ci\`o impiegando una rigorosa, dichiarativa, e auditable stesura del codice, aderendo ciecamente all'astrazione dell'\textit{Infrastructure as Code} (IaC).

\section{La Pipeline di Provisioning: HashiCorp Terraform}
La generazione fisica dell'hardware simulato, dello scaling e dei vincoli di routing sono dettati mediante codice dichiarativo scritto col linguaggio HCL di \textbf{Terraform}. 
Con Terraform non ci si cura minimamente di impartire una squenza temporale di comandi operativi. L'ingegnere formula una planimetria finale di ci\`o che intende materializzare ed \`e compito del software interagire coi complessi alberi REST API di AWS e applicare i differenziali per colmare il divario fra "realt\`a" ed "intenzione".

La directory di progetto dedicata ai file Terraform modella specificamente:
\begin{itemize}
    \item \textbf{VPC e Routing Privato:} Stabilire ed isolare una \texttt{Virtual Private Cloud} recante prefisso di instradamento \texttt{10.0.0.0/16}, provvista di tabelle di routing custom che disgreghino e distribuiscano le Subnet Pubbliche da agganciare ai Gateway di uscita globale.
    \item \textbf{Risorse EC2 Elastic Compute Cloud:} Unica concessione IaaS dell'architettura. Macchine base \texttt{t3.micro} destinate a fungere da nodi worker per l'alloggiamento del demone Docker. Le risorse non contengono e non devono mai contenere codice pre-installato: seguono il concetto di \textit{Immutable Bootstrapping}.
    \item \textbf{Security Groups e Filtri Ingress/Egress:} La prima e principale barriera contro manipolazioni esterne al progetto. Il Security group dichiara che solo ed unicamente due porte di protocollo TCP possono essere colpite dall'esterno: la porta SSH 22 (riservata ad Ansible o manutenzione eccezionale) e la porta 5000 HTTP a vantaggio dei payload di transazione diretti al framework applicativo. Nient'altro transita da e per il mondo esterno.
\end{itemize}

Un artificio di particolare rilievo tecnologico introdotto nell'IaC \`e la \textbf{Generazione Dinamica delle Credenziali Crittografiche SSH}.
L'approccio manuale prevede che si navighi a mano nella console AWS, si chieda un file \texttt{.pem} per l'infrastruttura e lo si inserisca nel codice. Al contrario, Terraform usa il provider \texttt{tls\_private\_key} per istruire l'ambiente di deploy locale a generare ex-novo un entropico paio asimmetrico di chiavi RSA a 4096-bit nel corso dello start-up, innalzando istantaneamente la porzione pubblica nel Vault di Amazon (\texttt{aws\_key\_pair}), e depositando temporaneamente e segretamente la chiave privata nel path dell'agente locale preposto all'orchestrazione software di l\`i a pochi istanti. L'intera catena di trust viene chiusa a tenuta stagna senza che file segreti permarcano impropriamente in commit storici sui repo GitHub.

\section{La Pipeline di Configurazione software: Ansible}
Dichiarata terminata con successo la fase di provisioning e disponendo ora del nascente IP pubblico della macchina virtuale, la catena di montaggio del \textit{Continuous Deployment} sfocia e delega lo scettro ad \textbf{Ansible}.

Mentre Terraform edifica muri e stanze fisiche (IaaS), Ansible esegue mansioni di fine architettura strutturale e domotica su file OS (Configuration Management), servendosi unicamente delle chiavi effimere RSA prodotte poc'anzi. Non occorrono script daemon installati lato vittima (Ansible si vanta dello striscione "\textit{Agent-less}"), serve unicamente possedere privilegi sudo e un tunnel crittografato aperto.

Il \textit{Playbook} YAML applicato all'istanza EC2 remota ricalca concetti rigidamente idempotenti, un mantra iterativo secondo cui applicare le direttive tre, cento o mille volte produrr\`a il medesimo esito della prima occorrenza:
\begin{itemize}
    \item Aggiunge formalmente ai trusted-repositories i server keys GPG di Docker per abilitare l'ingestione \texttt{apt} pulita.
    \item Ordina a Ubuntu l'installazione delle librerie del Docker Engine CE, del tool set Compose e dei Containerd.
    \item Dispone il trapianto del repository di sviluppo clonato (\texttt{scp/sync} delle directory) nelle aree \textit{user-home} designate.
    \item Emette l'ultimo fatidico commando \texttt{docker compose up --build -d}.
\end{itemize}

Smarcatisi dai cruscotti utente di AWS, l'intera genesi intercontinentale di PayMySeat, a zero setup locale pregresso, \`e ridotta a non pi\`u di un paio di input digitati sulla shell d'inizio rigo.


\chapter{Validazione Sperimentale e Sperimentazione Empirica}

Un'architettura formalmente e astrattamente esatta pu\`o nascondere difetti strutturali colossali nel momento esatto in cui subentra l'entropia del carico utente. L'esercitazione empirica ha testato ed esasperato questi domini di guasto.

\section{Verifica intensiva dell'Idempotenza API sotto Race Condition}
A riprova del superamento della concorrenza deleteria del doppio-click, si \`e attinto alla standard library di programmazione multi-core Python per comporre lo script autoportante e distruttivo \texttt{demo\_idempotenza.py}. 
Esso instanzia una batteria composta dal toolset \texttt{ThreadPoolExecutor} che imbraccia decine di Thread di sistema, armandoli tutti con l'esatto e sovrapponibile pacchetto \texttt{POST} provvisto per intero della medesima \texttt{Idempotency-Key} e direzionati simultaneamente, all'unisono verso i socket in listening dell'infrastruttura.

\textbf{Evidenze di output analizzate nei log:} 
Alla pressione del tasto di via, il sistema di orchestrazione accusa un modesto ma irrisorio carico di CPU ed elabora 10 richieste parallele in un arco misurabile di pochissimi frame macchina.
\begin{itemize}
    \item \textbf{Caso Zero (il "Vincitore"):} Uno solo e unico tra tutti i process-thread prender\`a materialmente possesso del varco. Il framework Python lo fa slittare per primo verso la cache Redis (che attesta virginit\`a della transazione). Permesso accordato per interrogare ed impegnare intensamente le risorse del disco rigido MySQL. Viene redatto l'insert query della transazione contabile. Viene allocato l'evento su outbox. La API fa un respire sollievo e riempie in RAM il dump confermativo JSON prima di rimetterlo all'utente d'origine.
    \item \textbf{I Casi Concorrenti (i 9 "Respinti"):} Lo sciame ritardatario (parliamo di latenze sub-millisecondo tra le istruzioni processore) varca i cancelli. Trova dinanzi a s\'e un panorama alterato a vita: Redis innesca la lettura che rivela che lo \textit{State} ha gi\`a subito alterazione. L'albero operativo del software recide il ramo verso MySQL ignorando a tutti gli effetti la direttiva ed estrude brutalmente in uscita lo scheletro della transazione JSON. Si manifesta in terminale HTTP Response \texttt{200 OK}. 
\end{itemize}

Il bilancio totale dell'esaminatore rivela che il Database \`e rimasto inalterato oltre l'unit\`a, l'utente vede pagato unicamente il suo biglietto e i sistemisti gioiscono dell'impenetrabilit\`a raggiunta e superata. La garanzia \textit{Lock Ottimistico} \`e provata con inattaccabile fermezza.

\section{Verifica estrema della Resilienza Outbox via Chaos Engineering}
Simulare la caduta a catena di componenti infrastrutturali centrali \`e l'unico mezzo che distilla la resilienza in informatica. La branca di questa disciplina si identifica come \textit{Chaos Engineering}.
Con il supporto di macro direttive si \`e proceduto al Kill del processo di sistema RabbitMQ proprio nel frangente centrale della transazione dei pagamenti.

In una vecchia e mal architettata applicazione web, questo scatenerebbe l'effetto domino bloccando i thread web e mandando in collasso l'API verso un disastroso \texttt{HTTP 502/504 Timeout} generalizzato.

Con PayMySeat la realt\`a registrata \`e abissalmente mutata.
\begin{itemize}
    \item L'utente (il Frontend che naviga la dashboard) vede ugualmente il pop-up verde del successo. Il danaro \`e correttamente registrato. Nessuna eccepita visibile su user experience.
    \item Ad assorbire i danni in prima linea c'\`e il guardiano isolato \textit{Outbox Relay}. Egli attinge l'evento e tenta coraggiosamente di contattare il nodo TCP del Broker (ora in down o distrutto). Trovando la porta sigillata, fallisce in via silente la routine asincrona loggando in background l'avvertimento, e con un sobrio passo indietro \textbf{rifiuta categoricamente} di etichettare la transazione come \texttt{PROCESSED}, preservandole a vita il delicato stato primordiale di \texttt{PENDING} nell'acciaio inossidabile del Database MySQL.
    \item Quindici minuti dopo la fine delle miserie umane, qualora un cron-job o Kubernetes provveda al ripristino di istanze container per RabbitMQ, l'\textit{Outbox Relay} ristabilisce docilmente i tunnel comunicativi ed immette d'un lampo nella pipeline gli accumulati eventi \texttt{PENDING}, come niente fosse accaduto. Nessun addebito monetario si trasformer\`a in ghosting fraudolento dell'account fruitore.
\end{itemize}


\chapter{Conclusioni}

A epilogo del progetto, la disamina meticolosa restituisce la fondatezza della teoria iniziale: PayMySeat risponde in modo elegante, solido, blindato e verticalmente scalabile alle mostruose e ingiuste sfide che il Web di nuova concezione scarica in seno allo sviluppatore Cloud. L'abbattimento progressivo e consapevole delle \textit{Fallacies of Distributed Computing} si realizza.

L'adozione ineccepibile del pattern di disaccoppiamento mediante Outbox Transazionale, combinata all'estetica isolata dei moduli asincroni ed alla capillarit\`a della persistenza polivalente e poliglotta assicura di abbattere colli di bottiglia antichi di due decadi.
Il progetto ha perimetrato il raggiungimento totale dei pilastri fondanti:
\begin{itemize}
    \item \textbf{Correttezza Matematica e Finanziaria dei dati:} Idempotenza forte su due livelli indipendenti impedisce doppi addebiti letali per il business.
    \item \textbf{Resilienza Disaccoppiata:} Le dipendenze dei componenti possono incrinarsi e fallire ritardando flussi macro, ma i circuiti breaker consentono alla nave di riemergere dal caos applicando il \textit{retry-loop}. Si ha il transito alla "Coerenza Eventuale".
    \item \textbf{Agilit\`a ed Automazione:} I flussi Terraform ed Ansible codificano lo standard aureo per un disaster-recovery e un deployment rapidissimo. L'ambiente \`e formalizzato a dovere in versionamenti Git e mai sottomesso al caos della configurazione puramente testuale.
\end{itemize}
L'esito complessivo forgia quindi in conclusione un vero e maturo prodotto ''Cloud-Native'', pronto per scenari gravosi.


\appendix
\chapter{Codice Sorgente Selezionato}

L'appendice seguente condensa selettivamente i sorgenti core dell'applicativo e gli script basilari IaC a mo' di completamento del saggio critico architetturale. L'analisi diretta da parte dell'osservatore pu\`o disperare e dirimere per intero le supposizioni sollevate nei soprastanti atti documentali. Sono di proposito stati esclusi elementi meramente decorativi e file di lock intermedi.

''' + appendix_latex + r'''

\end{document}
'''

with open(r'c:\Users\valer\Documents\Università\Sistemi Cloud\PayMySeat\Relazione_PayMySeat.tex', 'w', encoding='utf-8') as f:
    f.write(tex_content)
