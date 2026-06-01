// portal/src/components/AuthGate.jsx
import React, { useState } from 'react';
import { Activity, Eye, EyeOff, AlertTriangle, Loader2 } from 'lucide-react';

export default function AuthGate({ onLogin, onRegister, loading, error }) {
  const [mode,     setMode]     = useState('login');    // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm,  setConfirm]  = useState('');
  const [showPw,   setShowPw]   = useState(false);
  const [localErr, setLocalErr] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalErr(null);

    if (!username.trim() || !password.trim()) {
      setLocalErr('Username and password are required.'); return;
    }
    if (mode === 'register') {
      if (password.length < 8) {
        setLocalErr('Password must be at least 8 characters.'); return;
      }
      if (password !== confirm) {
        setLocalErr('Passwords do not match.'); return;
      }
      await onRegister(username.trim(), password);
    } else {
      await onLogin(username.trim(), password);
    }
  };

  const displayError = localErr || error;

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(15,23,42,0.97)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.97)_1px,transparent_1px)] bg-[size:32px_32px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,black,transparent)] pointer-events-none" />

      <div className="relative w-full max-w-sm">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="bg-emerald-500 p-3 rounded-xl text-slate-950 shadow-2xl shadow-emerald-500/30 mb-4">
            <Activity className="h-8 w-8" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
            CandleFlow Engine
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-1">v2.5 // Signal Intelligence Terminal</p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm shadow-2xl">

          {/* Tab switcher */}
          <div className="flex mb-6 bg-slate-950/60 rounded-xl p-1 border border-slate-800">
            {['login', 'register'].map(m => (
              <button key={m} onClick={() => { setMode(m); setLocalErr(null); }}
                className={`flex-1 py-2 text-xs font-mono font-black uppercase tracking-widest rounded-lg transition-all
                  ${mode === m
                    ? 'bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/20'
                    : 'text-slate-500 hover:text-slate-300'}`}>
                {m}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Username */}
            <div>
              <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="your_username"
                className="w-full bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/20 transition-all"
              />
            </div>

            {/* Password */}
            <div>
              <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  placeholder={mode === 'register' ? 'min. 8 characters' : '••••••••'}
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2.5 pr-10 text-sm text-slate-200 font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/20 transition-all"
                />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-3 text-slate-600 hover:text-slate-400 transition-colors">
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Confirm password (register only) */}
            {mode === 'register' && (
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">
                  Confirm Password
                </label>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  placeholder="repeat password"
                  className="w-full bg-slate-950/60 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-200 font-mono placeholder-slate-600 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/20 transition-all"
                />
              </div>
            )}

            {/* Error */}
            {displayError && (
              <div className="bg-rose-950/40 border border-rose-900 rounded-xl p-3 flex items-start gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
                <p className="text-xs font-mono text-rose-400">{displayError}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-mono font-black text-sm py-3 rounded-xl tracking-widest uppercase transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2"
            >
              {loading
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing...</>
                : mode === 'login' ? 'Login' : 'Create Account'}
            </button>
          </form>

          {/* Password strength hint for register */}
          {mode === 'register' && password.length > 0 && (
            <div className="mt-4">
              <div className="flex gap-1 mt-1">
                {[1,2,3,4].map(i => (
                  <div key={i} className={`h-0.5 flex-1 rounded-full transition-all ${
                    password.length >= i * 3
                      ? i <= 1 ? 'bg-rose-500'
                      : i <= 2 ? 'bg-amber-500'
                      : i <= 3 ? 'bg-blue-500'
                      : 'bg-emerald-500'
                      : 'bg-slate-800'
                  }`} />
                ))}
              </div>
              <p className="text-[9px] font-mono text-slate-600 mt-1">
                {password.length < 4  ? 'Too short' :
                 password.length < 7  ? 'Weak' :
                 password.length < 10 ? 'Good' : 'Strong'}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] font-mono text-slate-700 mt-4">
          NSE_GATEWAY_ONLINE // LOCALHOST SESSION
        </p>
      </div>
    </div>
  );
}