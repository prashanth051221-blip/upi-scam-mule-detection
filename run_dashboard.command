#!/bin/bash
# Double-click to start the UPI Scam & Mule Detection website at http://127.0.0.1:8000
cd "$(dirname "$0")"
exec > >(tee dashboard_log.txt) 2>&1
echo "Folder: $(pwd)"
source .venv/bin/activate || { echo "Could not activate .venv"; read -p "Press Enter to close"; exit 1; }
echo "Python: $(python --version)"
echo "Checking packages..."
pip install -q -r requirements.txt || echo "pip install had a problem (see above)"
echo
echo "Website: http://127.0.0.1:8000   (keep this window open; close it to stop)"
( sleep 3; open "http://127.0.0.1:8000" ) &
python web/manage.py runserver 127.0.0.1:8000
echo "Website stopped."
read -p "Press Enter to close"
