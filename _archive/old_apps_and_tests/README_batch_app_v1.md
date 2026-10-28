# Batch Transaction Anomaly Detection Web Application

A complete batch transaction anomaly detection system built with **Streamlit**, powered by an existing trained **Isolation Forest** model and **StandardScaler**.

---

## 🏗️ Project Structure

```
fraud_detection_app/
│
├── app.py                      # Main Streamlit Batch Dashboard (Sections 1–6)
├── feature_engineering.py      # Vectorized batch feature calculation engine (30 ML features)
├── sample_transactions.csv     # Pre-packaged 500-transaction demo dataset
├── requirements.txt            # Python dependencies
├── README.md                   # Comprehensive documentation and usage guide
│
└── models/
    ├── isolation_forest.pkl    # Trained Isolation Forest model (Untouched)
    ├── scaler.pkl              # Fitted StandardScaler (Untouched & never refitted)
    ├── feature_config.pkl      # Ordered list of exactly 30 model features
    └── preprocessing_config.pkl# Config specifying ml_features and log_features
```

---

## 🚀 How to Run the Streamlit Application

### 1. Set Up Virtual Environment (Recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
From the project root directory:
```bash
streamlit run fraud_detection_app/app.py
```
Then open your browser at `http://localhost:8501`.

---

## 📥 Required CSV Upload Format (14 Columns)

The uploaded transaction dataset must contain these **14 raw columns**:

| Column Name | Type | Description |
|---|---|---|
| `transaction_id` | String | Unique transaction reference ID |
| `sender_id` | String | Originating account identifier |
| `receiver_id` | String | Destination account identifier |
| `amount` | Float | Transaction financial value ($\ge 0$) |
| `transaction_type` | String | Type of transfer (PAYMENT, TRANSFER, CASH_OUT, etc.) |
| `transaction_step` | Integer | Simulation timeline step (1 step = 1 hour) |
| `sender_old_balance` | Float | Sender balance prior to transaction |
| `sender_new_balance` | Float | Sender balance after transaction |
| `receiver_old_balance` | Float | Receiver balance prior to transaction |
| `receiver_new_balance` | Float | Receiver balance after transaction |
| `transaction_time` | Datetime / String | Timestamp of transaction (`YYYY-MM-DD HH:MM:SS`) |
| `device_id` | String | Hardware/Device fingerprint ID |
| `device_change_flag` | Integer (0/1) | Flag indicating device change |
| `new_device_flag` | Integer (0/1) | Flag indicating unrecognized new device |

---

## 🔄 The 30 Model Features & Feature Engineering

All 30 ML features are computed automatically by `feature_engineering.py` strictly before the current transaction to prevent data leakage:

