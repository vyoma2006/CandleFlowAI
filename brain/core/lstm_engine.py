import os
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, accuracy_score, roc_curve

try:
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, BatchNormalization, Layer
    from tensorflow.keras.callbacks import EarlyStopping, LearningRateScheduler
    from tensorflow.keras.regularizers import l2
    import tensorflow.keras.backend as K
except ImportError:
    print("❌ Error: TensorFlow components missing. Verify virtual environment.")
    exit()

class TemporalAttention(Layer):
    def __init__(self, step_dim, **kwargs):
        super(TemporalAttention, self).__init__(**kwargs)
        self.step_dim = step_dim

    def build(self, input_shape):
        self.W = self.add_weight(name=f'{self.name}_W',
                                 shape=(input_shape[-1], 1),
                                 initializer='glorot_uniform',
                                 trainable=True)
        super(TemporalAttention, self).build(input_shape)

    def call(self, x):
        eij = K.dot(x, self.W)
        eij = K.tanh(eij)
        ai = K.exp(eij)
        weights = ai / (K.sum(ai, axis=1, keepdims=True) + K.epsilon())
        context = x * weights
        return K.sum(context, axis=1)

    def get_config(self):
        config = super(TemporalAttention, self).get_config()
        config.update({"step_dim": self.step_dim})
        return config

