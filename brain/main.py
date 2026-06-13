import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
from brain.core.indicators import calculate_indicators
from brain.core.lstm_engine import TemporalAttention
from sqlalchemy.orm import Session
from bridge.database import get_db
from bridge.auth import (
    create_user, authenticate_user, create_access_token,
    get_current_user, get_user_portfolio, toggle_user_ticker
)


try:
    from tensorflow.keras.models import load_model as load_lstm_model
    HAS_TF = True
except ImportError:
    HAS_TF = False

load_dotenv()
logger = logging.getLogger("uvicorn.error")

# ──────────────────────────────────────────────────────────────────────────────
# ⚡ IN-MEMORY TTL CACHE
# Eliminates redundant yfinance downloads for the same ticker.
# Stock data: 5-min TTL.  Nifty: 10-min TTL (market index changes slower).
# ──────────────────────────────────────────────────────────────────────────────
_cache: dict = {}   # { key: { "data": ..., "ts": float } }

STOCK_TTL_SECONDS = 300   # 5 minutes
NIFTY_TTL_SECONDS = 600   # 10 minutes


def cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < entry["ttl"]:
        return entry["data"]
    return None


def cache_set(key: str, data, ttl: int):
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}


def get_df_cached(symbol: str, period: str = "2y") -> pd.DataFrame:
    key = f"df:{symbol}:{period}"
    hit = cache_get(key)
    if hit is not None:
        logger.info(f"⚡ Cache HIT: {key}")
        return hit
    logger.info(f"📡 Cache MISS — downloading {symbol}")
    df = yf.download(symbol, period=period, interval="1d", progress=False, ignore_tz=True)
    if not df.empty:
        cache_set(key, df, STOCK_TTL_SECONDS)
    return df


def get_nifty_cached() -> pd.DataFrame:
    key = "df:^NSEI:2y"
    hit = cache_get(key)
    if hit is not None:
        return hit
    df = yf.download("^NSEI", period="2y", interval="1d", progress=False, ignore_tz=True)
    if not df.empty:
        cache_set(key, df, NIFTY_TTL_SECONDS)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 💾 LIFESPAN — ticker cache seeder
# ──────────────────────────────────────────────────────────────────────────────
GLOBAL_TICKER_CACHE = []

