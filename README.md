<h1 align="center">💳 PayMySeat</h1>

<p align="center">
  <b>Piattaforma cloud-native a microservizi per pagamenti idempotenti e rimborsi asincroni</b>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/flask-3.x-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask"></a>
  <a href="#"><img src="https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="#"><img src="https://img.shields.io/badge/terraform-IaC-7B42BC?style=flat-square&logo=terraform&logoColor=white" alt="Terraform"></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <i>Progetto per il corso di <b>Sistemi Cloud e Laboratorio</b> — LM-18, Università degli Studi di Catania</i>
</p>

<p align="center">
  <a href="#il-problema">Il Problema</a> ·
  <a href="#architettura">Architettura</a> ·
  <a href="#pattern-implementati">Pattern</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#api-reference">API</a> ·
  <a href="#infrastruttura-cloud">Cloud</a> ·
  <a href="#progetto-collegato">HoldMySeat</a>
</p>

---

## Il Problema

Quando un utente paga un biglietto online e la connessione cade a metà transazione, il frontend ripete la richiesta. Senza protezioni, il sistema addebita **due volte** la carta di credito.

PayMySeat risolve questo problema garantendo che ogni pagamento venga elaborato **esattamente una volta**, anche sotto retry aggressivi, crash dei servizi o partizioni di rete. L'architettura è costruita attorno a tre pattern complementari, ognuno dei quali copre una classe di guasto diversa:

| # | Pattern | Protegge da | Meccanismo |
|:-:|---------|-------------|------------|
| 1 | **Idempotency Key + Redis Lock** | Retry di rete e doppio-click | `SET NX EX` con TTL 24h sulla chiave univoca |
| 2 | **Transactional Outbox** | Perdita di eventi post-crash | Scrittura atomica (ACID) di pagamento + evento nella stessa transazione MySQL |
| 3 | **Webhook firmato HMAC-SHA256** | Notifiche contraffatte | Firma crittografica del payload con segreto condiviso |

> **Nota:** Rimuovendo Redis il sistema resta *corretto* ma viene sommerso dai retry. Rimuovendo l'Outbox il sistema è veloce ma rischia di perdere eventi in caso di crash del broker.

---

## Architettura

```
                        ┌──────────────────┐
   Browser / Client ───►│  Frontend React  │
      ▲                 └────────┬─────────┘
      │                          │
      │ HTTP REST                ▼
      │                   ┌─────────────┐
      └───────────────────┤ Payment API │◄─────── Idempotency-Key
                          └──────┬──────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   ┌──────────┐            ┌───────────┐           ┌───────────┐
   │ MySQL 8  │            │  Redis 7  │           │  MongoDB  │
   │ Payments │            │Idempotency│           │   Audit   │
   │ + Outbox │            │   Lock    │           │   Trail   │
   └────┬─────┘            └───────────┘           └───────────┘
        │ polling
        ▼
   ┌──────────┐      ┌──────────────────┐      ┌──────────────┐
   │ Outbox   │─────►│    RabbitMQ      │─────►│    Gateway   │
   │  Relay   │      │  (paymyseat_     │      │   Adapter    │
   │          │      │   events)        │      │  (Webhook →  │
   └──────────┘      └────────┬─────────┘      │  HoldMySeat) │
                              │                └──────────────┘
                              ▼
                     ┌──────────────────┐
                     │  Refund Worker   │
                     │  (Saga Pattern)  │
                     └──────────────────┘
```

### Servizi

| Servizio | Porta | Tecnologia | Responsabilità |
|----------|:-----:|------------|----------------|
| **Payment API** | `5000` | Flask · MySQL · Redis | REST API per checkout, idempotenza, richiesta rimborso |
| **Outbox Relay** | — | Python · MySQL · RabbitMQ | Poller che preleva eventi dalla tabella outbox e li pubblica sul broker |
| **Refund Worker** | — | Python · RabbitMQ · MongoDB | Consumer asincrono che elabora i rimborsi (Saga) |
| **Gateway Adapter** | `5002` | Flask · RabbitMQ | Simula un provider esterno (Stripe/PayPal), invia webhook firmati HMAC |
| **Frontend** | `5173` | React · Vite | Interfaccia utente per checkout e dashboard pagamenti |

