import io

with io.open('Relazione_PayMySeat.tex', 'r', encoding='utf-8') as f:
    content = f.read()

prefix = content.split('\\appendix')[0]

new_appendix = r'''\appendix
\chapter{Manuale d'Uso e Replicazione delle Prove}

Questa appendice contiene tutte le istruzioni necessarie per avviare l'infrastruttura in ambiente locale, eseguire la suite di test e validare empiricamente le garanzie architetturali di PayMySeat discusse nei capitoli precedenti. Seguendo passo passo questi comandi, l'esaminatore potr\`a constatare il corretto funzionamento dell'idempotenza, del pattern Transactional Outbox e delle comunicazioni asincrone con RabbitMQ.

\section{Prerequisiti di Sistema}
Per poter eseguire i test, la macchina host deve essere equipaggiata con il seguente software di base:
\begin{itemize}
    \item \textbf{Docker e Docker Compose:} Fondamentali per l'orchestrazione locale e per sollevare il database relazionale (MySQL), il message broker (RabbitMQ) e la cache (Redis) senza inquinare l'host.
    \item \textbf{Python 3.12+:} Necessario per eseguire gli script di test concorrenti e le chiamate API simulate tramite le librerie standard.
    \item \textbf{Postman o cURL:} Utili per interrogare liberamente gli endpoint esposti dalle API in modalit\`a interattiva.
\end{itemize}

\section{Avvio dell'Infrastruttura}
Aprire il terminale (o la PowerShell) e navigare all'interno della root del progetto. Prima di lanciare l'applicazione, assicurarsi che le porte di default (\texttt{3306} per MySQL, \texttt{5672} per RabbitMQ, \texttt{6379} per Redis e \texttt{5000} per Flask) siano libere sull'host.

Per innescare il build delle immagini e l'avvio in background di tutti e sette i container, digitare:
\begin{lstlisting}[language=bash]
docker compose up --build -d
\end{lstlisting}

L'operazione scaricher\`a le immagini ufficiali e compiler\`a i microservizi. Eseguire in seguito il seguente comando per monitorare che lo stato di tutti i servizi transiti su \texttt{Healthy}:
\begin{lstlisting}[language=bash]
docker compose ps
\end{lstlisting}
In questo frangente, il file \texttt{init-db.sql} sar\`a gi\`a stato ingerito da MySQL, popolando lo schema con la tabella dei pagamenti e la tabella di outbox.

\section{Prova 1: Flusso di Pagamento Standard (Happy Path)}
Una volta che l'API \`e esposta sulla porta 5000, \`e possibile simulare un acquisto legittimo. L'endpoint in ascolto richiede un payload JSON e un header crittografico per l'idempotenza.

Eseguire la seguente invocazione tramite \texttt{cURL}:
\begin{lstlisting}[language=bash]
curl -X POST http://localhost:5000/payments \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: test-happy-path-12345" \
     -d "{\"booking_id\": \"BK-001\", \"amount_cents\": 2500, \"currency\": \"EUR\"}"
\end{lstlisting}

\textbf{Comportamento atteso:}
\begin{enumerate}
    \item L'API risponder\`a quasi istantaneamente con un codice HTTP \texttt{200 OK} e uno status \texttt{PAID}.
    \item Osservando i log del relay (\texttt{docker compose logs -f outbox\_relay}), si noter\`a l'intercettazione del messaggio PENDING e la sua pubblicazione verso RabbitMQ.
    \item Osservando i log del gateway (\texttt{docker compose logs -f gateway\_adapter}), si vedr\`a la ricezione del messaggio AMQP e il calcolo della firma HMAC, concludendo l'invio (simulato) al webhook esterno.
\end{enumerate}

\section{Prova 2: Test Concorrenziale di Idempotenza}
L'obiettivo di questa prova \`e bombardare l'API con decine di richieste sovrapposte, tutte recanti lo stesso ID, per dimostrare che non vi sar\`a alcun doppio addebito e nessun crash del database per Constraint Violations, grazie al cuscinetto Redis.

Nella directory radice \`e presente lo script \texttt{demo\_idempotenza.py}. Avviarlo tramite l'interprete:
\begin{lstlisting}[language=bash]
python demo_idempotenza.py
\end{lstlisting}

Lo script utilizza la libreria \texttt{concurrent.futures.ThreadPoolExecutor} per spalancare 10 o pi\`u thread contemporanei che inoltreranno \textbf{esattamente la stessa POST} nello stesso millisecondo.
\textbf{Comportamento atteso:}
L'output a schermo certificher\`a che una (e una sola) risposta sar\`a elaborata ex-novo (elaborazione effettiva del pagamento e inserimento in DB), mentre le restanti \textit{N-1} richieste restituiranno il \textit{medesimo JSON di successo}, ma contrassegnato logicamente come hit in cache da Redis, senza aver toccato MySQL la seconda volta. Interrogando poi il database manualmente (\texttt{SELECT * FROM payments}), ci sar\`a un unico record registrato.

\section{Prova 3: Test di Resilienza (Chaos Engineering)}
Questa simulazione convalida l'affidabilit\`a dell'infrastruttura contro disservizi gravi. Il test si sviluppa uccidendo intenzionalmente il Broker dei Messaggi prima che l'API finisca di lavorare.

\begin{enumerate}
    \item Dal terminale, arrestare forzatamente il container RabbitMQ:
    \begin{lstlisting}[language=bash]
docker compose stop rabbitmq
    \end{lstlisting}
    \item Ripetere una POST di pagamento (usando una nuova Idempotency Key, es. \texttt{test-chaos-001}).
    \item L'API Web risponder\`a positivamente (\texttt{200 OK}): per il cliente il biglietto \`e salvo.
    \item I log del demone \textit{Outbox Relay} inizieranno a stampare eccezioni di tipo \texttt{AMQPConnectionError}, non potendo inoltrare l'evento. L'evento su DB rimarr\`a nel limbo temporaneo dello stato \texttt{PENDING}.
    \item Riaccendere RabbitMQ per emulare il ripristino di rete:
    \begin{lstlisting}[language=bash]
docker compose start rabbitmq
    \end{lstlisting}
    \item Non appena il container rientra online (entro 5-10 secondi), il relay ristabilir\`a autonomamente il socket TCP, assorbir\`a l'evento rimasto incagliato nel DB e lo sparer\`a in coda, ripristinando la \textit{Coerenza Eventuale} dell'intero sistema. Il ciclo di vita dell'ordine arriver\`a a compimento senza intervento umano.
\end{enumerate}
\end{document}
'''

with io.open('Relazione_PayMySeat.tex', 'w', encoding='utf-8') as f:
    f.write(prefix + new_appendix)