| # | Feature Name | Computation / Source | Preprocessing |
|---|---|---|---|
| 1 | `amount` | Direct from CSV | `np.log1p` + Scaled |
| 2 | `transaction_step` | Direct from CSV | Scaled |
| 3 | `sender_old_balance` | Direct from CSV | `np.log1p` + Scaled |
| 4 | `sender_new_balance` | Direct from CSV | `np.log1p` + Scaled |
| 5 | `receiver_old_balance` | Direct from CSV | `np.log1p` + Scaled |
| 6 | `receiver_new_balance` | Direct from CSV | `np.log1p` + Scaled |
| 7 | `transaction_hour` | Extracted from `transaction_time` (`dt.hour`) | Scaled |
| 8 | `is_night` | Derived from hour (`hour < 6` or `hour >= 22`) | Scaled |
| 9 | `transaction_frequency` | Baseline observation frequency (`1.0`) | Scaled |
| 10 | `same_step_txn_count_before` | Sender prior transactions in the same step | Scaled |
| 11 | `sender_txn_count_before` | Cumulative transactions sent by sender prior | Scaled |
| 12 | `sender_receiver_txn_count_before` | Cumulative prior transactions between this pair | Scaled |
| 13 | `sender_unique_recipients_before` | Cumulative unique recipients seen for sender | Scaled |
| 14 | `receiver_txn_count_before` | Cumulative transactions received prior | `np.log1p` + Scaled |
| 15 | `receiver_unique_senders_before` | Cumulative unique senders to receiver prior | `np.log1p` + Scaled |
| 16 | `time_since_previous_sender_txn` | Hours since previous sender txn (`-1.0` if 1st txn) | Scaled |
| 17 | `sender_balance_ratio` | `amount / (sender_old_balance + 1.0)` | `np.log1p` + Scaled |
| 18 | `sender_amount_mean_before` | Expanding mean of sender amounts prior | `np.log1p` + Scaled |
| 19 | `sender_amount_std_before` | Expanding sample std of sender amounts prior | `np.log1p` + Scaled |
| 20 | `amount_deviation` | `abs(amount - sender_amount_mean_before)` | `np.log1p` + Scaled |
| 21 | `amount_zscore` | Normalized Z-score of transfer amount | Scaled |
| 22 | `txns_last_1h` | Sender rolling count in last 1 hour strictly before | Scaled |
| 23 | `txns_last_6h` | Sender rolling count in last 6 hours strictly before | Scaled |
| 24 | `txns_last_24h` | Sender rolling count in last 24 hours strictly before | Scaled |
| 25 | `rapid_transaction_flag` | Burst indicator (time diff $\le 6$ min or same step) | Scaled |
| 26 | `device_change_flag` | Direct from CSV | Scaled |
| 27 | `new_device_flag` | Direct from CSV | Scaled |
| 28 | `hop_number` | Chain layering hop position in money trail | Scaled |
| 29 | `chain_length` | Total length of detected money-laundering chain | Scaled |
| 30 | `chain_duration_steps` | Duration in steps from chain root | Scaled |

---

## ⚡ Preprocessing & Scoring Pipeline

1. **Log Transformation**: Applied exclusively to the 11 features specified in `preprocessing_config.pkl`:
   `['amount', 'sender_old_balance', 'sender_new_balance', 'receiver_old_balance', 'receiver_new_balance', 'sender_amount_mean_before', 'sender_amount_std_before', 'amount_deviation', 'sender_balance_ratio', 'receiver_txn_count_before', 'receiver_unique_senders_before']`
2. **StandardScaler**: Scaled using `scaler.transform()`. `scaler.fit()` and `fit_transform()` are never invoked.
3. **Isolation Forest Prediction**:
   - `model.predict()`: `1` = Normal, `-1` = Anomaly.
   - `model.decision_function()`: `anomaly_score` (more negative = higher anomaly).
4. **Risk Ranking**:
   - **High Risk**: `anomaly_score < -0.05`
   - **Medium Risk**: `-0.05 <= anomaly_score < 0.0`
   - **Normal / Low Risk**: `anomaly_score >= 0.0`

---

## 📊 Dashboard Sections Walkthrough

- **Section 1: Upload**: Drag & drop batch CSV, view file metrics, and check automatic validation for missing columns, nulls, duplicates, and invalid numeric values.
- **Section 2: Dataset Overview**: KPI cards showing total volume, normal vs anomalous count, anomaly rate, and highest-risk transaction.
- **Section 3: Ranked Suspicious Transactions**: Interactive data table sorted by anomaly score ascending, with multi-level filtering by Risk Level, Prediction, Transaction Type, and Display Limits (Top 10, 25, 50, 100, 500, All).
- **Section 4: Anomaly Analysis**: Charts for class distribution, score histogram, temporal step trends, transaction type breakdown, and top-10 worst anomaly scores.
- **Section 5: Transaction Details**: Deep-dive selector into any specific transaction ID with full feature vector inspector (raw, log-transformed, and scaled values).
- **Section 6: Download**: Export Complete Scored Dataset or Anomalies-Only CSV.
