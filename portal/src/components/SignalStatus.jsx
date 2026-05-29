import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, DollarSign, Layers } from 'lucide-react';

// ─── Parses the position_status string from the backend ──────────────────────
function parseStatus(statusText) {
  if (!statusText) return null;
  const t = statusText.toLowerCase();

  if (t.includes('allocation committed') || t.includes('live signal verified')) {
    return {
      type: 'executed',
      icon: CheckCircle,
      iconColor: 'text-emerald-400',
      bgColor: 'bg-emerald-950/40',
      borderColor: 'border-emerald-900',
      title: 'Order Executed',
      body: statusText,
      action: null,
    };
  }
  if (t.includes('low cash')) {
    return {
      type: 'low_cash',
      icon: DollarSign,
      iconColor: 'text-amber-400',
      bgColor: 'bg-amber-950/30',
      borderColor: 'border-amber-900',
      title: 'Insufficient Cash Balance',
      body: 'Your paper wallet has insufficient funds to allocate this position.',
      action: 'Free up capital by closing an existing position, or reduce position size.',
    };
  }
  if (t.includes('position limit')) {
    return {
      type: 'position_limit',
      icon: Layers,
      iconColor: 'text-amber-400',
      bgColor: 'bg-amber-950/30',
      borderColor: 'border-amber-900',
      title: 'Max Position Limit Reached',
      body: 'The paper broker has reached its maximum concurrent open positions.',
      action: 'Close one or more existing positions before opening a new one.',
    };
  }
  if (t.includes('stand alone') || t.includes('signal ignored')) {
    return {
      type: 'ignored',
      icon: XCircle,
      iconColor: 'text-rose-400',
      bgColor: 'bg-rose-950/20',
      borderColor: 'border-rose-900',
      title: 'Signal Not Executed',
      body: 'Broker rules prevented this signal from being acted upon.',
      action: 'Check cash balance and active position count in the trade log.',
    };
  }
  if (t.includes('monitoring') || t.includes('no live')) {
    return {
      type: 'monitoring',
      icon: AlertTriangle,
      iconColor: 'text-slate-500',
      bgColor: 'bg-slate-900/40',
      borderColor: 'border-slate-800',
      title: 'Monitoring — No Action Taken',
      body: 'Signal is below execution threshold or is a HOLD.',
      action: null,
    };
  }
  // fallback
  return {
    type: 'info',
    icon: AlertTriangle,
    iconColor: 'text-slate-500',
    bgColor: 'bg-slate-900/40',
    borderColor: 'border-slate-800',
    title: 'Broker Status',
    body: statusText,
    action: null,
  };
}

export default function SignalStatus({ positionStatus }) {
  const parsed = parseStatus(positionStatus);
  if (!parsed) return null;

  const Icon = parsed.icon;

  return (
    <div className={`rounded-xl border p-3 flex items-start gap-3 ${parsed.bgColor} ${parsed.borderColor}`}>
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${parsed.iconColor}`} />
      <div className="flex-1 min-w-0">
        <p className={`text-[10px] font-mono font-black tracking-wider ${parsed.iconColor}`}>
          {parsed.title}
        </p>
        <p className="text-[10px] font-mono text-slate-400 mt-1 leading-relaxed">
          {parsed.body}
        </p>
        {parsed.action && (
          <p className="text-[10px] font-mono text-slate-500 mt-1.5 border-t border-slate-800/60 pt-1.5 leading-relaxed">
            → {parsed.action}
          </p>
        )}
      </div>
    </div>
  );
}