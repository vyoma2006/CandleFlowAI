"""
brain/backtest.py
─────────────────
CandleFlow Signal Backtester — Win Rate Edition

Walks through historical data for every ticker in bridge/data/nse_tickers.json,
fires the real LSTM on each 20-day window, then checks what price did over the
next N days to score the signal as correct or wrong.

Usage (run from project root CandleFlow/):
    python brain/backtest.py                        # all tickers, 10-day horizon
    python brain/backtest.py --horizon 5            # 5-day forward look
    python brain/backtest.py --horizon 20           # 20-day forward look
    python brain/backtest.py --tickers RELIANCE TCS # specific tickers only
    python brain/backtest.py --out results.csv      # save full results to CSV

Output:
    ┌─ Per-ticker summary table printed to terminal
    └─ Aggregate win rate across all signals
"""

import sys
import os
import argparse
import json
import warnings
warnings.filterwarnings("ignore")

# ── Ensure project root is on path ────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# ── Load model + indicators ───────────────────────────────────────────────────
try:
    from tensorflow.keras.models import load_model
    from core.lstm_engine import TemporalAttention
    HAS_TF = True
except ImportError:
    print("❌ TensorFlow not found. Activate your venv first.")
    sys.exit(1)

from core.indicators import calculate_indicators


# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
MODEL_PATH   = os.path.join(ROOT, "brain", "models", "candleflow_lstm.keras")
TICKERS_JSON = os.path.join(ROOT, "brain", "data", "nse_tickers.json")
TIME_STEPS   = 20

FEATURES = [
    'RSI', 'RSI_Lag_1', 'Price_to_SMA20', 'MACD_Hist_Pct',
    'BB_Width', 'ATR_Pct', 'CMF', 'Volume_Shock', 'Market_RSI'
]

# Signal thresholds — must match main.py exactly
SPREAD_STRONG = 0.08
SPREAD_WEAK   = 0.01
BB_SQUEEZE    = 3.0


# ──────────────────────────────────────────────────────────────────────────────
# LOAD MODEL
# ──────────────────────────────────────────────────────────────────────────────
def load_lstm():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at {MODEL_PATH}")
        sys.exit(1)
    def focal_loss_fixed(y_true, y_pred): return y_pred
    model = load_model(
        MODEL_PATH,
        custom_objects={"focal_loss_fixed": focal_loss_fixed, "TemporalAttention": TemporalAttention},
        compile=False
    )
    print(f"✅ LSTM loaded from {MODEL_PATH}\n")
    return model


# ──────────────────────────────────────────────────────────────────────────────
# SIGNAL DECODER — identical logic to main.py
# ──────────────────────────────────────────────────────────────────────────────
def decode_signal(
    raw_pred: float,
    bb_width_pct: float,
    market_slope: float,
    rsi: float = 50,
    macd_hist: float = 0,
    macd_hist_prev: float = 0,
    price_sma: float = 1.0,
    adx: float = 25,
) -> str:
    p_buy  = raw_pred
    p_sell = 1.0 - raw_pred
    net_spread = abs(p_buy - p_sell)
    direction  = "BUY" if p_buy > p_sell else "SELL"

    if bb_width_pct < BB_SQUEEZE:
        return "HOLD"

    if direction == "BUY":
        if net_spread >= SPREAD_STRONG:  signal = "STRONG BUY"
        elif net_spread >= SPREAD_WEAK:  signal = "BUY"
        else:                            signal = "HOLD"
    else:
        if net_spread >= SPREAD_STRONG:  signal = "STRONG SELL"
        elif net_spread >= SPREAD_WEAK:  signal = "SELL"
        else:                            signal = "HOLD"

    # Macro protection override
    if market_slope < -0.25 and "BUY" in signal:
        return "HOLD"

    # ── Technical confirmation gates (mirrors main.py exactly) ────────────────
    if "BUY" in signal:
        confirmations = 0
        if rsi >= 35:                         confirmations += 1
        if macd_hist > 0:                     confirmations += 1
        elif macd_hist > macd_hist_prev:      confirmations += 1
        if price_sma >= 0.96:                 confirmations += 1
        if adx < 35:                          confirmations += 1

        required = 3 if "STRONG" in signal else 2
        if confirmations < required:
            return "HOLD"

    return signal


