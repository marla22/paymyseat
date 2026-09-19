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

---

