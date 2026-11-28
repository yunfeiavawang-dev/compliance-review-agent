#!/bin/bash
# One-click demo launcher: kills stale Streamlit processes, starts fresh on port 8501.
set -e

cd "$(dirname "$0")/.."

echo "Stopping existing Streamlit processes..."
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

echo "Starting KYC Compliance Review Agent on http://localhost:8501"
streamlit run app.py --server.headless true --server.port 8501
