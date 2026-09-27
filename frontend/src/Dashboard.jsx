import { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPayments = async () => {
      try {
        const response = await axios.get(`http://${window.location.hostname}:5000/api/payments`);
        // Map the backend status 'COMPLETED' to 'PAID' for frontend consistency if needed
        // but backend already returns 'COMPLETED' (wait, the mock used PAID, let's just use what backend gives)
        setPayments(response.data.payments || []);
      } catch (error) {
        console.error("Errore fetch pagamenti:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPayments();
  }, []);

  const handleRefund = async (paymentId) => {
    try {
      await axios.post(`http://${window.location.hostname}:5000/api/payments/${paymentId}/refund`);
      alert(`Richiesta rimborso inviata per ${paymentId}`);
      // Ricarica la lista
      setLoading(true);
      const response = await axios.get(`http://${window.location.hostname}:5000/api/payments`);
      setPayments(response.data.payments || []);
      setLoading(false);
    } catch (error) {
      console.error("Errore invio rimborso:", error);
      alert("Errore nell'invio della richiesta di rimborso");
    }
  };

  return (
    <div className="relative min-h-screen bg-gray-950 py-12 px-4 sm:px-6 lg:px-8 font-sans overflow-hidden text-white">
      {/* Sfondi Neon Sfocati */}
      <div className="absolute top-0 right-1/4 w-[600px] h-[600px] bg-indigo-600/20 rounded-full filter blur-[150px] opacity-60"></div>
      <div className="absolute bottom-0 left-1/4 w-[500px] h-[500px] bg-emerald-600/20 rounded-full filter blur-[150px] opacity-50"></div>

      <div className="relative max-w-7xl mx-auto z-10">
        <div className="sm:flex sm:items-center sm:justify-between mb-12">
          <div>
            <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
              Transaction Control
            </h1>
            <p className="mt-2 text-sm text-gray-400 tracking-wide">
              Monitoraggio microservizi e gestione rimborsi Saga.
            </p>
          </div>
          <div className="mt-4 sm:mt-0">
            <Link
              to="/"
              className="inline-flex items-center px-6 py-3 border border-transparent rounded-xl shadow-[0_0_15px_rgba(99,102,241,0.3)] text-sm font-medium text-white bg-white/10 backdrop-blur-md hover:bg-white/20 transition-all border-white/10"
            >
              Nuovo Checkout
            </Link>
          </div>
        </div>

        <div className="bg-black/40 backdrop-blur-xl shadow-2xl rounded-3xl overflow-hidden border border-white/10">
          {loading ? (
            <div className="p-20 text-center flex flex-col items-center justify-center">
              <svg className="animate-spin h-10 w-10 text-indigo-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-gray-400 font-medium tracking-wider">Sincronizzazione col database...</span>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-white/10">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-6 py-5 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Payment ID</th>
                  <th className="px-6 py-5 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Booking</th>
                  <th className="px-6 py-5 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Importo</th>
                  <th className="px-6 py-5 text-left text-xs font-semibold text-gray-300 uppercase tracking-wider">Stato</th>
                  <th className="px-6 py-5 text-right text-xs font-semibold text-gray-300 uppercase tracking-wider">Azione</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-transparent">
                {payments.map((payment) => (
                  <tr key={payment.payment_id} className="hover:bg-white/5 transition-colors">
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-gray-400 font-mono">
                      {payment.payment_id}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm font-medium text-white">
                      {payment.booking_id}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-sm text-gray-300">
                      €{(payment.amount_cents / 100).toFixed(2)}
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap">
                      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${
                        payment.status === 'COMPLETED' || payment.status === 'PAID'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}>
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap text-right text-sm font-medium">
                      {(payment.status === 'COMPLETED' || payment.status === 'PAID') && (
                        <button 
                          onClick={() => handleRefund(payment.payment_id)}
                          className="text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-4 py-2 rounded-lg transition-colors border border-indigo-500/20"
                        >
                          Storna (Saga)
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}