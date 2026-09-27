import re
import io

with io.open('Relazione_PayMySeat.tex', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Idempotency language
text = re.sub(
    r'garanzia provata con inattaccabile fermezza\.',
    r'Il test eseguito ha verificato che, per le condizioni di concorrenza considerate, una sola richiesta ha completato l\'inserimento del pagamento, mentre le richieste duplicate hanno restituito il risultato associato alla chiave di idempotenza.',
    text
)
text = text.replace(
    'Il bilancio totale dell\'esaminatore rivela che il Database è rimasto inalterato oltre l\'unità.',
    'L\'esito delle prove dimostra che solo una delle 10 richieste concorrenti viene elaborata per intero, mentre le restanti 9 ricevono la risposta memorizzata (status 200) dal meccanismo di lock (SET NX) senza causare inserimenti duplicati nel database MySQL.'
)
text = text.replace('isolare in modo serializzabile la riga', 'usare un isolamento appropriato e un vincolo UNIQUE')
text = text.replace('isolamento SERIALIZABLE', 'isolamento (di default REPEATABLE READ in InnoDB)')

# 2. Outbox & TCP ACK
text = text.replace('conferma di ricezione (TCP ACK)', 'conferma di ricezione (Publisher Confirms)')
text = text.replace('garantendo matematicamente che l\'evento venga inoltrato Exactly-Once o At-Least-Once senza fallimenti silenziosi', 'garantendo l\'inoltro At-Least-Once (almeno una volta). Poiché l\'evento potrebbe essere processato più volte in caso di network failure post-pubblicazione, i sistemi a valle (come HoldMySeat) devono a loro volta implementare meccanismi di idempotenza')

# 3. HMAC, Replay Attacks & Security
text = text.replace('matematicamente irrevocabile', 'robusta')
text = re.sub(r'(La sicurezza.*?)(Questa garanzia \`e assoluta)', r'\1 Inoltre, pur garantendo l\'autenticità e l\'integrità, l\'uso esclusivo di HMAC non previene attacchi di tipo Replay (Replay Attack); per questo motivo in scenari di produzione reali è consigliabile abbinarlo al protocollo TLS/HTTPS e all\'inclusione di un Timestamp temporale (con finestra di validità) nel payload.', text)

# 4. Saga responsibilities
# Replace wording about refund worker deciding it.
text = text.replace(
    'Il microservizio "Refund Worker" resta sintonizzato in disparte. Esso ha l\'esclusiva responsabilità di stornare il saldo al cliente nel malaugurato caso in cui la prenotazione originaria ad HoldMySeat fallisca e si renda necessaria un\'azione compensativa (Saga Pattern).',
    'Nel pattern Saga implementato (Coreografia), HoldMySeat e PayMySeat agiscono indipendentemente. In caso di fallimento o rimborso, è la Payment API (su richiesta esplicita del cliente o del sistema esterno) a inserire un evento "refund.requested" in outbox. Il "Refund Worker" si limita ad ascoltare tale evento in modo asincrono, contattando il provider esterno per stornare l\'importo effettivo. L\'orchestrazione rimane decentralizzata.'
)

# 5. Tone down words
text = text.replace('ghosting fraudolento', 'perdita permanente e incontrollata')
text = text.replace('inattaccabile fermezza', 'elevata affidabilità')
text = text.replace('mostruose e ingiuste sfide', 'sfide complesse tipiche dei sistemi distribuiti')
text = text.replace('standard aureo', 'una pratica consolidata')
text = text.replace('elegante, solido, blindato e verticalmente scalabile', 'robusto e scalabile orizzontalmente')

# 6. Proposal vs Implementation Section
# Add right before \chapter{Manuale d'Uso e Replicazione delle Prove}
proposal_diff = r'''
\section{Evoluzione dalla Proposta al MVP (Minimum Viable Product)}
Durante la fase di stesura iniziale (Progetto Teorico), l'architettura era stata ideata per includere nativamente l'utilizzo di servizi Cloud completamente gestiti su AWS, tra cui Amazon SQS/MQ in sostituzione a RabbitMQ, DynamoDB al posto di MongoDB, e l'adozione dell'orchestrazione tramite Kubernetes (EKS) con Auto-Scaling e bilanciatori ALB. 

Ai fini della validazione sperimentale e per rientrare nei vincoli temporali del progetto, l'implementazione reale descritta nei capitoli successivi (e riproducibile nell'Appendice A) si basa invece su un ambiente Docker Compose su macchine EC2, accompagnato da script Terraform e Ansible. Questa infrastruttura (IaaS) simula fedelmente le interazioni a microservizi, mentre l'architettura a servizi gestiti e Kubernetes delineata in proposta rappresenta la traiettoria di evoluzione per uno scenario produttivo definitivo (Future Work).

'''
text = text.replace('\\chapter{Manuale d\'Uso e Replicazione delle Prove}', proposal_diff + '\n\\chapter{Manuale d\'Uso e Replicazione delle Prove}')


with io.open('Relazione_PayMySeat_fixed.tex', 'w', encoding='utf-8') as f:
    f.write(text)
