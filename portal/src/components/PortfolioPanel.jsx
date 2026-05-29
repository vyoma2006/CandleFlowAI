import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Trash2,
  PlusCircle, BarChart3, RefreshCw, BookMarked,
  ChevronRight
} from 'lucide-react';

// ─── Mini sparkline ───────────────────────────────────────────────────────────
const generateSparkline = (ticker, signal) => {
  const bars = [];
  let val = 50;
  for (let i = 0; i < 20; i++) {
    const drift = signal?.includes('BUY') ? 0.6 : signal?.includes('SELL') ? 0.4 : 0.5;
    val += (Math.random() - drift) * 8;
    val = Math.max(10, Math.min(90, val));
    bars.push(parseFloat(val.toFixed(2)));
  }
  return bars;
};

const Sparkline = ({ data, isUp }) => {
  if (!data || data.length < 2) return null;
  const w = 80, h = 28;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const color = isUp ? '#34d399' : '#f87171';
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="shrink-0 opacity-70">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
};

// ─── Signal badge ─────────────────────────────────────────────────────────────
const SignalBadge = ({ signal, small = false }) => {
  if (!signal) return null;
  const upper = signal.toUpperCase();
  let cls = 'bg-slate-800 text-slate-400 border-slate-700';
  if (upper.includes('STRONG BUY'))       cls = 'bg-emerald-950 text-emerald-400 border-emerald-500 animate-pulse';
  else if (upper.includes('BUY'))         cls = 'bg-green-950 text-green-400 border-green-600';
  else if (upper.includes('STRONG SELL')) cls = 'bg-rose-950 text-rose-400 border-rose-500 animate-pulse';
  else if (upper.includes('SELL'))        cls = 'bg-red-950 text-red-400 border-red-600';
  else                                    cls = 'bg-amber-950 text-amber-400 border-amber-600';
  return (
    <span className={`border font-mono font-black tracking-wider rounded-lg ${small ? 'text-[9px] px-1.5 py-0.5' : 'text-[10px] px-2 py-0.5'} ${cls}`}>
      {signal}
    </span>
  );
};

// ─── Single portfolio row ─────────────────────────────────────────────────────
const PortfolioRow = ({ item, onView, onRemove, isActive }) => {
  const isUp = (item.daily_change ?? 0) >= 0;
  const spark = React.useMemo(
    () => generateSparkline(item.ticker, item.ai_signal),
    [item.ticker, item.ai_signal]
  );

  // Invalid / unresolvable ticker state
  if (item._invalid || item._failed) {
    return (
      <div className="group relative flex items-center gap-3 px-4 py-3 border-b border-slate-900 border-l-2 border-l-rose-900/60 bg-rose-950/10">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-sm text-rose-400/80 tracking-tight line-through">
              {item.ticker?.replace('.NS', '')}
            </span>
            <span className="text-[9px] font-mono text-rose-500 border border-rose-900 bg-rose-950/60 px-1.5 py-0.5 rounded">
              INVALID SYMBOL
            </span>
          </div>
          <p className="text-[10px] text-rose-700 font-mono mt-0.5 truncate">
            Not found on NSE — use the search bar to find the correct symbol
          </p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(item.ticker); }}
          className="p-1 rounded-md text-rose-700 hover:text-rose-400 hover:bg-rose-950/40 shrink-0 transition-colors"
          aria-label={`Remove ${item.ticker}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div
      onClick={() => onView(item.ticker)}
      className={`group relative flex items-center gap-3 px-4 py-3 cursor-pointer border-b border-slate-900 transition-all hover:bg-slate-900/60
        ${isActive ? 'bg-slate-900/80 border-l-2 border-l-emerald-500' : 'border-l-2 border-l-transparent'}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-sm text-slate-100 tracking-tight truncate">
            {item.ticker?.replace('.NS', '')}
          </span>
          <SignalBadge signal={item.ai_signal} small />
        </div>
        <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">
          {item.name ?? item.ticker}
        </p>
      </div>

      <Sparkline data={spark} isUp={isUp} />

      <div className="text-right shrink-0">
        <p className="font-mono font-bold text-sm text-slate-200">
          {item.price != null
            ? `₹${item.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
            : '—'}
        </p>
        <p className={`font-mono text-[10px] font-semibold flex items-center justify-end gap-0.5 mt-0.5 ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
          {isUp ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
          {item.daily_change_pct != null
            ? `${isUp ? '+' : ''}${item.daily_change_pct.toFixed(2)}%`
            : '—'}
        </p>
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); onRemove(item.ticker); }}
        className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 p-1 rounded-md text-slate-600 hover:text-rose-400 hover:bg-rose-950/40 shrink-0"
        aria-label={`Remove ${item.ticker}`}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};

