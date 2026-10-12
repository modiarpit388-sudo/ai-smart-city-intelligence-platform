#!/usr/bin/env bash
# One-command start for Linux / macOS:  ./start.sh
set -e
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  echo "▶ Creating Python virtual environment ..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
if [ ! -f static/index.html ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "▶ Building the React frontend ..."
    (cd ../frontend && npm install --no-audit --no-fund && npm run build)
  else
    echo "⚠ frontend build not found and npm is missing – the API will run without the UI."
  fi
fi
python run.py
