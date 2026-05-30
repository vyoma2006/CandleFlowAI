import React from 'react';
import { Zap, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

// ─── Maps the new signal_quality string from main.py ─────────────────────────
// Values: "High Conviction — Strong directional spread detected"
//         "Moderate Conviction — Directional bias present"
//         "Low Conviction — Weak edge, exercise caution"
//         "No Edge — Model is near-neutral on this ticker"

function parseQuality(text) {
  if (!text) return null;
  const t = text.toLowerCase();

  if (t.includes('high conviction')) return {
    icon: Zap,
    iconColor: 'text-emerald-400',
    bgColor:   'bg-emerald-950/30',
    border:    'border-emerald-900/60',
    label:     'HIGH CONVICTION',
    body:      'Strong directional spread — signal is actionable.',
  };
  if (t.includes('moderate conviction')) return {
    icon: TrendingDown,
    iconColor: 'text-amber-400',
    bgColor:   'bg-amber-950/20',
    border:    'border-amber-900/60',
    label:     'MODERATE CONVICTION',
    body:      'Directional bias present — proceed with reduced size.',
  };
  if (t.includes('low conviction')) return {
    icon: AlertTriangle,
    iconColor: 'text-slate-400',
    bgColor:   'bg-slate-900/40',
    border:    'border-slate-800',
    label:     'LOW CONVICTION',
    body:      'Weak edge detected — consider waiting for confirmation.',
  };
  // "No Edge" or anything else
  return {
    icon: Minus,
    iconColor: 'text-slate-600',
    bgColor:   'bg-slate-900/20',
    border:    'border-slate-900',
    label:     'NO EDGE',
    body:      'Model is near-neutral — stand aside.',
  };
}

export default function SignalStatus({ positionStatus }) {
  const parsed = parseQuality(positionStatus);
  if (!parsed) return null;
  const Icon = parsed.icon;

  return (
    <div className={`rounded-xl border p-3 flex items-start gap-2.5 ${parsed.bgColor} ${parsed.border}`}>
      <Icon className={`h-3.5 w-3.5 mt-0.5 shrink-0 ${parsed.iconColor}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-[9px] font-mono font-black tracking-widest ${parsed.iconColor}`}>
          {parsed.label}
        </p>
        <p className="text-[10px] font-mono text-slate-400 mt-1 leading-relaxed">
          {parsed.body}
        </p>
      </div>
    </div>
  );
}