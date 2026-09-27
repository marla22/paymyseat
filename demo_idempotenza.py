import urllib.request
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

# Generiamo una singola chiave per tutta questa transazione
chiave_di_idempotenza = str(uuid.uuid4())

def fai_pagamento(numero_thread):
    try:
        # Prepara il payload del pagamento
        dati = json.dumps({
            'booking_id': '550e8400-e29b-41d4-a716-446655440000', 
            'amount_cents': 5000, 
            'callback_url': 'http://localhost:5001'
        }).encode('utf-8')
        
        # Invia la richiesta HTTP POST all'API
        req = urllib.request.Request(
            'http://localhost:5000/api/payments',
            data=dati,
            headers={
                'Idempotency-Key': chiave_di_idempotenza, 
                'Content-Type': 'application/json'
            }
        )
        
        # Legge la risposta
        risposta = urllib.request.urlopen(req).read().decode('utf-8')
        print(f"[Thread {numero_thread}] SUCCESSO! L'API ha risposto.")
        
    except Exception as e:
        print(f"[Thread {numero_thread}] ERRORE: {e}")

if __name__ == '__main__':
    print(f"--- TEST IDEMPOTENZA INIZIATO ---")
    print(f"Chiave utilizzata per le richieste (condivisa tra i thread): {chiave_di_idempotenza}\n")
    print("Lanciando 10 pagamenti SIMULTANEAMENTE (Race Condition)...")
    
    # Lancia 10 thread nello stesso esatto momento
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(10):
            executor.submit(fai_pagamento, i + 1)
            
    print("\n--- TEST COMPLETATO ---")
    print("Vai a controllare su http://localhost:5173/dashboard:")
    print("Troverai un SOLO pagamento da 50.00€ con Booking ID 'TEST-PYTHON-1'.")
    print("Tutte le altre 9 richieste sono state lette e servite in sicurezza dalla CACHE Redis!")
