import React, { useState, useEffect, useCallback } from 'react';
import { History, Trash2, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const STORAGE_KEY = 'candleflow_signal_history';
const MAX_ENTRIES = 50;

// ─── Persist helpers ──────────────────────────────────────────────────────────
export const logSignal = (stockData) => {
  if (!stockData?.ticker || !stockData?.ai_signal) return;
  try {
    const existing = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    const entry = {
      id:         Date.now(),
      ticker:     stockData.ticker,
      signal:     stockData.ai_signal,
      confidence: stockData.confidence,
      netSpread:  stockData.net_spread ?? null,
      price:      stockData.price,
      change_pct: stockData.daily_change_pct,
      timestamp:  new Date().toISOString(),
      rsi:        stockData.metrics?.rsi ?? null,
      adx:        stockData.metrics?.adx ?? null,
    };
    // Dedupe: if same ticker + signal within last 10 min, skip
    const tenMinAgo = Date.now() - 10 * 60 * 1000;
    const isDupe = existing.some(
      e => e.ticker === entry.ticker &&
           e.signal === entry.signal &&
           new Date(e.timestamp).getTime() > tenMinAgo
    );
    if (isDupe) return;
    const updated = [entry, ...existing].slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch { /* storage full or unavailable */ }
};

export const clearHistory = () => {
  try { localStorage.removeItem(STORAGE_KEY); } catch { }
};

// ─── Time formatter ───────────────────────────────────────────────────────────
const relTime = (iso) => {
  const diff = Date.now() - new Date(iso).getTime();
  const m    = Math.floor(diff / 60000);
  const h    = Math.floor(m / 60);
  const d    = Math.floor(h / 24);
  if (d > 0)  return `${d}d ago`;
  if (h > 0)  return `${h}h ago`;
  if (m > 0)  return `${m}m ago`;
  return 'just now';
};

// ─── Signal badge ─────────────────────────────────────────────────────────────
const SignalPill = ({ signal }) => {
  const s = signal?.toUpperCase() ?? '';
  let cls = 'bg-slate-800 text-slate-400 border-slate-700';
  if (s.includes('STRONG BUY'))  cls = 'bg-emerald-950 text-emerald-400 border-emerald-700';
  else if (s.includes('BUY'))    cls = 'bg-green-950 text-green-400 border-green-800';
  else if (s.includes('STRONG SELL')) cls = 'bg-rose-950 text-rose-400 border-rose-700';
  else if (s.includes('SELL'))   cls = 'bg-red-950 text-red-400 border-red-800';
  else                           cls = 'bg-amber-950 text-amber-400 border-amber-800';
  return (
    <span className={`text-[8px] font-mono font-black px-1.5 py-0.5 rounded border ${cls} shrink-0`}>
      {signal}
    </span>
  );
};

// ─── Ticker summary row ───────────────────────────────────────────────────────
// Groups by ticker — shows signal distribution
const TickerSummaryRow = ({ ticker, entries, onView }) => {
  const signals = entries.map(e => e.signal);
  const buys    = signals.filter(s => s.includes('BUY')).length;
  const sells   = signals.filter(s => s.includes('SELL')).length;
  const holds   = signals.filter(s => s === 'HOLD').length;
  const last    = entries[0];
  const bias    = buys > sells ? 'bull' : sells > buys ? 'bear' : 'neutral';

  return (
    <div
      onClick={() => onView(ticker)}
      className="px-3 py-2.5 border-b border-slate-900 hover:bg-slate-900/40 cursor-pointer transition-colors"
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-xs text-slate-200">
            {ticker.replace('.NS', '')}
          </span>
          <SignalPill signal={last.signal} />
        </div>
        <span className="text-[9px] font-mono text-slate-600">{relTime(last.timestamp)}</span>
      </div>

      {/* Signal distribution bar */}
      <div className="flex items-center gap-1.5">
        <div className="flex-1 h-1 bg-slate-900 rounded-full overflow-hidden flex">
          {buys  > 0 && <div className="bg-emerald-500 h-full" style={{ width: `${(buys  / entries.length) * 100}%` }} />}
          {holds > 0 && <div className="bg-amber-500  h-full" style={{ width: `${(holds / entries.length) * 100}%` }} />}
          {sells > 0 && <div className="bg-rose-500   h-full" style={{ width: `${(sells / entries.length) * 100}%` }} />}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {buys  > 0 && <span className="text-[8px] font-mono text-emerald-600">{buys}B</span>}
          {holds > 0 && <span className="text-[8px] font-mono text-amber-600">{holds}H</span>}
          {sells > 0 && <span className="text-[8px] font-mono text-rose-600">{sells}S</span>}
          <span className="text-[8px] font-mono text-slate-700">/{entries.length}</span>
        </div>
      </div>

      {/* Last price + confidence */}
      <div className="flex items-center justify-between mt-1">
        <span className="text-[9px] font-mono text-slate-500">
          ₹{last.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </span>
        <span className={`text-[9px] font-mono ${
          parseFloat(last.confidence) > 58 ? 'text-emerald-600' :
          parseFloat(last.confidence) > 52 ? 'text-amber-600' : 'text-slate-600'
        }`}>
          conf {last.confidence}
        </span>
      </div>
    </div>
  );
};

// ─── Recent log row (flat timeline view) ─────────────────────────────────────
const LogRow = ({ entry, onView }) => {
  const isUp = (entry.change_pct ?? 0) >= 0;
  return (
    <div
      onClick={() => onView(entry.ticker)}
      className="flex items-center gap-2.5 px-3 py-2 border-b border-slate-900 hover:bg-slate-900/40 cursor-pointer transition-colors"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-mono font-bold text-[11px] text-slate-300 truncate">
            {entry.ticker.replace('.NS', '')}
          </span>
          <SignalPill signal={entry.signal} />
        </div>
        <span className="text-[8px] font-mono text-slate-700 mt-0.5 block">{relTime(entry.timestamp)}</span>
      </div>
      <div className="text-right shrink-0">
        <span className="text-[10px] font-mono text-slate-400 block">
          ₹{entry.price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </span>
        <span className={`text-[8px] font-mono flex items-center justify-end gap-0.5 ${isUp ? 'text-emerald-600' : 'text-rose-600'}`}>
          {isUp ? <TrendingUp className="h-2 w-2" /> : <TrendingDown className="h-2 w-2" />}
          {Math.abs(entry.change_pct ?? 0).toFixed(2)}%
        </span>
      </div>
    </div>
  );
};

// ─── Summary stats strip ──────────────────────────────────────────────────────
const HistorySummary = ({ history }) => {
  const total    = history.length;
  const buys     = history.filter(e => e.signal.includes('BUY')).length;
  const sells    = history.filter(e => e.signal.includes('SELL')).length;
  const tickers  = new Set(history.map(e => e.ticker)).size;

  return (
    <div className="grid grid-cols-4 border-b border-slate-900">
      {[
        { label: 'Scans',   val: total,   color: 'text-slate-300' },
        { label: 'Tickers', val: tickers, color: 'text-blue-400'  },
        { label: 'Buy',     val: buys,    color: 'text-emerald-400' },
        { label: 'Sell',    val: sells,   color: 'text-rose-400'  },
      ].map(({ label, val, color }) => (
        <div key={label} className="py-2.5 flex flex-col items-center border-r border-slate-900 last:border-r-0">
          <span className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">{label}</span>
          <span className={`text-sm font-mono font-black mt-0.5 ${color}`}>{val}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────
export default function SignalHistory({ onViewAnalysis }) {
  const [history, setHistory] = useState([]);
  const [tab,     setTab]     = useState('tickers'); // 'tickers' | 'log'

  const reload = useCallback(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      setHistory(stored);
    } catch { setHistory([]); }
  }, []);

  useEffect(() => {
    reload();
    // Poll every 5s to pick up new signals logged by App.jsx
    const interval = setInterval(reload, 5000);
    return () => clearInterval(interval);
  }, [reload]);

  const handleClear = () => {
    clearHistory();
    setHistory([]);
  };

  // Group by ticker for the summary tab
  const byTicker = history.reduce((acc, entry) => {
    if (!acc[entry.ticker]) acc[entry.ticker] = [];
    acc[entry.ticker].push(entry);
    return acc;
  }, {});

  const tickersSorted = Object.entries(byTicker)
    .sort((a, b) => new Date(b[1][0].timestamp) - new Date(a[1][0].timestamp));

  return (
    <div className="bg-slate-900/40 border border-slate-900 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-900 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <History className="h-3.5 w-3.5 text-emerald-500" />
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
            Signal History
          </span>
        </div>
        {history.length > 0 && (
          <button
            onClick={handleClear}
            className="p-1.5 rounded-md text-slate-700 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
            title="Clear history"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Summary strip */}
      {history.length > 0 && <HistorySummary history={history} />}

      {/* Tabs */}
      {history.length > 0 && (
        <div className="flex border-b border-slate-900">
          {[
            { id: 'tickers', label: 'By Ticker' },
            { id: 'log',     label: 'Timeline'  },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex-1 py-2 text-[9px] font-mono font-black uppercase tracking-widest transition-colors
                ${tab === t.id
                  ? 'text-emerald-400 bg-emerald-950/30 border-b-2 border-emerald-500'
                  : 'text-slate-600 hover:text-slate-400'}`}>
              {t.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight: '320px' }}>
        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center px-4">
            <History className="h-6 w-6 text-slate-800 mb-2" />
            <p className="text-[10px] font-mono text-slate-600 leading-relaxed">
              No signals recorded yet.<br />
              Analyse a ticker to start logging.
            </p>
          </div>
        ) : tab === 'tickers' ? (
          tickersSorted.map(([ticker, entries]) => (
            <TickerSummaryRow
              key={ticker}
              ticker={ticker}
              entries={entries}
              onView={onViewAnalysis}
            />
          ))
        ) : (
          history.map(entry => (
            <LogRow key={entry.id} entry={entry} onView={onViewAnalysis} />
          ))
        )}
      </div>

      {history.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-900 bg-slate-950/40">
          <p className="text-[9px] font-mono text-slate-700 text-center tracking-wide">
            CLICK ROW TO RE-ANALYSE  //  LAST {Math.min(history.length, MAX_ENTRIES)} SCANS STORED
          </p>
        </div>
      )}
    </div>
  );
}