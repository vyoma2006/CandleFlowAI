import React, { useEffect, useState, useRef } from 'react';
import { TrendingUp, TrendingDown, BarChart2 } from 'lucide-react';

// ─── helpers ─────────────────────────────────────────────────────────────────
const fmt = (n) => n?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—';

// ─── Inline SVG chart — no external lib needed ───────────────────────────────
function LineChart({ candles }) {
  const W = 700, H = 180, PAD = { top: 12, right: 8, bottom: 24, left: 52 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  if (!candles?.length) return null;

  const closes  = candles.map(c => c.close);
  const minP    = Math.min(...closes);
  const maxP    = Math.max(...closes);
  const rangeP  = maxP - minP || 1;

  const volumes  = candles.map(c => c.volume);
  const maxVol   = Math.max(...volumes) || 1;
  const volH     = 32; // volume bar height budget

  const xStep = innerW / (candles.length - 1);

  const toX = (i) => PAD.left + i * xStep;
  const toY = (p) => PAD.top + innerH - ((p - minP) / rangeP) * innerH;

  // Build polyline points
  const linePts = candles.map((c, i) => `${toX(i).toFixed(1)},${toY(c.close).toFixed(1)}`).join(' ');

  // Area fill path
  const areaPath = [
    `M ${toX(0).toFixed(1)},${toY(candles[0].close).toFixed(1)}`,
    ...candles.map((c, i) => `L ${toX(i).toFixed(1)},${toY(c.close).toFixed(1)}`),
    `L ${toX(candles.length - 1).toFixed(1)},${(PAD.top + innerH).toFixed(1)}`,
    `L ${PAD.left.toFixed(1)},${(PAD.top + innerH).toFixed(1)}`,
    'Z'
  ].join(' ');

  const isUp = candles[candles.length - 1].close >= candles[0].close;
  const lineColor  = isUp ? '#34d399' : '#f87171';
  const areaColor  = isUp ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)';

  // Y-axis labels (4 ticks)
  const yTicks = [0, 0.33, 0.66, 1].map(t => ({
    y: PAD.top + innerH * (1 - t),
    label: fmt(minP + rangeP * t),
  }));

  // X-axis labels — show first, middle, last
  const xLabels = [0, Math.floor(candles.length / 2), candles.length - 1].map(i => ({
    x: toX(i),
    label: candles[i].date.slice(5), // MM-DD
  }));

  return (
    <svg viewBox={`0 0 ${W} ${H + volH + 8}`} width="100%" style={{ display: 'block' }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.15" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={PAD.left} y1={t.y} x2={W - PAD.right} y2={t.y}
            stroke="rgba(100,116,139,0.15)" strokeWidth="0.5" />
          <text x={PAD.left - 4} y={t.y + 4} textAnchor="end"
            fill="#475569" fontSize="9" fontFamily="'JetBrains Mono', monospace">
            {t.label}
          </text>
        </g>
      ))}

      {/* X axis labels */}
      {xLabels.map((l, i) => (
        <text key={i} x={l.x} y={H - 4} textAnchor="middle"
          fill="#475569" fontSize="9" fontFamily="'JetBrains Mono', monospace">
          {l.label}
        </text>
      ))}

      {/* Area fill */}
      <path d={areaPath} fill="url(#areaGrad)" />

      {/* Line */}
      <polyline points={linePts} fill="none" stroke={lineColor}
        strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />

      {/* Last price dot */}
      <circle
        cx={toX(candles.length - 1)}
        cy={toY(candles[candles.length - 1].close)}
        r="3" fill={lineColor} />

      {/* Volume bars */}
      {candles.map((c, i) => {
        const bH  = Math.max(2, (c.volume / maxVol) * (volH - 4));
        const bX  = toX(i) - (innerW / candles.length) * 0.35;
        const bW  = Math.max(1.5, (innerW / candles.length) * 0.7);
        const bY  = H + volH - bH;
        const col = c.close >= c.open ? 'rgba(52,211,153,0.4)' : 'rgba(248,113,113,0.4)';
        return <rect key={i} x={bX} y={bY} width={bW} height={bH} fill={col} rx="1" />;
      })}
    </svg>
  );
}

