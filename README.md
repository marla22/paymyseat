PayMySeat
Cloud-native payment and financial idempotency microservice

Progetto per il corso di Sistemi Cloud — LM-18, Università degli Studi di Catania
Cosa fa · Architettura · Quick start · Documentazione · Progetto collegato

Cosa fa
Gestione degli addebiti, tolleranza ai retry e coerenza finanziaria per la prenotazione posti. Il focus del progetto non è la semplice transazione di addebito: è garantire la sicurezza transazionale e l'idempotenza assoluta quando migliaia di richieste o retry di rete colpiscono l'API di pagamento contemporaneamente.

In un sistema di pagamento distribuito, un addebito non deve mai avvenire due volte. PayMySeat protegge il flusso con tre meccanismi coordinati:

#   Meccanismo                       Garantisce                                    Non garantisce
1   Redis SET NX EX (Idempotency)    Filtro immediato dei retry (doppio clic)       Persistenza a lungo termine (TTL 24h)
2   Transactional Outbox (MySQL)     Atomicità tra salvataggio ed eventi async    Invio diretto al broker di destinazione
3   HMAC-SHA256 Webhook Signatures   Autenticità e integrità dei callback          Gestione dei ritardi di rete del client

Togliendo Redis il sistema resta corretto sul DB relazionale ma viene sommerso dai retry.
Togliendo l'Outbox Pattern il sistema è veloce ma rischia di perdere notifiche in caso di crash.

Architettura
                        ┌──────────────────┐
   Browser / Client ───►│  Ingress / ALB   │
      ▲                 └────────┬─────────┘
      │                          │
      │ HTTP REST                ▼
      │                   ┌─────────────┐
      └───────────────────┤ Payment API │◄─────── (Idempotency-Key)
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

Tre componenti applicativi a responsabilità separata: la Payment API gestisce le richieste in ingresso, il Gateway Adapter simula il provider esterno e invia i webhook, il Refund Worker elabora le compensazioni asincrone in background.

Gli adapter semplificano il passaggio dall'ambiente di sviluppo locale a quello Cloud su AWS:

Adapter          Locale                 Cloud AWS
Messaggistica    RabbitMQ               Amazon MQ (RabbitMQ)
Cache            Redis                  Amazon ElastiCache (Redis)
Database         MySQL                  Amazon RDS MySQL

Quick start
Prerequisiti: Docker + Compose, Python 3.11+


cd paymyseat
docker compose up -d --build

Un comando solo. Costruisce le immagini dei microservizi, avvia i tre datastore/broker (MySQL, Redis, RabbitMQ), applica gli script SQL di inizializzazione e collega i servizi nella rete virtuale isolata.

Interfaccia           Indirizzo                     Applicazione
Payment API           http://localhost:5000/health  Healthcheck & Status
RabbitMQ Management   http://localhost:15672         Console Broker (guest / guest)
MySQL DB              localhost:3306                Database Relazionale (payuser / paypassword)

La dimostrazione centrale
cd tests
python -m pytest -v

100 richieste simultanee con la stessa chiave di idempotenza → 1 addebito elaborato, 99 risposte idonee intercettate dalla cache.

Struttura
services/
  payment_api/          Flask · MySQL · Redis — API d'incasso e controllo idempotenza
  gateway_adapter/      Flask — Mock Provider esterno di addebito (simulatore Stripe/PayPal)
  refund_worker/        Python · RabbitMQ — Consumer asincrono per l'elaborazione dei rimborsi
infra/
  local/                Terraform · Ansible · manifest Kubernetes (kubeadm su Multipass)
  aws/                  Terraform per il provisioning delle risorse su AWS
relazione/              Documentazione e relazione di progetto
tests/                  Suite di test di integrazione e concorrenza

Stato
Fase   Contenuto                                                          Stato
1a     Schema DB MySQL (Payments, Outbox, Refunds) e setup Docker Compose ✅
1b     Controllo Idempotenza su Redis e Transactional Outbox Pattern      ✅
1c     Gateway Adapter mock provider e gestione Webhook firmati HMAC      ⬜
1d     Refund Worker asincrono con RabbitMQ e gestione compensazioni      ⬜
2a     Dockerization completa — build multi-stage e stack in compose      ✅
2b     Kubernetes locale — cluster kubeadm su VM Multipass con Ingress    ⬜
3      IaC locale — provisioning con Terraform + Ansible                  ⬜
4      Cloudificazione AWS (EC2, RDS MySQL, ElastiCache, Amazon MQ)      ⬜
5      CI/CD (GitHub Actions → ECR → Deploy automatico)                    ⬜

Sicurezza & Ingestion
Il repository è protetto contro la fuga accidentale di segreti e credenziali Cloud su tre livelli:

* .gitignore — ignora file `.env`, chiavi `.pem`, stati `.tfstate` e variabili Terraform `.tfvars`.
* Hook pre-commit (.githooks/) — blocca il commit in caso di rilevamento di chiavi AWS, token o password hardcodate.
* Signature Verification — i webhook provenienti dal Gateway Adapter usano firme HMAC-SHA256 per garantire l'integrità del payload.

Progetto collegato
PayMySeat è un microservizio finanziario autonomo e completamente slegato dal dominio di prenotazione.

🔗 **HoldMySeat (Eleonora Giuffrida)**: [github.com/x-Lele-x/HoldMySeat](https://github.com/x-Lele-x/HoldMySeat)

L'interazione tra i due sistemi avviene esclusivamente tramite chiamata HTTP sincrona in fase di prenotazione e webhook asincrono di conferma esito. I broker di messaggi restano rigorosamente isolati all'interno dei rispettivi contesti.

---
**Corso:** Sistemi Cloud (LM-18) — Università degli Studi di Catania  
**Docenti:** Prof. Giuseppe Pappalardo · Prof. Salvatore Nicotra  
**Autrice:** Valeria Platania · **Licenza:** MIT