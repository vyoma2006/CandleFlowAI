import React, { useState, useEffect } from 'react';
import {
  TrendingUp, TrendingDown, ShieldAlert, Activity, Search,
  Newspaper, BarChart3, Radio, Percent, AlertTriangle,
} from 'lucide-react';

import PortfolioPanel  from './components/PortfolioPanel';
import PriceChart      from './components/PriceChart';
import MetricsGrid     from './components/MetricsGrid';
import ConfidenceMeter from './components/ConfidenceMeter';
import SignalStatus    from './components/SignalStatus';
import TradeLog        from './components/TradeLog';

export default function App() {
  const [searchQuery,   setSearchQuery]   = useState('RELIANCE');
  const [typedInput,    setTypedInput]    = useState('');
  const [suggestions,   setSuggestions]   = useState([]);
  const [showDropdown,  setShowDropdown]  = useState(false);
  const [stockData,     setStockData]     = useState(null);
  const [watchlist,     setWatchlist]     = useState([]);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState(null);

  // ── Portfolio load ──────────────────────────────────────────────────────────
  const loadWatchlist = async () => {
    try {
      const res  = await fetch('http://localhost:8000/api/user-portfolio');
      const data = await res.json();
      setWatchlist(data.tickers || []);
    } catch (err) {
      console.error('Portfolio loading failed:', err);
    }
  };

  useEffect(() => { loadWatchlist(); }, []);

  // ── Autocomplete debounce ───────────────────────────────────────────────────
  useEffect(() => {
    const clean = typedInput.trim();
    if (!clean || clean.endsWith('.NS')) { setSuggestions([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`http://localhost:8000/api/tickers/search?q=${encodeURIComponent(clean)}`);
        setSuggestions(await r.json());
      } catch { console.error('Autocomplete error'); }
    }, 150);
    return () => clearTimeout(t);
  }, [typedInput]);

  // ── Stock fetch ─────────────────────────────────────────────────────────────
  const fetchStockAnalysis = async (queryStr) => {
    setLoading(true);
    setError(null);
    try {
      const r    = await fetch(`http://localhost:8000/api/stock-info/${queryStr}`);
      const data = await r.json();
      if (data.error) { setError(data.error); setStockData(null); }
      else            { setStockData(data); setTypedInput(''); }
    } catch {
      setError('Failed to communicate with CandleFlow API gateway. Verify backend is running.');
      setStockData(null);
    } finally {
      setLoading(false);
    }
  };

  const toggleWatchlist = async (ticker) => {
    try {
      await fetch('http://localhost:8000/api/user-portfolio/toggle', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ ticker }),
      });
      loadWatchlist();
    } catch (err) { console.error('Portfolio update failed:', err); }
  };

  const handleViewAnalysis = (ticker) => {
    setSearchQuery(ticker);
    fetchStockAnalysis(ticker);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => { fetchStockAnalysis(searchQuery); }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const target = typedInput.trim() ? typedInput.trim().toUpperCase() : searchQuery;
    if (target) {
      const q = target.endsWith('.NS') ? target : `${target}.NS`;
      setSearchQuery(q);
      fetchStockAnalysis(q);
      setShowDropdown(false);
    }
  };

  // ── Signal badge ────────────────────────────────────────────────────────────
  const getSignalBadgeStyles = (signal) => {
    if (!signal) return 'bg-slate-800 text-slate-400 border-slate-700';
    const s = signal.toUpperCase();
    if (s.includes('STRONG BUY'))  return 'bg-emerald-950 text-emerald-400 border-emerald-500 animate-pulse';
    if (s.includes('BUY'))         return 'bg-green-950 text-green-400 border-green-600';
    if (s.includes('STRONG SELL')) return 'bg-rose-950 text-rose-400 border-rose-500 animate-pulse';
    if (s.includes('SELL'))        return 'bg-red-950 text-red-400 border-red-600';
    return 'bg-amber-950 text-amber-400 border-amber-600';
  };

  // ── Risk profile ────────────────────────────────────────────────────────────
  const computeRiskProfile = (data) => {
    if (!data?.price) return { stopLoss: 'N/A', takeProfit: 'N/A', sizing: '0% Allocation' };
    const { price, metrics, ai_signal: signal } = data;
    const atr = metrics?.atr || price * 0.015;
    let stopLoss = 0, takeProfit = 0;
    let sizing = '0% Capital Weight - Stand Aside (Cash Reserve)';
    if (signal?.includes('BUY')) {
      stopLoss   = price - 1.5 * atr;
      takeProfit = price + 3.0 * atr;
      sizing     = signal.includes('STRONG')
        ? '100% Full Capital Sizing Deployment Authorized'
        : '50% Standard Capital Allocation Authorized';
    } else if (signal?.includes('SELL')) {
      stopLoss   = price + 1.5 * atr;
      takeProfit = price - 3.0 * atr;
      sizing     = signal.includes('STRONG')
        ? '100% Full Short Position Capital Weight Deployment'
        : '50% Reduced Short Position Capital Weight';
    }
    return {
      stopLoss:   stopLoss   > 0 ? `₹${stopLoss.toLocaleString('en-IN',   { maximumFractionDigits: 2 })}` : 'Stand Aside',
      takeProfit: takeProfit > 0 ? `₹${takeProfit.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : 'Stand Aside',
      sizing,
    };
  };

  const riskProfile = stockData ? computeRiskProfile(stockData) : null;

  // ───────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500 selection:text-slate-950">

      {/* ── HEADER ── */}
      <header className="border-b border-slate-900 bg-slate-900/40 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-emerald-500 p-2 rounded-lg text-slate-950 shadow-lg shadow-emerald-500/20">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">
              CandleFlow Engine
            </h1>
            <p className="text-xs text-slate-500 font-mono">v2.5 // Live Paper-Trading Matrix Terminal</p>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-full max-w-md mx-4">
          <form onSubmit={handleSearchSubmit} className="relative w-full">
            <input
              type="text" autoComplete="off"
              placeholder="Search Ticker (e.g. F, Bank, Tata, Reliance)..."
              value={typedInput}
              onChange={e => { setTypedInput(e.target.value); setShowDropdown(true); }}
              onFocus={() => setShowDropdown(true)}
              onBlur={() => setTimeout(() => setShowDropdown(false), 250)}
              className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all font-mono"
            />
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
            <button type="submit" className="hidden">Analyze</button>
          </form>

          {showDropdown && typedInput.trim().length > 0 && suggestions.length > 0 && (
            <div className="absolute top-full left-0 w-full bg-[#0b1329] border border-slate-800 rounded-xl mt-1.5 shadow-2xl overflow-hidden z-50 max-h-64 overflow-y-auto divide-y divide-slate-800/40 custom-scrollbar">
              {suggestions.map(item => (
                <button key={item.symbol} type="button"
                  onMouseDown={e => { e.preventDefault(); setSearchQuery(item.symbol); fetchStockAnalysis(item.symbol); setShowDropdown(false); }}
                  className="w-full text-left px-4 py-3 hover:bg-emerald-950/40 font-mono transition-colors flex justify-between items-center group">
                  <span className="text-sm font-bold text-slate-200 group-hover:text-emerald-400 truncate pr-2">
                    {item.name}
                  </span>
                  <span className="text-xs font-bold text-emerald-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 shrink-0">
                    {item.symbol}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-mono text-slate-400">
          <Radio className="h-3.5 w-3.5 text-emerald-500 animate-ping" />
          <span>NSE_GATEWAY_ONLINE</span>
        </div>
      </header>

      {/* ── MAIN BODY — 3-column layout ── */}
      <div className="max-w-[1600px] mx-auto p-6">

        {/* Error banner */}
        {error && (
          <div className="bg-rose-950/40 border border-rose-800/60 text-rose-300 p-4 rounded-xl flex items-start space-x-3 mb-6">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-sm">Pipeline Exception Trace:</span>
              <p className="text-xs text-rose-400/90 mt-0.5 font-mono">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px_280px] gap-6 animate-pulse">
            <div className="space-y-6">
              <div className="h-36 bg-slate-900 rounded-2xl border border-slate-800" />
              <div className="h-72 bg-slate-900 rounded-2xl border border-slate-800" />
              <div className="h-48 bg-slate-900 rounded-2xl border border-slate-800" />
            </div>
            <div className="space-y-6">
              <div className="h-64 bg-slate-900 rounded-2xl border border-slate-800" />
              <div className="h-48 bg-slate-900 rounded-2xl border border-slate-800" />
            </div>
            <div className="space-y-6">
              <div className="h-96 bg-slate-900 rounded-2xl border border-slate-800" />
              <div className="h-48 bg-slate-900 rounded-2xl border border-slate-800" />
            </div>
          </div>
        ) : stockData ? (

          // ── 3-COLUMN GRID ──────────────────────────────────────────────────
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px_280px] gap-6 items-start">

            {/* ── COL 1: Main analysis ── */}
            <div className="space-y-6">

              {/* Ticker banner */}
              <div className="bg-slate-900/60 border border-slate-900 rounded-2xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/40">
                    {stockData.engine_mode}
                  </span>
                  <h2 className="text-3xl font-extrabold tracking-tight font-mono mt-2 text-slate-100">
                    {stockData.ticker}
                  </h2>
                </div>
                <div className="text-right flex md:flex-col justify-between items-center md:items-end">
                  <div className="text-4xl font-bold font-mono tracking-tight text-slate-100">
                    ₹{stockData.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className={`flex items-center space-x-1 font-mono text-sm font-semibold mt-1 ${stockData.daily_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {stockData.daily_change >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                    <span>
                      {stockData.daily_change >= 0 ? '+' : ''}{stockData.daily_change?.toFixed(2)}
                      ({stockData.daily_change_pct?.toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>

              {/* ── PRICE CHART (new) ── */}
              <PriceChart ticker={stockData.ticker} />

              {/* AI signal card */}
              <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-900 rounded-2xl p-6 grid grid-cols-1 md:grid-cols-3 gap-6 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

                {/* Signal + certainty */}
                <div className="flex flex-col justify-between space-y-4">
                  <div>
                    <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                      <BarChart3 className="h-3.5 w-3.5" />
                      Core Inference Output
                    </h3>
                    <div className="mt-3 flex items-baseline gap-3">
                      <span className={`px-4 py-2 text-xl font-mono font-black tracking-wider rounded-xl border ${getSignalBadgeStyles(stockData.ai_signal)}`}>
                        {stockData.ai_signal}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-xs font-mono text-slate-500 block">Certainty Distribution</span>
                    <span className="text-2xl font-bold font-mono text-slate-200">{stockData.confidence}</span>
                  </div>
                </div>

                {/* ── CONFIDENCE METER (new) ── */}
                <div className="flex items-center justify-center">
                  <ConfidenceMeter
                    confidence={stockData.confidence}
                    signal={stockData.ai_signal}
                  />
                </div>

                {/* Confidence band + signal status */}
                <div className="bg-slate-900/40 rounded-xl border border-slate-900/80 p-4 flex flex-col justify-between gap-3">
                  <div>
                    <span className="text-xs font-mono text-slate-500 block uppercase">Confidence Classification</span>
                    <p className="text-sm font-medium text-slate-300 mt-1">{stockData.confidence_band}</p>
                  </div>
                  {/* ── SIGNAL STATUS (replaces dead amber text) ── */}
                  <SignalStatus positionStatus={stockData.position_status} />
                </div>
              </div>

              {/* ── METRICS GRID with context (replaces raw numbers) ── */}
              <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-6">
                <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-1.5">
                  <Percent className="h-3.5 w-3.5" />
                  Pruned Non-Redundant Feature Monitor
                </h3>
                <MetricsGrid metrics={stockData.metrics} />
              </div>
            </div>

            {/* ── COL 2: Risk + News ── */}
            <div className="space-y-6">

              {/* Risk management */}
              <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 space-y-4">
                <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <ShieldAlert className="h-4 w-4 text-emerald-500" />
                  Volatility Management Loop
                </h3>
                <div className="space-y-3 font-mono text-xs">
                  <div className="bg-slate-950/80 border border-slate-900 p-3 rounded-xl flex justify-between items-center">
                    <span className="text-slate-500">STOP LOSS (1.5x ATR)</span>
                    <span className="font-bold text-rose-400 text-sm">{riskProfile?.stopLoss}</span>
                  </div>
                  <div className="bg-slate-950/80 border border-slate-900 p-3 rounded-xl flex justify-between items-center">
                    <span className="text-slate-500">TAKE PROFIT (3.0x ATR)</span>
                    <span className="font-bold text-emerald-400 text-sm">{riskProfile?.takeProfit}</span>
                  </div>
                  <div className="bg-slate-950/80 border border-slate-900 p-4 rounded-xl space-y-1">
                    <span className="text-slate-500 block uppercase text-[10px]">Capital Weight Sizing</span>
                    <p className="font-semibold text-slate-300 text-sm tracking-tight leading-snug">{riskProfile?.sizing}</p>
                  </div>
                </div>
              </div>

              {/* News */}
              <div className="bg-slate-900/40 border border-slate-900 rounded-2xl p-6 space-y-4">
                <h3 className="text-xs font-mono text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                  <Newspaper className="h-4 w-4" />
                  Market Sentiment Footprint
                </h3>
                <div className="space-y-3">
                  {stockData.news?.length > 0 ? stockData.news.map((item, idx) => (
                    <a key={idx} href={item.url} target="_blank" rel="noopener noreferrer"
                      className="block bg-slate-950/50 border border-slate-900 p-3 rounded-xl hover:border-slate-800 transition-all group">
                      <p className="text-xs font-medium text-slate-300 group-hover:text-emerald-400 transition-colors line-clamp-2 leading-relaxed">
                        {item.headline}
                      </p>
                      <span className="text-[10px] text-slate-600 font-mono block mt-1.5">Source // {item.source}</span>
                    </a>
                  )) : (
                    <div className="text-center py-6 text-slate-600 font-mono text-xs">
                      No active media sentiment flags located.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── COL 3: Portfolio + Trade Log (always visible) ── */}
            <div className="space-y-6">
              <PortfolioPanel
                watchlist={watchlist}
                activeTicker={searchQuery}
                onViewAnalysis={handleViewAnalysis}
                onToggle={toggleWatchlist}
                onRefresh={loadWatchlist}
              />
              {/* ── TRADE LOG (new) ── */}
              <TradeLog />
            </div>
          </div>

        ) : (
          <div className="text-center py-16 bg-slate-900/20 border border-dashed border-slate-900 rounded-2xl">
            <BarChart3 className="h-10 w-10 text-slate-700 mx-auto mb-3" />
            <p className="text-sm font-mono text-slate-500">
              Provide an active ticker string above to generate analysis vectors.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}