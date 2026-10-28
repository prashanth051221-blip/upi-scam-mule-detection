"""
UPI transaction simulator with labelled scams and money-mule rings.

Why this exists
---------------
The first model in this project was trained on PaySim-style data, where almost
every sender appears only once. Velocity, device and chain features were
therefore always zero in training, and the model learned to ignore them.
This simulator produces UPI-style data where those signals actually vary, and
where every fraudulent transaction carries a ground-truth label, so the system
can be measured (precision, recall, PR-AUC) instead of only "run".

What it models
--------------
Normal behaviour (label 0)
  * customers with personal VPAs, their own spending level, active hours,
    contacts and favourite merchants; P2P and P2M (QR / intent) payments
  * monthly salary credits (outside UPI) and rent payments
  * hard negatives that LOOK suspicious but are legitimate:
      - night owls who regularly pay at night
      - genuine phone changes (new device + ₹5,000 first-24h cap)
      - people who alternate between two devices
      - "family forwarders" who receive money and pass part of it on (A→B→C)
      - informal sellers (tutors, home businesses) who receive from many payers
      - occasional large payments (rent, insurance, education)
Fraud (label 1), each tagged with `fraud_type`
  * qr_scam                - victim scans a "receive money" QR and actually pays
  * fake_refund_call       - fake customer-care call, escalating payments
  * screen_share           - remote-access app; rapid balance drain, SAME device
  * sim_swap               - fraudster registers UPI on a new device at night,
                             is held to the ₹5,000 first-24h cap, then drains
  * fake_merchant_collect  - victim approves a collect request from a fraudulent
                             merchant VPA (P2P collect was discontinued by NPCI
                             from 1 Oct 2025, so this uses merchant collect)
  * mule_layering          - stolen money forwarded through 2-4 mule accounts,
                             usually within minutes, sometimes after hours

UPI rules applied (assumptions; see README for sources)
  * ₹1,00,000 per transaction and per rolling 24h for normal payments
  * up to ₹5,00,000 per transaction for high-value merchant categories
  * max 20 payments per rolling 24h
  * ₹5,000 total in the first 24h after a new UPI registration / device change

Account IDs carry no hint of the label: mules use the same VPA format as
customers, fake merchants the same format as real merchants.

Fraud is deliberately over-represented (~1-3% of transactions) so the models
see enough positives. Real-world UPI fraud rates are far lower; precision
figures should be read with that in mind.
"""

from __future__ import annotations

import argparse
import heapq
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# UPI limits (assumptions documented in README)
# ----------------------------------------------------------------------------
TXN_CAP = 100_000
DAILY_CAP = 100_000
HIGH_VALUE_TXN_CAP = 500_000
DAILY_COUNT_CAP = 20
NEW_REG_CAP_24H = 5_000
DAY = 86_400
HOUR = 3_600
MIN = 60

SCAM_TYPES = ["qr_scam", "fake_refund_call", "screen_share", "sim_swap", "fake_merchant_collect"]
FRAUD_TYPES = SCAM_TYPES + ["mule_layering"]

BANK_HANDLES = ["oksbi", "okaxis", "okhdfcbank", "okicici", "ybl", "paytm", "ibl", "axl"]
FIRST_NAMES = [
    "aarav", "ananya", "rohan", "priya", "vikram", "sneha", "arjun", "kavya", "rahul", "pooja",
    "aditya", "neha", "karan", "isha", "siddharth", "meera", "varun", "riya", "nikhil", "divya",
    "amit", "shreya", "manish", "tanvi", "suresh", "lakshmi", "deepak", "aishwarya", "harsh", "nisha",
    "gaurav", "simran", "yash", "anjali", "kunal", "swati", "rajesh", "pallavi", "ankit", "bhavna",
]
MERCHANT_CATEGORIES = ["grocery", "food", "fuel", "pharmacy", "ecommerce", "utility", "telecom", "transport"]


@dataclass
class SimConfig:
    n_customers: int = 4000
    n_merchants: int = 250
    n_high_value_merchants: int = 10
    days: int = 30
    start: str = "2026-03-01"
    seed: int = 7
    scam_events_per_day: float = 12.0
    fraud_start_day: float = 2.0
    n_rings: int = 10
    min_layers: int = 1          # intermediate mule layers between collectors and cash-out
    max_layers: int = 2
    scam_mix: Dict[str, float] = field(default_factory=lambda: {
        "qr_scam": 0.20, "fake_refund_call": 0.20, "screen_share": 0.20,
        "sim_swap": 0.15, "fake_merchant_collect": 0.25,
    })
    fraud_enabled: bool = True
    # rings that start late (only appear in the last part of the period)
    late_ring_share: float = 0.3


