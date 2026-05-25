import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

# 1. Load your pristine training matrix that the model loved
df = pd.read_csv('data/training_data.csv')

# 2. Pull a random slice from the validation/test partition (the tail end)
features = [
    'RSI', 'Price_to_SMA20', 'MACD_Pct', 'MACD_Hist_Pct', 'BB_Width', 'ATR_Pct',
    'Market_RSI', 'Market_Price_to_SMA20', 'Volume_Shock', 'CMF', 'ADX',
    'VWAP_Dist', 'MACD_Hist_Slope', 'RSI_Divergence', 'ATR_Volatility', 'Market_MACD_Hist_Slope',
    'Garman_Klass', 'RSI_Velocity', 'RSI_Acceleration', 'EMA_Diff_Pct', 'ROC_5',
    'RSI_Lag_1', 'RSI_Lag_2', 'Price_to_SMA20_Lag_1', 'Price_to_SMA20_Lag_2', 'MACD_Hist_Pct_Lag_1', 'MACD_Hist_Pct_Lag_2'
]

# Grab a known trending slice from the frozen CSV records
sample_sequence = df[features].tail(20).values
tensor_input = np.expand_dims(sample_sequence, axis=0)

# 3. Predict using your custom object bypass hook
def focal_loss_fixed(y_true, y_pred): return y_pred
model = load_model('models/candleflow_lstm.keras', custom_objects={"focal_loss_fixed": focal_loss_fixed}, compile=False)

probs = model.predict(tensor_input, verbose=0)[0]
print(f"\n🎯 Clean Diagnostic Vector [SELL: {probs[0]:.3f} | BUY: {probs[1]:.3f} | HOLD: {probs[2]:.3f}]")
