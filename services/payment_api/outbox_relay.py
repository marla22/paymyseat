import os
import json
import time
import pymysql
import pika
from pymongo import MongoClient

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "valeria")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DB = os.getenv("MYSQL_DB", "paymyseat_db")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")

def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )

def start_relay():
    print("[OutboxRelay] Connessione a RabbitMQ e MongoDB in corso...")
    
    # Init Mongo
    mongo_client = MongoClient(host=MONGO_HOST, port=27017, serverSelectionTimeoutMS=5000)
    db_mongo = mongo_client["paymyseat_audit"]
    receipts_col = db_mongo["receipts"]
    
    # Init RabbitMQ
    connection = None
    channel = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            channel = connection.channel()
            channel.exchange_declare(exchange='paymyseat_events', exchange_type='topic', durable=True)
            print("[OutboxRelay] Connesso a RabbitMQ e MongoDB.")
        except Exception as e:
            print(f"[OutboxRelay] RabbitMQ non pronto: {e}")
            time.sleep(5)

    print("[OutboxRelay] Avvio polling sulla tabella outbox_events...")
    while True:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Seleziona eventi in PENDING
                cursor.execute("SELECT id, event_type, payload FROM outbox_events WHERE status = 'PENDING' FOR UPDATE")
                events = cursor.fetchall()
                
                for event in events:
                    event_id = event['id']
                    event_type = event['event_type']
                    payload = event['payload']
                    
                    if isinstance(payload, str):
                        payload_data = json.loads(payload)
                    else:
                        payload_data = payload
                    
                    # 1. Pubblica su RabbitMQ
                    channel.basic_publish(
                        exchange='paymyseat_events',
                        routing_key=event_type,
                        body=json.dumps(payload_data),
                        properties=pika.BasicProperties(
                            delivery_mode=2, # make message persistent
                            content_type='application/json',
                        )
                    )
                    print(f"[OutboxRelay] Pubblicato evento {event_type} su RabbitMQ per Payment ID: {payload_data.get('payment_id')}")
                    
                    # 2. Salva su MongoDB (Document Store Audit)
                    receipts_col.insert_one({
                        "event_id": event_id,
                        "event_type": event_type,
                        "payload": payload_data,
                        "processed_at": time.time()
                    })
                    print(f"[OutboxRelay] Salvata ricevuta su MongoDB per l'evento {event_id}")
                    
                    # 3. Aggiorna stato outbox
                    cursor.execute("UPDATE outbox_events SET status = 'PROCESSED' WHERE id = %s", (event_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[OutboxRelay] Errore nel polling: {e}")
            if 'conn' in locals() and conn.open:
                conn.rollback()
                conn.close()
            
        time.sleep(2) # Polling interval

if __name__ == "__main__":
    start_relay()
