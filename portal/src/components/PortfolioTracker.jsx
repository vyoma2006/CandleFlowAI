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
      } catch (err) { setError(err.message); } 
      finally { setLoading(false); }
    };

    fetchPortfolio();
    const interval = setInterval(fetchPortfolio, 3000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !portfolio) return <div className="text-gray-400 text-sm animate-pulse">Syncing...</div>;
  if (error) return <div className="text-red-400 text-sm">⚠️ Telemetry Exception: {error}</div>;

  const { active_positions } = portfolio || { active_positions: [] };

  return (
    <div className="mt-8">
      <div className="bg-[#0b1329] border border-[#1e293b] rounded-xl shadow-lg overflow-hidden">
        <div className="px-5 py-4 bg-[#111c44]/40 border-b border-[#1e293b] flex justify-between items-center">
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">Portfolio</h3>
          <span className="bg-[#1e293b] text-gray-300 text-xs px-2.5 py-1 rounded-md font-medium">
            {active_positions.length} Open Positions
          </span>
        </div>

        {active_positions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No live capital allocated.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#070d19] border-b border-[#1e293b] text-xs font-semibold uppercase tracking-wider text-gray-400">
                  <th className="py-3 px-5">Asset Ticker</th>
                  <th className="py-3 px-5">Signal</th>
                  <th className="py-3 px-5">Confidence</th>
                  <th className="py-3 px-5">Trend</th>
                  <th className="py-3 px-5">Volatility</th>
                  <th className="py-3 px-5">Risk Score</th>
                  <th className="py-3 px-5">Momentum</th>
                  <th className="py-3 px-5">Direction</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b] text-sm font-medium text-gray-200">
                {active_positions.map((pos) => (
                  <tr key={pos.ticker} className="hover:bg-[#111c44]/20 transition-colors">
                    <td className="py-4 px-5 font-bold text-white">{pos.ticker}</td>
                    <td className="py-4 px-5 text-emerald-400 font-bold">BUY</td>
                    <td className="py-4 px-5 font-mono">0.87</td>
                    <td className="py-4 px-5 font-mono text-emerald-400">Bullish</td>
                    <td className="py-4 px-5 font-mono">Medium</td>
                    <td className="py-4 px-5 font-mono">6/10</td>
                    <td className="py-4 px-5 font-mono text-emerald-400">Strong</td>
                    <td className="py-4 px-5 font-mono text-emerald-400">Up</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}