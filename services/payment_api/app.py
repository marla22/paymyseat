import os
import json
import uuid
import pymysql
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Abilita CORS per l'integrazione con il Frontend React e HoldMySeat

# Configurazioni da ambiente
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "payuser")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "paypassword")
MYSQL_DB = os.getenv("MYSQL_DB", "paymyseat_db")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Connessione Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

@app.route('/health', methods=['GET'])
def healthcheck():
    return jsonify({"status": "UP", "service": "payment_api"}), 200

@app.route('/api/payments', methods=['POST'])
def create_payment():
    data = request.get_json() or {}

    # FIX 1: Lettura Idempotency-Key con fallback (Idempotency-Key oppure X-Idempotency-Key)
    idempotency_key = request.headers.get('Idempotency-Key') or request.headers.get('X-Idempotency-Key')
    if not idempotency_key:
        return jsonify({"error": "Idempotency-Key missing in headers"}), 400

    # FIX 2: Lettura amount_cents (intero in centesimi)
    amount_cents = data.get('amount_cents')
    booking_id = data.get('booking_id')
    
    if amount_cents is None or not booking_id:
        return jsonify({"error": "booking_id and amount_cents are required"}), 400

    # FIX 3: callback_url dinamico fornito nel payload da HoldMySeat
    callback_url = data.get('callback_url', 'http://localhost:5001/api/webhooks/payment')

    # Controlla idempotenza su Redis
    redis_lock_key = f"idempotency:{idempotency_key}"
    cached_response = redis_client.get(redis_lock_key)
    if cached_response:
        # Ritorna la risposta precedentemente salvata
        return jsonify(json.loads(cached_response)), 200

    payment_id = str(uuid.uuid4())
    
    # FIX 4: Nome evento conforme (payment.succeeded / payment.failed)
    event_type = "payment.succeeded"

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Salva il pagamento nel DB MySQL
            cursor.execute("""
                INSERT INTO payments (id, booking_id, amount_cents, status, idempotency_key, callback_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (payment_id, booking_id, amount_cents, 'COMPLETED', idempotency_key, callback_url))

            # Transactional Outbox: inserimento dell'evento
            outbox_payload = {
                "payment_id": payment_id,
                "booking_id": booking_id,
                "amount_cents": amount_cents,
                "status": "PAID",
                "callback_url": callback_url,
                "event_type": event_type
            }
            
            cursor.execute("""
                INSERT INTO outbox_events (event_type, payload, status)
                VALUES (%s, %s, %s)
            """, (event_type, json.dumps(outbox_payload), 'PENDING'))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

    response_data = {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "amount_cents": amount_cents,
        "status": "PAID",
        "event_type": event_type
    }

    # Salva in cache Redis la risposta per 24 ore (86400 secondi)
    redis_client.setex(redis_lock_key, 86400, json.dumps(response_data))

    return jsonify(response_data), 201


# FIX 6: Endpoint GET per recuperare i pagamenti filtrando per booking_id
@app.route('/api/payments', methods=['GET'])
def get_payments():
    booking_id = request.args.get('booking_id')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if booking_id:
                cursor.execute("""
                    SELECT id as payment_id, booking_id, amount_cents, status, created_at 
                    FROM payments 
                    WHERE booking_id = %s
                """, (booking_id,))
            else:
                cursor.execute("""
                    SELECT id as payment_id, booking_id, amount_cents, status, created_at 
                    FROM payments 
                    ORDER BY created_at DESC LIMIT 50
                """)
            payments = cursor.fetchall()
            
            # Format delle date in stringa ISO per la risposta JSON
            for p in payments:
                if 'created_at' in p and p['created_at']:
                    p['created_at'] = p['created_at'].isoformat()
                    
        return jsonify({"payments": payments}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)