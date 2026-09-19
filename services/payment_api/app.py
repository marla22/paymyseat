import os
import json
import uuid
from flask import Flask, request, jsonify
import redis
import mysql.connector

app = Flask(__name__)

# Collegamenti ai servizi d'appoggio definiti in docker-compose
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'payuser')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'paypassword')
MYSQL_DB = os.getenv('MYSQL_DB', 'paymyseat_db')

r_cache = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

def get_db():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB
    )

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "UP", "service": "Payment API"}), 200

@app.route('/api/payments', methods=['POST'])
def create_payment():
    data = request.get_json() or {}
    idempotency_key = request.headers.get('X-Idempotency-Key')
    booking_id = data.get('booking_id')
    amount = data.get('amount')

    if not idempotency_key or not booking_id or not amount:
        return jsonify({"error": "Parametri mancanti (X-Idempotency-Key, booking_id, amount)"}), 400

    # 1. CONTROLLO IDEMPOTENZA SU REDIS TTL = 86400s (24 H)
    # SETNX imposta la chiave solamente se non esiste
    is_new = r_cache.set(f"idempotency:{idempotency_key}", "PROCESSING", nx=True, ex=86400)
    
    if not is_new:
        cached_status = r_cache.get(f"idempotency:{idempotency_key}")
        return jsonify({
            "message": "Richiesta duplicata intercettata (Idempotente)",
            "idempotency_key": idempotency_key,
            "status": cached_status
        }), 200

    payment_id = str(uuid.uuid4())

    # 2. SALVATAGGIO TRANSAZIONALE SU MYSQl
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Inserire il pagamento
        insert_payment_query = """
            INSERT INTO payments (id, idempotency_key, booking_id, amount, status)
            VALUES (%s, %s, %s, %s, 'PENDING')
        """
        cursor.execute(insert_payment_query, (payment_id, idempotency_key, booking_id, amount))

        # Inserire Evento nella Outbox
        outbox_payload = json.dumps({
            "payment_id": payment_id,
            "booking_id": booking_id,
            "amount": amount,
            "status": "PENDING"
        })
        insert_outbox_query = """
            INSERT INTO outbox_events (event_type, payload)
            VALUES ('PaymentCreated', %s)
        """
        cursor.execute(insert_outbox_query, (outbox_payload,))

        conn.commit()
        cursor.close()
        conn.close()

        # Aggiornare lo stato in Redis
        r_cache.set(f"idempotency:{idempotency_key}", "SUCCESS", ex=86400)

        return jsonify({
            "payment_id": payment_id,
            "booking_id": booking_id,
            "amount": amount,
            "status": "PENDING",
            "message": "Pagamento preso in carico"
        }), 201

    except Exception as e:
        r_cache.delete(f"idempotency:{idempotency_key}")
        return jsonify({"error": "Errore durante la transazione sul DB", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)