# ──────────────────────────────────────────────────────────────────────────────
# DOWNLOAD + FEATURE PREP
# ──────────────────────────────────────────────────────────────────────────────
_nifty_features_cache = None

def get_nifty_features():
    global _nifty_features_cache
    if _nifty_features_cache is not None:
        return _nifty_features_cache
    print("📡 Downloading Nifty 50 index (shared across all tickers)...")
    df = yf.download("^NSEI", period="2y", interval="1d", progress=False, ignore_tz=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Open','High','Low','Close'])
    feats = calculate_indicators(df)
    feats['Market_RSI'] = feats['RSI']
    _nifty_features_cache = feats
    return feats


def prepare_ticker(symbol: str, nifty_features: pd.DataFrame):
    """
    Downloads 2y of data for `symbol`, computes indicators,
    joins Market_RSI, scales features using expanding window.
    Returns a DataFrame ready for slicing into sequences.
    """
    df = yf.download(symbol, period="2y", interval="1d", progress=False, ignore_tz=True)
    if df.empty or len(df) < 120:
        return None, None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Open','High','Low','Close'])

    feats = calculate_indicators(df)
    feats = feats.drop(columns=['Market_RSI'], errors='ignore')
    feats = feats.join(nifty_features[['Market_RSI']], how='left')
    feats['Market_RSI'] = feats['Market_RSI'].ffill().bfill()
    feats['RSI_Lag_1']  = feats['RSI'].shift(1)

    df_inf = feats[FEATURES].dropna().copy()

    # Expanding z-score (lookahead-free) — matches inference in main.py
    df_scaled = pd.DataFrame(index=df_inf.index)
    for col in FEATURES:
        mu  = df_inf[col].expanding(min_periods=20).mean()
        std = df_inf[col].expanding(min_periods=20).std() + 1e-9
        df_scaled[col] = (df_inf[col] - mu) / std

    df_ready = df_scaled.dropna(subset=FEATURES)

    # We also need raw close prices aligned to df_ready's index
    close_aligned = df['Close'].reindex(df_ready.index)

    # Also return raw feats so the backtest loop can read indicator values
    feats_aligned = feats.reindex(df_ready.index)

    return df_ready, close_aligned, feats_aligned


# ──────────────────────────────────────────────────────────────────────────────
# BACKTEST ONE TICKER
# ──────────────────────────────────────────────────────────────────────────────
def backtest_ticker(
    symbol:         str,
    model,
    nifty_features: pd.DataFrame,
    horizon:        int,
    step:           int = 5,    # run inference every N days to avoid redundancy
) -> dict:
    """
    Slides a 20-day window through all available history for `symbol`.
    For each window:
      - Gets the LSTM signal
      - Skips HOLD signals (no directional bet)
      - Looks forward `horizon` days
      - Marks WIN if price moved in the signal direction

    Returns a dict of stats for this ticker.
    """
    df_ready, close_prices, df_features = prepare_ticker(symbol, nifty_features)
    if df_ready is None or len(df_ready) < TIME_STEPS + horizon + 5:
        return None

    feature_matrix = df_ready[FEATURES].to_numpy()
    close_array    = close_prices.to_numpy(dtype=float)
    dates          = df_ready.index.tolist()

    # We need MACD_Hist_Slope from nifty for macro override
    nifty_slope = nifty_features.get('MACD_Hist_Slope', pd.Series(0, index=nifty_features.index))

    results = []
    # Slide window — stop horizon days before end so we can look forward
    indices = range(TIME_STEPS - 1, len(df_ready) - horizon, step)

    for i in indices:
        window    = feature_matrix[i - TIME_STEPS + 1 : i + 1]   # shape (20, 9)
        entry_idx = i
        exit_idx  = i + horizon

        if exit_idx >= len(close_array):
            break

        entry_price = float(close_array[entry_idx])
        exit_price  = float(close_array[exit_idx])

        if np.isnan(entry_price) or np.isnan(exit_price) or entry_price == 0:
            continue

        # LSTM inference
        tensor    = np.expand_dims(window, axis=0)
        raw_pred  = float(model.predict(tensor, verbose=0)[0][0])

        # Extract raw indicator values for confirmation gates
        rsi_val        = float(df_features['RSI'].iloc[i])             if 'RSI'            in df_features.columns else 50.0
        macd_hist_val  = float(df_features['MACD_Hist'].iloc[i])       if 'MACD_Hist'      in df_features.columns else 0.0
        macd_hist_prev = float(df_features['MACD_Hist'].iloc[i - 1])   if 'MACD_Hist'      in df_features.columns and i > 0 else 0.0
        price_sma_val  = float(df_features['Price_to_SMA20'].iloc[i])  if 'Price_to_SMA20' in df_features.columns else 1.0
        adx_val        = float(df_features['ADX'].iloc[i])             if 'ADX'            in df_features.columns else 25.0
        bb_width_pct   = float(df_features['BB_Width'].iloc[i] * 100)  if 'BB_Width'       in df_features.columns else 0.0

        date_i       = dates[i]
        market_slope = float(nifty_slope.get(date_i, 0)) if date_i in nifty_slope.index else 0.0

        signal = decode_signal(
            raw_pred, bb_width_pct, market_slope,
            rsi=rsi_val, macd_hist=macd_hist_val,
            macd_hist_prev=macd_hist_prev,
            price_sma=price_sma_val, adx=adx_val,
        )

        if signal == "HOLD":
            continue   # don't score HOLDs — no directional bet made

        price_change_pct = ((exit_price - entry_price) / entry_price) * 100

        # WIN = price went the direction the signal predicted
        if "BUY" in signal:
            win = price_change_pct > 0
        else:  # SELL
            win = price_change_pct < 0

        results.append({
            "date":              date_i.strftime("%Y-%m-%d") if hasattr(date_i, "strftime") else str(date_i)[:10],
            "signal":            signal,
            "entry_price":       round(entry_price, 2),
            "exit_price":        round(exit_price, 2),
            "price_change_pct":  round(price_change_pct, 2),
            "win":               win,
            "raw_pred":          round(raw_pred, 4),
        })

    if not results:
        return None

    df_res       = pd.DataFrame(results)
    total        = len(df_res)
    wins         = df_res['win'].sum()
    win_rate     = (wins / total * 100) if total > 0 else 0

    buy_df       = df_res[df_res['signal'].str.contains('BUY')]
    sell_df      = df_res[df_res['signal'].str.contains('SELL')]
    strong_df    = df_res[df_res['signal'].str.startswith('STRONG')]

    return {
        "ticker":            symbol,
        "total_signals":     total,
        "wins":              int(wins),
        "win_rate":          round(win_rate, 1),
        "buy_signals":       len(buy_df),
        "buy_win_rate":      round(buy_df['win'].mean() * 100, 1) if len(buy_df) > 0 else 0,
        "sell_signals":      len(sell_df),
        "sell_win_rate":     round(sell_df['win'].mean() * 100, 1) if len(sell_df) > 0 else 0,
        "strong_signals":    len(strong_df),
        "strong_win_rate":   round(strong_df['win'].mean() * 100, 1) if len(strong_df) > 0 else 0,
        "avg_price_chg":     round(df_res['price_change_pct'].mean(), 2),
        "detail":            df_res,
    }


# ──────────────────────────────────────────────────────────────────────────────
# PRINT HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def print_separator(char="─", width=90):
    print(char * width)

def print_ticker_summary(r: dict):
    wr_color = "🟢" if r['win_rate'] >= 55 else "🟡" if r['win_rate'] >= 45 else "🔴"
    print(
        f"  {r['ticker']:<20} "
        f"signals={r['total_signals']:<5} "
        f"win={r['win_rate']:>5.1f}% {wr_color}  │  "
        f"BUY {r['buy_win_rate']:>5.1f}% ({r['buy_signals']})  "
        f"SELL {r['sell_win_rate']:>5.1f}% ({r['sell_signals']})  "
        f"STRONG {r['strong_win_rate']:>5.1f}% ({r['strong_signals']})"
    )

def print_aggregate(all_results: list, horizon: int):
    total_sigs  = sum(r['total_signals'] for r in all_results)
    total_wins  = sum(r['wins']          for r in all_results)
    overall_wr  = (total_wins / total_sigs * 100) if total_sigs > 0 else 0

    buy_sigs    = sum(r['buy_signals']   for r in all_results)
    sell_sigs   = sum(r['sell_signals']  for r in all_results)
    strong_sigs = sum(r['strong_signals'] for r in all_results)

    buy_wins    = sum(int(r['buy_win_rate']    / 100 * r['buy_signals'])    for r in all_results)
    sell_wins   = sum(int(r['sell_win_rate']   / 100 * r['sell_signals'])   for r in all_results)
    strong_wins = sum(int(r['strong_win_rate'] / 100 * r['strong_signals']) for r in all_results)

    buy_wr    = (buy_wins    / buy_sigs    * 100) if buy_sigs    > 0 else 0
    sell_wr   = (sell_wins   / sell_sigs   * 100) if sell_sigs   > 0 else 0
    strong_wr = (strong_wins / strong_sigs * 100) if strong_sigs > 0 else 0

    # Win rate distribution
    excellent = sum(1 for r in all_results if r['win_rate'] >= 60)
    good      = sum(1 for r in all_results if 50 <= r['win_rate'] < 60)
    poor      = sum(1 for r in all_results if r['win_rate'] < 50)

    print_separator("═")
    print(f"\n  📊 CANDLEFLOW BACKTEST RESULTS  //  {horizon}-DAY FORWARD HORIZON")
    print(f"     Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"     Tickers tested: {len(all_results)}\n")
    print_separator()
    print(f"  OVERALL WIN RATE:    {overall_wr:>6.1f}%   ({total_wins}/{total_sigs} signals correct)")
    print_separator()
    print(f"  BUY  signals:        {buy_wr:>6.1f}%   ({buy_sigs} signals)")
    print(f"  SELL signals:        {sell_wr:>6.1f}%   ({sell_sigs} signals)")
    print(f"  STRONG signals only: {strong_wr:>6.1f}%   ({strong_sigs} signals)")
    print_separator()
    print(f"  Ticker distribution:")
    print(f"    🟢 Win rate ≥ 60%:   {excellent} tickers")
    print(f"    🟡 Win rate 50-60%:  {good} tickers")
    print(f"    🔴 Win rate < 50%:   {poor} tickers")
    print_separator("═")

    # Key interpretation
    print()
    if overall_wr >= 60:
        print("  ✅ Model shows STRONG predictive edge above 60% — signals are reliable.")
    elif overall_wr >= 52:
        print("  ⚠️  Model shows MARGINAL edge (52-60%) — signals have weak but real value.")
        print("     Consider only acting on STRONG BUY/SELL signals where confidence is higher.")
    else:
        print("  ❌ Model is near-random (<52%) — consider retraining with more data.")
        print("     Specifically check: are BUY signals firing on oversold downtrends?")

    if strong_wr > overall_wr + 5:
        print(f"\n  💡 STRONG signals outperform by {strong_wr - overall_wr:.1f}% —")
        print(f"     Consider only acting on STRONG BUY/SELL and ignoring weak signals.")
    print()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="CandleFlow Signal Backtester")
    parser.add_argument("--horizon",  type=int,   default=10,    help="Forward-look days (default: 10)")
    parser.add_argument("--step",     type=int,   default=5,     help="Inference step size in days (default: 5)")
    parser.add_argument("--tickers",  nargs="+",  default=None,  help="Specific tickers to test (e.g. RELIANCE TCS)")
    parser.add_argument("--out",      type=str,   default=None,  help="Save full results to CSV path")
    parser.add_argument("--top",      type=int,   default=None,  help="Only test top N tickers from JSON")
    args = parser.parse_args()

    # ── Load ticker list ──────────────────────────────────────────────────────
    if args.tickers:
        symbols = [f"{t.upper().strip()}.NS" if not t.endswith(".NS") else t.upper() for t in args.tickers]
    else:
        if not os.path.exists(TICKERS_JSON):
            print(f"❌ Ticker JSON not found: {TICKERS_JSON}")
            sys.exit(1)
        with open(TICKERS_JSON, "r") as f:
            raw = json.load(f)
        symbols = [f"{s}.NS" for s in raw.keys()]
        if args.top:
            symbols = symbols[:args.top]

    print_separator("═")
    print(f"  🚀 CandleFlow Backtester")
    print(f"     Tickers : {len(symbols)}")
    print(f"     Horizon : {args.horizon} trading days forward")
    print(f"     Step    : every {args.step} days")
    print(f"     Model   : {MODEL_PATH}")
    print_separator("═")
    print()

    # ── Load model + Nifty ────────────────────────────────────────────────────
    model          = load_lstm()
    nifty_features = get_nifty_features()

    # ── Run per-ticker ────────────────────────────────────────────────────────
    all_results  = []
    all_detail   = []
    failed       = []

    print(f"  {'TICKER':<20} {'SIGNALS':<8} {'WIN RATE':<10}  BUY / SELL / STRONG breakdown")
    print_separator()

    for i, symbol in enumerate(symbols):
        try:
            result = backtest_ticker(symbol, model, nifty_features, args.horizon, args.step)
            if result is None:
                failed.append(symbol)
                print(f"  {symbol:<20} ⚠️  skipped (insufficient data)")
                continue

            print_ticker_summary(result)

            detail_df = result.pop("detail")
            detail_df["ticker"] = symbol
            all_detail.append(detail_df)
            all_results.append(result)

        except Exception as e:
            failed.append(symbol)
            print(f"  {symbol:<20} ❌ error: {e}")

    # ── Aggregate summary ─────────────────────────────────────────────────────
    if all_results:
        print()
        print_aggregate(all_results, args.horizon)

        # Best and worst performers
        sorted_r = sorted(all_results, key=lambda x: x['win_rate'], reverse=True)
        print("  TOP 5 tickers by win rate:")
        for r in sorted_r[:5]:
            print(f"    {r['ticker']:<20} {r['win_rate']:.1f}%  ({r['total_signals']} signals)")
        print()
        print("  BOTTOM 5 tickers by win rate:")
        for r in sorted_r[-5:]:
            print(f"    {r['ticker']:<20} {r['win_rate']:.1f}%  ({r['total_signals']} signals)")
        print()

    if failed:
        print(f"  ⚠️  Skipped {len(failed)} tickers: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
        print()

    # ── Save to CSV ───────────────────────────────────────────────────────────
    if args.out and all_detail:
        full_df = pd.concat(all_detail, ignore_index=True)
        full_df.to_csv(args.out, index=False)
        print(f"  💾 Full signal-level results saved to: {args.out}")
        print()

    # ── Summary CSV (always saved) ────────────────────────────────────────────
    if all_results:
        summary_path = os.path.join(ROOT, "backtest_summary.csv")
        pd.DataFrame(all_results).to_csv(summary_path, index=False)
        print(f"  💾 Per-ticker summary saved to: {summary_path}")
        print()


if __name__ == "__main__":
    main()