class Account:
    __slots__ = (
        "id", "kind", "balance", "device", "used_devices", "last_txn_device", "alt_device",
        "reg_time", "sent_since_reg", "sent_window", "rate", "hour_mu", "hour_sd", "amt_scale",
        "p2m_share", "contacts", "fav_merchants", "is_forwarder", "is_seller", "is_mule",
        "ring", "layer", "mule_fast", "pending_forward", "paused_until", "salary", "victim_until",
        "merchant_cat", "dirty",
    )

    def __init__(self, acct_id: str, kind: str):
        self.id = acct_id
        self.kind = kind            # customer | merchant | mule | fake_merchant
        self.balance = 0.0
        self.device = None
        self.used_devices = set()
        self.last_txn_device = None
        self.alt_device = None
        self.reg_time = -1e18
        self.sent_since_reg = 0.0
        self.sent_window = deque()  # (t, amount, counts_to_daily_cap)
        self.rate = 0.0
        self.hour_mu = 14.0
        self.hour_sd = 3.0
        self.amt_scale = 1.0
        self.p2m_share = 0.7
        self.contacts: List[str] = []
        self.fav_merchants: List[str] = []
        self.is_forwarder = False
        self.is_seller = False
        self.is_mule = False
        self.ring = -1
        self.layer = -1
        self.mule_fast = True
        self.pending_forward = False
        self.paused_until = -1.0
        self.salary = 0.0
        self.victim_until = -1.0
        self.merchant_cat = ""
        self.dirty = 0.0            # stolen money held by a mule, not yet passed on


class UPISimulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.t0 = pd.Timestamp(cfg.start)
        self.horizon = cfg.days * DAY
        self.accounts: Dict[str, Account] = {}
        self.events: list = []
        self.seq = 0
        self.rows: list = []
        self.txn_counter = 0
        self.used_ids: set = set()
        self.customers: List[str] = []
        self.merchants: List[str] = []
        self.merchant_weights: np.ndarray = np.array([])
        self.high_value_merchants: List[str] = []
        self.sellers: List[str] = []
        self.rings: List[dict] = []
        self.event_counter = 0

    # ------------------------------------------------------------------
    # ID generation (no label leakage)
    # ------------------------------------------------------------------
    def _person_vpa(self) -> str:
        while True:
            name = self.rng.choice(FIRST_NAMES)
            vpa = f"{name}{self.rng.integers(10, 99999)}@{self.rng.choice(BANK_HANDLES)}"
            if vpa not in self.used_ids:
                self.used_ids.add(vpa)
                return vpa

    def _merchant_vpa(self) -> str:
        while True:
            vpa = f"q{self.rng.integers(100_000_000, 999_999_999)}@{self.rng.choice(['ybl', 'paytm', 'axl', 'ibl'])}"
            if vpa not in self.used_ids:
                self.used_ids.add(vpa)
                return vpa

    def _device(self) -> str:
        return "DEV_" + "".join(self.rng.choice(list("0123456789ABCDEF"), 10))

    def _push(self, t: float, kind: str, data: dict) -> None:
        if t < self.horizon:
            self.seq += 1
            heapq.heappush(self.events, (t, self.seq, kind, data))

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def _build_population(self) -> None:
        cfg, rng = self.cfg, self.rng
        # merchants
        for i in range(cfg.n_merchants):
            m = Account(self._merchant_vpa(), "merchant")
            m.balance = float(rng.lognormal(np.log(80_000), 1.0))
            m.merchant_cat = "high_value" if i < cfg.n_high_value_merchants else rng.choice(MERCHANT_CATEGORIES)
            self.accounts[m.id] = m
            if m.merchant_cat == "high_value":
                self.high_value_merchants.append(m.id)
            else:
                self.merchants.append(m.id)
        w = rng.zipf(1.6, len(self.merchants)).astype(float)
        self.merchant_weights = w / w.sum()

        # customers
        for _ in range(cfg.n_customers):
            c = Account(self._person_vpa(), "customer")
            c.salary = float(np.clip(rng.lognormal(np.log(35_000), 0.6), 8_000, 600_000))
            c.balance = float(np.clip(rng.lognormal(np.log(25_000), 1.0), 300, 2_000_000))
            c.device = self._device()
            c.rate = float(np.clip(rng.lognormal(np.log(0.9), 0.6), 0.1, 8.0))
            if rng.random() < 0.06:          # night owls (legit night activity)
                c.hour_mu, c.hour_sd = float(rng.uniform(22.5, 25.5)), 1.5
            else:
                c.hour_mu, c.hour_sd = float(rng.normal(14.5, 2.5)), float(rng.uniform(2.0, 4.0))
            c.amt_scale = float(np.clip(rng.lognormal(0.0, 0.5), 0.2, 6.0))
            c.p2m_share = float(rng.uniform(0.5, 0.85))
            c.is_forwarder = rng.random() < 0.05
            c.is_seller = rng.random() < 0.02
            if rng.random() < 0.03:          # alternates between two devices
                c.alt_device = self._device()
            self.accounts[c.id] = c
            self.customers.append(c.id)
            if c.is_seller:
                self.sellers.append(c.id)

        cust = np.array(self.customers)
        for cid in self.customers:
            c = self.accounts[cid]
            k = int(rng.integers(3, 15))
            c.contacts = list(rng.choice(cust, size=k, replace=False))
            if self.sellers and rng.random() < 0.3:
                c.contacts.append(str(rng.choice(self.sellers)))
            km = int(rng.integers(5, 20))
            c.fav_merchants = list(rng.choice(self.merchants, size=km, replace=False, p=self.merchant_weights))

    # ------------------------------------------------------------------
    # Mule rings
    # ------------------------------------------------------------------
    def _new_mule(self, ring: int, layer: int, recruited_pool: Optional[List[str]] = None,
                  as_merchant: bool = False) -> str:
        rng = self.rng
        if recruited_pool is not None and not as_merchant and rng.random() < 0.4 and recruited_pool:
            acct = self.accounts[recruited_pool.pop()]      # recruited real customer
        else:
            acct = Account(self._merchant_vpa() if as_merchant else self._person_vpa(),
                           "fake_merchant" if as_merchant else "mule")
            acct.balance = float(rng.uniform(0, 2_000))
            acct.device = self._device()
            acct.rate = float(rng.uniform(0.1, 0.5))       # small camouflage spending
            acct.hour_mu, acct.hour_sd = float(rng.normal(15, 3)), 3.0
            acct.amt_scale = float(rng.uniform(0.3, 1.0))
            acct.p2m_share = 0.9
            acct.fav_merchants = list(rng.choice(self.merchants, size=5, replace=False, p=self.merchant_weights))
            self.accounts[acct.id] = acct
        acct.is_mule = True
        acct.ring = ring
        acct.layer = layer
        acct.mule_fast = rng.random() < 0.7
        return acct.id

    def _build_rings(self) -> None:
        cfg, rng = self.cfg, self.rng
        if not cfg.fraud_enabled:
            return
        pool = list(rng.choice(self.customers, size=min(len(self.customers) // 20, 400), replace=False))
        span = cfg.days - cfg.fraud_start_day
        n_late = int(round(cfg.n_rings * cfg.late_ring_share))
        for k in range(cfg.n_rings):
            if k < n_late:   # rings that only appear near the end (unseen in training)
                start = cfg.fraud_start_day + span * rng.uniform(0.72, 0.8)
                end = cfg.days
            else:
                start = cfg.fraud_start_day + span * rng.uniform(0.0, 0.5)
                end = min(cfg.days, start + rng.uniform(0.35, 0.75) * span)
            n_layers = int(rng.integers(cfg.min_layers, cfg.max_layers + 1))
            ring = {
                "id": k, "start": start * DAY, "end": end * DAY,
                "collectors": [self._new_mule(k, 0, pool) for _ in range(int(rng.integers(4, 9)))],
                "fake_merchants": [self._new_mule(k, 0, as_merchant=True) for _ in range(int(rng.integers(1, 3)))],
                "layers": [[self._new_mule(k, j + 1) for _ in range(int(rng.integers(2, 4)))]
                           for j in range(n_layers)],
                "cashout": [self._new_mule(k, n_layers + 1) for _ in range(int(rng.integers(1, 3)))],
            }
            self.rings.append(ring)
            # camouflage spending for new mule accounts during the ring's life
            for mid in ring["collectors"] + sum(ring["layers"], []) + ring["cashout"]:
                m = self.accounts[mid]
                if m.kind == "mule":
                    self._schedule_normal(m, start * DAY, end * DAY)

    def _next_hop_accounts(self, mule: Account) -> List[str]:
        ring = self.rings[mule.ring]
        if mule.layer == 0:
            nxt = ring["layers"][0] if ring["layers"] else ring["cashout"]
        elif mule.layer <= len(ring["layers"]) - 1:
            nxt = ring["layers"][mule.layer]
        elif mule.layer == len(ring["layers"]):
            nxt = ring["cashout"]
        else:
            return []
        k = 1 if self.rng.random() < 0.6 else 2
        return list(self.rng.choice(nxt, size=min(k, len(nxt)), replace=False))

    # ------------------------------------------------------------------
    # Scheduling of normal activity
    # ------------------------------------------------------------------
    def _sample_time_of_day(self, acct: Account) -> float:
        h = self.rng.normal(acct.hour_mu, acct.hour_sd)
        if acct.hour_mu < 20:
            h = float(np.clip(h, 5.5, 23.9))
        return (h % 24.0) * HOUR

    def _schedule_normal(self, acct: Account, t_from: float, t_to: float) -> None:
        rng = self.rng
        d0, d1 = int(t_from // DAY), int(np.ceil(t_to / DAY))
        for d in range(d0, d1):
            n = rng.poisson(acct.rate)
            for _ in range(n):
                t = d * DAY + self._sample_time_of_day(acct) + rng.uniform(0, 60)
                if t_from <= t < t_to:
                    self._push(t, "normal", {"acct": acct.id})

    def _schedule_population(self) -> None:
        cfg, rng = self.cfg, self.rng
        for cid in self.customers:
            c = self.accounts[cid]
            self._schedule_normal(c, 0, self.horizon)
            # salary (outside UPI) on day 1-5, and again after 30 days if the sim is longer
            for month_start in range(0, cfg.days, 30):
                sd = month_start + int(rng.integers(0, 5))
                self._push(sd * DAY + 9 * HOUR + rng.uniform(0, HOUR), "salary", {"acct": cid})
            if rng.random() < 0.3:      # pays rent to a landlord (another customer)
                landlord = str(rng.choice(self.customers))
                rent = float(round(rng.uniform(6_000, 40_000), -2))
                for month_start in range(0, cfg.days, 30):
                    rd = month_start + int(rng.integers(1, 6))
                    self._push(rd * DAY + rng.uniform(9, 21) * HOUR, "rent",
                               {"acct": cid, "to": landlord, "amount": rent})
            if rng.random() < 0.04:     # genuine phone change
                self._push(rng.uniform(1, cfg.days - 0.5) * DAY, "device_change", {"acct": cid})

    def _schedule_scams(self) -> None:
        cfg, rng = self.cfg, self.rng
        if not cfg.fraud_enabled:
            return
        types = list(cfg.scam_mix.keys())
        probs = np.array([cfg.scam_mix[k] for k in types], dtype=float)
        probs /= probs.sum()
        d_start = int(np.floor(cfg.fraud_start_day))
        for d in range(d_start, cfg.days):
            for _ in range(rng.poisson(cfg.scam_events_per_day)):
                stype = str(rng.choice(types, p=probs))
                if stype == "sim_swap":
                    hr = rng.choice([rng.uniform(22, 24), rng.uniform(0, 5)]) if rng.random() < 0.75 else rng.uniform(5, 22)
                else:
                    hr = rng.uniform(9, 21.5)
                t = d * DAY + hr * HOUR
                if t >= cfg.fraud_start_day * DAY:
                    self._push(t, "scam", {"type": stype})

    # ------------------------------------------------------------------
    # Limits and recording
    # ------------------------------------------------------------------
    def _allowed(self, acct: Account, t: float, high_value: bool = False) -> float:
        """Max amount `acct` may send now under balance + UPI limits."""
        while acct.sent_window and t - acct.sent_window[0][0] > DAY:
            acct.sent_window.popleft()
        if len(acct.sent_window) >= DAILY_COUNT_CAP:
            return 0.0
        cap = HIGH_VALUE_TXN_CAP if high_value else TXN_CAP
        if not high_value:
            used = sum(a for (_, a, counts) in acct.sent_window if counts)
            cap = min(cap, DAILY_CAP - used)
        if t - acct.reg_time < DAY:
            cap = min(cap, NEW_REG_CAP_24H - acct.sent_since_reg)
        return max(0.0, min(cap, acct.balance))

    def _record(self, t: float, s_id: str, r_id: str, amount: float, ttype: str,
                label: int = 0, ftype: str = "", ring: int = -1, event: int = -1,
                high_value: bool = False) -> Optional[float]:
        s, r = self.accounts[s_id], self.accounts[r_id]
        if s_id == r_id:
            return None
        amount = float(round(amount, 2))
        if amount < 1.0 or amount > self._allowed(s, t, high_value) + 1e-6:
            return None
        device = s.device
        if s.alt_device is not None and self.rng.random() < 0.3:
            device = s.alt_device
        dev_change = int(s.last_txn_device is not None and device != s.last_txn_device)
        new_dev = int(len(s.used_devices) > 0 and device not in s.used_devices)
        s.used_devices.add(device)
        s.last_txn_device = device

        s_old, r_old = s.balance, r.balance
        s.balance -= amount
        r.balance += amount
        s.sent_window.append((t, amount, not high_value))
        if t - s.reg_time < DAY:
            s.sent_since_reg += amount
        self.txn_counter += 1
        ts = self.t0 + pd.Timedelta(seconds=float(t))
        self.rows.append((
            f"UPI{self.txn_counter:08d}", s_id, r_id, amount, ttype, int(t // HOUR) + 1,
            round(s_old, 2), round(s.balance, 2), round(r_old, 2), round(r.balance, 2),
            ts.strftime("%Y-%m-%d %H:%M:%S"), device, dev_change, new_dev,
            label, ftype, ring, event,
        ))
        self._after_credit(t, r, amount, label)
        return amount

    def _after_credit(self, t: float, r: Account, amount: float, label: int) -> None:
        rng = self.rng
        if r.is_mule and label == 1:
            r.dirty += amount
        if r.is_mule and label == 1 and not r.pending_forward and self.rings:
            ring = self.rings[r.ring]
            if r.layer > len(ring["layers"]):          # cash-out account
                self._push(t + rng.uniform(1, 12) * HOUR, "cashout", {"acct": r.id})
            else:
                delay = rng.uniform(2, 30) * MIN if r.mule_fast else rng.uniform(1, 8) * HOUR
                r.pending_forward = True
                self._push(t + delay, "mule_forward", {"acct": r.id})
        elif r.kind == "customer" and r.is_forwarder and label == 0 and rng.random() < 0.4:
            self._push(t + rng.uniform(5, 120) * MIN, "family_forward",
                       {"acct": r.id, "amount": amount * rng.uniform(0.3, 0.9)})

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _normal_payment(self, t: float, acct: Account) -> None:
        rng = self.rng
        if t < acct.paused_until:
            return
        if rng.random() < acct.p2m_share or not acct.contacts:
            if acct.kind == "customer" and rng.random() < 0.005 and self.high_value_merchants:
                to = str(rng.choice(self.high_value_merchants))
                amt = float(np.clip(rng.lognormal(np.log(25_000), 0.8), 2_000, 250_000))
                self._record(t, acct.id, to, round(amt, -2), "P2M", high_value=True)
                return
            if rng.random() < 0.1 or not acct.fav_merchants:
                to = str(rng.choice(self.merchants, p=self.merchant_weights))
            else:
                to = str(rng.choice(acct.fav_merchants))
            amt = rng.lognormal(np.log(300 * acct.amt_scale), 0.9)
            ttype = "P2M_COLLECT" if (self.accounts[to].merchant_cat in ("ecommerce", "utility") and rng.random() < 0.15) else "P2M"
        else:
            if rng.random() < 0.08:
                to = str(rng.choice(self.sellers)) if (self.sellers and rng.random() < 0.4) else str(rng.choice(self.customers))
            else:
                to = str(rng.choice(acct.contacts))
            amt = rng.lognormal(np.log(1_500 * acct.amt_scale), 1.0)
            if rng.random() < 0.5:
                amt = max(100.0, round(amt, -2))
            ttype = "P2P"
        amt = float(min(amt, 0.9 * acct.balance))
        if amt >= 1:
            self._record(t, acct.id, to, amt, ttype)

    def _mule_forward(self, t: float, m: Account) -> None:
        rng = self.rng
        m.pending_forward = False
        dirty = min(m.dirty, m.balance)
        if dirty < 1_000:
            return
        targets = self._next_hop_accounts(m)
        if not targets:
            return
        total = dirty * rng.uniform(0.85, 0.98)
        allowed = self._allowed(m, t)
        send = min(total, allowed)
        if send < 500:
            # blocked by daily cap: try again later
            m.pending_forward = True
            self._push(t + DAY + rng.uniform(0, 3) * HOUR, "mule_forward", {"acct": m.id})
            return
        shares = rng.dirichlet(np.ones(len(targets))) if len(targets) > 1 else np.array([1.0])
        tt = t
        for tgt, sh in zip(targets, shares):
            amt = send * sh
            if amt >= 100 and self._record(tt, m.id, tgt, amt, "P2P", 1, "mule_layering", m.ring) is not None:
                m.dirty = max(0.0, m.dirty - amt)
            tt += rng.uniform(0.3, 4) * MIN
        if total - send > 2_000:
            m.pending_forward = True
            self._push(t + DAY + rng.uniform(0, 3) * HOUR, "mule_forward", {"acct": m.id})

    def _pick_victim(self, t: float, min_balance: float) -> Optional[Account]:
        for _ in range(30):
            v = self.accounts[str(self.rng.choice(self.customers))]
            if (not v.is_mule) and v.balance >= min_balance and t > v.victim_until and t >= v.paused_until:
                return v
        return None

    def _active_ring(self, t: float) -> Optional[dict]:
        active = [r for r in self.rings if r["start"] <= t < r["end"]]
        if not active:
            return None
        return active[int(self.rng.integers(len(active)))]

    def _scam(self, t: float, stype: str) -> None:
        rng = self.rng
        ring = self._active_ring(t)
        if ring is None:
            return
        self.event_counter += 1
        ev = self.event_counter
        rid = ring["id"]
        if stype == "qr_scam":
            v = self._pick_victim(t, 3_000)
            if v is None:
                return
            mule = str(rng.choice(ring["collectors"]))
            base = float(round(rng.uniform(1_000, 25_000), -2))
            tt = t
            for _ in range(int(rng.integers(1, 4))):
                amt = min(base, self._allowed(v, tt))
                if amt < 500 or self._record(tt, v.id, mule, amt, "P2P", 1, stype, rid, ev) is None:
                    break
                tt += rng.uniform(2, 20) * MIN
        elif stype == "fake_refund_call":
            v = self._pick_victim(t, 5_000)
            if v is None:
                return
            mule = str(rng.choice(ring["collectors"]))
            amt = float(round(rng.uniform(2_000, 10_000), -2))
            tt = t
            for _ in range(int(rng.integers(2, 6))):
                a = min(amt, self._allowed(v, tt))
                if a < 500 or self._record(tt, v.id, mule, a, "P2P", 1, stype, rid, ev) is None:
                    break
                amt = round(amt * rng.uniform(1.5, 2.5), -2)
                tt += rng.uniform(3, 15) * MIN
        elif stype == "screen_share":
            v = self._pick_victim(t, 8_000)
            if v is None:
                return
            mules = list(rng.choice(ring["collectors"], size=min(2, len(ring["collectors"])), replace=False))
            target = v.balance * rng.uniform(0.6, 1.0)
            n = int(rng.integers(2, 6))
            tt = t
            for i in range(n):
                a = min(target / n * rng.uniform(0.7, 1.3), self._allowed(v, tt))
                if a < 500:
                    break
                self._record(tt, v.id, str(mules[i % len(mules)]), round(a, -1), "P2P", 1, stype, rid, ev)
                tt += rng.uniform(1, 4) * MIN
        elif stype == "sim_swap":
            v = self._pick_victim(t, 10_000)
            if v is None:
                return
            # fraudster registers UPI on a new device -> ₹5,000 cap for 24h
            v.device = self._device()
            v.reg_time, v.sent_since_reg = t, 0.0
            v.paused_until = t + 3 * DAY          # real owner has lost the SIM
            mules = list(rng.choice(ring["collectors"], size=min(2, len(ring["collectors"])), replace=False))
            tt = t + rng.uniform(5, 30) * MIN
            for _ in range(int(rng.integers(1, 3))):
                a = min(float(rng.choice([4_999, 4_900, 2_500, 2_000, 3_000])), self._allowed(v, tt))
                if a < 500:
                    break
                self._record(tt, v.id, str(rng.choice(mules)), a, "P2P", 1, stype, rid, ev)
                tt += rng.uniform(1, 10) * MIN
            # after the cooling period, drain
            tt = t + DAY + rng.uniform(0.1, 6) * HOUR
            for _ in range(int(rng.integers(1, 4))):
                a = min(v.balance * rng.uniform(0.4, 0.95), self._allowed(v, tt))
                if a < 500:
                    break
                self._push(tt, "scam_payment", {"from": v.id, "to": str(rng.choice(mules)),
                                                "amount": round(a, -2), "type": stype, "ring": rid, "event": ev})
                tt += rng.uniform(2, 15) * MIN
            # owner re-registers on a fresh device later (legit device change)
            self._push(t + 3 * DAY + rng.uniform(0, 12) * HOUR, "device_change", {"acct": v.id})
        elif stype == "fake_merchant_collect":
            v = self._pick_victim(t, 2_000)
            if v is None:
                return
            fm = str(rng.choice(ring["fake_merchants"]))
            tt = t
            for _ in range(int(rng.integers(1, 3))):
                a = min(float(round(rng.uniform(999, 15_000), -1)), self._allowed(v, tt))
                if a < 300 or self._record(tt, v.id, fm, a, "P2M_COLLECT", 1, stype, rid, ev) is None:
                    break
                tt += rng.uniform(2, 30) * MIN
        # a victim is not targeted again for a week
        v.victim_until = t + 7 * DAY

    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        self._build_population()
        self._build_rings()
        self._schedule_population()
        self._schedule_scams()
        rng = self.rng
        while self.events:
            t, _, kind, data = heapq.heappop(self.events)
            if kind == "normal":
                self._normal_payment(t, self.accounts[data["acct"]])
            elif kind == "salary":
                a = self.accounts[data["acct"]]
                a.balance += a.salary
            elif kind == "rent":
                a = self.accounts[data["acct"]]
                if t >= a.paused_until:
                    self._record(t, a.id, data["to"], data["amount"], "P2P")
            elif kind == "device_change":
                a = self.accounts[data["acct"]]
                a.device = self._device()
                a.reg_time, a.sent_since_reg = t, 0.0
            elif kind == "family_forward":
                a = self.accounts[data["acct"]]
                if a.contacts and t >= a.paused_until:
                    amt = min(data["amount"], 0.9 * a.balance)
                    if amt >= 100:
                        self._record(t, a.id, str(rng.choice(a.contacts)), round(amt, -1), "P2P")
            elif kind == "mule_forward":
                self._mule_forward(t, self.accounts[data["acct"]])
            elif kind == "cashout":
                a = self.accounts[data["acct"]]
                taken = min(a.dirty, a.balance) * rng.uniform(0.9, 1.0)   # ATM / cash, outside UPI
                a.balance -= taken
                a.dirty = 0.0
            elif kind == "scam":
                self._scam(t, data["type"])
            elif kind == "scam_payment":
                self._record(t, data["from"], data["to"], data["amount"], "P2P", 1,
                             data["type"], data["ring"], data["event"])

        cols = REQUIRED_OUT + ["is_fraud", "fraud_type", "fraud_ring", "scam_event"]
        df = pd.DataFrame(self.rows, columns=cols)
        return df.sort_values(["transaction_time", "transaction_id"]).reset_index(drop=True)


REQUIRED_OUT = [
    "transaction_id", "sender_id", "receiver_id", "amount", "transaction_type", "transaction_step",
    "sender_old_balance", "sender_new_balance", "receiver_old_balance", "receiver_new_balance",
    "transaction_time", "device_id", "device_change_flag", "new_device_flag",
]


def simulate(**kwargs) -> pd.DataFrame:
    return UPISimulator(SimConfig(**kwargs)).run()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a labelled UPI transaction dataset")
    ap.add_argument("--customers", type=int, default=4000)
    ap.add_argument("--merchants", type=int, default=250)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="data/upi_sim_train.csv.gz")
    a = ap.parse_args()
    data = simulate(n_customers=a.customers, n_merchants=a.merchants, days=a.days, seed=a.seed)
    data.to_csv(a.out, index=False)
    print(f"{len(data):,} transactions, fraud rate {data.is_fraud.mean():.2%} -> {a.out}")
    print(data.fraud_type.value_counts())
