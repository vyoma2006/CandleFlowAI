import React from 'react';

// ─── Arc gauge — pure SVG, no external lib ────────────────────────────────────
// Tiers:  < 55% = grey (noise)  |  55–70% = amber (caution)  |  > 70% = signal color
export default function ConfidenceMeter({ confidence, signal }) {
  // confidence comes in as "52.59%" string from backend — parse it
  const raw = typeof confidence === 'string'
    ? parseFloat(confidence.replace('%', ''))
    : (confidence ?? 50);

  const pct = Math.min(100, Math.max(0, raw));

  // Tier logic
  let tier, tierLabel, trackColor, needleColor;
  if (pct < 55) {
    tier = 'noise'; tierLabel = 'LOW CONVICTION';
    trackColor = '#334155'; needleColor = '#475569';
  } else if (pct < 70) {
    tier = 'caution'; tierLabel = 'MODERATE SIGNAL';
    trackColor = '#78350f'; needleColor = '#f59e0b';
  } else {
    const isShort = signal?.includes('SELL');
    tier = 'signal'; tierLabel = 'HIGH CONVICTION';
    trackColor = isShort ? '#7f1d1d' : '#064e3b';
    needleColor = isShort ? '#f87171' : '#34d399';
  }

  // SVG arc math — semicircle (180° sweep)
  const R = 52, CX = 70, CY = 70;
  const startAngle = -180; // left
  const sweepAngle = 180;  // half circle

  const polarToXY = (deg, r) => {
    const rad = (deg * Math.PI) / 180;
    return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
  };

  // Background arc (full 180°)
  const bgStart = polarToXY(startAngle, R);
  const bgEnd   = polarToXY(0, R);
  const bgPath  = `M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 0 1 ${bgEnd.x} ${bgEnd.y}`;

  // Fill arc
  const fillAngle = startAngle + (sweepAngle * pct) / 100;
  const fillEnd   = polarToXY(fillAngle, R);
  const largeArc  = sweepAngle * pct / 100 > 180 ? 1 : 0;
  const fillPath  = `M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 ${largeArc} 1 ${fillEnd.x} ${fillEnd.y}`;

  // Needle
  const needleAngle = startAngle + (sweepAngle * pct) / 100;
  const needleTip   = polarToXY(needleAngle, R - 6);
  const needleBase  = polarToXY(needleAngle, 10);

  // Tier tick markers at 55% and 70%
  const ticks = [55, 70].map(v => {
    const a  = startAngle + (sweepAngle * v) / 100;
    const p1 = polarToXY(a, R + 4);
    const p2 = polarToXY(a, R - 4);
    return { p1, p2, a };
  });

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 140 80" width="160" height="92">
        {/* Background track */}
        <path d={bgPath} fill="none" stroke="#1e293b" strokeWidth="10" strokeLinecap="round" />

        {/* Colored fill */}
        {pct > 0 && (
          <path d={fillPath} fill="none" stroke={trackColor} strokeWidth="10" strokeLinecap="round" />
        )}

        {/* Tier tick marks */}
        {ticks.map((t, i) => (
          <line key={i}
            x1={t.p1.x} y1={t.p1.y} x2={t.p2.x} y2={t.p2.y}
            stroke="#334155" strokeWidth="1.5" />
        ))}

        {/* Needle */}
        <line
          x1={needleBase.x} y1={needleBase.y}
          x2={needleTip.x}  y2={needleTip.y}
          stroke={needleColor} strokeWidth="2" strokeLinecap="round" />
        <circle cx={CX} cy={CY} r="4" fill={needleColor} />

        {/* Center value */}
        <text x={CX} y={CY + 16} textAnchor="middle"
          fill={needleColor} fontSize="13" fontWeight="bold"
          fontFamily="'JetBrains Mono', monospace">
          {pct.toFixed(1)}%
        </text>

        {/* Min / Max labels */}
        <text x={polarToXY(startAngle, R).x - 2} y={CY + 4} textAnchor="end"
          fill="#334155" fontSize="7" fontFamily="'JetBrains Mono', monospace">0</text>
        <text x={polarToXY(0, R).x + 2} y={CY + 4} textAnchor="start"
          fill="#334155" fontSize="7" fontFamily="'JetBrains Mono', monospace">100</text>
      </svg>

      {/* Tier label */}
      <span className={`text-[9px] font-mono font-black tracking-widest mt-0 ${
        tier === 'noise'   ? 'text-slate-600' :
        tier === 'caution' ? 'text-amber-500' : 'text-emerald-400'
      }`}>
        {tierLabel}
      </span>

      {/* Threshold legend */}
      <div className="flex items-center gap-3 mt-1.5">
        {[
          { color: 'bg-slate-600',  label: '<55% noise' },
          { color: 'bg-amber-500',  label: '55–70% caution' },
          { color: 'bg-emerald-500',label: '>70% signal' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${color}`} />
            <span className="text-[8px] font-mono text-slate-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}