### Datastore

| Componente | Immagine Docker | Scopo |
|------------|-----------------|-------|
| **MySQL 8** | `mysql:8.0` | Storage transazionale ACID (pagamenti + outbox) |
| **Redis** | `redis:alpine` | Lock distribuito per idempotenza (TTL 24h) |
| **MongoDB** | `mongo:6.0` | Audit trail e storico rimborsi (Document Store) |
| **RabbitMQ** | `rabbitmq:3-management-alpine` | Message broker per comunicazione asincrona tra servizi |

---

## Pattern Implementati

### 1. Idempotency Key (Cache-Aside con Redis)

Ogni richiesta di pagamento deve includere un header `Idempotency-Key` (o `X-Idempotency-Key`). La Payment API verifica su Redis se la chiave è già stata processata:

- **Cache HIT →** Restituisce la risposta salvata (HTTP `200`), nessuna scrittura su DB.
- **Cache MISS →** Processa la transazione, salva su MySQL, cachea la risposta per 24h.

```python
redis_lock_key = f"idempotency:{idempotency_key}"
cached_response = redis_client.get(redis_lock_key)
if cached_response:
    return jsonify(json.loads(cached_response)), 200
```

### 2. Transactional Outbox

Il pagamento e l'evento di notifica vengono scritti nella **stessa transazione SQL**. Un servizio separato (Outbox Relay) preleva periodicamente gli eventi pendenti dalla tabella `outbox_events` e li pubblica su RabbitMQ, garantendo la consegna *at-least-once* senza rischio di perdita dati.

```sql
-- Nella stessa transazione ACID:
INSERT INTO payments (...) VALUES (...);
INSERT INTO outbox_events (event_type, payload, status) VALUES ('payment.succeeded', '...', 'PENDING');
COMMIT;
```

### 3. Saga Pattern per Rimborsi

I rimborsi non vengono processati in modo sincrono. La richiesta genera un evento `refund.requested` nella tabella outbox, che viene poi consumato dal **Refund Worker** tramite RabbitMQ. In caso di fallimento, il messaggio viene rimesso in coda (`NACK + requeue`) per un retry automatico.

### 4. Webhook con Firma HMAC-SHA256

Il Gateway Adapter firma ogni notifica webhook con `HMAC-SHA256` usando un segreto condiviso, inviando la firma nell'header `X-PayMySeat-Signature` con formato `sha256=<hex>`. Il sistema ricevente (HoldMySeat) può così verificare l'autenticità e l'integrità del messaggio.

---

## Quick Start

### Prerequisiti

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- Python 3.11+ (solo per lo script di demo)

### Avvio

```bash
git clone https://github.com/marla22/paymyseat.git
cd paymyseat
docker compose up -d --build
```

Un singolo comando costruisce le immagini dei microservizi, avvia tutti i datastore, applica lo schema SQL di inizializzazione e collega i servizi nella rete Docker.

### Verifica

| Interfaccia | URL | Credenziali |
|-------------|-----|-------------|
| Payment API (Health) | http://localhost:5000/health | — |
| Frontend React | http://localhost:5173 | — |
| RabbitMQ Management | http://localhost:15672 | `guest` / `guest` |
| MySQL | `localhost:3306` | `valeria` / `password` |

### Demo Idempotenza

Lo script `demo_idempotenza.py` lancia richieste concorrenti con la stessa chiave per dimostrare che solo la prima viene elaborata:

```bash
pip install requests
python demo_idempotenza.py
```

---

## API Reference

### `POST /api/payments`

Crea un nuovo pagamento. Richiede un header `Idempotency-Key`.

```bash
curl -X POST http://localhost:5000/api/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: chiave-univoca-123" \
  -d '{"booking_id": "BOOK-001", "amount_cents": 2500, "callback_url": "http://holdmyseat/api/webhooks/payment"}'
```

