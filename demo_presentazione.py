import requests
import json
import uuid
import time
import threading

API_URL = "http://localhost:5000/api/payments"
# Endpoint fasullo per il webhook locale
WEBHOOK_URL = "http://localhost:5001/webhook"

def print_header(title):
    print("\n" + "="*50)
    print(f"🚀 DEMO: {title}")
    print("="*50)

def invia_pagamento(amount, idempotency_key=None, booking_id=None):
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())
    if not booking_id:
        booking_id = f"DEMO-{int(time.time())}"
        
    payload = {
        "booking_id": booking_id,
        "amount_cents": amount,
        "callback_url": WEBHOOK_URL
    }
    
    headers = {
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json"
    }
    
    print(f"Inviando POST {API_URL}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Idempotency-Key: {idempotency_key}")
    
    start_time = time.time()
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        end_time = time.time()
        print(f"\n[Risposta ricevuta in {round(end_time - start_time, 2)}s]")
        print(f"Status Code: {response.status_code}")
        print(f"Body: {json.dumps(response.json(), indent=2)}")
        return response
    except Exception as e:
        print(f"Errore di connessione: {e}")

def demo_successo():
    print_header("Pagamento con Successo (Importo: 25.00€)")
    print("In questa demo inviamo un pagamento valido. Verrà salvato come COMPLETED e il webhook di successo partirà in background.")
    invia_pagamento(2500)

def demo_fallimento():
    print_header("Pagamento Fallito / Carta Rifiutata (Importo: 25.13€)")
    print("In questa demo l'importo finisce per 13. Il Gateway simulerà il rifiuto della carta.")
    print("Verrà salvato come FAILED e partirà il webhook 'payment.failed' per innescare la Saga Compensation.")
    invia_pagamento(2513)

def demo_idempotenza():
    print_header("Idempotenza (Race Condition / Doppia Chiamata)")
    print("In questa demo inviamo due richieste ESATTAMENTE IDENTICHE (stessa Idempotency-Key) nello stesso millisecondo.")
    print("Solo la prima verrà elaborata, la seconda verrà bloccata dal Lock di Redis (Errore 409).")
    
    idempotency_key = str(uuid.uuid4())
    booking_id = f"IDEMPO-{int(time.time())}"
    
    def worker(nome_thread):
        print(f"[{nome_thread}] Partito!")
        invia_pagamento(3000, idempotency_key, booking_id)

    t1 = threading.Thread(target=worker, args=("Thread-1",))
    t2 = threading.Thread(target=worker, args=("Thread-2",))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    while True:
        print("\n" + "#"*50)
        print("  TOOL DI PRESENTAZIONE PAYMYSEAT  ")
        print("#"*50)
        print("1. Esegui Demo: Pagamento Completato")
        print("2. Esegui Demo: Pagamento Fallito (Simulazione Banca)")
        print("3. Esegui Demo: Idempotenza")
        print("4. Esci")
        
        scelta = input("\nScegli un'opzione (1-4): ")
        
        if scelta == '1':
            demo_successo()
        elif scelta == '2':
            demo_fallimento()
        elif scelta == '3':
            demo_idempotenza()
        elif scelta == '4':
            print("Uscita dal tool. Buona fortuna per l'esame!")
            break
        else:
            print("Scelta non valida.")
        
        time.sleep(1)
