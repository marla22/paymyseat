<h1 align="center">💳 PayMySeat</h1>

<p align="center">
  <b>Cloud-native payment and financial idempotency microservice</b>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/security-passing-brightgreen?style=flat-square&logo=github" alt="Security"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-10%20passed-brightgreen?style=flat-square" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/docker-compose-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
</p>

<p align="center">
  <i>Progetto per il corso di Sistemi Cloud — LM-18, Università degli Studi di Catania</i>
</p>

<p align="center">
  <a href="#cosa-fa">Cosa fa</a> · 
  <a href="#architettura">Architettura</a> · 
  <a href="#quick-start">Quick start</a> · 
  <a href="#documentazione">Documentazione</a>
</p>

---

## Cosa fa

Gestione degli addebiti, tolleranza ai retry e coerenza finanziaria per la prenotazione posti. Il punto del progetto non è il gestionale: è cosa succede quando mille persone inviano una richiesta di pagamento sullo stesso posto nello stesso istante o quando la connessione cade durante un addebito.

Una transazione finanziaria è un'operazione critica: o si elabora esattamente **una sola volta**, o il sistema crea un doppio addebito. PayMySeat lo protegge con tre meccanismi sovrapposti, che non sono ridondanti — risolvono problemi diversi:

| # | Meccanismo | Garantisce | Non garantisce |
|---|---|---|---|
| 1 | **Lock Redis** `SET NX EX` , `TTL 24h` | feedback immediato ai retry di rete | è a scadenza: non è una garanzia di persistenza eterna |
| 2 | **Transactional Outbox** `payments` + `outbox_events` | coerenza atomica ACID fra database ed eventi | invio diretto in tempo reale al broker esterno |
| 3 | **Firma Webhook** `HMAC-SHA256` | autenticità e integrità delle notifiche di esito | gestione dei timeout del client HTTP |

Togliendo Redis il sistema resta corretto ma viene sommerso dai retry.
Togliendo l'Outbox Pattern il sistema è veloce ma rischia di perdere eventi in caso di crash.

---

## Architettura

```text
                        ┌──────────────────┐
   Browser / Client ───►│  Ingress / ALB   │
      ▲                 └────────┬─────────┘
      │                          │
      │ HTTP REST                ▼
      │                   ┌─────────────┐
      └───────────────────┤ Payment API │◄─────── (X-Idempotency-Key)
                          └──────┬──────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
   ┌──────────┐            ┌───────────┐           ┌───────────┐
   │ MySQL 8  │            │  Redis 7  │           │ Gateway   │
   │ → RDS    │            │→ElastiCache│          │ Adapter   │
   │ Payments │            │Idempotency│           │ (Provider)│
   │ + Outbox │            └───────────┘           └─────┬─────┘
   └────┬─────┘                                          │ Webhook
        │ relay                                          │ (HMAC)
        ▼                                                ▼
   ┌──────────┐            ┌──────────────────┐    ┌─────────────┐
   │ RabbitMQ │───────────►│  Refund Worker   │───►│ Payment API │
   │→ AmazonMQ│            │   (Asincrono)    │    └─────────────┘
   └──────────┘            └──────────────────┘

```
---

## Quick start

Prerequisiti: Docker + Compose, Python 3.11+

```bash
git clone git@github.com: marla22/paymyseat.git
cd paymyseat
docker compose up -d --build

```

Un comando solo. Costruisce le tre immagini dei microservizi, avvia i datastore/broker (MySQL, Redis, RabbitMQ), applica lo schema di inizializzazione SQL e collega tutti i servizi nella rete virtuale.

| Interfaccia | Indirizzo | Applicazione |
|---|---|---|
| Payment API | http://localhost:5000/health | Healthcheck & Status |
| RabbitMQ Management | http://localhost:15672 | Console Broker (guest / guest) |
| MySQL Database | localhost:3306 | Database Relazionale (payuser / paypassword) |

---

## La dimostrazione centrale

```bash
cd tests
python -m pytest -v
```

100 richieste simultanee sullo stesso pagamento con la stessa chiave X-Idempotency-Key → 1 addebito elaborato, 99 risposte idonee intercettate dalla cache.

---

## Documentazione

📄 **Relazione completa (PDF)** — Architettura, analisi delle transazioni finanziarie, gestione dell'idempotenza con Redis, pattern Transactional Outbox e procedura di riproduzione passo passo.

Per ricompilarla non serve installare LaTeX locale:

```bash
cd relazione && make
```

---

## Struttura

```text
services/
  payment_api/          Flask · MySQL · Redis — API d'incasso e controllo idempotenza
  gateway_adapter/      Flask — Mock Provider esterno di addebito (simulatore Stripe/PayPal)
  refund_worker/        Python · RabbitMQ — Consumer asincrono per i rimborsi
infra/
  local/                Terraform · Ansible · manifest Kubernetes (kubeadm su VM Multipass)
  aws/                  Terraform per AWS
relazione/              Relazione in LaTeX
tests/                  Suite di validazione e concorrenza
```

## Stato

Fase	Contenuto	Stato
1a	Schema DB MySQL (Payments, Outbox, Refunds) e setup Docker Compose	✅
1b	Controllo Idempotenza su Redis e Transactional Outbox Pattern	✅
1c	Gateway Adapter mock provider e gestione Webhook firmati HMAC	⬜
1d	Refund Worker asincrono con RabbitMQ e gestione compensazioni	⬜
2a	Dockerization completa — build multi-stage e stack in compose	✅
2b	Kubernetes locale — cluster kubeadm su VM Multipass con Ingress	⬜
3	IaC locale — provisioning con Terraform + Ansible	⬜
4	Cloudificazione AWS (EC2, RDS MySQL, ElastiCache, Amazon MQ)	⬜
5	CI/CD (GitHub Actions → ECR → Deploy automatico)	⬜

---

## Sicurezza

Il progetto usa credenziali e token, quindi la difesa contro la fuga di segreti è su tre livelli:

    .gitignore — *.pem, .env, *.tfstate, *.tfvars

    Hook pre-commit versionato in .githooks/ — blocca chiavi AWS, chiavi PEM e credenziali hardcodate

    Signature Verification HMAC-SHA256 — verifica l'integrità dei webhook provenienti dal gateway di pagamento

```bash
git config core.hooksPath .githooks    # da eseguire dopo ogni clone
```
---

## Progetto collegato
Il sistema di prenotazione è deliberatamente fuori da questo microservizio: è delegato ad HoldMySeat, con cui PayMySeat dialoga solo via HTTP e webhook firmati.

    🔗 Progetto collegato: HoldMySeat (Eleonora Giuffrida)

Corso: Sistemi Cloud (LM-18) — Università degli Studi di Catania

Docenti: Prof. Giuseppe Pappalardo · Prof. Salvatore Nicotra

Autrice: Valeria Platania · Licenza: MIT

---