// ─── Add ticker input — uses autocomplete search, not raw input ───────────────
const AddTickerBar = ({ onAdd }) => {
  const [val, setVal]         = useState('');
  const [focused, setFocused] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  // Debounced autocomplete — same endpoint as App.jsx
  useEffect(() => {
    const clean = val.trim();
    if (!clean || clean.endsWith('.NS')) { setSuggestions([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`http://localhost:8000/api/tickers/search?q=${encodeURIComponent(clean)}`);
        const d = await r.json();
        setSuggestions(d ?? []);
      } catch { setSuggestions([]); }
    }, 150);
    return () => clearTimeout(t);
  }, [val]);

  const pick = (symbol) => {
    onAdd(symbol);
    setVal('');
    setSuggestions([]);
  };

  return (
    <div className="relative border-b border-slate-900">
      <div className={`flex items-center gap-2 px-3 py-2.5 transition-colors ${focused ? 'bg-slate-900/60' : 'bg-transparent'}`}>
        <PlusCircle className="h-3.5 w-3.5 text-slate-600 shrink-0" />
        <input
          type="text"
          value={val}
          onChange={e => setVal(e.target.value.toUpperCase())}
          onKeyDown={e => {
            if (e.key === 'Enter' && suggestions.length > 0) pick(suggestions[0].symbol);
            else if (e.key === 'Escape') { setVal(''); setSuggestions([]); }
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => { setFocused(false); setSuggestions([]); }, 200)}
          placeholder="Add ticker  e.g. INFY, TCS…"
          maxLength={20}
          className="flex-1 bg-transparent text-xs font-mono text-slate-300 placeholder-slate-600 outline-none"
        />
        {val.trim().length >= 2 && suggestions.length === 0 && (
          <span className="text-[9px] font-mono text-slate-700">no matches</span>
        )}
      </div>

      {/* Autocomplete dropdown */}
      {suggestions.length > 0 && focused && (
        <div className="absolute left-0 right-0 top-full bg-slate-950 border border-slate-800 rounded-b-xl shadow-2xl z-50 max-h-48 overflow-y-auto divide-y divide-slate-900">
          {suggestions.map(item => (
            <button
              key={item.symbol}
              type="button"
              onMouseDown={() => pick(item.symbol)}
              className="w-full text-left px-3 py-2.5 hover:bg-emerald-950/40 font-mono transition-colors flex justify-between items-center group"
            >
              <span className="text-xs text-slate-300 group-hover:text-emerald-400 truncate pr-2">
                {item.name}
              </span>
              <span className="text-[10px] font-bold text-emerald-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 shrink-0">
                {item.symbol}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Summary strip ────────────────────────────────────────────────────────────
const SummaryStrip = ({ items }) => {
  const total  = items.length;
  const bull   = items.filter(i => i.ai_signal?.includes('BUY')).length;
  const bear   = items.filter(i => i.ai_signal?.includes('SELL')).length;
  const valid  = items.filter(i => !i._invalid && !i._failed);
  const avgRsi = valid.length
    ? (valid.reduce((a, i) => a + (i.metrics?.rsi ?? i.rsi ?? 50), 0) / valid.length).toFixed(1)
    : null;

  const cells = [
    { label: 'Held',    val: total,           color: 'text-slate-300' },
    { label: 'Bull',    val: bull,            color: 'text-emerald-400' },
    { label: 'Bear',    val: bear,            color: 'text-rose-400' },
    { label: 'Avg RSI', val: avgRsi ?? '—',   color: 'text-amber-400' },
  ];

  return (
    <div className="grid grid-cols-4 border-b border-slate-900">
      {cells.map(({ label, val, color }) => (
        <div key={label} className="py-2.5 flex flex-col items-center border-r border-slate-900 last:border-r-0">
          <span className="text-[8px] font-mono text-slate-600 uppercase tracking-widest">{label}</span>
          <span className={`text-base font-mono font-black mt-0.5 ${color}`}>{val}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Main PortfolioPanel ──────────────────────────────────────────────────────
/**
 * Props:
 *   watchlist      — string[] of ticker symbols from App state
 *   activeTicker   — currently viewed ticker string (for highlight)
 *   onViewAnalysis — (ticker: string) => void
 *   onToggle       — (ticker: string) => void  (POST /api/user-portfolio/toggle)
 *   onRefresh      — () => void                (re-fetches /api/user-portfolio)
 */
export default function PortfolioPanel({
  watchlist = [],
  activeTicker,
  onViewAnalysis,
  onToggle,
  onRefresh,
}) {
  const [enriched,   setEnriched]   = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [collapsed,  setCollapsed]  = useState(false);

  const enrichWatchlist = useCallback(async (tickers) => {
    if (!tickers.length) { setEnriched([]); return; }
    setLoading(true);
    try {
      const results = await Promise.allSettled(
        tickers.map(t =>
          fetch(`http://localhost:8000/api/stock-info/${t}`)
            .then(r => r.json())
            .catch(() => ({ ticker: t, _failed: true }))
        )
      );
      setEnriched(
        results.map((r, i) => {
          const base = { ticker: tickers[i] };
          if (r.status !== 'fulfilled')  return { ...base, _failed: true };
          // Backend returns { error: "..." } when ticker symbol is invalid
          if (r.value?.error)            return { ...base, _invalid: true, _errorMsg: r.value.error };
          return { ...base, ...r.value };
        })
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    enrichWatchlist(watchlist);
  }, [watchlist, enrichWatchlist]);

  const handleAdd = async (sym) => {
    const ticker = sym.endsWith('.NS') ? sym : `${sym}.NS`;
    await onToggle(ticker);
    onRefresh?.();
  };

  const handleRemove = async (ticker) => {
    await onToggle(ticker);
    onRefresh?.();
  };

  return (
    <aside className="bg-slate-900/40 border border-slate-900 rounded-2xl overflow-hidden flex flex-col">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-900 bg-slate-900/60">
        <div className="flex items-center gap-2">
          <BookMarked className="h-3.5 w-3.5 text-emerald-500" />
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">
            Portfolio Watchlist
          </span>
          <span className="text-[9px] font-mono text-slate-600 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
            {watchlist.length} tickers
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => { onRefresh?.(); enrichWatchlist(watchlist); }}
            className="p-1.5 rounded-md text-slate-600 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
            title="Refresh portfolio data"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin text-emerald-500' : ''}`} />
          </button>
          <button
            onClick={() => setCollapsed(c => !c)}
            className="p-1.5 rounded-md text-slate-600 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            <ChevronRight className={`h-3 w-3 transition-transform ${collapsed ? '' : 'rotate-90'}`} />
          </button>
        </div>
      </div>

      {!collapsed && (
        <>
          <SummaryStrip items={enriched} />
          <AddTickerBar onAdd={handleAdd} />

          <div className="overflow-y-auto flex-1 custom-scrollbar" style={{ maxHeight: '420px' }}>
            {loading && !enriched.length ? (
              <div className="space-y-2 p-3 animate-pulse">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-12 bg-slate-900 rounded-xl border border-slate-800" />
                ))}
              </div>
            ) : enriched.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center px-4">
                <BarChart3 className="h-8 w-8 text-slate-800 mb-3" />
                <p className="text-xs font-mono text-slate-600 leading-relaxed">
                  No tickers in watchlist.<br />
                  Add one above to begin tracking.
                </p>
              </div>
            ) : (
              enriched.map(item => (
                <PortfolioRow
                  key={item.ticker}
                  item={item}
                  onView={onViewAnalysis}
                  onRemove={handleRemove}
                  isActive={activeTicker === item.ticker}
                />
              ))
            )}
          </div>

          {enriched.length > 0 && (
            <div className="px-4 py-2 border-t border-slate-900 bg-slate-950/40">
              <p className="text-[9px] font-mono text-slate-700 text-center tracking-wide">
                CLICK ROW TO ANALYZE  //  HOVER TO REMOVE
              </p>
            </div>
          )}
        </>
      )}
    </aside>
  );
}