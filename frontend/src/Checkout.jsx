import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link, useSearchParams } from 'react-router-dom';

export default function Checkout() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [paymentResult, setPaymentResult] = useState(null);

  // Parse Query Params
  const booking_id = searchParams.get('booking_id') || "BK-" + Math.floor(Math.random() * 10000);
  const amount_cents = parseInt(searchParams.get('amount_cents')) || 2500;
  const event_name = searchParams.get('event_name') || "Concerto Sinfonico";
  const venue = searchParams.get('venue') || "Colonne Sonore Studio Ghibli";
  const seats = searchParams.get('seats') || "F12, F13";
  const email_param = searchParams.get('email') || "";
  const callback_url = searchParams.get('callback_url') || "http://localhost:5001/webhook";
  const return_url = searchParams.get('return_url') || "";

  const amount_eur = (amount_cents / 100).toFixed(2);

  const [cardName, setCardName] = useState(email_param);
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');

  const [idempotencyKey] = useState(() => 
    crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36)
  );

  const handlePayment = async (e) => {
    e.preventDefault();
    setStatus('loading');
    
    try {
      const response = await axios.post(`http://${window.location.hostname}:5000/api/payments`, {
        booking_id: booking_id,
        amount_cents: amount_cents,
        callback_url: callback_url 
      }, {
        headers: {
          'Idempotency-Key': idempotencyKey,
          'Content-Type': 'application/json'
        }
      });

      setTimeout(() => {
        setPaymentResult(response.data);
        setStatus('success');
        
        // Auto-redirect if return_url is provided
        if (return_url) {
          setTimeout(() => {
            window.location.href = return_url;
          }, 4000);
        }
      }, 1200);

    } catch (error) {
      console.error("Errore durante il pagamento:", error);
      setStatus('error');
    }
  };

  // --- SCHERMATA DI ESITO PAGAMENTO ---
  if (status === 'success' && paymentResult) {
    const isFailed = paymentResult.status === 'FAILED';
    const bgColor = isFailed ? 'bg-red-600/30' : 'bg-emerald-600/30';
    const titleColor = isFailed ? 'from-red-400 to-orange-400' : 'from-emerald-400 to-cyan-400';
    const titleText = isFailed ? 'Pagamento Rifiutato' : 'Pagamento Confermato';
    const descText = isFailed ? 'La tua carta è stata declinata dalla banca.' : 'Transazione crittografata e completata con successo.';
    const badgeColor = isFailed ? 'text-red-400 bg-red-400/10' : 'text-emerald-400 bg-emerald-400/10';

    return (
      <div className="relative min-h-screen bg-gray-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 overflow-hidden text-white">
        {/* Sfondi Neon Sfocati */}
        <div className={`absolute top-1/4 left-1/4 w-96 h-96 ${bgColor} rounded-full filter blur-[128px] opacity-70`}></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/20 rounded-full filter blur-[128px] opacity-70"></div>

        <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
          <div className="bg-white/10 backdrop-blur-xl py-10 px-6 shadow-2xl sm:rounded-3xl sm:px-10 border border-white/20 text-center">
            <div className={`mx-auto flex items-center justify-center h-20 w-20 rounded-full ${isFailed ? 'bg-red-500/20 border border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.3)]' : 'bg-emerald-500/20 border border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.3)]'} mb-6`}>
              {isFailed ? (
                <svg className="h-10 w-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-10 w-10 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <h2 className={`text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r ${titleColor} mb-2`}>
              {titleText}
            </h2>
            <p className="text-gray-400 mb-8 text-sm">{descText}</p>
            
            <div className="bg-black/40 rounded-2xl p-5 text-left border border-white/10 mb-8 space-y-4 shadow-inner">
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Stato</span>
                <span className={`font-bold ${badgeColor} px-3 py-1 rounded-full text-xs tracking-wider`}>{paymentResult.status}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Booking ID</span>
                <span className="font-semibold text-white tracking-wider">{paymentResult.booking_id}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Payment ID</span>
                <span className="font-mono text-gray-300 text-xs">{paymentResult.payment_id.split('-')[0]}...</span>
              </div>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row">
              {return_url ? (
                <a href={return_url} className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-[0_0_20px_rgba(59,130,246,0.3)] text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 transition-all">
                  Torna al sito del venditore (Redirect tra 4s...)
                </a>
              ) : (
                <Link to="/dashboard" className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-[0_0_20px_rgba(59,130,246,0.3)] text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 transition-all">
                  Dashboard
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- SCHERMATA DI CHECKOUT ---
  return (
    <div className="relative min-h-screen bg-gray-950 pt-10 pb-16 px-4 sm:px-6 lg:px-8 font-sans overflow-hidden text-white flex items-center justify-center">
      
      {/* Elementi Decorativi di Sfondo (Neon Orbs) */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-purple-600/20 rounded-full filter blur-[150px] opacity-70"></div>
      <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-600/20 rounded-full filter blur-[150px] opacity-70"></div>

      <div className="relative w-full max-w-6xl mx-auto z-10">
        <div className="text-center mb-12">
          <h2 className="text-5xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
            PayMySeat
          </h2>
          <p className="mt-3 text-gray-400 font-light tracking-wide">Next-Gen Cloud Payment Gateway</p>
        </div>

        <div className="bg-white/5 backdrop-blur-2xl shadow-2xl rounded-3xl overflow-hidden flex flex-col lg:flex-row border border-white/10">
          
          {/* Colonna Riepilogo Ordine (Sinistra) */}
          <div className="p-8 lg:w-5/12 bg-black/20 border-b lg:border-b-0 lg:border-r border-white/10 flex flex-col justify-between">
            <div>
              <h3 className="text-xl font-semibold text-white mb-8 flex items-center gap-2">
                <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                Riepilogo Ordine
              </h3>
              
              <div className="flex items-start space-x-5 mb-8 bg-white/5 p-4 rounded-2xl border border-white/5">
                <div className="h-16 w-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
                  <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-base font-semibold text-white leading-tight">{event_name}</h4>
                  <p className="text-sm text-purple-300 mt-1">{venue}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-white/10 text-xs rounded-md text-gray-300">Posti: {seats}</span>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 pt-6 space-y-4">
              <div className="border-t border-white/10 pt-4 flex justify-between items-center">
                <span className="text-lg font-medium text-gray-300">Totale</span>
                <span className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">€{amount_eur}</span>
              </div>
            </div>
          </div>

          {/* Colonna Form di Pagamento (Destra) */}
          <div className="p-8 lg:p-12 lg:w-7/12">
            <h3 className="text-xl font-semibold text-white mb-8">Dettagli di Pagamento</h3>
            
            {status === 'error' && (
              <div className="mb-8 rounded-2xl bg-red-500/10 p-4 border border-red-500/50 backdrop-blur-sm">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-red-400 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm text-red-200">Errore di connessione al microservizio. Riprova.</p>
                </div>
              </div>
            )}

            <form onSubmit={handlePayment} className="space-y-6">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Titolare Carta</label>
                <input 
                  type="text" 
                  required 
                  value={cardName}
                  onChange={(e) => setCardName(e.target.value)}
                  className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all" 
                  placeholder="es. Valeria Platania" 
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Numero Carta</label>
                <div className="relative">
                  <input 
                    type="text" 
                    required 
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    className="w-full bg-black/20 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-white placeholder-gray-500 font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all" 
                    placeholder="0000 0000 0000 0000" 
                  />
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Scadenza</label>
                  <input 
                    type="text" 
                    required 
                    value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 font-mono focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all" 
                    placeholder="MM/AA" 
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">CVC</label>
                  <input 
                    type="password" 
                    required 
                    value={cvc}
                    maxLength="3"
                    onChange={(e) => setCvc(e.target.value)}
                    className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 font-mono focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all" 
                    placeholder="•••" 
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={status === 'loading'}
                className={`w-full relative group overflow-hidden rounded-xl p-[1px] mt-4 transition-all ${status === 'loading' ? 'opacity-70 cursor-not-allowed' : 'hover:scale-[1.02]'}`}
              >
                <span className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-xl opacity-70 group-hover:opacity-100 transition-opacity duration-300"></span>
                <div className="relative flex items-center justify-center bg-black/50 backdrop-blur-md px-8 py-4 rounded-xl">
                  {status === 'loading' ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span className="font-bold text-white tracking-wide">Elaborazione sicura...</span>
                    </>
                  ) : (
                    <span className="font-bold text-white tracking-wide">Conferma Pagamento — €{amount_eur}</span>
                  )}
                </div>
              </button>
            </form>

            <div className="mt-8 flex items-center justify-center space-x-2 text-xs text-gray-500">
              <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span>Protetto da crittografia end-to-end 256-bit</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}