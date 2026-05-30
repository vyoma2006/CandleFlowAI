import React, { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, BarChart2 } from 'lucide-react';

const fmt = (n) => n?.toLocaleString('en-IN', { maximumFractionDigits: 2 }) ?? '—';

// ─── Main price line + volume ─────────────────────────────────────────────────
function LineChart({ candles }) {
  const W = 700, H = 180;
  const PAD = { top: 12, right: 8, bottom: 24, left: 58 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top  - PAD.bottom;
  const volH   = 32;

  if (!candles?.length) return null;

  const closes = candles.map(c => c.close);
  const minP   = Math.min(...closes);
  const maxP   = Math.max(...closes);
  const rangeP = maxP - minP || 1;
  const maxVol = Math.max(...candles.map(c => c.volume)) || 1;
  const xStep  = innerW / (candles.length - 1);

  const toX = (i) => PAD.left + i * xStep;
  const toY = (p) => PAD.top + innerH - ((p - minP) / rangeP) * innerH;

  const linePts = candles.map((c, i) => `${toX(i).toFixed(1)},${toY(c.close).toFixed(1)}`).join(' ');
  const areaPath = [
    `M ${toX(0).toFixed(1)},${toY(candles[0].close).toFixed(1)}`,
    ...candles.map((c, i) => `L ${toX(i).toFixed(1)},${toY(c.close).toFixed(1)}`),
    `L ${toX(candles.length - 1).toFixed(1)},${(PAD.top + innerH).toFixed(1)}`,
    `L ${PAD.left},${(PAD.top + innerH).toFixed(1)}`,
    'Z',
  ].join(' ');

  const isUp      = candles[candles.length - 1].close >= candles[0].close;
  const lineColor = isUp ? '#34d399' : '#f87171';

  const yTicks = [0, 0.33, 0.66, 1].map(t => ({
    y:     PAD.top + innerH * (1 - t),
    label: fmt(minP + rangeP * t),
  }));

  const xLabels = [0, Math.floor(candles.length / 2), candles.length - 1].map(i => ({
    x: toX(i), label: candles[i].date.slice(5),
  }));

  return (
    <svg viewBox={`0 0 ${W} ${H + volH + 8}`} width="100%" style={{ display: 'block' }}>
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={lineColor} stopOpacity="0.18" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0"    />
        </linearGradient>
      </defs>

      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={PAD.left} y1={t.y} x2={W - PAD.right} y2={t.y}
            stroke="rgba(100,116,139,0.15)" strokeWidth="0.5" />
          <text x={PAD.left - 5} y={t.y + 4} textAnchor="end"
            fill="#475569" fontSize="9" fontFamily="'JetBrains Mono', monospace">
            {t.label}
          </text>
        </g>
      ))}

      {xLabels.map((l, i) => (
        <text key={i} x={l.x} y={H - 4} textAnchor="middle"
          fill="#475569" fontSize="9" fontFamily="'JetBrains Mono', monospace">
          {l.label}
        </text>
      ))}

      <path d={areaPath} fill="url(#areaGrad)" />
      <polyline points={linePts} fill="none" stroke={lineColor}
        strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={toX(candles.length - 1)} cy={toY(candles[candles.length - 1].close)}
        r="3.5" fill={lineColor} />

      {candles.map((c, i) => {
        const bH  = Math.max(2, (c.volume / maxVol) * (volH - 4));
        const bX  = toX(i) - (innerW / candles.length) * 0.35;
        const bW  = Math.max(1.5, (innerW / candles.length) * 0.7);
        const bY  = H + volH - bH;
        const col = c.close >= c.open ? 'rgba(52,211,153,0.35)' : 'rgba(248,113,113,0.35)';
        return <rect key={i} x={bX} y={bY} width={bW} height={bH} fill={col} rx="1" />;
      })}
    </svg>
  );
}

