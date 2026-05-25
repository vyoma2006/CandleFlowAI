import React, { useState, useEffect } from 'react';

export default function PortfolioTracker() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPortfolio = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/portfolio');
        if (!response.ok) throw new Error('Failed to fetch portfolio matrix data.');
        const data = await response.json();
        setPortfolio(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    // Initial load + 3-second rapid telemetry polling loop
    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !portfolio) return <div className="text-gray-400 text-sm animate-pulse">Syncing virtual ledger accounts...</div>;
  if (error) return <div className="text-red-400 text-sm">⚠️ Telemetry Exception: {error}</div>;

  const { cash, total_equity, floating_pnl, active_positions } = portfolio || { cash: 100000, total_equity: 100000, floating_pnl: 0, active_positions: [] };
  const isProfit = floating_pnl >= 0;

  return (
    <div className="mt-8 space-y-6">
      {/* 💳 EXECUTIVE ACCOUNT VALUATION BANNER */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#0b1329] border border-[#1e293b] rounded-xl p-5 shadow-lg">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Liquid Cash Reserves</p>
          <p className="text-2xl font-bold text-white mt-1">₹{cash.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
        
        <div className="bg-[#0b1329] border border-[#1e293b] rounded-xl p-5 shadow-lg">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Total Portfolio Equity</p>
          <p className="text-2xl font-bold text-[#00ffcc] mt-1">₹{total_equity.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>

        <div className={`bg-[#0b1329] border border-[#1e293b] rounded-xl p-5 shadow-lg transition-colors duration-300 ${isProfit ? 'border-emerald-900/30' : 'border-rose-900/30'}`}>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Net Floating Profit / Loss</p>
          <p className={`text-2xl font-bold mt-1 ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isProfit ? '+' : ''}₹{floating_pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
      </div>

      {/* 📊 ACTIVE POSITION LEDGER MATRIX */}
      <div className="bg-[#0b1329] border border-[#1e293b] rounded-xl shadow-lg overflow-hidden">
        <div className="px-5 py-4 bg-[#111c44]/40 border-b border-[#1e293b] flex justify-between items-center">
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">Active Recurrent Position Matrix</h3>
          <span className="bg-[#1e293b] text-gray-300 text-xs px-2.5 py-1 rounded-md font-medium">
            {active_positions.length} Open Positions
          </span>
        </div>

        {active_positions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No live capital allocated. Deploy signals from the scanner module above to mount a position.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#070d19] border-b border-[#1e293b] text-xs font-semibold uppercase tracking-wider text-gray-400">
                  <th className="py-3 px-5">Asset Ticker</th>
                  <th className="py-3 px-5">Type</th>
                  <th className="py-3 px-5 text-right">Entry Price</th>
                  <th className="py-3 px-5 text-right">Live Tick</th>
                  <th className="py-3 px-5 text-right">Stop Loss</th>
                  <th className="py-3 px-5 text-right">Take Profit</th>
                  <th className="py-3 px-5 text-right">Unrealized PnL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b] text-sm font-medium text-gray-200">
                {active_positions.map((pos) => {
                  const posProfit = pos.pnl >= 0;
                  return (
                    <tr key={pos.ticker} className="hover:bg-[#111c44]/20 transition-colors duration-150">
                      <td className="py-4 px-5 font-bold text-white tracking-wide">{pos.ticker}</td>
                      <td className="py-4 px-5">
                        <span className={`px-2.5 py-0.5 rounded text-xs font-bold tracking-wider ${pos.type === 'BUY' ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40' : 'bg-rose-950/80 text-rose-400 border border-rose-800/40'}`}>
                          {pos.type}
                        </span>
                      </td>
                      <td className="py-4 px-5 text-right font-mono">₹{pos.entry_price.toFixed(2)}</td>
                      <td className="py-4 px-5 text-right font-mono text-gray-400">₹{pos.live_price.toFixed(2)}</td>
                      <td className="py-4 px-5 text-right font-mono text-rose-400/90">₹{pos.stop_loss.toFixed(2)}</td>
                      <td className="py-4 px-5 text-right font-mono text-emerald-400/90">₹{pos.take_profit.toFixed(2)}</td>
                      <td className={`py-4 px-5 text-right font-mono font-bold ${posProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {posProfit ? '+' : ''}{pos.pnl_pct.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}