**Risposta (201):**
```json
{
  "payment_id": "uuid-generato",
  "booking_id": "BOOK-001",
  "amount_cents": 2500,
  "status": "PAID",
  "event_type": "payment.succeeded"
}
```

### `GET /api/payments?booking_id=BOOK-001`

Recupera i pagamenti filtrati per `booking_id`.

### `POST /api/payments/<payment_id>/refund`

Richiede il rimborso asincrono di un pagamento completato. Restituisce HTTP `202 Accepted`.

---

## Infrastruttura Cloud

L'infrastruttura AWS è definita interamente come codice (IaC) e versionata nel repository.

### Terraform (`infra/cloud/terraform/`)

Provisioning automatico di:
- **VPC** con subnet pubblica e Internet Gateway
- **Security Groups** con regole firewall per le porte dei servizi
- **Istanza EC2** (`t3.micro`, free tier) con chiave SSH generata automaticamente
- **Chiave RSA** (`tls_private_key`) salvata localmente per l'accesso passwordless

```bash
cd infra/cloud/terraform
terraform init
terraform plan
terraform apply
```

### Ansible (`infra/cloud/ansible/`)

Configurazione automatizzata dell'istanza EC2:
- Installazione Docker Engine e Docker Compose
- Aggiunta dell'utente al gruppo `docker`
- Copia e avvio dello stack applicativo

```bash
cd infra/cloud/ansible
ansible-playbook -i inventory playbook.yml
```

---

## Struttura del Progetto

```
PayMySeat/
├── services/
│   ├── payment_api/            # Flask · MySQL · Redis
│   │   ├── app.py              # API REST (checkout, idempotenza, rimborso)
│   │   ├── outbox_relay.py     # Poller MySQL → RabbitMQ
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── gateway_adapter/        # Flask · RabbitMQ
│   │   ├── app.py              # Mock provider + webhook HMAC
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── refund_worker/          # Python · RabbitMQ · MongoDB
│       ├── app.py              # Consumer asincrono (Saga)
│       ├── Dockerfile
│       └── requirements.txt
├── frontend/                   # React + Vite
├── infra/
│   ├── cloud/
│   │   ├── terraform/          # VPC, EC2, Security Groups
│   │   └── ansible/            # Playbook per Docker setup
│   └── local/
│       └── k8s/                # Manifesti Kubernetes (opzionale)
├── docker-compose.yml          # Orchestrazione completa dello stack
├── init-db.sql                 # Schema di inizializzazione MySQL
├── demo_idempotenza.py         # Script di test per idempotenza concorrente
└── relazione_progetto_Cloud.pdf
```

---

## Sicurezza

| Livello | Meccanismo | Dettaglio |
|---------|-----------|-----------|
| **Repository** | `.gitignore` | Esclude `*.pem`, `.env`, `*.tfstate`, `*.tfvars`, `.terraform/` |
| **Trasporto** | Firma HMAC-SHA256 | Verifica integrità e autenticità dei webhook tra Gateway e HoldMySeat |
| **Applicazione** | Idempotency Lock | Impedisce doppi addebiti a livello di business logic |

---

## Progetto Collegato

PayMySeat gestisce esclusivamente il dominio dei **pagamenti e rimborsi**. La gestione delle prenotazioni e dei posti a sedere è delegata al microservizio partner:

> 🔗 **[HoldMySeat](https://github.com/x-Lele-x/HoldMySeat)** — Sistema di prenotazione posti (@x-Lele-x)

I due sistemi comunicano tramite:
- **HTTP REST** — HoldMySeat invia richieste di pagamento a PayMySeat
- **Webhook firmati** — PayMySeat notifica l'esito (`payment.succeeded` / `payment.failed`) all'URL di callback fornito da HoldMySeat

---

<p align="center">
  <b>Corso:</b> Sistemi Cloud e Laboratorio (LM-18) — Università degli Studi di Catania<br>
  <b>Docenti:</b> Prof. Giuseppe Pappalardo · Prof. Salvatore Nicotra<br>
  <b>Autrice:</b> Valeria Platania · <b>Licenza:</b> MIT
</p>
