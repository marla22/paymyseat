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
    # FIX 4: Evento standard 'payment.succeeded'
    webhook_payload = {
        "payment_id": payment_id,
        "booking_id": booking_id,
        "amount_cents": amount_cents,
        "status": "PAID",
        "event_type": "payment.succeeded"
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)