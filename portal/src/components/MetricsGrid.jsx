import React from 'react';

// ─── Context rules per indicator ─────────────────────────────────────────────
const METRIC_CONTEXT = {
  rsi: (v) => {
    if (v >= 70) return { label: 'OVERBOUGHT', color: 'text-rose-400',    bar: 'bg-rose-500',    pct: Math.min(100, v) };
    if (v <= 30) return { label: 'OVERSOLD',   color: 'text-emerald-400', bar: 'bg-emerald-500', pct: Math.min(100, v) };
    if (v >= 55) return { label: 'BULLISH',    color: 'text-green-400',   bar: 'bg-green-500',   pct: v };
    if (v <= 45) return { label: 'BEARISH',    color: 'text-amber-400',   bar: 'bg-amber-500',   pct: v };
    return             { label: 'NEUTRAL',     color: 'text-slate-400',   bar: 'bg-slate-600',   pct: v };
  },
  adx: (v) => {
    if (v >= 40) return { label: 'STRONG TREND',  color: 'text-emerald-400', bar: 'bg-emerald-500', pct: Math.min(100, v * 1.5) };
    if (v >= 25) return { label: 'TRENDING',       color: 'text-green-400',   bar: 'bg-green-500',   pct: Math.min(100, v * 1.5) };
    if (v >= 15) return { label: 'WEAK TREND',     color: 'text-amber-400',   bar: 'bg-amber-500',   pct: Math.min(100, v * 1.5) };
    return             { label: 'NO TREND',        color: 'text-slate-500',   bar: 'bg-slate-700',   pct: Math.min(100, v * 1.5) };
  },
  macd: (v) => {
    if (v > 0)  return { label: 'BULLISH CROSS', color: 'text-emerald-400', bar: 'bg-emerald-500', pct: Math.min(100, Math.abs(v) * 5) };
    if (v < 0)  return { label: 'BEARISH CROSS', color: 'text-rose-400',    bar: 'bg-rose-500',    pct: Math.min(100, Math.abs(v) * 5) };
    return             { label: 'ZERO LINE',     color: 'text-slate-400',   bar: 'bg-slate-600',   pct: 0 };
  },
  macd_hist: (v) => {
    if (v > 0)  return { label: 'EXPANDING UP',   color: 'text-emerald-400', bar: 'bg-emerald-500', pct: Math.min(100, Math.abs(v) * 8) };
    if (v < 0)  return { label: 'EXPANDING DOWN', color: 'text-rose-400',    bar: 'bg-rose-500',    pct: Math.min(100, Math.abs(v) * 8) };
    return             { label: 'FLAT',           color: 'text-slate-400',   bar: 'bg-slate-600',   pct: 0 };
  },
  bb_width: (v) => {
    if (v < 3)  return { label: 'SQUEEZE',        color: 'text-amber-400',   bar: 'bg-amber-500',   pct: Math.min(100, v * 10) };
    if (v < 8)  return { label: 'NORMAL',         color: 'text-slate-400',   bar: 'bg-slate-600',   pct: Math.min(100, v * 10) };
    return             { label: 'EXPANSION',      color: 'text-blue-400',    bar: 'bg-blue-500',    pct: Math.min(100, v * 10) };
  },
  atr: (v) => ({
    label: 'VOLATILITY', color: 'text-slate-400', bar: 'bg-slate-600',
    pct: Math.min(100, v / 2),
  }),
  price_to_sma20: (v) => {
    if (v > 1.03) return { label: 'ABOVE SMA20',  color: 'text-emerald-400', bar: 'bg-emerald-500', pct: Math.min(100, (v - 1) * 1000) };
    if (v < 0.97) return { label: 'BELOW SMA20',  color: 'text-rose-400',    bar: 'bg-rose-500',    pct: Math.min(100, (1 - v) * 1000) };
    return               { label: 'AT SMA20',     color: 'text-slate-400',   bar: 'bg-slate-600',   pct: 50 };
  },
};

const DISPLAY_NAMES = {
  rsi:            'RSI',
  price_to_sma20: 'Price / SMA20',
  macd:           'MACD',
  macd_hist:      'MACD Hist',
  bb_width:       'BB Width %',
  atr:            'ATR',
  adx:            'ADX',
};

// ─── Single metric card ───────────────────────────────────────────────────────
function MetricCard({ metricKey, value }) {
  const ctx = METRIC_CONTEXT[metricKey]?.(value) ?? {
    label: '', color: 'text-slate-400', bar: 'bg-slate-600', pct: 50,
  };

  const displayVal = typeof value === 'number' && value % 1 !== 0
    ? value.toFixed(3)
    : value;

  return (
    <div className="bg-slate-950/60 border border-slate-900 p-3.5 rounded-xl flex flex-col gap-2">
      {/* Top row: key + context label */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-slate-500 font-mono uppercase tracking-tight">
          {DISPLAY_NAMES[metricKey] ?? metricKey.replace(/_/g, ' ')}
        </span>
        <span className={`text-[8px] font-mono font-black tracking-wider ${ctx.color}`}>
          {ctx.label}
        </span>
      </div>

      {/* Value */}
      <span className="text-sm font-bold font-mono text-slate-300">
        {displayVal}
      </span>

      {/* Progress bar */}
      <div className="h-0.5 bg-slate-900 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${ctx.bar}`}
          style={{ width: `${ctx.pct.toFixed(1)}%` }}
        />
      </div>
    </div>
  );
}

// ─── Grid of all metrics ──────────────────────────────────────────────────────
export default function MetricsGrid({ metrics }) {
  if (!metrics) return null;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 font-mono">
      {Object.entries(metrics).map(([key, val]) => (
        <MetricCard key={key} metricKey={key} value={val} />
      ))}
    </div>
  );
}