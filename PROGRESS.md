# Progress log

Kept up to date so the work can be resumed from here if a session ends.

## Done
- Labelled UPI simulator, new feature engine, retrained hybrid model, comparison, ablation, unseen-scam test, NetworkX rings, thresholds, reason codes, real-time scoring (~1 ms), 11 tests. Results in RESULTS.md.
- Streamlit dashboard (fraud_detection_app/app.py), still working.
- Django website in `web/` (replaces Streamlit as the main UI):
  - `web/upi_site/` settings (no database; signed-cookie sessions), `web/dashboard/` app
  - `services.py` reuses scoring.py / explain.py / mule_rings.py (no duplicate model logic)
  - Pages: start, overview, alerts, payment detail, mule rings (vis-network graph), evidence
  - Static: css/app.css (design tokens, dark mode, responsive), js/charts.js, js/ring.js,
    vendor Chart.js 4.4.4 + vis-network 9.1.9, Public Sans + IBM Plex Mono fonts (offline)

## Status (27 Oct 2026)
All items finished: phone-width fix, ring-graph spacing, 11/11 model tests and 3/3 website tests passing, launcher and requirements updated, README section added, files copied and verified.

## Open items (for later)
- Write the paper from RESULTS.md
- Rewrite the status report and deck to describe the new system (only references and wording were fixed)
- Optional: run Isolation Forest as a separate safety net to keep its strength on unseen SIM swaps

## How to run the website
```bash
cd ~/Documents/Pbl.2 && source .venv/bin/activate
pip install -r requirements.txt
python web/manage.py runserver 8000      # open http://127.0.0.1:8000
```
