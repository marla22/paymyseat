# PayMySeat - Guida Definitiva alla Presentazione

Questa guida serve come **copione personale** per guidarti durante la presentazione ai professori. Contiene le spiegazioni e **tutti i comandi esatti** che dovrai copiare e incollare nel terminale.

---

## 1. Prima di iniziare: Il Setup
*Fai questo prima che inizino gli esami, così sei già pronta.*

1. **Docker Desktop** deve essere aperto e funzionante.
2. Apri **VS Code** nella cartella del progetto.
3. Apri **due schede nel browser**:
   - Tab 1: `http://localhost` *(Il tuo Frontend React)*
   - Tab 2: `http://localhost:15672` *(RabbitMQ - login: `guest` / `guest`)*
4. Assicurati che esista il file `.env` con il segreto condiviso.
5. Apri il **Terminale** (su WSL/Ubuntu) ed esegui:
   ```bash
   docker compose up -d --build
   ```
6. Verifica che sia tutto pronto digitando:
   ```bash
   docker compose ps
   ```
   *(Tutti i container devono avere lo stato "Up")*.

---

## 2. Introduzione al Progetto (2 minuti)

> "Il mio progetto si chiama **PayMySeat** ed è il microservizio delegato alla gestione dei pagamenti. L'obiettivo principale di questo lavoro non è fare un semplice gestionale CRUD, ma risolvere un problema critico e reale dei sistemi distribuiti moderni: **cosa succede se l'utente clicca due volte 'Paga' per sbaglio o se la connessione cade a metà operazione?** 
> 
> Senza meccanismi di protezione, il sistema addebiterebbe i soldi due volte o lascerebbe i dati in uno stato incosistente. Per garantire una robustezza enterprise, ho implementato tre pattern:
> 1. **L'Idempotenza (con Redis)** per bloccare i pagamenti duplicati.
> 2. **Il Transactional Outbox** per non perdere mai gli eventi.
> 3. **Il Pattern Saga** per gestire i rimborsi in maniera sicura e asincrona."

---

## 3. Mostrare l'Architettura (3 minuti)
*Apri su VS Code il file `docker-compose.yml` e mostralo.*

> "L'intero ecosistema è containerizzato in 4 microservizi Python, orchestrati attorno a 3 datastore differenti:"

- **Payment API (porta 5000):** "Riceve le richieste di pagamento e salva la transazione su MySQL."
- **Outbox Relay:** "Un demone che preleva continuamente gli eventi dal database e li invia a RabbitMQ, evitando il problema della 'dual-write'."
- **Refund Worker:** "Un processo in ascolto sulle code RabbitMQ che gestisce in modo asincrono i rimborsi (Pattern Saga)."
- **Gateway Adapter (porta 5002):** "Funge da *Anti-Corruption Layer*. Finge di essere una banca (es. Stripe) e firma i webhook con **HMAC-SHA256**."

---

## 4. La Demo Pratica (I Comandi)

### Demo A: Il Frontend (1 min)
*Apri `http://localhost` sul browser.*
> "Questa è la UI. Quando clicchiamo su 'Paga', il frontend genera un UUID e lo invia al backend come **Idempotency Key** per evitare doppi addebiti."

### Demo B: Pagamento Singolo Base (1 min)
*Fai un pagamento di test dal terminale per mostrare che il backend risponde bene.*
**Esegui questo comando:**
```bash
curl -X POST http://localhost:5000/api/payments \
-H "Content-Type: application/json" \
-H "Idempotency-Key: DEMO-PROF-001" \
-d '{"booking_id": "550e8400-e29b-41d4-a716-446655440000", "amount_cents": 5000, "callback_url": "http://localhost:5001/api/webhooks/payment"}'
```
> "Ho appena mandato una richiesta per un biglietto da 50 euro. Il sistema ha generato l'ID e ha inserito la transazione (HTTP 201)."

### Demo C: Idempotenza Base - Protezione doppio click (1 min)
*Rilancia ESATTAMENTE lo stesso comando di prima.*
**Esegui di nuovo:**
```bash
curl -X POST http://localhost:5000/api/payments \
-H "Content-Type: application/json" \
-H "Idempotency-Key: DEMO-PROF-001" \
-d '{"booking_id": "550e8400-e29b-41d4-a716-446655440000", "amount_cents": 5000, "callback_url": "http://localhost:5001/api/webhooks/payment"}'
```
> "Come vedete, mandando la stessa identica richiesta, il sistema non ha creato un secondo pagamento. Ha riconosciuto la chiave in Redis e ha restituito la risposta in cache istantaneamente (HTTP 200). Zero doppi addebiti."

