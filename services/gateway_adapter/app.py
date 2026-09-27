import os
import json
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Secret condivisibile per la firma HMAC delle notifiche webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "paymyseat_shared_secret_key")

@app.route('/health', methods=['GET'])
def healthcheck():
    return jsonify({"status": "UP", "service": "gateway_adapter"}), 200

@app.route('/api/gateway/charge', methods=['POST'])
def process_charge():
    data = request.get_json() or {}
    
    payment_id = data.get('payment_id')
    booking_id = data.get('booking_id')
    amount_cents = data.get('amount_cents')
    
    # FIX 3: Utilizza il callback_url dinamico inviato dal client/HoldMySeat
    callback_url = data.get('callback_url', 'http://localhost:5001/api/webhooks/payment')

    if not payment_id or not booking_id or not callback_url:
        return jsonify({"error": "Missing required fields"}), 400

    # Simulazione della risposta del provider esterno (Stripe/PayPal)
    is_failure = str(amount_cents).endswith('13')
    webhook_payload = {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "amount_cents": amount_cents,
        "status": "FAILED" if is_failure else "PAID",
        "event_type": "payment.failed" if is_failure else "payment.succeeded"
    }
    
    payload_json = json.dumps(webhook_payload)

    # Calcolo della firma HMAC-SHA256
    computed_hmac_hex = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # FIX 5: Header 'X-PayMySeat-Signature' formattato con prefisso 'sha256=<hex>'
    headers = {
        'Content-Type': 'application/json',
        'X-PayMySeat-Signature': f"sha256={computed_hmac_hex}"
    }

    # Invio del Webhook asincrono al callback_url di HoldMySeat
    try:
        response = requests.post(callback_url, data=payload_json, headers=headers, timeout=5)
        webhook_status = response.status_code
    except Exception as e:
        print(f"[Gateway Adapter] Errore invio webhook a {callback_url}: {e}")
        webhook_status = "FAILED"

    return jsonify({
        "status": "PROCESSED",
        "payment_id": payment_id,
        "webhook_sent_to": callback_url,
        "webhook_status": webhook_status
    }), 200

import threading
import pika
import time

def start_rabbitmq_consumer():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "rabbitmq")))
            channel = connection.channel()
            channel.exchange_declare(exchange='paymyseat_events', exchange_type='topic', durable=True)
            result = channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            channel.queue_bind(exchange='paymyseat_events', queue=queue_name, routing_key='payment.succeeded')
            
            def callback(ch, method, properties, body):
                try:
                    payload = json.loads(body)
                    callback_url = payload.get("callback_url")
                    if not callback_url:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                    
                    # Simulazione fallimento per importi che finiscono con 13
                    amount_cents = payload.get("amount_cents", 0)
                    if str(amount_cents).endswith('13'):
                        payload["event_type"] = "payment.failed"
                        payload["status"] = "FAILED"
                        print(f"[Gateway] Importo terminante in 13. Simulazione fallimento.")

                    # Calcolo firma
                    payload_str = json.dumps(payload)
                    computed_hmac_hex = hmac.new(
                        WEBHOOK_SECRET.encode('utf-8'),
                        payload_str.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'X-PayMySeat-Signature': f"sha256={computed_hmac_hex}"
                    }
                    
                    print(f"[Gateway] Inviando webhook a {callback_url}...")
                    requests.post(callback_url, data=payload_str, headers=headers, timeout=5)
                except Exception as e:
                    print(f"[Gateway] Errore invio webhook: {e}")
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            print("[Gateway] In ascolto su RabbitMQ per inviare webhooks...")
            channel.start_consuming()
        except Exception as e:
            print(f"[Gateway] RabbitMQ disconnesso, ritento tra 5s: {e}")
            time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=5002, debug=True, use_reloader=False)