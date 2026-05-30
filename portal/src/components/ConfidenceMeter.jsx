import React from 'react';

// ─── Model-aware tier thresholds ─────────────────────────────────────────────
// Your sigmoid model's real output range is roughly 0.50–0.65.
// A net_spread of 0.01 triggers BUY/SELL, 0.08 triggers STRONG BUY/SELL.
// So we tune tiers around that reality:
//   < 52%  → noise     (spread < 0.04, no meaningful edge)
//   52–58% → caution   (spread 0.04–0.08, weak directional bias)
//   > 58%  → signal    (spread > 0.08, strong conviction)
//
// The `netSpread` prop (0–1) is used when available for more precision.
// Falls back to raw pct if netSpread is not passed.

const getTier = (pct, netSpread, signal) => {
  const spread = netSpread != null ? netSpread : Math.abs((pct / 100) - 0.5) * 2;

  if (spread >= 0.08 || pct > 58) {
    const isSell = signal?.includes('SELL');
    return {
      tier:       'signal',
      label:      'HIGH CONVICTION',
      labelColor: isSell ? 'text-rose-400'    : 'text-emerald-400',
      trackColor: isSell ? '#7f1d1d'          : '#064e3b',
      fillColor:  isSell ? '#f87171'          : '#34d399',
    };
  }
  if (spread >= 0.04 || pct > 52) {
    return {
      tier:       'caution',
      label:      'MODERATE SIGNAL',
      labelColor: 'text-amber-400',
      trackColor: '#78350f',
      fillColor:  '#f59e0b',
    };
  }
  return {
    tier:       'noise',
    label:      'LOW CONVICTION',
    labelColor: 'text-slate-500',
    trackColor: '#1e293b',
    fillColor:  '#475569',
  };
};

export default function ConfidenceMeter({ confidence, signal, netSpread }) {
  const raw = typeof confidence === 'string'
    ? parseFloat(confidence.replace('%', ''))
    : (confidence ?? 50);
  const pct = Math.min(100, Math.max(0, raw));

  const { tier, label, labelColor, trackColor, fillColor } = getTier(pct, netSpread, signal);

  // SVG arc — semicircle 180° sweep
  // CY=75 (not 70) gives the arc more vertical room so the bottom doesn't get clipped
  const R = 52, CX = 72, CY = 75;

  const polarToXY = (deg, r) => ({
    x: CX + r * Math.cos((deg * Math.PI) / 180),
    y: CY + r * Math.sin((deg * Math.PI) / 180),
  });

  const bgStart   = polarToXY(-180, R);
  const bgEnd     = polarToXY(0,    R);
  const bgPath    = `M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 0 1 ${bgEnd.x} ${bgEnd.y}`;

  const fillAngle = -180 + (180 * pct) / 100;
  const fillEnd   = polarToXY(fillAngle, R);
  const largeArc  = pct > 50 ? 1 : 0;
  const fillPath  = `M ${bgStart.x} ${bgStart.y} A ${R} ${R} 0 ${largeArc} 1 ${fillEnd.x} ${fillEnd.y}`;

  const needleTip  = polarToXY(fillAngle, R - 8);
  const needleBase = polarToXY(fillAngle, 10);

  // Tier boundary ticks at 52% and 58% (model-tuned)
  const ticks = [52, 58].map(v => {
    const a  = -180 + (180 * v) / 100;
    const p1 = polarToXY(a, R + 5);
    const p2 = polarToXY(a, R - 5);
    return { p1, p2 };
  });

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 144 90" width="164" height="100">
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
          stroke={fillColor} strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={CX} cy={CY} r="4.5" fill={fillColor} />

        {/* Value */}
        <text x={CX} y={CY + 16} textAnchor="middle"
          fill={fillColor} fontSize="13" fontWeight="bold"
          fontFamily="'JetBrains Mono', monospace">
          {pct.toFixed(1)}%
        </text>

        {/* 0 / 100 labels */}
        <text x={polarToXY(-180, R).x - 2} y={CY + 4} textAnchor="end"
          fill="#334155" fontSize="7" fontFamily="'JetBrains Mono', monospace">0</text>
        <text x={polarToXY(0, R).x + 2}    y={CY + 4} textAnchor="start"
          fill="#334155" fontSize="7" fontFamily="'JetBrains Mono', monospace">100</text>
      </svg>

      {/* Tier label */}
      <span className={`text-[9px] font-mono font-black tracking-widest -mt-1 ${labelColor}`}>
        {label}
      </span>

      {/* Model-tuned legend */}
      <div className="flex items-center gap-3 mt-2">
        {[
          { color: 'bg-slate-600',  label: '<52% noise'    },
          { color: 'bg-amber-500',  label: '52–58% caution' },
          { color: 'bg-emerald-500',label: '>58% signal'   },
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