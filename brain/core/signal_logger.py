import os
import csv
from datetime import datetime

LOG_FILE = 'data/live_signal_logs.csv'

def initialize_logger():
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Ticker', 'Live_Price', 'Raw_LSTM_Prob', 
                'Amplified_Score', 'Final_Signal', 'Confidence', 'Confidence_Band', 
                'Market_Slope', 'Engine_Mode', 'RSI_14', 'MACD_Hist', 'ADX_14', 
                'Forward_Day1_Price', 'Forward_Day3_Price', 'Forward_Day5_Price', 'Status'
            ])

def log_live_prediction(ticker, price, raw_prob, amplified_score, signal, confidence, confidence_band, market_slope, mode, metrics):
    initialize_logger()
    try:
        with open(LOG_FILE, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ticker,
                price,
                round(float(raw_prob), 4) if raw_prob is not None else 'N/A',
                round(float(amplified_score), 4),
                signal,
                confidence,
                confidence_band,
                round(float(market_slope), 6),
                mode,
                round(float(metrics.get('rsi', 0)), 2),
                round(float(metrics.get('macd_hist', 0)), 4),
                round(float(metrics.get('adx', 0)), 2),
                '', '', '', 'OPEN'
            ])
    except Exception as e:
        print(f"🚨 Live Logger File Access Failure: {e}")