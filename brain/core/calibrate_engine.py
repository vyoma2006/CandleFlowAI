import numpy as np
import pandas as pd
import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression

def train_platt_calibration_layer(X_val_scaled, y_val, raw_model_path, export_path):
    """
    Fits an institutional Platt Scaling model over compressed raw predictions
    to transform network outputs into true, calibrated real-world probabilities.
    """
    print("⚖️ Initializing Platt Scaling Calibration Sequence...")
    
    # Load raw underlying tabular estimator
    raw_model = joblib.load(raw_model_path)
    
    # Fit the sigmoid calibrator over validation arrays
    calibrator = CalibratedClassifierCV(
        estimator=raw_model,
        method='sigmoid',
        cv='prefit' # Safeguards pre-trained weight architectures
    )
    
    # Solve for optimal log-loss parameters (A and B scaling constraints)
    calibrator.fit(X_val_scaled, y_val)
    
    # Save the calibrated architecture downstream
    joblib.dump(calibrator, export_path)
    print(f"🚀 High-fidelity calibrated model exported successfully to: {export_path}")
    
    return calibrator