// ─── RSI strip — higher contrast ─────────────────────────────────────────────
function RsiStrip({ candles }) {
  const W = 700, H = 52;
  const PAD = { top: 8, right: 8, bottom: 14, left: 58 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top  - PAD.bottom;

  const rsiData = candles.filter(c => c.rsi != null);
  if (rsiData.length < 2) return null;

  const allI  = rsiData.map(c => candles.indexOf(c));
  const xStep = innerW / (candles.length - 1);
  const toX   = (i) => PAD.left + i * xStep;
  const toY   = (v) => PAD.top + innerH - ((v - 0) / 100) * innerH;

  const pts = rsiData.map((c, j) =>
    `${toX(allI[j]).toFixed(1)},${toY(c.rsi).toFixed(1)}`
  ).join(' ');

  const lastRsi   = rsiData[rsiData.length - 1].rsi;
  const rsiColor  = lastRsi > 70 ? '#f87171' : lastRsi < 30 ? '#34d399' : '#7dd3fc';
  const rsiLabel  = lastRsi > 70 ? 'OB' : lastRsi < 30 ? 'OS' : '';

  // Overbought / oversold fill zones
  const ob70y  = toY(70);
  const os30y  = toY(30);
  const chartB = toY(0);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      {/* OB zone fill */}
      <rect x={PAD.left} y={PAD.top} width={innerW} height={ob70y - PAD.top}
        fill="rgba(248,113,113,0.04)" />
      {/* OS zone fill */}
      <rect x={PAD.left} y={os30y} width={innerW} height={chartB - os30y}
        fill="rgba(52,211,153,0.04)" />

      {[70, 30].map(v => (
        <g key={v}>
          <line x1={PAD.left} y1={toY(v)} x2={W - PAD.right} y2={toY(v)}
            stroke={v === 70 ? 'rgba(248,113,113,0.35)' : 'rgba(52,211,153,0.35)'}
            strokeWidth="0.8" strokeDasharray="4,3" />
          <text x={PAD.left - 5} y={toY(v) + 3} textAnchor="end"
            fill={v === 70 ? '#f87171' : '#34d399'}
            fontSize="8" fontFamily="'JetBrains Mono', monospace" opacity="0.7">
            {v}
          </text>
        </g>
      ))}

      {/* RSI line — thicker, colored */}
      <polyline points={pts} fill="none" stroke={rsiColor}
        strokeWidth="1.6" strokeLinejoin="round" />

      {/* Current RSI dot + label */}
      <circle cx={toX(allI[allI.length - 1])} cy={toY(lastRsi)}
        r="3" fill={rsiColor} />
      <text x={W - PAD.right} y={toY(lastRsi) - 3} textAnchor="end"
        fill={rsiColor} fontSize="9" fontFamily="'JetBrains Mono', monospace" fontWeight="bold">
        RSI {lastRsi?.toFixed(1)}{rsiLabel ? ` (${rsiLabel})` : ''}
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

  // Period % move — more useful than just today's OHLC
  const periodMove = last && first
    ? (((last.close - first.close) / first.close) * 100)
    : null;
  const periodAbsolute = last && first
    ? (last.close - first.close)
    : null;

  const RANGES = [7, 15, 30, 60];

  return (
    <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart2 className="h-3.5 w-3.5 text-slate-500" />
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
            Price Chart
          </span>
          {periodMove != null && (
            <span className={`flex items-center gap-1 text-[10px] font-mono font-bold ${isUp ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isUp ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {isUp ? '+' : ''}{periodMove.toFixed(2)}% ({range}d)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {RANGES.map(d => (
            <button key={d} onClick={() => setRange(d)}
              className={`text-[9px] font-mono px-2 py-0.5 rounded border transition-colors
                ${range === d
                  ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                  : 'border-slate-800 text-slate-600 hover:text-slate-400 hover:border-slate-700'}`}>
              {d}D
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div className="h-56 bg-slate-900/60 rounded-xl border border-slate-800 animate-pulse" />
      ) : error ? (
        <div className="h-56 flex items-center justify-center text-xs font-mono text-slate-600">{error}</div>
      ) : candles.length > 0 ? (
        <div className="space-y-0">
          <LineChart candles={candles} />
          <div className="border-t border-slate-900/40 pt-1">
            <RsiStrip candles={candles} />
          </div>
        </div>
      ) : null}

      {/* Footer — period move instead of just today's OHLC */}
      {last && first && (
        <div className="grid grid-cols-5 gap-2 mt-3 pt-3 border-t border-slate-900">
          {[
            ['Open',  first.open,  null],
            ['High',  Math.max(...candles.map(c => c.high)),  null],
            ['Low',   Math.min(...candles.map(c => c.low)),   null],
            ['Close', last.close,  null],
            ['Move',  Math.abs(periodAbsolute), isUp],
          ].map(([lbl, val, upFlag]) => (
            <div key={lbl} className="text-center">
              <span className="text-[8px] font-mono text-slate-600 block">{lbl}</span>
              <span className={`text-[11px] font-mono font-bold block ${
                upFlag === true  ? 'text-emerald-400' :
                upFlag === false ? 'text-rose-400'    : 'text-slate-300'
              }`}>
                {lbl === 'Move'
                  ? `${isUp ? '+' : '-'}₹${fmt(val)}`
                  : `₹${fmt(val)}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}