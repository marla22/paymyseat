import os
import json
import uuid
import time
import pymysql
import redis
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Abilita CORS per l'integrazione con React e HoldMySeat

# Configurazioni ambiente
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "payuser")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "paypassword")
MYSQL_DB = os.getenv("MYSQL_DB", "paymyseat_db")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Connessione Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Gestione Connessione DB con Retry Automatico
def get_db_connection(retries=10, delay=2):
    for i in range(retries):
        try:
            conn = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            return conn
        except pymysql.err.OperationalError as e:
            if i == retries - 1:
                raise e
            print(f"[Payment API] MySQL non ancora pronto, riprovo tra {delay}s... (tentativo {i+1}/{retries})")
            time.sleep(delay)

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

    # Controlla idempotenza su Redis con Lock Atomico (risolve race conditions)
    redis_lock_key = f"idempotency:{idempotency_key}"
    
    # Prima proviamo a leggere se c'è una risposta JSON già completata
    cached_response = redis_client.get(redis_lock_key)
    if cached_response and cached_response != "PENDING":
        return jsonify(json.loads(cached_response)), 200
        
    # Tenta di acquisire il lock atomico per l'elaborazione esclusiva (SET NX)
    lock_acquired = redis_client.set(redis_lock_key, "PENDING", nx=True, ex=86400)
    
    if not lock_acquired:
        # Un'altra richiesta con la stessa chiave è attualmente in esecuzione ("PENDING")
        return jsonify({"error": "Payment already processing for this idempotency key"}), 409

    payment_id = str(uuid.uuid4())
    
    # Simulazione della banca: se l'importo finisce con 13 fallisce
    is_failure = str(amount_cents).endswith('13')
    payment_status = 'FAILED' if is_failure else 'COMPLETED'
    event_type = 'payment.failed' if is_failure else 'payment.succeeded'

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Salva il pagamento nel DB MySQL
            cursor.execute("""
                INSERT INTO payments (id, booking_id, amount_cents, status, idempotency_key, callback_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (payment_id, booking_id, amount_cents, payment_status, idempotency_key, callback_url))

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
        conn.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

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
    
    try:
        conn = get_db_connection()
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
                    
        conn.close()
        return jsonify({"payments": payments}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

@app.route('/api/payments/<payment_id>/refund', methods=['POST'])
def request_refund(payment_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Verifica se il pagamento esiste ed è completato
            cursor.execute("SELECT amount_cents, booking_id, status FROM payments WHERE id = %s", (payment_id,))
            payment = cursor.fetchone()
            
            if not payment:
                return jsonify({"error": "Payment not found"}), 404
            
            if payment['status'] != 'COMPLETED' and payment['status'] != 'PAID':
                return jsonify({"error": f"Cannot refund payment in status {payment['status']}"}), 400

            # Aggiorna lo stato in REFUND_REQUESTED
            cursor.execute("UPDATE payments SET status = 'REFUND_REQUESTED' WHERE id = %s", (payment_id,))
            
            # Inserisci evento nella outbox
            outbox_payload = {
                "payment_id": payment_id,
                "booking_id": payment['booking_id'],
                "amount": payment['amount_cents'] # Usato dal refund worker come 'amount'
            }
            
            cursor.execute("""
                INSERT INTO outbox_events (event_type, payload, status)
                VALUES (%s, %s, %s)
            """, ('refund.requested', json.dumps(outbox_payload), 'PENDING'))
            
        conn.commit()
        conn.close()
        
        # Invalida la cache Redis per evitare inconsistenza
        redis_client.delete(f"idempotency:*") # In un caso reale si salverebbe l'idempotency key insieme al payment
        
        return jsonify({"status": "REFUND_REQUESTED", "payment_id": payment_id}), 202
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)