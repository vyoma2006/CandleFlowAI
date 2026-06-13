import React, { useEffect, useState } from 'react';
import { Receipt, TrendingUp, TrendingDown, RefreshCw, Clock } from 'lucide-react';

const fmt = (n) => n?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—';
const fmtPct = (n) => (n != null ? `${n >= 0 ? '+' : ''}${n.toFixed(2)}%` : '—');

// ─── Single trade row ─────────────────────────────────────────────────────────
function TradeRow({ position }) {
  const isLong   = position.direction?.toUpperCase() === 'BUY';
  const pnl      = position.unrealized_pnl ?? position.realized_pnl ?? 0;
  const pnlPct   = position.pnl_pct ?? 0;
  const isProfit = pnl >= 0;

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-slate-900 hover:bg-slate-900/40 transition-colors">
      {/* Direction badge */}
      <span className={`text-[9px] font-mono font-black px-1.5 py-0.5 rounded border shrink-0
        ${isLong
          ? 'bg-green-950 text-green-400 border-green-900'
          : 'bg-red-950 text-red-400 border-red-900'}`}>
        {isLong ? 'LONG' : 'SHORT'}
      </span>

      {/* Ticker */}
      <span className="font-mono font-bold text-xs text-slate-200 flex-1 truncate">
        {position.ticker?.replace('.NS', '')}
      </span>

      {/* Entry price */}
      <div className="text-right shrink-0">
        <span className="text-[9px] text-slate-600 font-mono block">ENTRY</span>
        <span className="text-[11px] font-mono text-slate-400">₹{fmt(position.entry_price)}</span>
      </div>

      {/* Current / exit price */}
      <div className="text-right shrink-0">
        <span className="text-[9px] text-slate-600 font-mono block">
          {position.status === 'closed' ? 'EXIT' : 'CMP'}
        </span>
        <span className="text-[11px] font-mono text-slate-400">
          ₹{fmt(position.current_price ?? position.exit_price)}
        </span>
      </div>

      {/* P&L */}
      <div className={`text-right shrink-0 ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
        <div className="flex items-center justify-end gap-0.5">
          {isProfit ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
          <span className="text-[11px] font-mono font-bold">₹{fmt(Math.abs(pnl))}</span>
        </div>
        <span className="text-[9px] font-mono">{fmtPct(pnlPct)}</span>
      </div>

      {/* Status dot */}
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
        position.status === 'open' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-700'
      }`} />
    </div>
  );
}

// ─── Summary strip ────────────────────────────────────────────────────────────
function TradeSummary({ data }) {
  if (!data) return null;
  const totalPnl     = data.total_unrealized_pnl ?? 0;
  const cashBal      = data.cash_balance ?? 0;
  const openCount    = data.open_positions ?? 0;
  const closedCount  = (data.closed_trades ?? []).length;
  const isProfit     = totalPnl >= 0;

  return (
    <div className="grid grid-cols-4 border-b border-slate-900">
      {[
        { label: 'Cash',   val: `₹${(cashBal / 1000).toFixed(0)}K`, color: 'text-slate-300' },
        { label: 'Open',   val: openCount,  color: 'text-blue-400' },
        { label: 'Closed', val: closedCount, color: 'text-slate-400' },
        { label: 'P&L',    val: `${isProfit ? '+' : ''}₹${(Math.abs(totalPnl) / 1000).toFixed(1)}K`,
          color: isProfit ? 'text-emerald-400' : 'text-rose-400' },
      ].map(({ label, val, color }) => (
        <div key={label} className="py-2.5 flex flex-col items-center border-r border-slate-900 last:border-r-0">
          <span className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">{label}</span>
          <span className={`text-sm font-mono font-black mt-0.5 ${color}`}>{val}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Main TradeLog ────────────────────────────────────────────────────────────
export default function TradeLog() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab,     setTab]     = useState('open'); // 'open' | 'closed'

  const load = () => {
    setLoading(true);
    fetch('https://candleflowai.onrender.com/api/portfolio')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openTrades   = data?.positions ?? [];
  const closedTrades = data?.closed_trades ?? [];
  const rows         = tab === 'open' ? openTrades : closedTrades;

  return (
    <div className="bg-slate-900/40 border border-slate-900 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-900 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <Receipt className="h-3.5 w-3.5 text-emerald-500" />
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
            Paper Trade Log
          </span>
        </div>
        <button
          onClick={load}
          className="p-1.5 rounded-md text-slate-600 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin text-emerald-500' : ''}`} />
        </button>
      </div>

      {/* Summary */}
      <TradeSummary data={data} />

      {/* Tabs */}
      <div className="flex border-b border-slate-900">
        {['open', 'closed'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 text-[9px] font-mono font-black uppercase tracking-widest transition-colors
              ${tab === t
                ? 'text-emerald-400 bg-emerald-950/30 border-b-2 border-emerald-500'
                : 'text-slate-600 hover:text-slate-400'}`}
          >
            {t} ({t === 'open' ? openTrades.length : closedTrades.length})
          </button>
        ))}
      </div>

      {/* Trade rows */}
      <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight: '240px' }}>
        {loading && !data ? (
          <div className="space-y-1 p-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-10 bg-slate-900 rounded border border-slate-800" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center px-4">
            <Clock className="h-6 w-6 text-slate-800 mb-2" />
            <p className="text-[10px] font-mono text-slate-600">
              {tab === 'open' ? 'No open positions.' : 'No closed trades yet.'}
            </p>
          </div>
        ) : (
          rows.map((pos, i) => <TradeRow key={i} position={pos} />)
        )}
      </div>
    </div>
  );
}