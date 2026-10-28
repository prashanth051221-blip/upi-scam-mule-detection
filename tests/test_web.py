"""
Smoke test for the Django website: every page loads for every demo dataset,
uploads are validated, and exports work.

Run from the project folder:
    python tests/test_web.py
"""

from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upi_site.settings")

import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402

settings.ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_pages():
    for slug in ("normal", "scams", "rings"):
        c = Client()
        r = c.get(f"/demo/{slug}/", follow=True)
        check(r.status_code == 200, f"{slug}: overview {r.status_code}")
        for url in ("/alerts/", "/alerts/?view=scored&sort=amount&page=2", "/alerts/?level=High",
                    "/rings/", "/evidence/", "/export/alerts.csv"):
            r = c.get(url)
            check(r.status_code == 200, f"{slug}: {url} -> {r.status_code}")
        html = c.get("/alerts/?view=scored").content.decode()
        tx = re.search(r'/payment/(UPI\d+)/', html)
        check(tx is not None, f"{slug}: no payment link in alert queue")
        r = c.get(f"/payment/{tx.group(1)}/")
        check(r.status_code == 200, f"{slug}: payment page {r.status_code}")
        if slug != "normal":
            check(c.get("/rings/0/").status_code == 200, f"{slug}: ring 0 page")
        else:
            check("No mule rings" in c.get("/rings/").content.decode(), "normal data should show no rings")


def test_settings_change_threshold():
    c = Client()
    c.get("/demo/scams/")
    before = c.get("/overview/").content.decode()
    c.post("/settings/", {"mode": "capacity", "capacity": "1", "next": "/overview/"})
    after = c.get("/overview/").content.decode()
    check("Top 1% of payments" in after and before != after, "capacity rule not applied")


def test_upload_validation():
    c = Client()
    bad = io.BytesIO(b"a,b\n1,2\n")
    bad.name = "bad.csv"
    r = c.post("/", {"csv": bad}, follow=True)
    check("Missing required column" in r.content.decode(), "bad upload not rejected with a clear message")
    good_path = ROOT / "fraud_detection_app" / "dataset_1_normal_baseline.csv"
    with open(good_path, "rb") as f:
        r = c.post("/", {"csv": f}, follow=True)
    check(r.status_code == 200 and "Payments scored" in r.content.decode(), "good upload failed")


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} web tests passed")
    sys.exit(1 if failed else 0)
