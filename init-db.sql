-- Inizializzazione Database PayMySeat

CREATE DATABASE IF NOT EXISTS paymyseat_db;
USE paymyseat_db;

-- Tabella Pagamenti (aggiornata con amount_cents e callback_url)
DROP TABLE IF EXISTS payments;
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(64) NOT NULL,
    amount_cents INT NOT NULL,
    status VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    callback_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Transactional Outbox (per gestione eventi affidabile)
DROP TABLE IF EXISTS outbox_events;
CREATE TABLE outbox_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Rimborsi (gestita dal Refund Worker)
DROP TABLE IF EXISTS refunds;
CREATE TABLE refunds (
    id VARCHAR(36) PRIMARY KEY,
    payment_id VARCHAR(36) NOT NULL,
    booking_id VARCHAR(64) NOT NULL,
    amount_cents INT NOT NULL,
    reason TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
);