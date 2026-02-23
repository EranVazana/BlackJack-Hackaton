#!/bin/bash
# Run Blackjack UI Client (Streamlit)

cd "$(dirname "$0")/../../.."
echo "🎮 Starting Blackjack UI Client..."
streamlit run client/ui.py