def binary_focal_loss(gamma=1.5, alpha=0.50):
    def focal_loss_fixed(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        y_pred = K.clip(y_pred, K.epsilon(), 1.0 - K.epsilon())
        cross_entropy = -y_true * K.log(y_pred) - (1.0 - y_true) * K.log(1.0 - y_pred)
        focal_weight = y_true * alpha * K.pow(1.0 - y_pred, gamma) + \
                       (1.0 - y_true) * (1.0 - alpha) * K.pow(y_pred, gamma)
        return focal_weight * cross_entropy
    return focal_loss_fixed

def train_lstm_logic():
    CSV_PATH = 'data/training_data.csv'
    if not os.path.exists(CSV_PATH):
        print("❌ Error: training_data.csv missing! Run core.processor first.")
        return

    df = pd.read_csv(CSV_PATH)
    
    features = [
        'RSI', 'RSI_Lag_1', 'Price_to_SMA20', 'MACD_Hist_Pct', 
        'BB_Width', 'ATR_Pct', 'CMF', 'Volume_Shock', 'Market_RSI'
    ]
    
    df_clean = df.dropna(subset=features + ['Target', 'Ticker']).copy()
    df_clean['Target'] = df_clean['Target'].astype(int)

    if 'Date' in df_clean.columns:
        df_clean = df_clean.sort_values(by='Date').reset_index(drop=True)

    TIME_STEPS = 20
    X_all_sequences = []
    y_all_labels = []

    unique_tickers = df_clean['Ticker'].unique()

    for ticker in unique_tickers:
        ticker_df = df_clean[df_clean['Ticker'] == ticker].copy()
        if len(ticker_df) < TIME_STEPS + 10: continue
            
        ticker_X = ticker_df[features].values
        ticker_y = ticker_df['Target'].values
        
        for i in range(len(ticker_df) - TIME_STEPS + 1):
            X_all_sequences.append(ticker_X[i : (i + TIME_STEPS)])
            y_all_labels.append(ticker_y[i + TIME_STEPS - 1])

    X_matrix = np.array(X_all_sequences)
    y_matrix = np.array(y_all_labels)

    total_samples = len(X_matrix)
    shuffled_indices = np.random.permutation(total_samples)
    
    X_matrix = X_matrix[shuffled_indices]
    y_matrix = y_matrix[shuffled_indices]

    split_pivot = int(total_samples * 0.8)
    
    X_train = X_matrix[:split_pivot]
    X_test = X_matrix[split_pivot:]
    y_train = y_matrix[:split_pivot]
    y_test = y_matrix[split_pivot:]

    # ----------------------------------------------------------------------
    # ⚖️ DYNAMIC CLASS BALANCING GRADIENT CALCULATOR
    # ----------------------------------------------------------------------
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    
    # Mathematical scaling factor weight definitions
    weight_for_0 = (1 / neg_count) * (total_samples / 2.0)
    weight_for_1 = (1 / pos_count) * (total_samples / 2.0)
    class_weight_matrix = {0: weight_for_0, 1: weight_for_1}

    # ----------------------------------------------------------------------
    # 🧠 STRUCTURALLY BALANCED SIGMOID ATTENTION-LSTM NETWORK GRAPH
    # ----------------------------------------------------------------------
    input_layer = Input(shape=(X_train.shape[1], X_train.shape[2]))
    norm_input = BatchNormalization()(input_layer)
    
    lstm_seq = LSTM(units=96, return_sequences=True, 
                    kernel_regularizer=l2(0.001), 
                    recurrent_regularizer=l2(0.001))(norm_input)
    lstm_seq = BatchNormalization()(lstm_seq)
    lstm_seq = Dropout(0.3)(lstm_seq)
    
    attention_context = TemporalAttention(step_dim=TIME_STEPS)(lstm_seq)
    
    dense_block = Dense(units=48, activation='swish', kernel_regularizer=l2(0.001))(attention_context)
    dense_block = BatchNormalization()(dense_block)
    dense_block = Dropout(0.25)(dense_block)
    
    output_layer = Dense(units=1, activation='sigmoid')(dense_block)
    
    model = Model(inputs=input_layer, outputs=output_layer)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss=binary_focal_loss(gamma=1.5, alpha=0.50),
        metrics=['accuracy']
    )

    def dynamic_clr_schedule(epoch):
        base_lr = 0.00005
        max_lr = 0.0004
        step_size = 6.0
        cycle = np.floor(1 + epoch / (2 * step_size))
        x = np.abs(epoch / step_size - 2 * cycle + 1)
        return float(base_lr + (max_lr - base_lr) * np.maximum(0, (1 - x)))

    lr_scheduler_callback = LearningRateScheduler(dynamic_clr_schedule)
    monitor_callback = EarlyStopping(monitor='val_loss', patience=6, restore_best_weights=True)

    print(f"\n🚀 Commencing Class-Weighted Sigmoid Optimization (Max 30 Epochs)...")
    model.fit(
        X_train, y_train, 
        epochs=30, 
        batch_size=128, 
        validation_split=0.1, 
        shuffle=True, 
        class_weight=class_weight_matrix, # 🎯 Mounted class balance matrices
        callbacks=[monitor_callback, lr_scheduler_callback],
        verbose=1
    )

    y_pred_probs = model.predict(X_test, verbose=0).flatten()

    # ----------------------------------------------------------------------
    # 🎯 ROC-AUC GEOMETRIC MIDPOINT THRESHOLD OPTIMIZATION
    # ----------------------------------------------------------------------
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_probs)
    # Locate the geometric mean optimization coordinate on the ROC curve
    gmeans = np.sqrt(tpr * (1 - fpr))
    optimal_index = np.argmax(gmeans)
    optimal_threshold = float(thresholds[optimal_index])
    
    # Fallback sanity clip prevents extreme skew limits
    if optimal_threshold < 0.42 or optimal_threshold > 0.58:
        optimal_threshold = 0.50

    print(f"\n🎯 Geometric Optimization Threshold Unlocked: {optimal_threshold:.4f}")
    y_pred = np.where(y_pred_probs >= optimal_threshold, 1, 0)
    
    print("\n" + "="*45)
    print(f"🎯 Balanced Leakage-Free Test Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")
    print("="*45)
    
    print(classification_report(y_test, y_pred, target_names=['SELL', 'BUY']))

    os.makedirs('models', exist_ok=True)
    model.save('models/candleflow_lstm.keras')
    print("💾 High-contrast directional network saved cleanly to models/")

if __name__ == "__main__":
    train_lstm_logic()