@asynccontextmanager
async def application_lifespan(app: FastAPI):
    global GLOBAL_TICKER_CACHE
    logger.info("📡 [CandleFlow] Initializing ticker cache...")

    base_dir        = os.path.dirname(os.path.abspath(__file__))
    local_json_path = os.path.join(base_dir, "data", "nse_tickers.json")

    try:
        if os.path.exists(local_json_path):
            with open(local_json_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            GLOBAL_TICKER_CACHE = [
                {"symbol": f"{s}.NS", "raw_symbol": s.strip().lower(), "name": n.strip()}
                for s, n in raw_data.items()
            ]
            logger.info(f"✅ Loaded {len(GLOBAL_TICKER_CACHE)} tickers from disk.")
        else:
            raise FileNotFoundError(f"Missing: {local_json_path}")
    except Exception as e:
        logger.error(f"🚨 Ticker cache init failed: {e} — using fallback.")
        fallback = {
            "ADANIENT":"Adani Enterprises Ltd","AXISBANK":"Axis Bank Ltd",
            "BAJFINANCE":"Bajaj Finance Ltd","BHARTIARTL":"Bharti Airtel Ltd",
            "HDFCBANK":"HDFC Bank Ltd","HINDUNILVR":"Hindustan Unilever Ltd",
            "INFY":"Infosys Ltd","ITC":"ITC Ltd","ICICIBANK":"ICICI Bank Ltd",
            "MARUTI":"Maruti Suzuki India Ltd","NESTLEIND":"Nestle India Ltd",
            "RELIANCE":"Reliance Industries Ltd","SBIN":"State Bank of India",
            "SUNPHARMA":"Sun Pharmaceutical Industries Ltd",
            "TCS":"Tata Consultancy Services Ltd","TATASTEEL":"Tata Steel Ltd",
            "TITAN":"Titan Company Ltd","WIPRO":"Wipro Ltd",
        }
        GLOBAL_TICKER_CACHE = [
            {"symbol": f"{s}.NS", "raw_symbol": s.lower(), "name": n}
            for s, n in fallback.items()
        ]

    yield
    logger.info("🛑 CandleFlow shutting down.")


app = FastAPI(title="CandleFlow Engine", lifespan=application_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://candle-flow-ai-1d8s.vercel.app",  # replace with your frontend URL
        "http://localhost:5173",               # optional local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ──────────────────────────────────────────────────────────────────────────────
# LSTM MODEL
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LSTM_PATH = os.path.join(
    BASE_DIR,
    "models",
    "candleflow_lstm.keras"
)
lstm_model = None

if HAS_TF and os.path.exists(LSTM_PATH):
    try:
        def focal_loss_fixed(y_true, y_pred): return y_pred
        lstm_model = load_lstm_model(
            LSTM_PATH,
            custom_objects={"focal_loss_fixed": focal_loss_fixed, "TemporalAttention": TemporalAttention},
            compile=False
        )
        print("🤖 LSTM engine mounted.")
    except Exception as e:
        print(f"🚨 Model load failed: {e}")
else:
    print("❌ LSTM model missing.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://candle-flow-ai-1d8s.vercel.app",  # replace with your frontend URL
        "http://localhost:5173",               # optional local dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if np.isnan(f) or np.isinf(f) else f
    except:
        return default


def fetch_local_indian_news(ticker_symbol):
    clean = ticker_symbol.split('.')[0]
    url   = f"https://news.google.com/rss/search?q={clean}+stock+news+india&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        root = ET.fromstring(requests.get(url, timeout=3).content)
        return [
            {"headline": i.find('title').text.rsplit(' - ', 1)[0],
             "url": i.find('link').text, "source": "Google News"}
            for i in root.findall('.//item')[:3]
        ]
    except:
        return []


def resolve_ticker(query: str) -> str:
    u = query.upper().strip()
    if u.endswith(".NS"):
        return u.replace(".NS.NS", ".NS")
    shortcuts = {
        "RELIANCE": "RELIANCE.NS", "RIL": "RELIANCE.NS",
        "WIPRO": "WIPRO.NS", "WIT": "WIPRO.NS",
        "INFY": "INFY.NS", "INFOSYS": "INFY.NS",
        "TCS": "TCS.NS", "SAIL": "SAIL.NS",
    }
    if u in shortcuts:
        return shortcuts[u]
    search = yf.Search(query, max_results=10)
    for r in search.quotes:
        sym = r.get('symbol', '')
        if r.get('quoteType') == 'EQUITY' and sym.endswith('.NS'):
            return sym
    return f"{u}.NS"


# ──────────────────────────────────────────────────────────────────────────────
# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

class RegisterPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", tags=["auth"])
def register(
    payload: RegisterPayload,
    db: Session = Depends(get_db)
):
    user = create_user(
        payload.username,
        payload.password,
        db
    )

    return {
        "status": "success",
        "username": user.username,
        "id": user.id
    }


from pydantic import BaseModel

class LoginPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login", tags=["auth"])
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = authenticate_user(
        payload.username,
        payload.password,
        db
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password."
        )

    token = create_access_token({"sub": user.username})

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
    }

@app.get("/api/auth/me", tags=["auth"])
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "created_at": current_user["created_at"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# ── PORTFOLIO ROUTES (now per-user & auth-protected) ─────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/user-portfolio")
def api_get_portfolio(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "tickers": get_user_portfolio(current_user, db)
    }


@app.post("/api/user-portfolio/toggle")
def api_toggle_portfolio(
    payload: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticker = payload.get("ticker", "").upper().strip()

    if not ticker:
        return {
            "status": "error",
            "message": "No ticker provided"
        }

    updated = toggle_user_ticker(
        ticker,
        current_user,
        db
    )

    return {
        "status": "success",
        "tickers": updated
    }


# ──────────────────────────────────────────────────────────────────────────────
# ── TICKER SEARCH (public) ────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/tickers/search", tags=["data"])
def search_tickers(q: str = ""):
    query = q.lower().strip()
    if not query:
        return []
    hits = [
        {"symbol": s["symbol"], "name": s["name"]}
        for s in GLOBAL_TICKER_CACHE
        if s["raw_symbol"].startswith(query) or s["name"].lower().startswith(query)
    ]
    return sorted(hits, key=lambda x: x["name"])[:8]


# ──────────────────────────────────────────────────────────────────────────────
# ── PRICE HISTORY (public, cached) ───────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/price-history/{ticker}", tags=["data"])
def get_price_history(ticker: str, days: int = 30):
    symbol = resolve_ticker(ticker)
    period = "3mo" if days <= 90 else "6mo"

    cache_key = f"history:{symbol}:{days}"
    cached    = cache_get(cache_key)
    if cached:
        return cached

    df = yf.download(symbol, period=period, interval="1d", progress=False, ignore_tz=True)
    if df.empty:
        return {"error": f"No price data for {symbol}"}
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df    = df.dropna(subset=["Open","High","Low","Close"]).tail(days)
    close = df["Close"].astype(float)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = (100 - 100 / (1 + gain / (loss + 1e-9))).round(2)

    candles = []
    for ts, row in df.iterrows():
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        rsi_val  = float(rsi.loc[ts]) if ts in rsi.index and not np.isnan(float(rsi.loc[ts])) else None
        candles.append({
            "date":   date_str,
            "open":   round(float(row["Open"]),  2),
            "high":   round(float(row["High"]),  2),
            "low":    round(float(row["Low"]),   2),
            "close":  round(float(row["Close"]), 2),
            "volume": int(row["Volume"]) if not np.isnan(float(row["Volume"])) else 0,
            "rsi":    rsi_val,
        })

    result = {"ticker": symbol, "candles": candles}
    cache_set(cache_key, result, STOCK_TTL_SECONDS)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# ── CORE SIGNAL ROUTE (public, cached, zero broker side-effects) ──────────────
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/stock-info/{query}", tags=["data"])
def get_stock_full_info(query: str):

    # ── 1. Resolve ticker symbol ──
    best_ticker = resolve_ticker(query)

    # ── 2. Check result cache — skip heavy work if fresh ──
    result_key = f"result:{best_ticker}"
    cached     = cache_get(result_key)
    if cached:
        logger.info(f"⚡ Returning cached result for {best_ticker}")
        return cached

    try:
        # ── 3. Download data (each call is itself cached) ──
        df       = get_df_cached(best_ticker)
        nifty_df = get_nifty_cached()

        if df.empty or len(df) < 100 or nifty_df.empty:
            return {"error": "Insufficient history available for expanding sequence scaling."}

        if isinstance(df.columns,       pd.MultiIndex): df.columns       = df.columns.get_level_values(0)
        if isinstance(nifty_df.columns, pd.MultiIndex): nifty_df.columns = nifty_df.columns.get_level_values(0)

        df       = df.dropna(subset=['Open','High','Low','Close'])
        nifty_df = nifty_df.dropna(subset=['Open','High','Low','Close'])

        latest_close   = float(df['Close'].iloc[-1])
        previous_close = float(df['Close'].iloc[-2])
        daily_change   = latest_close - previous_close
        daily_change_pct = (daily_change / previous_close) * 100

        df_features    = calculate_indicators(df)
        nifty_features = calculate_indicators(nifty_df)

        nifty_features['Market_RSI'] = nifty_features['RSI']
        df_features = df_features.drop(columns=['Market_RSI'], errors='ignore')
        df_features = df_features.join(nifty_features[['Market_RSI']], how='left')
        df_features['Market_RSI'] = df_features['Market_RSI'].ffill().bfill()
        df_features['RSI_Lag_1']  = df_features['RSI'].shift(1)

        FEATURES = [
            'RSI','RSI_Lag_1','Price_to_SMA20','MACD_Hist_Pct',
            'BB_Width','ATR_Pct','CMF','Volume_Shock','Market_RSI'
        ]

        df_inference = df_features[FEATURES].dropna().copy()
        df_scaled    = pd.DataFrame(index=df_inference.index)
        for col in FEATURES:
            mu  = df_inference[col].expanding(min_periods=20).mean()
            std = df_inference[col].expanding(min_periods=20).std() + 1e-9
            df_scaled[col] = (df_inference[col] - mu) / std

        df_ready = df_scaled.dropna(subset=FEATURES)
        if len(df_ready) < 20:
            return {"error": "Insufficient valid frames for lookahead-free parsing."}

        if lstm_model is None:
            return {"error": "Directional recurrent array is uninitialized."}

        scaled_seq  = df_ready[FEATURES].to_numpy()[-20:]
        raw_pred    = float(lstm_model.predict(np.expand_dims(scaled_seq, axis=0), verbose=0)[0][0])
        p_buy, p_sell = raw_pred, 1.0 - raw_pred

        net_spread         = abs(p_buy - p_sell)
        direction          = "BUY" if p_buy > p_sell else "SELL"
        display_confidence = p_buy if direction == "BUY" else p_sell
        current_bb_width   = float(df_features['BB_Width'].iloc[-1] * 100)

        logger.info(f"[{best_ticker}] raw={raw_pred:.4f} spread={net_spread:.4f} bb={current_bb_width:.2f}%")

        # ── Signal rules ──
        if current_bb_width < 3.0:
            ai_signal_text  = "HOLD"
            confidence_band = f"Volatility Squeeze Active ({current_bb_width:.1f}%) // Range Bound Trap"
        else:
            if direction == "BUY":
                if net_spread >= 0.08:
                    ai_signal_text  = "STRONG BUY"
                    confidence_band = f"High-Velocity Breakout Trajectory Confirmed ({p_buy*100:.1f}%)"
                elif net_spread >= 0.01:
                    ai_signal_text  = "BUY"
                    confidence_band = f"Structural Momentum Alignment Confirmed ({p_buy*100:.1f}%)"
                else:
                    ai_signal_text  = "HOLD"
                    confidence_band = f"Neutral Model Confidence Spread Matrix ({net_spread*100:.1f}%)"
            else:
                if net_spread >= 0.08:
                    ai_signal_text  = "STRONG SELL"
                    confidence_band = f"Premium Bearish Acceleration Confirmed ({p_sell*100:.1f}%)"
                elif net_spread >= 0.01:
                    ai_signal_text  = "SELL"
                    confidence_band = f"Validated Downside Trend Continuity ({p_sell*100:.1f}%)"
                else:
                    ai_signal_text  = "HOLD"
                    confidence_band = f"Neutral Model Confidence Spread Matrix ({net_spread*100:.1f}%)"

        # Macro protection
        market_slope = float(df_features['MACD_Hist_Slope'].iloc[-1]) if 'MACD_Hist_Slope' in df_features.columns else 0.0
        if market_slope < -0.25 and "BUY" in ai_signal_text:
            ai_signal_text  = "HOLD"
            confidence_band = "Macro Index Downside Momentum Protection Override Active"

        # Signal quality label
        if net_spread >= 0.08:   signal_quality = "High Conviction — Strong directional spread detected"
        elif net_spread >= 0.04: signal_quality = "Moderate Conviction — Directional bias present"
        elif net_spread >= 0.01: signal_quality = "Low Conviction — Weak edge, exercise caution"
        else:                    signal_quality = "No Edge — Model is near-neutral on this ticker"

        result = {
            "ticker":           best_ticker,
            "price":            round(safe_float(latest_close), 2),
            "daily_change":     round(safe_float(daily_change), 2),
            "daily_change_pct": round(safe_float(daily_change_pct), 2),
            "ai_signal":        ai_signal_text,
            "confidence":       f"{round(display_confidence * 100, 2)}%",
            "confidence_band":  confidence_band,
            "signal_quality":   signal_quality,
            "net_spread":       round(net_spread, 4),
            "engine_mode":      "Dual-Class Sigmoid Compass + Signal Intelligence Terminal",
            "news":             fetch_local_indian_news(best_ticker),
            "metrics": {
                "rsi":            round(safe_float(df_features['RSI'].iloc[-1]), 2),
                "price_to_sma20": round(safe_float(df_features['Price_to_SMA20'].iloc[-1]), 3),
                "macd":           round(safe_float(df_features['MACD'].iloc[-1]), 2),
                "macd_hist":      round(safe_float(df_features['MACD_Hist'].iloc[-1]), 2),
                "bb_width":       round(safe_float(df_features['BB_Width'].iloc[-1] * 100), 2),
                "atr":            round(safe_float(df_features['ATR'].iloc[-1]), 2),
                "adx":            round(safe_float(df_features['ADX'].iloc[-1]), 2) if 'ADX' in df_features.columns else 0.0,
            }
        }

        # Cache the full result for 5 min
        cache_set(result_key, result, STOCK_TTL_SECONDS)
        return result

    except Exception as e:
        return {"error": f"Inference System Exception: {str(e)}"}