// ─── RSI mini strip ───────────────────────────────────────────────────────────
function RsiStrip({ candles }) {
  const W = 700, H = 48, PAD = { top: 6, right: 8, bottom: 14, left: 52 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const rsiData = candles.filter(c => c.rsi != null);
  if (rsiData.length < 2) return null;

  const allI = rsiData.map(c => candles.indexOf(c));
  const xStep = innerW / (candles.length - 1);
  const toX   = (i) => PAD.left + i * xStep;
  const toY   = (v) => PAD.top + innerH - ((v - 0) / 100) * innerH;

  const pts = rsiData.map((c, j) => `${toX(allI[j]).toFixed(1)},${toY(c.rsi).toFixed(1)}`).join(' ');
  const lastRsi = rsiData[rsiData.length - 1].rsi;
  const rsiColor = lastRsi > 70 ? '#f87171' : lastRsi < 30 ? '#34d399' : '#94a3b8';

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      {/* 70 / 30 bands */}
      {[70, 30].map(v => (
        <g key={v}>
          <line x1={PAD.left} y1={toY(v)} x2={W - PAD.right} y2={toY(v)}
            stroke="rgba(100,116,139,0.2)" strokeWidth="0.5" strokeDasharray="3,3" />
          <text x={PAD.left - 4} y={toY(v) + 3} textAnchor="end"
            fill="#334155" fontSize="8" fontFamily="'JetBrains Mono', monospace">{v}</text>
        </g>
      ))}
      <polyline points={pts} fill="none" stroke={rsiColor}
        strokeWidth="1.2" strokeLinejoin="round" />
      {/* current RSI label */}
      <text x={W - PAD.right} y={toY(lastRsi) - 2} textAnchor="end"
        fill={rsiColor} fontSize="8" fontFamily="'JetBrains Mono', monospace" fontWeight="bold">
        RSI {lastRsi?.toFixed(1)}
      </text>
    </svg>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────
export default function PriceChart({ ticker }) {
  const [candles, setCandles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [range,   setRange]   = useState(30);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    fetch(`http://localhost:8000/api/price-history/${ticker}?days=${range}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) { setError(d.error); setCandles([]); }
        else setCandles(d.candles ?? []);
      })
      .catch(() => setError('Chart data unavailable'))
      .finally(() => setLoading(false));
  }, [ticker, range]);

  const last  = candles[candles.length - 1];
  const first = candles[0];
  const isUp  = last && first ? last.close >= first.close : true;
  const pctChg = last && first
    ? (((last.close - first.close) / first.close) * 100).toFixed(2)
    : null;

  const RANGES = [7, 15, 30, 60];

  return (
    <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-5">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart2 className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
            Price Chart
          </span>
          {pctChg && (
            <span className={`flex items-center gap-1 text-[10px] font-mono font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {isUp ? '+' : ''}{pctChg}% ({range}d)
            </span>
          )}
        </div>

        {/* Range selector */}
        <div className="flex items-center gap-1">
          {RANGES.map(d => (
            <button
              key={d}
              onClick={() => setRange(d)}
              className={`text-[9px] font-mono px-2 py-0.5 rounded border transition-colors
                ${range === d
                  ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                  : 'border-slate-800 text-slate-600 hover:text-slate-400 hover:border-slate-700'}`}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      {/* Chart body */}
      {loading ? (
        <div className="h-52 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse" />
      ) : error ? (
        <div className="h-52 flex items-center justify-center text-xs font-mono text-slate-600">
          {error}
        </div>
      ) : candles.length > 0 ? (
        <div className="space-y-1">
          <LineChart candles={candles} />
          <div className="border-t border-slate-900/60 pt-1">
            <RsiStrip candles={candles} />
          </div>
        </div>
      ) : null}

      {/* OHLC footer */}
      {last && (
        <div className="grid grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-900">
          {[['O', last.open], ['H', last.high], ['L', last.low], ['C', last.close]].map(([lbl, val]) => (
            <div key={lbl} className="text-center">
              <span className="text-[8px] font-mono text-slate-600 block">{lbl}</span>
              <span className="text-[11px] font-mono font-bold text-slate-300">₹{fmt(val)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}