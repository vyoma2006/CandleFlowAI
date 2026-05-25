import os
import pandas as pd
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.calibration import CalibratedClassifierCV

def train_logic():
    # 1. Load the data
    if not os.path.exists('data/training_data.csv'):
        print("❌ Error: data/training_data.csv not found. Run your data processor script first!")
        return

    df = pd.read_csv('data/training_data.csv')
    
    # 2. 💡 THE UPDATE: Define the Expanded, Multidimensional Feature Set
    features = [
        # Base Stationary Indicators
        'RSI', 
        'Price_to_SMA20', 
        'MACD_Pct', 
        'MACD_Hist_Pct', 
        'BB_Width', 
        'ATR_Pct',
        
        # 🌍 Market Regime Benchmark Indicators (Nifty 50 Context)
        'Market_RSI',
        'Market_Price_to_SMA20',
        
        # 🕒 Temporal Historical Lags (Pseudo-Sequence Memory)
        'RSI_Lag_1',
        'RSI_Lag_2',
        'Price_to_SMA20_Lag_1',
        'Price_to_SMA20_Lag_2',
        'MACD_Hist_Pct_Lag_1',
        'MACD_Hist_Pct_Lag_2'
    ] 
    
    # Safety Check: Ensure all new attributes exist in your compiled CSV
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        print(f"❌ Error: The following indicators are missing from your CSV: {missing_features}")
        print("👉 Please run your processor.py script first to verify your columns generated.")
        return

    # Drop rows containing NaN values
    df_clean = df.dropna(subset=features + ['Target'])

    X = df_clean[features]
    y = df_clean['Target']

    # 3. Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    print(f"🧠 Training the Calibrated Macro-Regime + Lagged XGBoost Model...")
    
    # Calculate Sample Weights dynamically to counter the structural bullish bias
    train_sample_weights = compute_sample_weight(class_weight='balanced', y=y_train)

    # Base XGBoost config - depth adjusted to 4 to accommodate 14 features smoothly
    base_model = xgb.XGBClassifier(
        n_estimators=100,       
        max_depth=4,            
        learning_rate=0.03,     
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'   
    )
    
    # Cross-validation mapping inside the wrapper
    calibrated_model = CalibratedClassifierCV(
        estimator=base_model, 
        method='sigmoid', 
        cv=3
    )
    
    # Fit the calibrated ensemble wrapper on the expanded training data pool
    calibrated_model.fit(X_train, y_train, sample_weight=train_sample_weights)

    # 4. Check Performance against the unseen 20% test baseline
    predictions = calibrated_model.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    print("\n" + "="*40)
    print(f"✅ Training Complete! Calibrated System Accuracy: {acc * 100:.2f}%")
    print("="*40)
    print(classification_report(y_test, predictions))

    # 5. Save the Upgraded 'Brain'
    os.makedirs('models', exist_ok=True)
    joblib.dump(calibrated_model, 'models/candleflow_v1.joblib')
    print("💾 Calibrated Model successfully saved to 'models/candleflow_v1.joblib'")

if __name__ == "__main__":
    train_logic()