"""
Refined generator for 3 presentation-ready demo CSV datasets for PBL-III showcase:
1. dataset_1_normal_baseline.csv: Standard normal retail/P2P traffic (High Normal % / Low Risk)
2. dataset_2_scam_attacks.csv: High-risk targeted attacks (Nocturnal Takeovers, Phishing, Device Spoofs)
3. dataset_3_mule_layering_chains.csv: Organized multi-hop money mule layering chains & fan-in aggregation
"""

import datetime
import os
import pickle
import numpy as np
import pandas as pd

from fraud_detection_app.feature_engineering import validate_raw_csv, compute_30_features


def generate_curated_datasets():
    np.random.seed(42)
    base_time = datetime.datetime(2026, 3, 1, 0, 0, 0)

    # =========================================================================
    # DATASET 1: NORMAL BASELINE (300 Rows)
    # Calibrated to typical PaySim normal distribution (Daytime, steps 180-320,
    # amounts $12k-$48k, positive balances, primary device)
    # =========================================================================
    n1 = 300
    steps_1 = []
    times_1 = []

    for i in range(n1):
        # Steps between 160 and 320 (middle of the month)
        step = int(np.random.randint(160, 320))
        day = (step // 24) + 1
        hour = int(np.random.choice([10, 11, 12, 13, 14, 15, 16, 17, 18, 19]))
        minute = int(np.random.randint(0, 60))
        second = int(np.random.randint(0, 60))
        t = datetime.datetime(2026, 3, day, hour, minute, second)
        steps_1.append(step)
        times_1.append(t)

    order_1 = np.argsort(times_1)
    steps_1 = [steps_1[i] for i in order_1]
    times_1 = [times_1[i] for i in order_1]

    senders_1 = [f"C{np.random.randint(1001, 1035):04d}" for _ in range(n1)]
    receivers_1 = [f"M{np.random.randint(2001, 2030):04d}" for _ in range(n1)]
    types_1 = [np.random.choice(["PAYMENT", "TRANSFER"], p=[0.70, 0.30]) for _ in range(n1)]

    amounts_1, s_old_1, s_new_1, r_old_1, r_new_1, dev_ids_1, dev_ch_1, new_dev_1 = [], [], [], [], [], [], [], []

    for i in range(n1):
        # Typical normal transfer amount: $10,000 to $45,000
        amt = float(np.round(np.random.uniform(12000.0, 42000.0), 2))
        s_old = float(np.round(amt + np.random.uniform(8000.0, 35000.0), 2))
        s_new = float(np.round(s_old - amt, 2))
        r_old = float(np.round(np.random.uniform(5000.0, 40000.0), 2))
        r_new = float(np.round(r_old + amt, 2))

        amounts_1.append(amt)
        s_old_1.append(s_old)
        s_new_1.append(s_new)
        r_old_1.append(r_old)
        r_new_1.append(r_new)
        dev_ids_1.append(f"DEV_{senders_1[i]}")
        dev_ch_1.append(0)
        new_dev_1.append(0)

    df1 = pd.DataFrame({
        "transaction_id": [f"TXN_NORM_{i+1:04d}" for i in range(n1)],
        "sender_id": senders_1,
        "receiver_id": receivers_1,
        "amount": amounts_1,
        "transaction_type": types_1,
        "transaction_step": steps_1,
        "sender_old_balance": s_old_1,
        "sender_new_balance": s_new_1,
        "receiver_old_balance": r_old_1,
        "receiver_new_balance": r_new_1,
        "transaction_time": [t.strftime("%Y-%m-%d %H:%M:%S") for t in times_1],
        "device_id": dev_ids_1,
        "device_change_flag": dev_ch_1,
        "new_device_flag": new_dev_1,
    })

    # =========================================================================
    # DATASET 2: HIGH-RISK SCAM & FRAUD ATTACKS (400 Rows)
    # Injects prominent attack patterns:
    # - Nocturnal Account Takeovers (02:00-04:00 AM, unrecognized new device, 100% balance wipeout)
    # - Sudden Phishing Amount Spikes ($750k-$1.2M)
    # - Zero old balance abnormal transfers
    # =========================================================================
    n2 = 400
    steps_2 = []
    times_2 = []

    for i in range(n2):
        step = int(np.random.randint(50, 450))
        day = (step // 24) + 1
        # 30% of traffic concentrated in nocturnal fraud hours (01:00 to 04:00 AM)
        if np.random.rand() < 0.30:
            hour = int(np.random.choice([1, 2, 3, 4]))
        else:
            hour = int(np.random.choice(range(8, 22)))
        minute = int(np.random.randint(0, 60))
        second = int(np.random.randint(0, 60))
        t = datetime.datetime(2026, 3, min(31, day), hour, minute, second)
        steps_2.append(step)
        times_2.append(t)

    order_2 = np.argsort(times_2)
    steps_2 = [steps_2[i] for i in order_2]
    times_2 = [times_2[i] for i in order_2]

    senders_2 = [f"C{np.random.randint(1001, 1060):04d}" for _ in range(n2)]
    receivers_2 = [f"M{np.random.randint(2001, 2040):04d}" for _ in range(n2)]
    types_2 = [np.random.choice(["PAYMENT", "TRANSFER", "CASH_OUT"], p=[0.40, 0.45, 0.15]) for _ in range(n2)]

    amounts_2, s_old_2, s_new_2, r_old_2, r_new_2, dev_ids_2, dev_ch_2, new_dev_2 = [], [], [], [], [], [], [], []

    targeted_compromised = ["C1005", "C1014", "C1022", "C1038", "C1049", "C1055"]

    for i in range(n2):
        s_id = senders_2[i]
        t = times_2[i]
        is_night = (t.hour < 6 or t.hour >= 22)

        # High-Risk Attack 1: Nocturnal Account Takeover
        if s_id in targeted_compromised and is_night and np.random.rand() < 0.75:
            amt = float(np.random.choice([550000.0, 850000.0, 1100000.0, 1450000.0]))
            s_old = amt
            s_new = 0.0 # 100% balance drained
            r_old = float(np.random.randint(0, 3000))
            r_new = r_old + amt
            dev_change = 1
            new_dev = 1
            dev_id = f"ROGUE_DEVICE_{np.random.randint(800, 999)}"
            types_2[i] = "TRANSFER"
            receivers_2[i] = f"MULE_DEST_{np.random.randint(501, 520)}"

        # High-Risk Attack 2: Massive Phishing Spike
        elif np.random.rand() < 0.12:
            amt = float(np.random.choice([600000.0, 920000.0, 1300000.0]))
            s_old = amt + 1500.0
            s_new = 1500.0
            r_old = 500.0
            r_new = 500.0 + amt
            dev_change = 1
            new_dev = 0
            dev_id = f"DEV_CHANGED_{s_id}"
            types_2[i] = "TRANSFER"
            receivers_2[i] = f"PHISHING_REC_{np.random.randint(601, 630)}"

        # Normal transaction
        else:
            amt = float(np.round(np.random.uniform(15000.0, 38000.0), 2))
            s_old = float(np.round(amt + np.random.uniform(10000.0, 30000.0), 2))
            s_new = float(np.round(s_old - amt, 2))
            r_old = float(np.round(np.random.uniform(5000.0, 25000.0), 2))
            r_new = float(np.round(r_old + amt, 2))
            dev_change = 1 if np.random.rand() < 0.02 else 0
            new_dev = 0
            dev_id = f"DEV_{s_id}"

        amounts_2.append(amt)
        s_old_2.append(s_old)
        s_new_2.append(s_new)
        r_old_2.append(r_old)
        r_new_2.append(r_new)
        dev_ids_2.append(dev_id)
        dev_ch_2.append(dev_change)
        new_dev_2.append(new_dev)

    df2 = pd.DataFrame({
        "transaction_id": [f"TXN_SCAM_{i+1:04d}" for i in range(n2)],
        "sender_id": senders_2,
        "receiver_id": receivers_2,
        "amount": amounts_2,
        "transaction_type": types_2,
        "transaction_step": steps_2,
        "sender_old_balance": s_old_2,
        "sender_new_balance": s_new_2,
        "receiver_old_balance": r_old_2,
        "receiver_new_balance": r_new_2,
        "transaction_time": [t.strftime("%Y-%m-%d %H:%M:%S") for t in times_2],
        "device_id": dev_ids_2,
        "device_change_flag": dev_ch_2,
        "new_device_flag": new_dev_2,
    })

    # =========================================================================
    # DATASET 3: MONEY MULE & MULTI-HOP LAYERING RINGS (350 Rows)
    # Features structured layering chains:
    # Victim -> Mule A -> Mule B -> Mule C -> Cashout
    # Fan-in aggregation from multiple victims -> Aggregator Mule -> Dispersal
    # =========================================================================
    n3 = 350
    steps_3 = []
    times_3 = []

    for i in range(n3):
        step = int(np.random.randint(100, 350))
        day = (step // 24) + 1
        hour = int(np.random.choice(range(6, 23)))
        minute = int(np.random.randint(0, 60))
        second = int(np.random.randint(0, 60))
        t = datetime.datetime(2026, 3, min(31, day), hour, minute, second)
        steps_3.append(step)
        times_3.append(t)

    order_3 = np.argsort(times_3)
    steps_3 = [steps_3[i] for i in order_3]
    times_3 = [times_3[i] for i in order_3]

    senders_3 = [f"C{np.random.randint(1001, 1050):04d}" for _ in range(n3)]
    receivers_3 = [f"M{np.random.randint(2001, 2030):04d}" for _ in range(n3)]
    types_3 = [np.random.choice(["PAYMENT", "TRANSFER"], p=[0.60, 0.40]) for _ in range(n3)]

    amounts_3, s_old_3, s_new_3, r_old_3, r_new_3, dev_ids_3, dev_ch_3, new_dev_3 = [], [], [], [], [], [], [], []

    # Insert structured multi-hop chains
    chain_events = [
        # Chain 1: Multi-hop transfer chain (4 hops in rapid succession at step 200)
        ("VIC_USER_1", "MULE_LAYER_1", 750000.0, 200, 0, "TRANSFER"),
        ("MULE_LAYER_1", "MULE_LAYER_2", 745000.0, 200, 5, "TRANSFER"),
        ("MULE_LAYER_2", "MULE_LAYER_3", 740000.0, 201, 12, "TRANSFER"),
        ("MULE_LAYER_3", "CASHOUT_ATM_1", 735000.0, 201, 18, "CASH_OUT"),

        # Chain 2: Fan-in aggregation (3 victims to AGGREGATOR_MULE at step 250)
        ("VIC_USER_2", "MULE_AGGREGATOR", 400000.0, 250, 2, "TRANSFER"),
        ("VIC_USER_3", "MULE_AGGREGATOR", 380000.0, 250, 8, "TRANSFER"),
        ("VIC_USER_4", "MULE_AGGREGATOR", 420000.0, 250, 14, "TRANSFER"),
        ("MULE_AGGREGATOR", "CASHOUT_ATM_2", 600000.0, 251, 3, "CASH_OUT"),
        ("MULE_AGGREGATOR", "CASHOUT_ATM_3", 590000.0, 251, 9, "CASH_OUT"),
    ]

    for i in range(n3):
        amt = float(np.round(np.random.uniform(14000.0, 36000.0), 2))
        s_old = float(np.round(amt + np.random.uniform(8000.0, 28000.0), 2))
        s_new = float(np.round(s_old - amt, 2))
        r_old = float(np.round(np.random.uniform(6000.0, 30000.0), 2))
        r_new = float(np.round(r_old + amt, 2))

        amounts_3.append(amt)
        s_old_3.append(s_old)
        s_new_3.append(s_new)
        r_old_3.append(r_old)
        r_new_3.append(r_new)
        dev_ids_3.append(f"DEV_{senders_3[i]}")
        dev_ch_3.append(0)
        new_dev_3.append(0)

    # Place chain events at specific slots
    slots = [15, 16, 17, 18, 90, 91, 92, 93, 94]
    for idx_slot, (s_m, r_m, amt_m, st_base, min_off, t_type) in zip(slots, chain_events):
        senders_3[idx_slot] = s_m
        receivers_3[idx_slot] = r_m
        amounts_3[idx_slot] = amt_m
        types_3[idx_slot] = t_type
        steps_3[idx_slot] = st_base
        times_3[idx_slot] = datetime.datetime(2026, 3, (st_base // 24) + 1, (st_base % 24), min_off, 0)
        s_old_3[idx_slot] = amt_m + 500.0
        s_new_3[idx_slot] = 500.0
        r_old_3[idx_slot] = 200.0
        r_new_3[idx_slot] = 200.0 + amt_m
        dev_ch_3[idx_slot] = 1
        new_dev_3[idx_slot] = 1
        dev_ids_3[idx_slot] = f"MULE_DEVICE_{idx_slot}"

    # Sort dataset 3 chronologically
    order_3_final = np.argsort(times_3)
    df3 = pd.DataFrame({
        "transaction_id": [f"TXN_MULE_{i+1:04d}" for i in range(n3)],
        "sender_id": [senders_3[i] for i in order_3_final],
        "receiver_id": [receivers_3[i] for i in order_3_final],
        "amount": [amounts_3[i] for i in order_3_final],
        "transaction_type": [types_3[i] for i in order_3_final],
        "transaction_step": [steps_3[i] for i in order_3_final],
        "sender_old_balance": [s_old_3[i] for i in order_3_final],
        "sender_new_balance": [s_new_3[i] for i in order_3_final],
        "receiver_old_balance": [r_old_3[i] for i in order_3_final],
        "receiver_new_balance": [r_new_3[i] for i in order_3_final],
        "transaction_time": [times_3[i].strftime("%Y-%m-%d %H:%M:%S") for i in order_3_final],
        "device_id": [dev_ids_3[i] for i in order_3_final],
        "device_change_flag": [dev_ch_3[i] for i in order_3_final],
        "new_device_flag": [new_dev_3[i] for i in order_3_final],
    })

    datasets = [
        ("dataset_1_normal_baseline.csv", df1, "Clean Normal Retail / P2P Baseline"),
        ("dataset_2_scam_attacks.csv", df2, "High-Risk Fraud & Nocturnal Account Takeovers"),
        ("dataset_3_mule_layering_chains.csv", df3, "Organized Money Mule Layering Chains & Dispersal"),
    ]

    for filename, df_out, desc in datasets:
        # Save in both directories
        df_out.to_csv(os.path.join("fraud_detection_app", filename), index=False)
        df_out.to_csv(filename, index=False)
        print(f"✓ Saved {filename} ({len(df_out)} transactions) — {desc}")


if __name__ == "__main__":
    generate_curated_datasets()
