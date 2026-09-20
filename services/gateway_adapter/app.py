import os
import hmac
import hashlib
import json
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configurazione Segreto HMAC e URL Webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super_secret_hmac_key_2026")
PAYMENT_API_WEBHOOK_URL = os.getenv("PAYMENT_API_WEBHOOK_URL", "http://payment_api:5000/api/v1/payments/webhook")

def generate_hmac_signature(payload_str: str, secret: str) -> str:
    """ Genera una firma HMAC-SHA256 basata sul payload JSON. """
    return hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "gateway_adapter"}), 200

@app.route('/api/v1/charge', methods=['POST'])
def process_charge():
    """
    Simula l'addebito sul provider esterno.
    Riceve: { "payment_id": "...", "amount": 25.50, "card_token": "..." }
    """
    data = request.get_json() or {}
    payment_id = data.get("payment_id")
    amount = data.get("amount")

    if not payment_id or not amount:
        return jsonify({"error": "payment_id e amount obbligatori"}), 400

    # Simula esito: se l'importo è 999.99 simula un fallimento del circuito
    if float(amount) == 999.99:
        status = "FAILED"
        failure_reason = "Insufficient funds / Declined by Bank"
    else:
        status = "SUCCESS"
        failure_reason = None

    transaction_id = f"txn_{int(time.time() * 1000)}"

    # Risposta sincera immediata al chiamante (Payment API)
    response_data = {
        "transaction_id": transaction_id,
        "payment_id": payment_id,
        "status": status,
        "failure_reason": failure_reason
    }

    # Invia notifica Webhook asincrona indietro alla Payment API
    send_webhook_notification(payment_id, transaction_id, status)

    return jsonify(response_data), 200

def send_webhook_notification(payment_id: str, transaction_id: str, status: str):
    """
    Costruisce la notifica Webhook, la firma con HMAC-SHA256 e la invia alla Payment API.
    """
    payload = {
        "event": "payment.updated",
        "payment_id": payment_id,
        "transaction_id": transaction_id,
        "status": status,
        "timestamp": int(time.time())
    }

    payload_json = json.dumps(payload, separators=(',', ':'))
    signature = generate_hmac_signature(payload_json, WEBHOOK_SECRET)

    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": signature
    }

    try:
        # Invia il webhook in background/retry se necessario
        requests.post(PAYMENT_API_WEBHOOK_URL, data=payload_json, headers=headers, timeout=5)
    except Exception as e:
        print(f"[GatewayAdapter] Impossibile inviare webhook a {PAYMENT_API_WEBHOOK_URL}: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)