### Demo D: Idempotenza Estrema - Concorrenza Reale (2 min)
*Testiamo lo stress simultaneo.*
**Esegui:**
```bash
python3 demo_idempotenza.py
```
> "Questo script simula **10 utenti che cliccano 'Paga' nell'esatto millisecondo** usando la stessa chiave. Grazie al sistema di lock distribuito: solo la prima richiesta crea il pagamento (`HTTP 201`), le altre 9 sono bloccate all'istante e ricevono l'esito dalla cache (`HTTP 200`)."

### Demo E: Rimborso e RabbitMQ (Pattern Saga)
*Fai vedere la dashboard su `http://localhost:15672`, poi lancia il rimborso. Inserisci l'ID ricevuto dalla Demo B al posto di TUO_PAYMENT_ID.*
**Esegui (sostituendo l'ID):**
```bash
curl -X POST http://localhost:5000/api/payments/TUO_PAYMENT_ID/refund \
-H "Content-Type: application/json"
```
> "Il rimborso non è bloccante (status: REFUND_REQUESTED). Viene salvato nella tabella Outbox, pubblicato su RabbitMQ e consumato dal **Refund Worker** in background verso la banca esterna. Questa è l'architettura **Eventual Consistent**."

---

## 5. Il Cloud e l'Infrastruttura AWS (Novità)
*Mostra su VS Code la cartella `infra/cloud/`.*

> "L'intero processo di deployment in Cloud su **AWS** è completamente automatizzato tramite Infrastructure as Code."

- **Apri `terraform/main.tf` e `compute.tf`:** "Con Terraform definisco l'infrastruttura di rete (VPC, Security Group aperto solo su 5000) e creo l'istanza EC2 (`t3.micro`)."
- **Apri `ansible/playbook.yml`:** "Ansible si connette via SSH al server AWS, installa Docker, clona il codice (incluso il file .env) e avvia l'ecosistema."

---

## 6. Demo Integrazione con HoldMySeat (Eleonora)
*Questa sezione spiega i comandi esatti da lanciare per la demo in coppia su AWS.*

### Passo 1: Deploy su AWS e Scambio degli IP
> "Io e Eleonora abbiamo due macchine EC2 distinte. Siccome i nostri IP pubblici AWS cambiano ad ogni avvio, dobbiamo prima accendere l'infrastruttura e poi scambiarci gli IP."

**1.1 Accendi la tua infrastruttura su AWS:**
Apri il terminale (su WSL) ed esegui:
```bash
cd infra/cloud/terraform
terraform init
terraform apply -auto-approve
```

**1.2 Recupera il tuo IP pubblico:**
Una volta che Terraform ha finito, l'IP pubblico del tuo server comparirà in verde alla fine dell'output (sotto la voce `instance_public_ip`). Se non lo vedi, puoi stamparlo con:
```bash
terraform output instance_public_ip
```

**1.3 Lo scambio:**
- **Tu:** Invia questo IP a Eleonora (su Discord/WhatsApp). Lei lo inserirà nel suo file `.env` per sapere a quale indirizzo inviare i pagamenti.
- **Tu:** Non devi configurare l'IP di Eleonora! Il tuo sistema è programmato per leggerlo dinamicamente dal campo `callback_url` che lei ti manderà nella richiesta.

---

### Passo 2: Demo di un Acquisto Riuscito
*(Fai inviare a Eleonora una richiesta di pagamento reale dal suo sistema verso il tuo IP)*
> "Eleonora mi ha appena inviato una richiesta di pagamento POST. Il mio sistema riceve il suo `booking_id` (in formato UUID), salva la transazione, ed elabora l'esito con RabbitMQ. 
> Infine, il mio Gateway calcola una firma HMAC-SHA256 con il nostro **segreto condiviso** nascosto nel `.env` e invia l'esito `payment.success` al suo Webhook. La sua convalida passa perché le firme coincidono!"

---

### Passo 3: Demo del Pagamento Fallito (Compensating Transaction)
*(Chiedi a Eleonora di inviarti un pagamento con un importo che termina con "13", ad esempio 5013 centesimi).*
> "Ora testiamo la resilienza del sistema. Eleonora mi invia un pagamento destinato a fallire (nel mio gateway, simulo una carta rifiutata e un saldo insufficiente se l'importo termina per 13).
> Il mio sistema prova ad addebitare, la finta banca rifiuta, e io invio subito al suo Webhook un evento `payment.failed`. 
> 
> Questo è il momento più importante: non appena Eleonora riceve il mio webhook di errore, il suo Pattern Saga scatta in automatico eseguendo una *Compensating Transaction* che annulla il blocco del posto e lo rimette in vendita per gli altri utenti. Il sistema distribuito è rimasto perfettamente coerente."