import os
import json
import time
import pika
import requests

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
QUEUE_NAME = "refund_queue"
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway_adapter:5001/api/v1/charge")

def process_refund(ch, method, properties, body):
    try:
        data = json.loads(body.decode('utf-8'))
        payment_id = data.get("payment_id")
        amount = data.get("amount")
        
        print(f"[RefundWorker] Elaborazione rimborso per Payment ID: {payment_id}, Importo: {amount}")

        # Simula chiamata di storno verso il Gateway Adapter
        payload = {
            "payment_id": f"refund_{payment_id}",
            "amount": amount
        }
        
        response = requests.post(GATEWAY_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"[RefundWorker] Rimborso completato con successo per {payment_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f"[RefundWorker] Errore dal gateway per {payment_id}: {response.text}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as e:
        print(f"[RefundWorker] Errore nell'elaborazione del messaggio: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    print("[RefundWorker] Connessione a RabbitMQ in corso...")
    
    # Retry loop per attendere l'avvio completo di RabbitMQ
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_refund)
            
            print(f"[RefundWorker] In ascolto sulla coda '{QUEUE_NAME}'...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("[RefundWorker] RabbitMQ non ancora pronto, nuovo tentativo tra 5 secondi...")
            time.sleep(5)
        except Exception as e:
            print(f"[RefundWorker] Errore imprevisto: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()