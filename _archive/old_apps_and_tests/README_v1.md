# Transaction Anomaly Detection Web Application

An interactive fintech/banking dashboard for real-time transaction anomaly detection built with **Streamlit**, powered by an existing pre-trained **Isolation Forest** model and pre-fitted **StandardScaler**.

> ⚠️ **IMPORTANT PROTOTYPE NOTICE**:  
> This application is an **evaluation prototype** and is **NOT claimable as production-ready**. In production fraud detection architectures, historical behavioral features (such as 1h/6h/24h rolling transaction counts, historical transaction variance, and multi-hop transfer chains) are queried in real-time from a distributed Feature Store or graph database. For this single-transaction interactive form, clearly documented prototype defaults are applied for features where historical context is unavailable.

---

## 📁 Project Structure

```
├── app.py                      # Main Streamlit fraud detection dashboard
├── requirements.txt            # Required Python packages
├── README.md                   # Comprehensive documentation and running instructions
├── test_pipeline.py            # Automated test suite verifying the 6 pipeline requirements
├── isolation_forest.pkl        # Trained Isolation Forest model (Untouched & not retrained)
├── scaler.pkl                  # Fitted StandardScaler (Untouched & not refitted)
├── feature_config.pkl          # Ordered list of exactly 30 model features
└── preprocessing_config.pkl    # Configuration specifying ml_features and log_features
```

---

## ⚙️ Installation & Running the App

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Set Up Virtual Environment (Recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```
Once started, open your web browser at `http://localhost:8501`.

---

## 🛡️ Model Architecture & Features

The model expects **exactly 30 features** in the exact order saved in `feature_config.pkl`:

| # | Feature Name | Source / Type | Preprocessing | Description |
|---|---|---|---|---|
| 1 | `amount` | User Input | `np.log1p` + Scaled | Transaction monetary amount |
| 2 | `transaction_step` | User Input | Scaled | Simulation timeline step (1 step = 1 hour) |
| 3 | `sender_old_balance` | User Input | `np.log1p` + Scaled | Sender initial balance prior to transfer |
| 4 | `sender_new_balance` | User Input | `np.log1p` + Scaled | Sender resulting balance after transfer |
| 5 | `receiver_old_balance` | User Input | `np.log1p` + Scaled | Receiver initial balance prior to transfer |
| 6 | `receiver_new_balance` | User Input | `np.log1p` + Scaled | Receiver resulting balance after transfer |
| 7 | `transaction_hour` | Derived | Scaled | Extracted hour of transaction (0–23) |
| 8 | `is_night` | Derived | Scaled | Binary flag (1 if hour < 6 or >= 22, else 0) |
| 9 | `transaction_frequency` | Prototype Default | Scaled | Baseline observation frequency (`1.0`) |
| 10 | `same_step_txn_count_before` | Prototype Default | Scaled | Prior txns in current step (`0.0`) |
| 11 | `sender_txn_count_before` | Prototype Default | Scaled | Historical sender transaction count (`0.0`) |
| 12 | `sender_receiver_txn_count_before` | Prototype Default | Scaled | Historical pair interaction count (`0.0`) |
| 13 | `sender_unique_recipients_before` | Prototype Default | Scaled | Historical sender unique recipients (`0.0`) |
| 14 | `receiver_txn_count_before` | Prototype Default | `np.log1p` + Scaled | Historical receiver transaction count (`0.0`) |
| 15 | `receiver_unique_senders_before` | Prototype Default | `np.log1p` + Scaled | Historical receiver unique senders (`0.0`) |
| 16 | `time_since_previous_sender_txn` | Prototype Default | Scaled | Elapsed time since prior txn (`-1.0` encodes no prior txn) |
| 17 | `sender_balance_ratio` | Derived | `np.log1p` + Scaled | Ratio: `amount / (sender_old_balance + 1)` |
| 18 | `sender_amount_mean_before` | Prototype Default | `np.log1p` + Scaled | Historical mean transfer amount (`0.0`) |
| 19 | `sender_amount_std_before` | Prototype Default | `np.log1p` + Scaled | Historical transfer amount std (`0.0`) |
| 20 | `amount_deviation` | Prototype Default | `np.log1p` + Scaled | Absolute deviation from sender average (`0.0`) |
| 21 | `amount_zscore` | Prototype Default | Scaled | Z-score of transfer amount (`0.0`) |
| 22 | `txns_last_1h` | Prototype Default | Scaled | Rolling 1-hour transaction velocity (`0.0`) |
| 23 | `txns_last_6h` | Prototype Default | Scaled | Rolling 6-hour transaction velocity (`0.0`) |
| 24 | `txns_last_24h` | Prototype Default | Scaled | Rolling 24-hour transaction velocity (`0.0`) |
| 25 | `rapid_transaction_flag` | Prototype Default | Scaled | High-frequency burst indicator (`0.0`) |
| 26 | `device_change_flag` | User Input | Scaled | Binary flag (1 if device changed, else 0) |
| 27 | `new_device_flag` | User Input | Scaled | Binary flag (1 if new device used, else 0) |
| 28 | `hop_number` | Prototype Default | Scaled | Graph position in money flow chain (`0.0`) |
| 29 | `chain_length` | Prototype Default | Scaled | Graph money-laundering chain length (`0.0`) |
| 30 | `chain_duration_steps` | Prototype Default | Scaled | Step duration of transaction chain (`0.0`) |

---

## 🔄 Preprocessing Pipeline

To maintain strict alignment with the training process:
1. **Dynamic Config**: `preprocessing_config.pkl` is loaded to identify the 11 log-transformed features:
   - `amount`, `sender_old_balance`, `sender_new_balance`, `receiver_old_balance`, `receiver_new_balance`, `sender_amount_mean_before`, `sender_amount_std_before`, `amount_deviation`, `sender_balance_ratio`, `receiver_txn_count_before`, `receiver_unique_senders_before`.
2. **Log Transformation**: `np.log1p(x)` is applied exclusively to these 11 features.
3. **StandardScaler**: Pre-fitted `scaler.pkl` transforms the full 30-feature vector using `scaler.transform()`. `fit()` and `fit_transform()` are never invoked.
4. **Inference**: Pre-trained `isolation_forest.pkl` scores the scaled vector:
   - `model.predict()`: Returns `1` (Normal) or `-1` (Anomaly).
   - `model.decision_function()`: Returns raw decision anomaly score (positive = normal, negative = anomaly).

---

## 📋 Input Validation Rules

The application enforces business logic and mathematical validity before inference:
- **Missing Required Fields**: Transaction ID cannot be blank.
- **Negative Amount**: Amount must be strictly `> 0.0`.
- **Negative Balances**: Sender Old/New Balance and Receiver Old/New Balance cannot be `< 0.0`.
- **Invalid Transaction Step**: Step must be a positive integer `>= 1`.
- **Sanity Warnings**: Non-blocking business alerts if transfer amount exceeds available sender balance.

---

## 🧪 Verification & Automated Testing

You can run the included automated verification script at any time:

```bash
python test_pipeline.py
```

This script verifies:
1. All 4 pickle files load successfully.
2. Exactly 30 features are passed in exact matching order.
3. The scaler parameters are unchanged (no refitting).
4. The Isolation Forest trees and offsets are unchanged (no retraining).
5. Both normal and anomalous transactions produce accurate predictions and decision scores.
