#!/bin/bash
# Run Blackjack Statistics Dashboard (Streamlit)

cd "$(dirname "$0")/../../.."
echo "📊 Starting Blackjack Statistics Dashboard..."
streamlit run dashboard/app.py
